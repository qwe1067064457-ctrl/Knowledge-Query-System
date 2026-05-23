from __future__ import annotations

from context.registry.registry import ContextRegistryManager
from context.registry.registry_types import ContextRegistryEntry
from context.session.session_manager import SessionManager


def _entry(turn_id: str, object_id: str) -> ContextRegistryEntry:
    return ContextRegistryEntry(
        object_id=object_id,
        object_type="claim",
        tenant_id="tenant_a",
        group_id="general",
        session_id="session_1",
        source_turn_id=turn_id,
        content=f"content-{object_id}",
        refs=("ref",),
        salience_score=1.0,
        source_power="challenge_power",
    )


def test_registry_append_and_list_recent_entries(tmp_path) -> None:
    session_manager = SessionManager(tmp_path / "storage")
    registry_manager = ContextRegistryManager(session_manager, max_turns=5, max_entries_per_turn=10)

    registry_manager.append_entries(
        session_id="session_1",
        tenant_id="tenant_a",
        group_id="general",
        agent_id="default",
        entries=[_entry("turn_1", "obj_1"), _entry("turn_2", "obj_2")],
    )

    recent = registry_manager.list_recent_entries(
        session_id="session_1",
        tenant_id="tenant_a",
        group_id="general",
        agent_id="default",
        limit=10,
    )

    assert [item.object_id for item in recent] == ["obj_1", "obj_2"]


def test_registry_prune_keeps_recent_turn_window(tmp_path) -> None:
    session_manager = SessionManager(tmp_path / "storage")
    registry_manager = ContextRegistryManager(session_manager, max_turns=2, max_entries_per_turn=2)

    registry_manager.append_entries(
        session_id="session_1",
        tenant_id="tenant_a",
        group_id="general",
        agent_id="default",
        entries=[
            _entry("turn_1", "obj_1"),
            _entry("turn_2", "obj_2"),
            _entry("turn_3", "obj_3"),
        ],
    )
    pruned = registry_manager.prune_registry(
        session_id="session_1",
        tenant_id="tenant_a",
        group_id="general",
        agent_id="default",
    )

    assert [item.object_id for item in pruned.entries] == ["obj_2", "obj_3"]
