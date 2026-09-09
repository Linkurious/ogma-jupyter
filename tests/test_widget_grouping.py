"""Tests for OgmaWidget grouping: group_nodes(), ungroup_nodes(),
group_edges(), and ungroup_edges().

Grouping state is a synced traitlet (``node_grouping`` / ``edge_grouping``), not
a custom message — that way it survives being set before the widget is
displayed, which would otherwise drop a ``self.send(...)`` on the floor.
"""

import pytest

from ogma_jupyter import OgmaWidget
from conftest import SAMPLE_GRAPH


class TestGroupNodes:
    def test_group_nodes_sets_traitlet(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        assert w.node_grouping is None
        w.group_nodes(key="data.type")
        assert w.node_grouping == {"key": "data.type"}

    def test_group_nodes_nested_path(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_nodes(key="data.department.name")
        assert w.node_grouping == {"key": "data.department.name"}

    def test_group_nodes_replaces_previous(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_nodes(key="data.type")
        w.group_nodes(key="data.country")
        assert w.node_grouping == {"key": "data.country"}


class TestUngroupNodes:
    def test_ungroup_nodes_clears_traitlet(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_nodes(key="data.type")
        w.ungroup_nodes()
        assert w.node_grouping is None

    def test_ungroup_nodes_when_not_grouped(self):
        w = OgmaWidget()
        w.ungroup_nodes()
        assert w.node_grouping is None


class TestGroupEdges:
    def test_group_edges_sets_empty_spec(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        assert w.edge_grouping is None
        w.group_edges()
        assert w.edge_grouping == {}

    def test_group_edges_forwards_key(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_edges(key="data.country")
        assert w.edge_grouping == {"key": "data.country"}

    def test_group_edges_forwards_all_options(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
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
        assert w.edge_grouping == {
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
        w.group_edges(data_aggregate=spec)
        spec["totalWeight"]["field"] = "data.MUTATED"
        spec["added"] = {"op": "count"}
        assert w.edge_grouping["dataAggregate"] == {
            "totalWeight": {"op": "sum", "field": "data.weight"},
        }

    def test_group_edges_replaces_previous(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_edges(key="data.a")
        w.group_edges(key="data.b")
        assert w.edge_grouping == {"key": "data.b"}


class TestUngroupEdges:
    def test_ungroup_edges_clears_traitlet(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_edges(key="data.country")
        w.ungroup_edges()
        assert w.edge_grouping is None

    def test_ungroup_edges_when_not_grouped(self):
        w = OgmaWidget()
        w.ungroup_edges()
        assert w.edge_grouping is None
