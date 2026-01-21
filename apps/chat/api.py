"""
Chat API endpoints - converted from chat.controller.ts and conversation.controller.ts
"""

import json
import httpx
from django.conf import settings
from django.http import HttpRequest, StreamingHttpResponse
from ninja import Router
from ninja.errors import HttpError

from utils.auth import AuthBearer, get_current_user
from .models import ChatConversation, ChatMessage, MessageRole
from .schemas import (
    ConversationOut,
    ConversationDetailOut,
    CreateConversationIn,
    UpdateConversationIn,
    ChatIn,
    ChatOut,
    ChatMessageOut,
    ChatUsageOut,
)

router = Router(auth=AuthBearer())

# KIE API configuration
KIE_API_URL = "https://api.kie.ai/gemini-3-pro/v1/chat/completions"


def build_kie_messages(messages: list, system_prompt: str | None, image_url: str | None):
    """Build messages array for KIE API format."""
    api_messages = []

    # Add system prompt if provided
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})

    # Add conversation messages
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else msg.get("content", "")
        role = msg.role if hasattr(msg, "role") else msg.get("role", "user")

        # If last user message and has image, format with image
        if role == "user" and image_url and msg == messages[-1]:
            api_messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": content},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            })
        else:
            api_messages.append({"role": role, "content": content})

    return api_messages


# ============ Conversation endpoints ============


@router.get("/conversations", response=list[ConversationOut])
def list_conversations(request: HttpRequest, limit: int = 50, offset: int = 0):
    """List user's conversations."""
    user = get_current_user(request)
    conversations = ChatConversation.objects.filter(user=user).order_by("-updated_at")[
        offset : offset + limit
    ]
    return [ConversationOut.from_orm(c) for c in conversations]


@router.post("/conversations", response=ConversationOut)
def create_conversation(request: HttpRequest, data: CreateConversationIn):
    """Create a new conversation."""
    user = get_current_user(request)

    conversation = ChatConversation.objects.create(
        user=user,
        title=data.title or "Cuộc trò chuyện mới",
        agent_id=data.agentId,
    )

    return ConversationOut.from_orm(conversation)


@router.get("/conversations/{conversation_id}", response=ConversationDetailOut)
def get_conversation(request: HttpRequest, conversation_id: str):
    """Get conversation with messages."""
    user = get_current_user(request)

    try:
        conversation = ChatConversation.objects.prefetch_related("messages").get(
            id=conversation_id, user=user
        )
    except ChatConversation.DoesNotExist:
        raise HttpError(404, "Conversation not found")

    messages = [ChatMessageOut.from_orm(m) for m in conversation.messages.all()]

    return ConversationDetailOut(
        id=conversation.id,
        title=conversation.title,
        agentId=conversation.agent_id,
        messages=messages,
        createdAt=conversation.created_at,
        updatedAt=conversation.updated_at,
    )


@router.put("/conversations/{conversation_id}", response=ConversationOut)
def update_conversation(request: HttpRequest, conversation_id: str, data: UpdateConversationIn):
    """Update conversation title."""
    user = get_current_user(request)

    try:
        conversation = ChatConversation.objects.get(id=conversation_id, user=user)
    except ChatConversation.DoesNotExist:
        raise HttpError(404, "Conversation not found")

    conversation.title = data.title
    conversation.save()

    return ConversationOut.from_orm(conversation)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(request: HttpRequest, conversation_id: str):
    """Delete a conversation."""
    user = get_current_user(request)

    try:
        conversation = ChatConversation.objects.get(id=conversation_id, user=user)
    except ChatConversation.DoesNotExist:
        raise HttpError(404, "Conversation not found")

    conversation.delete()
    return {"message": "Conversation deleted"}


# ============ Chat endpoints ============


@router.post("/", response=ChatOut)
async def chat(request: HttpRequest, data: ChatIn):
    """Send a chat message and get response."""
    user = get_current_user(request)

    # Build messages for KIE API
    api_messages = build_kie_messages(data.messages, data.systemPrompt, data.imageUrl)

    # Get or create conversation
    conversation = None
    if data.conversationId:
        try:
            conversation = await ChatConversation.objects.aget(
                id=data.conversationId, user=user
            )
        except ChatConversation.DoesNotExist:
            pass

    if not conversation:
        last_msg = data.messages[-1].content if data.messages else "New Chat"
        conversation = await ChatConversation.objects.acreate(
            user=user,
            title=last_msg[:50] if len(last_msg) > 50 else last_msg,
            agent_id=data.agentId or "general_base",
        )

    # Save user message
    if data.messages:
        await ChatMessage.objects.acreate(
            conversation=conversation,
            role=MessageRole.USER,
            content=data.messages[-1].content,
        )

    # Call KIE API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            KIE_API_URL,
            headers={
                "Authorization": f"Bearer {settings.KIE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "messages": api_messages,
                "stream": False,
            },
            timeout=120.0,
        )

    if response.status_code != 200:
        raise HttpError(500, f"Failed to get response from AI: {response.text}")

    result = response.json()
    assistant_message = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # Save assistant message
    await ChatMessage.objects.acreate(
        conversation=conversation,
        role=MessageRole.ASSISTANT,
        content=assistant_message,
        tokens_used=total_tokens,
    )

    # Update user credits
    if total_tokens:
        user.token_balance -= total_tokens // 10
        await user.asave()

    return ChatOut(
        message=assistant_message,
        usage=ChatUsageOut(
            promptTokens=prompt_tokens,
            completionTokens=completion_tokens,
            totalTokens=total_tokens,
            cost=total_tokens * 0.00001,
        ),
        conversationId=conversation.id,
    )


@router.post("/stream")
async def chat_stream(request: HttpRequest, data: ChatIn):
    """Stream chat response using KIE API."""
    user = get_current_user(request)

    # Build messages for KIE API
    api_messages = build_kie_messages(data.messages, data.systemPrompt, data.imageUrl)

    # Get or create conversation
    conversation = None
    if data.conversationId:
        try:
            conversation = await ChatConversation.objects.aget(
                id=data.conversationId, user=user
            )
        except ChatConversation.DoesNotExist:
            pass

    if not conversation:
        last_msg = data.messages[-1].content if data.messages else "New Chat"
        conversation = await ChatConversation.objects.acreate(
            user=user,
            title=last_msg[:50] if len(last_msg) > 50 else last_msg,
            agent_id=data.agentId or "general_base",
        )

    # Save user message
    if data.messages:
        await ChatMessage.objects.acreate(
            conversation=conversation,
            role=MessageRole.USER,
            content=data.messages[-1].content,
        )

    async def generate():
        full_response = ""
        total_tokens = 0

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    KIE_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.KIE_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "messages": api_messages,
                        "stream": True,
                    },
                    timeout=120.0,
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    full_response += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"

                                # Get usage from final chunk
                                if "usage" in chunk:
                                    total_tokens = chunk["usage"].get("total_tokens", 0)
                            except Exception:
                                continue

            # Estimate tokens if not provided
            if not total_tokens:
                total_tokens = len(full_response) // 4 + len(str(api_messages)) // 4

            # Save assistant message
            await ChatMessage.objects.acreate(
                conversation=conversation,
                role=MessageRole.ASSISTANT,
                content=full_response,
                tokens_used=total_tokens,
            )

            # Update user credits
            if total_tokens:
                user.token_balance -= total_tokens // 10
                await user.asave()

            yield f"data: {json.dumps({'done': True, 'conversationId': str(conversation.id), 'usage': {'estimatedTokens': total_tokens, 'cost': total_tokens * 0.00001}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingHttpResponse(
        generate(),
        content_type="text/event-stream",
    )
