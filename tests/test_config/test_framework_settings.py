from __future__ import annotations

from petfish_bi_cli.config.settings import BudgetConfig, DataConfig, ModelConfig, Settings
from petfish_bi_cli.framework import make_bi_agent


class TestMakeBiAgentWithSettings:
    def test_uses_settings_model_when_no_model_passed(self):
        settings = Settings(
            model=ModelConfig(provider="fake", name="fake"),
            data=DataConfig(root="references", semantic_dir="references/semantic"),
            budget=BudgetConfig(),
        )
        agent = make_bi_agent(settings=settings)
        assert agent is not None
        assert len(agent.tools) >= 2

    def test_explicit_model_overrides_settings(self):
        from petfishframework.models.fake import FakeModel

        settings = Settings(
            model=ModelConfig(provider="fake", name="fake"),
        )
        custom_model = FakeModel()
        agent = make_bi_agent(model=custom_model, settings=settings)
        assert agent.model is custom_model

    def test_settings_data_root_used(self, tmp_path):
        settings = Settings(
            model=ModelConfig(provider="fake", name="fake"),
            data=DataConfig(root=str(tmp_path), semantic_dir=str(tmp_path / "semantic")),
        )
        (tmp_path / "semantic").mkdir()
        agent = make_bi_agent(settings=settings)
        assert agent is not None
