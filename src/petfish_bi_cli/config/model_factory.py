from __future__ import annotations

from petfishframework.core.contracts import ModelAdapter

from .settings import ModelConfig, Settings


class ModelFactory:
    """Build ModelAdapter instances from ModelConfig."""

    @staticmethod
    def build(cfg: ModelConfig) -> ModelAdapter:
        provider = cfg.provider.lower()
        if provider == "fake":
            from petfishframework.models.fake import FakeModel
            return FakeModel()
        if provider == "openai":
            from petfishframework.models.openai import OpenAIModel
            return OpenAIModel(
                model=cfg.name,
                api_key=cfg.api_key,
                base_url=cfg.base_url,
            )
        if provider == "anthropic":
            from petfishframework.models.anthropic import AnthropicModel
            return AnthropicModel(
                model=cfg.name,
                api_key=cfg.api_key,
                base_url=cfg.base_url,
            )
        raise ValueError(f"Unknown model provider: {cfg.provider}")

    @staticmethod
    def build_with_fallback(
        primary: ModelConfig,
        fallback: ModelConfig | None = None,
    ) -> ModelAdapter:
        """Try primary; if construction fails, try fallback."""
        try:
            return ModelFactory.build(primary)
        except Exception:
            if fallback is not None:
                return ModelFactory.build(fallback)
            raise


def build_model(settings: Settings) -> ModelAdapter:
    """Convenience: build model from Settings (with fallback if configured)."""
    primary = settings.primary_model
    fallback = settings.fallback_model
    return ModelFactory.build_with_fallback(primary, fallback)
