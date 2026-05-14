"""LLM configuration service — CRUD, encryption, test connection."""

from __future__ import annotations

import base64
import time
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.error_codes import ErrorCode
from app.data.file_io import FileIO
from app.llm import LLMError
from app.llm.anthropic_client import AnthropicClient
from app.llm.openai_client import OpenAICompatibleClient

_CONFIG_FILE = "llm_configs.json"


class ModelRouter:
    """Factory for LLM clients based on provider."""

    _clients: dict[str, Any] = {}

    def get_client(
        self,
        provider: str,
        api_key: str,
        model: str,
        base_url: str = "",
    ) -> Any:
        """Return an LLM client for the given provider."""
        cache_key = f"{provider}:{model}:{api_key[:8]}"
        if cache_key in self._clients:
            return self._clients[cache_key]
        if provider == "anthropic":
            client = AnthropicClient(
                api_key=api_key,
                model=model,
                base_url=base_url if base_url else None,
            )
        elif provider in ("openai", "openai_compatible"):
            client = OpenAICompatibleClient(
                api_key=api_key,
                model=model,
                base_url=base_url,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
        self._clients[cache_key] = client
        return client


model_router = ModelRouter()


def _config_path() -> Path:
    from app.core.config import ensure_app_data_dir
    return ensure_app_data_dir() / _CONFIG_FILE


def _load() -> dict:
    p = _config_path()
    if p.exists():
        return FileIO.read_json(p)
    return {"configs": []}


def _save(data: dict) -> None:
    FileIO.write_json(_config_path(), data)


def _encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key using AES-GCM when APP_SECRET_KEY is set.

    Falls back to plaintext storage if APP_SECRET_KEY is not configured.
    """
    if not settings.app_secret_key:
        return plaintext

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os
    import hashlib

    key = hashlib.sha256(settings.app_secret_key.encode("utf-8")).digest()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return "enc:" + base64.b64encode(nonce + ciphertext_and_tag).decode("ascii")


def _decrypt_api_key(encoded: str) -> str:
    """Decrypt a stored API key. Falls back to returning as-is if not encrypted."""
    if not encoded.startswith("enc:"):
        return encoded
    if not settings.app_secret_key:
        return encoded

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag
    import hashlib

    try:
        key = hashlib.sha256(settings.app_secret_key.encode("utf-8")).digest()
        aesgcm = AESGCM(key)
        raw = base64.b64decode(encoded[4:])
        nonce = raw[:12]
        ciphertext_and_tag = raw[12:]
        return aesgcm.decrypt(nonce, ciphertext_and_tag, None).decode("utf-8")
    except (InvalidTag, ValueError, Exception):
        return encoded


def _mask_key(key: str) -> str:
    """Mask an API key for display."""
    if not key:
        return ""
    if key.startswith("enc:"):
        return "enc:****" + key[-4:] if len(key) > 8 else "enc:****"
    if len(key) > 8:
        return key[:4] + "****" + key[-4:]
    return "****"


class LLMService:
    """Manage LLM configurations with encrypted API key storage."""

    @staticmethod
    def list_configs() -> list[dict[str, Any]]:
        """List all LLM configs with API keys masked."""
        data = _load()
        result = []
        for c in data.get("configs", []):
            key = c.get("api_key_encrypted", "")
            masked = _mask_key(key)
            result.append({
                "id": c["id"],
                "name": c["name"],
                "provider": c["provider"],
                "model": c["model"],
                "url": c.get("url", ""),
                "api_key_masked": masked,
                "is_default": c.get("is_default", False),
            })
        return result

    @staticmethod
    def add_config(
        name: str,
        provider: str,
        model: str,
        url: str,
        api_key: str,
        is_default: bool = False,
    ) -> str:
        """Add a new LLM configuration. Returns the generated config ID."""
        data = _load()
        if is_default:
            for c in data["configs"]:
                c["is_default"] = False
        config = {
            "id": str(uuid.uuid4()),
            "name": name,
            "provider": provider,
            "model": model,
            "url": url,
            "api_key_encrypted": _encrypt_api_key(api_key),
            "is_default": is_default,
        }
        data["configs"].append(config)
        _save(data)
        return config["id"]

    @staticmethod
    def update_config(
        config_id: str,
        name: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        url: str | None = None,
        api_key: str | None = None,
    ) -> bool:
        """Update an existing LLM configuration. Returns True if found."""
        data = _load()
        for c in data["configs"]:
            if c["id"] == config_id:
                if name is not None:
                    c["name"] = name
                if provider is not None:
                    c["provider"] = provider
                if model is not None:
                    c["model"] = model
                if url is not None:
                    c["url"] = url
                if api_key is not None:
                    c["api_key_encrypted"] = _encrypt_api_key(api_key)
                _save(data)
                return True
        return False

    @staticmethod
    def delete_config(config_id: str) -> bool:
        """Delete an LLM configuration. Returns True if found and removed."""
        data = _load()
        before = len(data["configs"])
        data["configs"] = [c for c in data["configs"] if c["id"] != config_id]
        if len(data["configs"]) < before:
            _save(data)
            return True
        return False

    @staticmethod
    def set_default(config_id: str) -> bool:
        """Set a config as the default. Returns True if found."""
        data = _load()
        found = False
        for c in data["configs"]:
            if c["id"] == config_id:
                c["is_default"] = True
                found = True
            else:
                c["is_default"] = False
        if found:
            _save(data)
        return found

    @staticmethod
    def get_config(config_id: str) -> dict[str, Any] | None:
        """Get a raw config dict by ID (with encrypted key)."""
        for c in _load()["configs"]:
            if c["id"] == config_id:
                return c
        return None

    @staticmethod
    def get_default_config() -> dict[str, Any] | None:
        """Get the default config, or the first config if no default is set."""
        data = _load()
        for c in data["configs"]:
            if c.get("is_default"):
                return c
        if data["configs"]:
            return data["configs"][0]
        return None

    @staticmethod
    async def test_connection(config_id: str) -> dict[str, Any]:
        """Test connectivity to an LLM provider.

        Returns dict with ok, latency_ms, error, model_info keys.
        """
        config = LLMService.get_config(config_id)
        if not config:
            return {
                "ok": False,
                "latency_ms": None,
                "error": f"Config {config_id} not found",
                "model_info": None,
            }

        api_key = _decrypt_api_key(config["api_key_encrypted"])
        provider = config["provider"]
        model = config["model"]
        base_url = config.get("url", "")

        try:
            client = model_router.get_client(
                provider=provider,
                api_key=api_key,
                model=model,
                base_url=base_url,
            )
            result = await client.test_connection()
            return {
                "ok": True,
                "latency_ms": result.get("latency_ms"),
                "error": None,
                "model_info": result.get("model", model),
            }
        except LLMError as e:
            return {
                "ok": False,
                "latency_ms": None,
                "error": str(e),
                "model_info": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "latency_ms": None,
                "error": f"{type(e).__name__}: {e}",
                "model_info": None,
            }

    @staticmethod
    def _mask_key(key: str) -> str:
        """Mask an API key for display."""
        if not key:
            return ""
        if key.startswith("enc:"):
            return "enc:****" + key[-4:] if len(key) > 8 else "enc:****"
        if len(key) > 8:
            return key[:4] + "****" + key[-4:]
        return "****"
