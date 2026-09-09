"""Tests for OgmaWidget incremental-mutation methods: add_nodes(), add_edges(),
add_graph().

These append to the ``_pending_ops`` synced traitlet with a monotonic ``seq``
field, so the frontend can pick up only the entries it hasn't applied yet —
whether they were enqueued before or after the widget was displayed.
"""

import pytest

from ogma_jupyter import OgmaWidget
from ogma_jupyter.errors import OgmaDataError
from conftest import SAMPLE_GRAPH


class TestAddNodes:
    def test_empty_by_default(self):
        w = OgmaWidget()
        assert w._pending_ops == []

    def test_appends_one_op(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.add_nodes([{"id": "z", "data": {"label": "Zoe"}}])
        assert w._pending_ops == [
            {"seq": 1, "kind": "add_nodes", "nodes": [{"id": "z", "data": {"label": "Zoe"}}]}
        ]

    def test_seq_increments(self):
        w = OgmaWidget()
        w.add_nodes([{"id": "a"}])
        w.add_nodes([{"id": "b"}])
        assert [op["seq"] for op in w._pending_ops] == [1, 2]

    def test_rejects_non_list(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError):
            w.add_nodes({"id": "z"})  # type: ignore[arg-type]

    def test_rejects_non_dict_entry(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError):
            w.add_nodes(["z"])  # type: ignore[list-item]


class TestAddEdges:
    def test_appends_one_op(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.add_edges([{"id": "e10", "source": "a", "target": "b"}])
        assert w._pending_ops == [
            {
                "seq": 1,
                "kind": "add_edges",
                "edges": [{"id": "e10", "source": "a", "target": "b"}],
            }
        ]

    def test_rejects_missing_source(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError):
            w.add_edges([{"id": "e10", "target": "b"}])

    def test_rejects_missing_target(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError):
            w.add_edges([{"id": "e10", "source": "a"}])


class TestAddGraph:
    def test_appends_one_op(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.add_graph({"nodes": [{"id": "z"}], "edges": [{"id": "e10", "source": "a", "target": "z"}]})
        assert w._pending_ops == [
            {
                "seq": 1,
                "kind": "add_graph",
                "graph": {
                    "nodes": [{"id": "z"}],
                    "edges": [{"id": "e10", "source": "a", "target": "z"}],
                },
            }
        ]

    def test_rejects_missing_nodes(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError):
            w.add_graph({"edges": []})

    def test_rejects_missing_edges(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError):
            w.add_graph({"nodes": []})


class TestMixedOps:
    def test_ops_share_monotonic_seq(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.add_nodes([{"id": "z"}])
        w.add_edges([{"id": "e10", "source": "a", "target": "z"}])
        w.add_graph({"nodes": [{"id": "y"}], "edges": []})
        seqs = [op["seq"] for op in w._pending_ops]
        kinds = [op["kind"] for op in w._pending_ops]
        assert seqs == [1, 2, 3]
        assert kinds == ["add_nodes", "add_edges", "add_graph"]
