from __future__ import annotations

import pytest

from workflow.runtime_skills.agent_factory import BoundedReactAgentFactory
from workflow.runtime_skills.unit_runtime_config import FORBIDDEN_REACT_TOOLS, UNIT_RUNTIME_CONFIG, get_unit_runtime_config


def test_unit_runtime_config_sets_worker_only_and_bounded_react_units() -> None:
    assert get_unit_runtime_config("qa_like").react_enabled is False
    assert get_unit_runtime_config("chat_like").react_enabled is False
    assert get_unit_runtime_config("reject_like").react_enabled is False
    assert get_unit_runtime_config("compare").react_enabled is True
    assert get_unit_runtime_config("verify").react_enabled is True
    assert get_unit_runtime_config("synthesis").react_enabled is True


def test_unit_runtime_config_never_exposes_forbidden_tools() -> None:
    for config in UNIT_RUNTIME_CONFIG.values():
        assert set(config.tools).isdisjoint(FORBIDDEN_REACT_TOOLS)


def test_bounded_react_agent_factory_returns_only_unit_whitelist() -> None:
    spec = BoundedReactAgentFactory().spec_for("compare")

    assert spec.tool_names == ("evidence_anchor", "caution_assembly", "answer_constraint")
    assert spec.output_schema == "CompareResultPayload"


def test_bounded_react_agent_factory_rejects_forbidden_or_worker_only_tools() -> None:
    factory = BoundedReactAgentFactory()

    with pytest.raises(ValueError, match="forbidden tools"):
        factory.spec_for("compare", extra_tools=("target_resolution",))

    with pytest.raises(ValueError, match="does not allow react"):
        factory.spec_for("qa_like")
