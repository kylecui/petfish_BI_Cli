from __future__ import annotations

import pytest

from petfish_bi_cli.config.model_factory import ModelFactory
from petfish_bi_cli.config.settings import ModelConfig, Settings


class TestModelFactory:
    def test_build_fake(self):
        cfg = ModelConfig(provider="fake", name="fake")
        model = ModelFactory.build(cfg)
        assert model is not None

    def test_build_openai_without_key_raises(self):
        cfg = ModelConfig(provider="openai", name="gpt-4o", api_key=None)
        with pytest.raises(ValueError, match="api_key"):
            ModelFactory.build(cfg)

    def test_build_unknown_provider_raises(self):
        cfg = ModelConfig(provider="gemini", name="gemini-pro")
        with pytest.raises(ValueError, match="Unknown"):
            ModelFactory.build(cfg)

    def test_build_with_fallback_primary_succeeds(self):
        primary = ModelConfig(provider="fake", name="fake")
        fallback = ModelConfig(provider="fake", name="fake")
        model = ModelFactory.build_with_fallback(primary, fallback)
        assert model is not None

    def test_build_with_fallback_primary_fails(self):
        primary = ModelConfig(provider="openai", name="gpt-4o", api_key=None)
        fallback = ModelConfig(provider="fake", name="fake")
        model = ModelFactory.build_with_fallback(primary, fallback)
        assert model is not None

    def test_build_with_fallback_both_fail(self):
        primary = ModelConfig(provider="openai", name="gpt-4o", api_key=None)
        fallback = ModelConfig(provider="openai", name="gpt-4o", api_key=None)
        with pytest.raises(ValueError):
            ModelFactory.build_with_fallback(primary, fallback)

    def test_build_from_settings_primary(self):
        settings = Settings(
            roles={
                "primary": ModelConfig(provider="fake", name="fake"),
                "fallback": ModelConfig(provider="fake", name="fake"),
            }
        )
        from petfish_bi_cli.config.model_factory import build_model

        model = build_model(settings)
        assert model is not None

    def test_build_from_settings_no_roles(self):
        settings = Settings(model=ModelConfig(provider="fake", name="fake"))
        from petfish_bi_cli.config.model_factory import build_model

        model = build_model(settings)
        assert model is not None
