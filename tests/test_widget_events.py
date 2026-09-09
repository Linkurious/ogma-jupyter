"""Tests for OgmaWidget event subscription API: on(), off(), once()."""

import pytest
from conftest import SAMPLE_GRAPH

from ogma_jupyter import OgmaWidget
from ogma_jupyter.errors import OgmaDataError


def _emit(widget, event_name, payload):
    """Simulate a JS -> Python ogma_event message reaching the widget."""
    msg = {"type": "ogma_event", "event": event_name, "payload": payload}
    widget._dispatch_message(widget, msg, [])


class TestOn:
    def test_on_adds_event_name_to_subscriptions(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.on("click", lambda evt: None)
        assert w.event_subscriptions == ["click"]

    def test_on_does_not_duplicate_subscription_for_second_handler(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.on("click", lambda evt: None)
        w.on("click", lambda evt: None)
        assert w.event_subscriptions == ["click"]

    def test_on_rejects_empty_event_name(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with pytest.raises(OgmaDataError):
            w.on("", lambda evt: None)

    def test_dispatch_calls_registered_handler_with_payload(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        received = []
        w.on("click", received.append)
        _emit(w, "click", {"target": {"id": "a"}})
        assert received == [{"target": {"id": "a"}}]

    def test_dispatch_calls_all_handlers_for_same_event(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        received_a, received_b = [], []
        w.on("click", received_a.append)
        w.on("click", received_b.append)
        _emit(w, "click", {"x": 1})
        assert received_a == [{"x": 1}]
        assert received_b == [{"x": 1}]

    def test_dispatch_ignores_other_event_names(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        received = []
        w.on("click", received.append)
        _emit(w, "mouseover", {"x": 1})
        assert received == []

    def test_dispatch_ignores_non_ogma_event_messages(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        received = []
        w.on("click", received.append)
        w._dispatch_message(w, {"type": "run_layout"}, [])
        assert received == []


class TestOff:
    def test_off_removes_specific_handler(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        received_a, received_b = [], []
        w.on("click", received_a.append)
        w.on("click", received_b.append)
        w.off("click", received_a.append)
        _emit(w, "click", {"x": 1})
        assert received_a == []
        assert received_b == [{"x": 1}]

    def test_off_without_handler_removes_all_handlers(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        received = []
        w.on("click", received.append)
        w.off("click")
        _emit(w, "click", {"x": 1})
        assert received == []

    def test_off_clears_event_subscriptions_when_no_handlers_remain(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.on("click", lambda evt: None)
        w.off("click")
        assert w.event_subscriptions == []

    def test_off_keeps_subscription_while_other_handlers_remain(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        handler_a = lambda evt: None  # noqa: E731
        w.on("click", handler_a)
        w.on("click", lambda evt: None)
        w.off("click", handler_a)
        assert w.event_subscriptions == ["click"]

    def test_off_on_unknown_event_is_a_no_op(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.off("never-subscribed")  # should not raise
        assert w.event_subscriptions == []


class TestOnce:
    def test_once_fires_only_a_single_time(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        received = []
        w.once("click", received.append)
        _emit(w, "click", {"x": 1})
        _emit(w, "click", {"x": 2})
        assert received == [{"x": 1}]

    def test_once_removes_subscription_after_firing(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.once("click", lambda evt: None)
        assert w.event_subscriptions == ["click"]
        _emit(w, "click", {})
        assert w.event_subscriptions == []


class TestMultipleEvents:
    def test_independent_event_names_tracked_separately(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        click_events, hover_events = [], []
        w.on("click", click_events.append)
        w.on("mouseover", hover_events.append)
        assert set(w.event_subscriptions) == {"click", "mouseover"}
        _emit(w, "click", {"kind": "click"})
        _emit(w, "mouseover", {"kind": "mouseover"})
        assert click_events == [{"kind": "click"}]
        assert hover_events == [{"kind": "mouseover"}]
