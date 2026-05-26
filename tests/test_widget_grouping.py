"""Tests for OgmaWidget grouping: group_nodes() and ungroup_nodes()."""

import pytest

from ogma_jupyter import OgmaWidget
from conftest import SAMPLE_GRAPH, capture_messages


class TestGroupNodes:
    def test_group_nodes_sends_message(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.group_nodes(key="data.type")
        assert len(msgs) == 1
        assert msgs[0] == {"type": "group_nodes", "key": "data.type"}

    def test_group_nodes_nested_path(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.group_nodes(key="data.department.name")
        assert msgs[0]["key"] == "data.department.name"

    def test_group_nodes_sends_correct_type(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.group_nodes(key="data.type")
        assert msgs[0]["type"] == "group_nodes"


class TestUngroupNodes:
    def test_ungroup_nodes_sends_message(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.ungroup_nodes()
        assert len(msgs) == 1
        assert msgs[0] == {"type": "ungroup_nodes"}

    def test_ungroup_nodes_sends_correct_type(self):
        w = OgmaWidget()
        with capture_messages(w) as msgs:
            w.ungroup_nodes()
        assert msgs[0]["type"] == "ungroup_nodes"
