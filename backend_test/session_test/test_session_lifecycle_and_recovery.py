from __future__ import annotations

from pathlib import Path

from context.session_manager import SessionManager


def test_create_and_archive_session_updates_lifecycle_state(session_manager) -> None:
    session = session_manager.create_session(
        "law",
        "agent_a",
        "u",
        metadata={"title": "合同会话"},
    )

    created = session_manager.get_session(session.id, "law", "agent_a")
    assert created is not None
    assert created.status.value == "active"
    assert created.archived_at is None
    assert created.metadata == {"title": "合同会话"}

    session_manager.archive_session(session.id, "law", "agent_a")

    archived = session_manager.get_session(session.id, "law", "agent_a")
    assert archived is not None
    assert archived.status.value == "archived"
    assert archived.archived_at is not None


def test_archived_session_still_accepts_new_entries(session_manager, make_entry) -> None:
    session = session_manager.create_session("law", "agent_a", "u")
    session_manager.archive_session(session.id, "law", "agent_a")

    session_manager.append_entry(
        "law",
        "agent_a",
        make_entry(
            session_id=session.id,
            group_id="law",
            role="user",
            content="归档后继续写入",
            token_count=6,
        ),
    )

    archived = session_manager.get_session(session.id, "law", "agent_a")
    transcript = session_manager.get_transcript("law", "agent_a", session.id)

    assert archived is not None
    assert archived.status.value == "archived"
    assert len(transcript) == 1
    assert transcript[0].content == "归档后继续写入"


def test_delete_session_removes_metadata_and_transcript(session_manager, make_entry) -> None:
    session = session_manager.create_session("law", "agent_a", "u")
    session_manager.append_entry(
        "law",
        "agent_a",
        make_entry(
            session_id=session.id,
            group_id="law",
            role="user",
            content="待删除会话",
            token_count=4,
        ),
    )

    transcript_path = (
        session_manager.groups_path
        / "law"
        / "agents"
        / "agent_a"
        / "sessions"
        / f"{session.id}.jsonl"
    )
    meta_path = transcript_path.with_suffix(".meta.json")

    session_manager.delete_session(session.id, "law", "agent_a")

    assert session_manager.get_session(session.id, "law", "agent_a") is None
    assert session_manager.get_transcript("law", "agent_a", session.id) == []
    assert not transcript_path.exists()
    assert not meta_path.exists()


def test_session_can_be_recovered_by_new_manager_instance(
    tmp_storage_root: Path,
    make_entry,
) -> None:
    storage_path = tmp_storage_root / "storage"
    writer = SessionManager(storage_path)
    session = writer.create_session(
        "law",
        "agent_a",
        "u",
        metadata={"title": "恢复测试"},
    )
    writer.append_entry(
        "law",
        "agent_a",
        make_entry(
            session_id=session.id,
            group_id="law",
            role="user",
            content="第一次咨询",
            token_count=5,
        ),
    )

    recovered = SessionManager(storage_path)
    recovered_session = recovered.get_session(session.id, "law", "agent_a")
    recovered_transcript = recovered.get_transcript("law", "agent_a", session.id)
    recovered_list = recovered.list_user_sessions("law", "agent_a", "u")

    assert recovered_session is not None
    assert recovered_session.metadata == {"title": "恢复测试"}
    assert [entry.content for entry in recovered_transcript] == ["第一次咨询"]
    assert [item.id for item in recovered_list] == [session.id]


def test_recovery_with_wrong_coordinates_or_user_returns_nothing(
    tmp_storage_root: Path,
    make_entry,
) -> None:
    storage_path = tmp_storage_root / "storage"
    writer = SessionManager(storage_path)
    session = writer.create_session("law", "agent_a", "owner")
    writer.append_entry(
        "law",
        "agent_a",
        make_entry(
            session_id=session.id,
            group_id="law",
            role="user",
            content="恢复边界",
            token_count=4,
        ),
    )

    recovered = SessionManager(storage_path)

    assert recovered.get_session(session.id, "medical", "agent_a") is None
    assert recovered.get_session(session.id, "law", "agent_b") is None
    assert recovered.get_transcript("medical", "agent_a", session.id) == []
    assert recovered.get_transcript("law", "agent_b", session.id) == []
    assert recovered.list_user_sessions("law", "agent_a", "someone-else") == []
