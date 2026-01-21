"""
API Keys endpoints - converted from keys.controller.ts
"""

import re
import secrets
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from django.conf import settings
from django.http import HttpRequest
from ninja import Router

from utils.auth import AuthBearer, get_current_user
from .models import ApiKey
from .schemas import ApiKeyOut, ApiKeyCreateIn, ApiKeyCreateOut, ApiKeyRevealOut

router = Router(auth=AuthBearer())

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return "sk_" + secrets.token_hex(32)


def hash_api_key(key: str) -> str:
    """Hash API key with HMAC-SHA256 and pepper."""
    return hmac.new(
        settings.API_KEY_PEPPER.encode(),
        key.encode(),
        hashlib.sha256,
    ).hexdigest()


def encrypt_api_key(key: str) -> str:
    """Encrypt API key for storage using AES-256-CBC."""
    encryption_key = settings.API_KEY_ENCRYPTION_KEY.ljust(32)[:32].encode()
    iv = secrets.token_bytes(16)
    cipher = Cipher(algorithms.AES(encryption_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # PKCS7 padding
    padding_length = 16 - (len(key) % 16)
    padded_data = key.encode() + bytes([padding_length] * padding_length)

    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return iv.hex() + ":" + encrypted.hex()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for retrieval."""
    try:
        iv_hex, encrypted = encrypted_key.split(":")
        iv = bytes.fromhex(iv_hex)
        encrypted_bytes = bytes.fromhex(encrypted)

        encryption_key = settings.API_KEY_ENCRYPTION_KEY.ljust(32)[:32].encode()
        cipher = Cipher(algorithms.AES(encryption_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()
        # Remove PKCS7 padding
        padding_length = padded_data[-1]
        return padded_data[:-padding_length].decode()
    except Exception:
        return ""


@router.get("/", response=list[ApiKeyOut])
def get_keys(request: HttpRequest):
    """Get all API keys for current user (masked)."""
    user = get_current_user(request)
    keys = ApiKey.objects.filter(user=user, is_active=True).order_by("-created_at")

    return [
        ApiKeyOut(
            id=key.id,
            name=key.name,
            key=f"{key.key_prefix}...{key.key_hash[:4]}",
            can_reveal=bool(key.encrypted_key),
            created_at=key.created_at,
            last_used_at=key.last_used_at,
        )
        for key in keys
    ]


@router.get("/{key_id}/reveal", response=ApiKeyRevealOut)
def reveal_key(request: HttpRequest, key_id: str):
    """Reveal full API key."""
    if not UUID_REGEX.match(key_id):
        return {"error": "Invalid key ID format"}, 400

    user = get_current_user(request)
    try:
        key = ApiKey.objects.get(id=key_id, user=user, is_active=True)
    except ApiKey.DoesNotExist:
        return {"error": "API key not found"}, 404

    if not key.encrypted_key:
        return {"error": "Full key not available"}, 400

    full_key = decrypt_api_key(key.encrypted_key)
    if not full_key:
        return {"error": "Failed to decrypt API key"}, 500

    return ApiKeyRevealOut(key=full_key)


@router.post("/", response=ApiKeyCreateOut)
def create_key(request: HttpRequest, data: ApiKeyCreateIn):
    """Create a new API key."""
    user = get_current_user(request)

    # Validate name
    name = data.name.strip()[:50]
    if len(name) < 1:
        return {"error": "Key name is required"}, 400

    # Check limit (max 10 keys per user)
    existing_count = ApiKey.objects.filter(user=user, is_active=True).count()
    if existing_count >= 10:
        return {"error": "Maximum 10 API keys allowed per account"}, 400

    # Generate new key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:8]
    encrypted_key = encrypt_api_key(raw_key)

    api_key = ApiKey.objects.create(
        user=user,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        encrypted_key=encrypted_key,
    )

    return ApiKeyCreateOut(
        api_key=ApiKeyOut(
            id=api_key.id,
            name=api_key.name,
            key=f"{key_prefix}...{key_hash[:4]}",
            can_reveal=True,
            created_at=api_key.created_at,
            last_used_at=None,
        ),
        key=raw_key,
    )


@router.delete("/{key_id}")
def delete_key(request: HttpRequest, key_id: str):
    """Delete (soft) an API key."""
    if not UUID_REGEX.match(key_id):
        return {"error": "Invalid key ID format"}, 400

    user = get_current_user(request)
    try:
        key = ApiKey.objects.get(id=key_id, user=user)
    except ApiKey.DoesNotExist:
        return {"error": "API key not found"}, 404

    key.is_active = False
    key.save()

    return {"message": "API key deleted"}
