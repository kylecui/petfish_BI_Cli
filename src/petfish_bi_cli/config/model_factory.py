from __future__ import annotations

import os

from petfishframework.core.contracts import ModelAdapter

from .settings import ModelConfig, Settings


def _resolve_api_key(cfg: ModelConfig, settings: Settings) -> str | None:
    """Resolve API key: explicit config → Vault → environment variable."""
    if cfg.api_key:
        return cfg.api_key

    if settings.vault.enabled and settings.vault.api_key_path:
        from petfishframework.credentials import VaultCredentialSource

        source = VaultCredentialSource(
            vault_url=settings.vault.url,
            token=settings.vault.token,
        )
        return source.read_secret(settings.vault.api_key_path)

    provider = cfg.provider.lower()
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY")
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_API_KEY")
    return None


class ModelFactory:
    """Build ModelAdapter instances from ModelConfig."""

    @staticmethod
    def build(cfg: ModelConfig, settings: Settings | None = None) -> ModelAdapter:
        provider = cfg.provider.lower()
        if provider == "fake":
            from petfishframework.models.fake import FakeModel

            return FakeModel()
        resolved_key = cfg.api_key
        if settings is not None:
            resolved_key = _resolve_api_key(cfg, settings)
        if provider == "openai":
            from petfishframework.models.openai import OpenAIModel

            return OpenAIModel(
                model=cfg.name,
                api_key=resolved_key,
                base_url=cfg.base_url,
            )
        if provider == "anthropic":
            from petfishframework.models.anthropic import AnthropicModel

            return AnthropicModel(
                model=cfg.name,
                api_key=resolved_key,
                base_url=cfg.base_url,
            )
        raise ValueError(f"Unknown model provider: {cfg.provider}")

    @staticmethod
    def build_with_fallback(
        primary: ModelConfig,
        fallback: ModelConfig | None = None,
        settings: Settings | None = None,
    ) -> ModelAdapter:
        """Try primary; if construction fails, try fallback."""
        try:
            return ModelFactory.build(primary, settings=settings)
        except Exception:
            if fallback is not None:
                return ModelFactory.build(fallback, settings=settings)
            raise


def build_model(settings: Settings) -> ModelAdapter:
    """Convenience: build model from Settings (with fallback if configured)."""
    primary = settings.primary_model
    fallback = settings.fallback_model
    return ModelFactory.build_with_fallback(primary, fallback, settings=settings)
