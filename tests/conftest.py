from __future__ import annotations

import os
from unittest.mock import patch

import pytest

_BI_CLI_ENV_KEYS = [
    "BI_CLI_MODEL_PROVIDER",
    "BI_CLI_MODEL_NAME",
    "BI_CLI_MODEL_API_KEY",
    "BI_CLI_MODEL_BASE_URL",
    "BI_CLI_MODEL_TEMPERATURE",
    "BI_CLI_MODEL_MAX_TOKENS",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_BASE_URL",
    "ANTHROPIC_BASE_URL",
]


@pytest.fixture(autouse=True)
def _isolate_env(request):
    markers = {m.name for m in request.node.iter_markers()}
    if "integration" in markers:
        yield
        return
    for key in _BI_CLI_ENV_KEYS:
        os.environ.pop(key, None)
    if "dotenv" in markers:
        yield
    else:
        with patch("petfish_bi_cli.config.settings._load_dotenv"):
            yield
    for key in _BI_CLI_ENV_KEYS:
        os.environ.pop(key, None)
