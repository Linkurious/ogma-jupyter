"""Tests for OgmaWidget style classes: add_class(), highlight() and
clear_highlight()."""

import pytest
from conftest import SAMPLE_GRAPH, capture_messages

from ogma_jupyter import OgmaWidget, rules
from ogma_jupyter.errors import OgmaDataError


class TestAddClass:
    def test_defaults_to_empty(self):
        assert OgmaWidget().style_classes == []

    def test_adds_class(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.add_class("dimmed", node_attributes={"opacity": 0.2}, edge_attributes={"layer": -1})
        assert w.style_classes == [
            {"name": "dimmed", "nodeAttributes": {"opacity": 0.2}, "edgeAttributes": {"layer": -1}}
        ]

    def test_same_name_replaces(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.add_class("dimmed", node_attributes={"opacity": 0.2})
        w.add_class("other", edge_attributes={"width": 1})
        w.add_class("dimmed", node_attributes={"opacity": 0.5})
        assert [c["name"] for c in w.style_classes] == ["other", "dimmed"]
        assert w.style_classes[-1]["nodeAttributes"] == {"opacity": 0.5}

    def test_accepts_rule_descriptors(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        color = rules.map(field="data.type", values={"person": "red"})
        w.add_class("typed", node_attributes={"color": color})
        assert w.style_classes[0]["nodeAttributes"]["color"] == color

    def test_empty_name_raises(self):
        with pytest.raises(OgmaDataError):
            OgmaWidget().add_class("", node_attributes={"opacity": 0.2})

    def test_non_dict_attributes_raise(self):
        with pytest.raises(OgmaDataError):
            OgmaWidget().add_class("dimmed", node_attributes="nope")


class TestHighlight:
    def test_sends_message(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.highlight(nodes=["a", "b"], edges=["e1"], duration=250)
        assert msgs == [{
            "type": "highlight",
            "className": "dimmed",
            "nodes": ["a", "b"],
            "edges": ["e1"],
            "duration": 250,
        }]

    def test_accepts_sets(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.highlight(nodes={"a"}, class_name="faded")
        assert msgs[0]["nodes"] == ["a"]
        assert msgs[0]["edges"] == []
        assert msgs[0]["className"] == "faded"

    def test_clear_highlight_sends_empty_selection(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.clear_highlight(duration=100)
        assert msgs == [{
            "type": "highlight",
            "className": "dimmed",
            "nodes": [],
            "edges": [],
            "duration": 100,
        }]
