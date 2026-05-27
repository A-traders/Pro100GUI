"""Tests for the orchestrator event bus."""

import pytest

from pro100gui.orchestrator.events import (
    EventBus,
    EventRecorder,
    PhaseFinished,
    PhaseStarted,
    SessionStarted,
)


def test_subscribe_and_publish():
    bus = EventBus()
    seen: list = []
    bus.subscribe(seen.append)
    bus.publish(SessionStarted(session_id="x", n_phases=3))
    assert len(seen) == 1
    assert isinstance(seen[0], SessionStarted)
    assert seen[0].session_id == "x"


def test_unsubscribe_stops_delivery():
    bus = EventBus()
    seen: list = []
    bus.subscribe(seen.append)
    bus.unsubscribe(seen.append)
    bus.publish(SessionStarted(session_id="x"))
    assert seen == []


def test_unsubscribe_unknown_is_noop():
    bus = EventBus()
    bus.unsubscribe(lambda _: None)  # must not raise


def test_no_duplicate_subscriptions():
    bus = EventBus()
    seen: list = []
    bus.subscribe(seen.append)
    bus.subscribe(seen.append)
    assert bus.subscriber_count() == 1
    bus.publish(SessionStarted())
    assert len(seen) == 1


def test_broken_subscriber_is_dropped():
    bus = EventBus()
    calls: list = []

    def broken(e):
        calls.append("b")
        raise RuntimeError("intentional")

    def fine(e):
        calls.append("f")

    bus.subscribe(broken)
    bus.subscribe(fine)
    bus.publish(SessionStarted())
    # fine still gets called even after broken raises
    assert "f" in calls
    # broken is dropped after first failure
    bus.publish(SessionStarted())
    assert calls.count("b") == 1


def test_event_recorder_collects_in_order():
    bus = EventBus()
    rec = EventRecorder()
    bus.subscribe(rec)
    bus.publish(SessionStarted(session_id="s1"))
    bus.publish(PhaseStarted(job_key="M5.back", tf="M5", phase="back"))
    bus.publish(PhaseFinished(job_key="M5.back", ok=True, duration_s=1.0))
    assert len(rec.events) == 3
    assert isinstance(rec.events[0], SessionStarted)
    assert isinstance(rec.events[1], PhaseStarted)
    assert isinstance(rec.events[2], PhaseFinished)


def test_event_recorder_of_type_filters():
    bus = EventBus()
    rec = EventRecorder()
    bus.subscribe(rec)
    bus.publish(SessionStarted())
    bus.publish(PhaseStarted())
    bus.publish(PhaseFinished())
    started = rec.of_type(PhaseStarted)
    assert len(started) == 1
    assert isinstance(started[0], PhaseStarted)


def test_event_has_timestamp():
    e = SessionStarted(session_id="x")
    assert e.ts is not None
    assert e.ts.tzinfo is not None
