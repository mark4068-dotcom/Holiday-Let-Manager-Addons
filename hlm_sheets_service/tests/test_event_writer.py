"""Idempotency tests for the private event write boundary."""

from uuid import uuid4

import pytest
from hlm_sheets_service.app import append_events_idempotently


def event(event_id=None):
    return {"event_id": event_id or str(uuid4())}


class FakeWriter:
    def __init__(self, existing=(), fail_after_append=False, fail_before_append=False):
        self.ids = set(existing)
        self.rows = []
        self.fail_after_append = fail_after_append
        self.fail_before_append = fail_before_append

    def existing_event_ids(self):
        return set(self.ids)

    def append_rows(self, rows):
        if self.fail_before_append:
            raise TimeoutError("request did not reach Google")
        self.rows.extend(rows)
        self.ids.update(row[1] for row in rows)
        if self.fail_after_append:
            raise TimeoutError("response was lost")


def test_existing_and_same_batch_duplicates_are_not_appended() -> None:
    existing_id = str(uuid4())
    new_id = str(uuid4())
    writer = FakeWriter(existing={existing_id})

    accepted, duplicates = append_events_idempotently(
        writer,
        [event(existing_id), event(new_id), event(new_id)],
    )

    assert accepted == [new_id]
    assert duplicates == [existing_id, new_id]
    assert len(writer.rows) == 1


def test_lost_response_after_successful_append_is_reconciled() -> None:
    new_id = str(uuid4())
    writer = FakeWriter(fail_after_append=True)

    accepted, duplicates = append_events_idempotently(writer, [event(new_id)])

    assert accepted == [new_id]
    assert duplicates == []
    assert writer.ids == {new_id}


def test_failed_append_that_did_not_commit_remains_retryable() -> None:
    writer = FakeWriter(fail_before_append=True)

    with pytest.raises(TimeoutError, match="did not reach"):
        append_events_idempotently(writer, [event()])
