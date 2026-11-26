"""Tests for OgmaWidget grouping: group_nodes(), ungroup_nodes(),
group_edges(), and ungroup_edges().

Grouping state is a synced traitlet (``node_grouping`` / ``edge_grouping``), not
a custom message — that way it survives being set before the widget is
displayed, which would otherwise drop a ``self.send(...)`` on the floor.
"""

import pytest

from ogma_jupyter import OgmaWidget
from ogma_jupyter.errors import OgmaDataError
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


class TestGroupNodesOptions:
    def test_group_nodes_list_key(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_nodes(key=("data.type", "data.country"))
        assert w.node_grouping == {"key": ["data.type", "data.country"]}

    def test_group_nodes_forwards_all_options(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_nodes(
            key="data.victimOf",
            selector_key="data.victim",
            id_prefix="victims-",
            data={"kind": "COMPUTER"},
            data_aggregate={"total": {"op": "sum", "field": "data.score"}},
            label="{{count}} victims ({{groupId}})",
            edge_data_aggregate={"firstSeen": {"op": "min", "field": "data.TIME"}},
            show_contents=True,
            padding=4,
            group_layout="grid",
            enabled=False,
        )
        assert w.node_grouping == {
            "key": "data.victimOf",
            "selectorKey": "data.victim",
            "idPrefix": "victims-",
            "data": {"kind": "COMPUTER"},
            "dataAggregate": {"total": {"op": "sum", "field": "data.score"}},
            "label": "{{count}} victims ({{groupId}})",
            "edgeDataAggregate": {"firstSeen": {"op": "min", "field": "data.TIME"}},
            "showContents": True,
            "padding": 4,
            "groupLayout": {"name": "grid", "params": {}},
            "enabled": False,
        }

    def test_group_layout_dict_is_normalized(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_nodes(key="data.type", group_layout={"name": "grid", "col_distance": 10})
        assert w.node_grouping["groupLayout"] == {"name": "grid", "params": {"colDistance": 10}}

    def test_group_layout_unknown_raises(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with pytest.raises(OgmaDataError):
            w.group_nodes(key="data.type", group_layout="nope")

    def test_group_nodes_data_is_copied(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        data = {"kind": "COMPUTER"}
        w.group_nodes(key="data.type", data=data)
        data["kind"] = "MUTATED"
        assert w.node_grouping["data"] == {"kind": "COMPUTER"}


class TestEnableNodeGrouping:
    def test_enable_keeps_spec(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_nodes(key="data.type", show_contents=True, enabled=False)
        assert not w.node_grouping_enabled
        w.enable_node_grouping()
        assert w.node_grouping == {"key": "data.type", "showContents": True, "enabled": True}
        assert w.node_grouping_enabled

    def test_disable(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_nodes(key="data.type")
        assert w.node_grouping_enabled
        w.disable_node_grouping()
        assert w.node_grouping == {"key": "data.type", "enabled": False}

    def test_enable_without_grouping_raises(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with pytest.raises(OgmaDataError):
            w.enable_node_grouping()


class TestGroupEdgesOptions:
    def test_group_edges_list_key(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.group_edges(key=["data.kind", "data.AUTH_TYPE"], label="")
        assert w.edge_grouping == {"key": ["data.kind", "data.AUTH_TYPE"], "label": ""}
