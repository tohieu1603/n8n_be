"""
Chat API endpoints - N8N Teacher chatbot with tool calling support.

Uses PromptBuilder to manage system prompts and conversation memory.
Supports LLM tool calling to get accurate n8n node information.
"""

import json
import logging
import httpx
from django.conf import settings
from django.http import HttpRequest, StreamingHttpResponse
from ninja import Router
from ninja.errors import HttpError

logger = logging.getLogger(__name__)

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
from agents import (
    PromptBuilder,
    get_prompt_builder,
    get_tool_definitions,
    get_tool_executor,
)

router = Router(auth=AuthBearer())

# LLM API configurations
LLM_CONFIGS = {
    "kie": {
        "url": "https://api.kie.ai/gemini-3-pro/v1/chat/completions",
        "get_key": lambda: settings.KIE_API_KEY,
        "model": None,  # Not needed for KIE
    },
    "deepseek": {
        "url": getattr(settings, "DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"),
        "get_key": lambda: getattr(settings, "DEEPSEEK_API_KEY", ""),
        "model": getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat"),
    },
}


def get_llm_config() -> dict:
    """Get LLM configuration based on LLM_PROVIDER setting."""
    provider = getattr(settings, "LLM_PROVIDER", "kie")
    config = LLM_CONFIGS.get(provider, LLM_CONFIGS["kie"])
    logger.info(f"[LLM] Using provider: {provider}")
    return {
        "url": config["url"],
        "api_key": config["get_key"](),
        "model": config["model"],
        "provider": provider,
    }


# Initialize prompt builder and tool executor
prompt_builder = get_prompt_builder("n8n_teacher")
tool_executor = get_tool_executor()

# Max tool call iterations (prevent infinite loops)
MAX_TOOL_ITERATIONS = 10  # Allow more iterations for complex reasoning


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


async def call_llm_api(
    messages: list[dict],
    tools: list[dict] = None,
    stream: bool = False,
) -> dict:
    """
    Call LLM API (KIE or DeepSeek) with optional tools.

    Args:
        messages: Messages for the API
        tools: Optional tool definitions for function calling
        stream: Whether to stream response

    Returns:
        API response dict
    """
    llm_config = get_llm_config()

    request_body = {
        "messages": messages,
        "stream": stream,
    }

    # Add model for providers that need it (DeepSeek)
    if llm_config["model"]:
        request_body["model"] = llm_config["model"]

    # Add tools if provided and MCP is enabled
    if tools and getattr(settings, "MCP_ENABLED", True):
        request_body["tools"] = tools
        request_body["tool_choice"] = "auto"

    logger.debug(f"[LLM] Calling {llm_config['provider']} API: {llm_config['url']}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            llm_config["url"],
            headers={
                "Authorization": f"Bearer {llm_config['api_key']}",
                "Content-Type": "application/json",
            },
            json=request_body,
            timeout=120.0,
        )

    if response.status_code != 200:
        logger.error(f"[LLM] API error: {response.text}")
        raise HttpError(500, f"Failed to get response from AI: {response.text}")

    return response.json()


async def process_tool_calls(
    messages: list[dict],
    response: dict,
    iteration: int = 0,
) -> tuple[str, dict]:
    """
    Process tool calls from LLM response.

    If the response contains tool calls, execute them and call LLM again.
    Continues until LLM returns a final text response or max iterations.

    Args:
        messages: Current message history
        response: LLM API response
        iteration: Current iteration count

    Returns:
        Tuple of (final_message, usage_info)
    """
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    tool_calls = message.get("tool_calls", [])
    usage = response.get("usage", {})

    # If no tool calls or max iterations reached, return content
    if not tool_calls or iteration >= MAX_TOOL_ITERATIONS:
        return message.get("content", ""), usage

    # Execute tool calls
    tool_results = await tool_executor.execute_tool_calls(tool_calls)

    # Build messages with assistant's tool call and tool results
    new_messages = messages.copy()

    # Add assistant message with tool calls
    new_messages.append({
        "role": "assistant",
        "content": message.get("content") or "",
        "tool_calls": tool_calls
    })

    # Add tool results
    for result in tool_results:
        new_messages.append(result.to_message())

    # Call LLM again with tool results
    tools = get_tool_definitions() if iteration + 1 < MAX_TOOL_ITERATIONS else None
    new_response = await call_llm_api(new_messages, tools=tools)

    # Accumulate usage
    new_usage = new_response.get("usage", {})
    usage["prompt_tokens"] = usage.get("prompt_tokens", 0) + new_usage.get("prompt_tokens", 0)
    usage["completion_tokens"] = usage.get("completion_tokens", 0) + new_usage.get("completion_tokens", 0)
    usage["total_tokens"] = usage.get("total_tokens", 0) + new_usage.get("total_tokens", 0)

    # Recursively process if more tool calls
    return await process_tool_calls(new_messages, new_response, iteration + 1)


@router.post("/", response=ChatOut)
async def chat(request: HttpRequest, data: ChatIn):
    """Send a chat message and get response with tool calling support."""
    user = get_current_user(request)

    # Get current user message
    current_message = data.messages[-1].content if data.messages else ""

    # Build messages using PromptBuilder
    api_messages, conversation = prompt_builder.build_from_request(
        user_message=current_message,
        conversation_id=data.conversationId,
        messages_model=ChatMessage,
        conversation_model=ChatConversation,
        image_url=data.imageUrl
    )

    # Filter conversation by user (security)
    if conversation and conversation.user_id != user.id:
        conversation = None

    # Create new conversation if needed
    if not conversation:
        conversation = await ChatConversation.objects.acreate(
            user=user,
            title=current_message[:50] if len(current_message) > 50 else current_message,
            agent_id="n8n_teacher",
        )

    # Save user message
    if current_message:
        await ChatMessage.objects.acreate(
            conversation=conversation,
            role=MessageRole.USER,
            content=current_message,
        )

    # Call LLM with tools
    tools = get_tool_definitions() if getattr(settings, "MCP_ENABLED", True) else None
    response = await call_llm_api(api_messages, tools=tools)

    # Process tool calls if any
    assistant_message, usage = await process_tool_calls(api_messages, response)

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # Save assistant message (only final response, not tool calls)
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
def chat_stream(request: HttpRequest, data: ChatIn):
    """
    Stream chat response using KIE API.

    Note: Tool calling with streaming requires special handling.
    For simplicity, we use non-streaming for tool calls, then stream the final response.
    """
    user = get_current_user(request)

    # Get current user message
    current_message = data.messages[-1].content if data.messages else ""

    # Build messages using PromptBuilder
    api_messages, conversation = prompt_builder.build_from_request(
        user_message=current_message,
        conversation_id=data.conversationId,
        messages_model=ChatMessage,
        conversation_model=ChatConversation,
        image_url=data.imageUrl
    )

    # Filter conversation by user (security)
    if conversation and conversation.user_id != user.id:
        conversation = None

    # Create new conversation if needed
    if not conversation:
        conversation = ChatConversation.objects.create(
            user=user,
            title=current_message[:50] if len(current_message) > 50 else current_message,
            agent_id="n8n_teacher",
        )

    # Save user message
    if current_message:
        ChatMessage.objects.create(
            conversation=conversation,
            role=MessageRole.USER,
            content=current_message,
        )

    def generate():
        import asyncio

        full_response = ""
        total_tokens = 0
        mcp_enabled = getattr(settings, "MCP_ENABLED", True)
        llm_config = get_llm_config()

        logger.info(f"[ChatStream] Starting generate(), MCP enabled: {mcp_enabled}, Provider: {llm_config['provider']}")

        try:
            # Recursive tool calling loop (max MAX_TOOL_ITERATIONS)
            api_messages_current = api_messages
            iteration = 0

            if mcp_enabled:
                tools = get_tool_definitions()
                logger.info(f"[ChatStream] Got {len(tools)} tool definitions")

                while iteration < MAX_TOOL_ITERATIONS:
                    logger.info(f"[ChatStream] Tool calling iteration {iteration + 1}/{MAX_TOOL_ITERATIONS}")

                    # Build request body
                    request_body = {
                        "messages": api_messages_current,
                        "tools": tools,
                        "tool_choice": "auto",
                        "stream": False,
                    }
                    if llm_config["model"]:
                        request_body["model"] = llm_config["model"]

                    # Use sync httpx for non-streaming tool call
                    logger.info(f"[ChatStream] Calling {llm_config['provider']} API with tools...")
                    with httpx.Client() as client:
                        response = client.post(
                            llm_config["url"],
                            headers={
                                "Authorization": f"Bearer {llm_config['api_key']}",
                                "Content-Type": "application/json",
                            },
                            json=request_body,
                            timeout=120.0,
                        )

                    logger.info(f"[ChatStream] LLM API response status: {response.status_code}")

                    if response.status_code != 200:
                        logger.error(f"[ChatStream] LLM API error: {response.text}")
                        yield f"data: {json.dumps({'error': 'API error'})}\n\n"
                        return

                    result = response.json()
                    choice = result.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    tool_calls = message.get("tool_calls", [])
                    content = message.get("content", "")

                    # Accumulate tokens
                    total_tokens += result.get("usage", {}).get("total_tokens", 0)
                    logger.info(f"[ChatStream] LLM response: content_length={len(content)}, tool_calls={len(tool_calls)}")

                    # Stream reasoning content if present (even if there are tool calls)
                    if content:
                        logger.info(f"[ChatStream] Streaming reasoning content: {content[:100]}...")
                        full_response += content

                        # Stream the content in chunks
                        chunk_size = 20
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i+chunk_size]
                            yield f"data: {json.dumps({'content': chunk})}\n\n"

                    # If no tool calls, we have the final response
                    if not tool_calls:
                        logger.info("[ChatStream] No tool calls - final response ready")

                        # Content was already streamed above, just save and finish
                        if full_response:
                            ChatMessage.objects.create(
                                conversation=conversation,
                                role=MessageRole.ASSISTANT,
                                content=full_response,
                                tokens_used=total_tokens,
                            )

                            if total_tokens:
                                user.token_balance -= total_tokens // 10
                                user.save()

                            yield f"data: {json.dumps({'done': True, 'conversationId': str(conversation.id), 'usage': {'estimatedTokens': total_tokens, 'cost': total_tokens * 0.00001}})}\n\n"
                            return
                        break

                    # Process tool calls
                    logger.info(f"[ChatStream] Processing tool calls: {[tc.get('function', {}).get('name') for tc in tool_calls]}")

                    # Send status to frontend
                    status_msg = f"Đang tìm kiếm thông tin... (bước {iteration + 1})"
                    yield f"data: {json.dumps({'status': status_msg})}\n\n"

                    # Execute tool calls synchronously
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    try:
                        logger.info("[ChatStream] Executing tool calls via MCP...")
                        tool_results = loop.run_until_complete(
                            tool_executor.execute_tool_calls(tool_calls)
                        )
                        logger.info(f"[ChatStream] Tool execution completed. Results: {len(tool_results)}")
                        for tr in tool_results:
                            logger.info(f"[ChatStream] Tool {tr.tool_name}: success={tr.success}, error={tr.error}")
                            # Log tool result content
                            if tr.success and tr.result:
                                content_preview = str(tr.result)[:500] if len(str(tr.result)) > 500 else str(tr.result)
                                logger.info(f"[ChatStream] Tool {tr.tool_name} result:\n{content_preview}")
                    except Exception as e:
                        logger.exception(f"[ChatStream] Tool execution error: {e}")
                        raise
                    finally:
                        loop.close()

                    # Build messages with tool results for next iteration
                    api_messages_current = api_messages_current.copy()
                    api_messages_current.append({
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": tool_calls
                    })

                    for tr in tool_results:
                        tool_msg = tr.to_message()
                        logger.debug(f"[ChatStream] Adding tool result to messages")
                        api_messages_current.append(tool_msg)

                    logger.info(f"[ChatStream] Built {len(api_messages_current)} messages for next iteration")
                    iteration += 1

                # After loop, prepare for streaming
                api_messages_final = api_messages_current

                # If we exited loop due to MAX_TOOL_ITERATIONS but haven't gotten final response,
                # add a message to force LLM to stop calling tools
                if iteration >= MAX_TOOL_ITERATIONS and not full_response:
                    api_messages_final.append({
                        "role": "system",
                        "content": "You have reached the maximum number of tool calls. Please provide your final answer now without calling any more tools. Include the workflow in ```n8n-workflow format if applicable."
                    })
                    logger.warning(f"[ChatStream] Reached MAX_TOOL_ITERATIONS ({MAX_TOOL_ITERATIONS}), forcing final response")

                logger.info(f"[ChatStream] Completed {iteration} tool calling iterations, total tokens: {total_tokens}, response_length: {len(full_response)}")
            else:
                # MCP disabled, use original messages
                api_messages_final = api_messages
                logger.info("[ChatStream] MCP disabled, skipping tool calls")

            # Now stream the final response
            logger.info(f"[ChatStream] Starting final streaming call with {len(api_messages_final)} messages")

            # Build request body for streaming (WITHOUT tools to force text response)
            stream_request_body = {
                "messages": api_messages_final,
                "stream": True,
            }
            if llm_config["model"]:
                stream_request_body["model"] = llm_config["model"]

            # Note: Don't send tools array or tool_choice here to force text-only response

            with httpx.Client() as client:
                with client.stream(
                    "POST",
                    llm_config["url"],
                    headers={
                        "Authorization": f"Bearer {llm_config['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json=stream_request_body,
                    timeout=120.0,
                ) as response:
                    logger.info(f"[ChatStream] Streaming response status: {response.status_code}")
                    line_count = 0
                    for line in response.iter_lines():
                        line_count += 1
                        logger.debug(f"[ChatStream] Line {line_count}: {line[:100] if line else 'empty'}")
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                logger.info("[ChatStream] Received [DONE] signal")
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])

                                # Skip if choices is empty
                                if not choices:
                                    logger.debug("[ChatStream] Empty choices, skipping")
                                    continue

                                content = choices[0].get("delta", {}).get("content", "")
                                if content:
                                    full_response += content
                                    logger.debug(f"[ChatStream] Content chunk: {content[:50]}")
                                    yield f"data: {json.dumps({'content': content})}\n\n"

                                # Get usage from final chunk
                                if "usage" in chunk:
                                    total_tokens += chunk["usage"].get("total_tokens", 0)
                            except Exception as e:
                                logger.warning(f"[ChatStream] Error parsing chunk: {e}")
                                continue
                    logger.info(f"[ChatStream] Streaming complete. Total lines: {line_count}, Response length: {len(full_response)}")

            # Estimate tokens if not provided
            if not total_tokens:
                total_tokens = len(full_response) // 4 + len(str(api_messages_final)) // 4

            # Save assistant message
            ChatMessage.objects.create(
                conversation=conversation,
                role=MessageRole.ASSISTANT,
                content=full_response,
                tokens_used=total_tokens,
            )

            # Update user credits
            if total_tokens:
                user.token_balance -= total_tokens // 10
                user.save()

            yield f"data: {json.dumps({'done': True, 'conversationId': str(conversation.id), 'usage': {'estimatedTokens': total_tokens, 'cost': total_tokens * 0.00001}})}\n\n"

        except Exception as e:
            logger.exception(f"[ChatStream] Error in generate(): {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingHttpResponse(
        generate(),
        content_type="text/event-stream",
    )
