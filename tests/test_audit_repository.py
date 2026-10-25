
import json

import pytest

from app.storage.audit_repository import AuditRepository


@pytest.fixture
def repository(tmp_path):
    return AuditRepository(tmp_path / "audit.db")


def test_record_and_retrieve_event(repository):
    event = {
        "event_type": "verification_completed",
        "timestamp": "2026-10-22T10:00:00+00:00",
        "details": {
            "status": "VERIFIED",
            "human_review_required": False,
        },
    }

    event_id = repository.record_event("RUN001", event)

    saved_events = repository.get_events("RUN001")

    assert event_id > 0
    assert len(saved_events) == 1
    assert saved_events[0]["event_type"] == "verification_completed"
    assert saved_events[0]["details"]["status"] == "VERIFIED"


def test_events_are_separated_by_run(repository):
    repository.record_event(
        "RUN001",
        {"event_type": "started", "details": {}},
    )
    repository.record_event(
        "RUN002",
        {"event_type": "started", "details": {}},
    )

    assert len(repository.get_events("RUN001")) == 1
    assert len(repository.get_events("RUN002")) == 1


def test_record_multiple_events(repository):
    events = [
        {"event_type": "started", "details": {}},
        {
            "event_type": "verification_completed",
            "details": {"status": "VERIFIED"},
        },
    ]

    ids = repository.record_events("RUN003", events)

    saved_events = repository.get_events("RUN003")

    assert len(ids) == 2
    assert len(saved_events) == 2
    assert saved_events[0]["event_type"] == "started"
    assert saved_events[1]["event_type"] == "verification_completed"


def test_empty_run_id_is_rejected(repository):
    with pytest.raises(ValueError):
        repository.record_event(
            "",
            {"event_type": "started", "details": {}},
        )


def test_empty_event_type_is_rejected(repository):
    with pytest.raises(ValueError):
        repository.record_event(
            "RUN004",
            {"event_type": "", "details": {}},
        )


def test_database_preserves_events_after_reopening(tmp_path):
    db_path = tmp_path / "persistent_audit.db"

    first_repository = AuditRepository(db_path)
    first_repository.record_event(
        "RUN005",
        {
            "event_type": "verification_completed",
            "details": {"status": "VERIFIED"},
        },
    )

    second_repository = AuditRepository(db_path)
    events = second_repository.get_events("RUN005")

    assert len(events) == 1
    assert events[0]["details"]["status"] == "VERIFIED"
