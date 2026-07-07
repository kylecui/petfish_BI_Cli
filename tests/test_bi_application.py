from __future__ import annotations

from pathlib import Path

from petfishframework.models.fake import FakeModel

from petfish_bi_cli.application import BIApplication
from petfish_bi_cli.domain import BIQuery, BIReport

PROJECT_ROOT = Path(__file__).parent.parent
DATA_ROOT = PROJECT_ROOT / "references"
SEMANTIC_DIR = DATA_ROOT / "semantic"


class TestBIApplicationExecute:
    def test_execute_returns_bi_report(self):
        """T004: Architecture spike — validates full pipeline wiring."""
        model = FakeModel.script_tool_then_answer(
            tool_name="load_data",
            tool_args={"source": "jd_products", "metric": "avg_price"},
            final_answer='{"answer": "CROCS JD avg price loaded", "data": {}, "status": "ok"}',
        )
        app = BIApplication(data_root=DATA_ROOT, semantic_dir=SEMANTIC_DIR)
        report = app.execute(BIQuery(prompt="CROCS JD price"), model=model)

        assert isinstance(report, BIReport)
        assert report.status == "ok"
        assert report.session_id

    def test_execute_returns_session_id(self):
        model = FakeModel.script_tool_then_answer(
            tool_name="load_data",
            tool_args={"source": "jd_products"},
            final_answer='{"answer": "done", "data": {}, "status": "ok"}',
        )
        app = BIApplication(data_root=DATA_ROOT, semantic_dir=SEMANTIC_DIR)
        report = app.execute(BIQuery(prompt="test"), model=model)
        assert len(report.session_id) > 0

    def test_get_session_returns_record(self):
        model = FakeModel.script_tool_then_answer(
            tool_name="load_data",
            tool_args={"source": "jd_products"},
            final_answer='{"answer": "done", "data": {}, "status": "ok"}',
        )
        app = BIApplication(data_root=DATA_ROOT, semantic_dir=SEMANTIC_DIR)
        report = app.execute(BIQuery(prompt="test"), model=model)

        record = app.get_session(report.session_id)
        assert record is not None
        assert record.query.prompt == "test"
        assert record.registry.count > 0

    def test_get_session_unknown_returns_none(self):
        app = BIApplication(data_root=DATA_ROOT, semantic_dir=SEMANTIC_DIR)
        assert app.get_session("nonexistent") is None

    def test_execute_parse_error_handling(self):
        from petfishframework.core.types import ModelResponse

        model = FakeModel(
            responses=(
                ModelResponse(content="this is not valid JSON"),
            ),
        )
        app = BIApplication(data_root=DATA_ROOT, semantic_dir=SEMANTIC_DIR)
        report = app.execute(BIQuery(prompt="test"), model=model)
        assert report.status in ("parse_error", "ok")

    def test_execute_no_tool_calls(self):
        """Model returns answer directly without calling any tools."""
        from petfishframework.core.types import ModelResponse

        model = FakeModel(
            responses=(
                ModelResponse(content='{"answer": "I have no data", "data": {}, "status": "ok"}'),
            ),
        )
        app = BIApplication(data_root=DATA_ROOT, semantic_dir=SEMANTIC_DIR)
        report = app.execute(BIQuery(prompt="test"), model=model)
        assert isinstance(report, BIReport)
