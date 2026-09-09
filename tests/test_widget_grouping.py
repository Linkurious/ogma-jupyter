"""Tests for OgmaWidget grouping: group_nodes(), ungroup_nodes(),
group_edges(), and ungroup_edges()."""

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


class TestGroupEdges:
    def test_group_edges_sends_message(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.group_edges()
        assert len(msgs) == 1
        assert msgs[0] == {"type": "group_edges"}

    def test_group_edges_sends_correct_type(self):
        w = OgmaWidget()
        with capture_messages(w) as msgs:
            w.group_edges()
        assert msgs[0]["type"] == "group_edges"

    def test_group_edges_forwards_key(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.group_edges(key="data.country")
        assert msgs[0] == {"type": "group_edges", "key": "data.country"}

    def test_group_edges_forwards_all_options(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.group_edges(
                key="data.country",
                selector_key="data.visible",
                data_aggregate={
                    "totalWeight": {"op": "sum", "field": "data.weight"},
                    "maxTime": {"op": "max", "field": "data.TIME"},
                },
                separate_edges_by_direction=True,
                enabled=False,
            )
        assert msgs[0] == {
            "type": "group_edges",
            "key": "data.country",
            "selectorKey": "data.visible",
            "dataAggregate": {
                "totalWeight": {"op": "sum", "field": "data.weight"},
                "maxTime": {"op": "max", "field": "data.TIME"},
            },
            "separateEdgesByDirection": True,
            "enabled": False,
        }

    def test_group_edges_data_aggregate_is_deep_copied(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        spec = {"totalWeight": {"op": "sum", "field": "data.weight"}}
        with capture_messages(w) as msgs:
            w.group_edges(data_aggregate=spec)
        spec["totalWeight"]["field"] = "data.MUTATED"
        spec["added"] = {"op": "count"}
        assert msgs[0]["dataAggregate"] == {
            "totalWeight": {"op": "sum", "field": "data.weight"},
        }


class TestUngroupEdges:
    def test_ungroup_edges_sends_message(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.ungroup_edges()
        assert len(msgs) == 1
        assert msgs[0] == {"type": "ungroup_edges"}

    def test_ungroup_edges_sends_correct_type(self):
        w = OgmaWidget()
        with capture_messages(w) as msgs:
            w.ungroup_edges()
        assert msgs[0]["type"] == "ungroup_edges"
