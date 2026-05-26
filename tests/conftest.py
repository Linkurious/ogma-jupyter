"""Shared fixtures and helpers for ogma-jupyter tests."""

import pytest
from contextlib import contextmanager
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Sample graph data (RawGraph format — matches Ogma's native data model)
# ---------------------------------------------------------------------------

SAMPLE_GRAPH = {
    "nodes": [
        {"id": "a", "attributes": {"x": 0, "y": -60}, "data": {"label": "Alice", "type": "person", "score": 10}},
        {"id": "b", "attributes": {"x": -70, "y": 40}, "data": {"label": "Bob", "type": "org", "score": 50}},
        {"id": "c", "attributes": {"x": 70, "y": 40}, "data": {"label": "Carol", "type": "person", "score": 30}},
    ],
    "edges": [
        {"id": "e1", "source": "a", "target": "b", "data": {"weight": 1.0, "type": "owns"}},
        {"id": "e2", "source": "b", "target": "c", "data": {"weight": 2.0, "type": "works"}},
        {"id": "e3", "source": "c", "target": "a", "data": {"weight": 0.5, "type": "owns"}},
    ],
}


@pytest.fixture
def sample_graph():
    return SAMPLE_GRAPH


# ---------------------------------------------------------------------------
# Widget message capture helper
# ---------------------------------------------------------------------------

@contextmanager
def capture_messages(widget):
    """Capture messages sent from widget to frontend via widget.send()."""
    messages = []
    with patch.object(widget, "send", side_effect=lambda msg, buffers=None: messages.append(msg)):
        yield messages


@pytest.fixture
def captured_messages():
    """Return the capture_messages context manager for use in tests."""
    return capture_messages
