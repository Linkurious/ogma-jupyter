"""Tests for OgmaWidget core: instantiation, license key, graph_data, demo."""

import os
import pytest
from unittest.mock import patch

import ogma_jupyter as og
from ogma_jupyter import OgmaWidget
from ogma_jupyter.errors import OgmaDataError, OgmaLicenseError

from conftest import SAMPLE_GRAPH


# ---------------------------------------------------------------------------
# Module-level license key API
# ---------------------------------------------------------------------------

class TestSetLicense:
    def setup_method(self):
        og.set_license("")  # reset before each test

    def test_set_license_stores_key(self):
        og.set_license("my-key")
        assert og._license_key == "my-key"

    def test_widget_inherits_module_license(self):
        og.set_license("module-key")
        w = OgmaWidget()
        assert w._license_key == "module-key"

    def test_widget_constructor_overrides_module_license(self):
        og.set_license("module-key")
        w = OgmaWidget(license_key="override-key")
        assert w._license_key == "override-key"

    def test_env_var_fallback(self):
        og.set_license("")
        with patch.dict(os.environ, {"OGMA_LICENSE_KEY": "env-key"}):
            w = OgmaWidget()
            assert w._license_key == "env-key"

    def test_constructor_takes_precedence_over_env_var(self):
        with patch.dict(os.environ, {"OGMA_LICENSE_KEY": "env-key"}):
            w = OgmaWidget(license_key="explicit-key")
            assert w._license_key == "explicit-key"

    def test_set_license_clears_previous_key(self):
        og.set_license("first-key")
        og.set_license("")
        w = OgmaWidget()
        assert w._license_key == ""


# ---------------------------------------------------------------------------
# Widget instantiation
# ---------------------------------------------------------------------------

class TestWidgetInstantiation:
    def test_default_graph_data_is_empty(self):
        w = OgmaWidget()
        assert w.graph_data == {"nodes": [], "edges": []}

    def test_constructor_accepts_graph_data(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        assert len(w.graph_data["nodes"]) == 3
        assert len(w.graph_data["edges"]) == 3

    def test_graph_data_can_be_set_after_init(self):
        w = OgmaWidget()
        w.graph_data = SAMPLE_GRAPH
        assert len(w.graph_data["nodes"]) == 3

    def test_default_style_rules_are_empty(self):
        w = OgmaWidget()
        assert w.style_rules == []

    def test_default_graph_layout_is_none(self):
        w = OgmaWidget()
        assert w.graph_layout is None


# ---------------------------------------------------------------------------
# graph_data validation
# ---------------------------------------------------------------------------

class TestGraphDataValidation:
    def test_accepts_empty_graph(self):
        w = OgmaWidget(graph_data={"nodes": [], "edges": []})
        assert w.graph_data["nodes"] == []

    def test_accepts_nodes_only(self):
        w = OgmaWidget(graph_data={"nodes": [{"id": "a"}], "edges": []})
        assert len(w.graph_data["nodes"]) == 1

    def test_raises_when_graph_data_is_not_dict(self):
        with pytest.raises(OgmaDataError, match="graph_data must be a dict"):
            OgmaWidget(graph_data="bad")

    def test_raises_when_nodes_missing(self):
        with pytest.raises(OgmaDataError, match="nodes"):
            OgmaWidget(graph_data={"edges": []})

    def test_raises_when_edges_missing(self):
        with pytest.raises(OgmaDataError, match="edges"):
            OgmaWidget(graph_data={"nodes": []})

    def test_raises_when_nodes_is_not_list(self):
        with pytest.raises(OgmaDataError, match="nodes"):
            OgmaWidget(graph_data={"nodes": "bad", "edges": []})

    def test_raises_when_edges_is_not_list(self):
        with pytest.raises(OgmaDataError, match="edges"):
            OgmaWidget(graph_data={"nodes": [], "edges": "bad"})

    def test_raises_when_node_is_not_dict(self):
        with pytest.raises(OgmaDataError, match="node"):
            OgmaWidget(graph_data={"nodes": ["not-a-dict"], "edges": []})

    def test_raises_when_edge_missing_source(self):
        with pytest.raises(OgmaDataError, match="source"):
            OgmaWidget(graph_data={"nodes": [], "edges": [{"target": "b"}]})

    def test_raises_when_edge_missing_target(self):
        with pytest.raises(OgmaDataError, match="target"):
            OgmaWidget(graph_data={"nodes": [], "edges": [{"source": "a"}]})


# ---------------------------------------------------------------------------
# graph_data coordinate normalization
# ---------------------------------------------------------------------------

class TestGraphDataNormalization:
    def test_lifts_root_level_xy_into_attributes(self):
        with pytest.warns(UserWarning, match="attributes"):
            w = OgmaWidget(
                graph_data={"nodes": [{"id": "a", "x": 10, "y": 20}], "edges": []}
            )
        node = w.graph_data["nodes"][0]
        assert node["attributes"] == {"x": 10, "y": 20}
        assert "x" not in node
        assert "y" not in node

    def test_merges_with_existing_attributes(self):
        with pytest.warns(UserWarning):
            w = OgmaWidget(
                graph_data={
                    "nodes": [
                        {"id": "a", "x": 10, "attributes": {"color": "red"}}
                    ],
                    "edges": [],
                }
            )
        node = w.graph_data["nodes"][0]
        assert node["attributes"] == {"color": "red", "x": 10}

    def test_existing_attribute_coordinates_take_precedence(self):
        with pytest.warns(UserWarning):
            w = OgmaWidget(
                graph_data={
                    "nodes": [
                        {"id": "a", "x": 10, "attributes": {"x": 99}}
                    ],
                    "edges": [],
                }
            )
        node = w.graph_data["nodes"][0]
        assert node["attributes"]["x"] == 99
        assert "x" not in node

    def test_no_warning_when_coordinates_already_nested(self, recwarn):
        w = OgmaWidget(
            graph_data={
                "nodes": [{"id": "a", "attributes": {"x": 0, "y": 0}}],
                "edges": [],
            }
        )
        assert w.graph_data["nodes"][0]["attributes"] == {"x": 0, "y": 0}
        assert len(recwarn) == 0



# ---------------------------------------------------------------------------
# demo() function
# ---------------------------------------------------------------------------

class TestDemo:
    def test_demo_returns_ogma_widget(self):
        w = og.demo()
        assert isinstance(w, OgmaWidget)

    def test_demo_has_nodes(self):
        w = og.demo()
        assert len(w.graph_data["nodes"]) > 0

    def test_demo_has_edges(self):
        w = og.demo()
        assert len(w.graph_data["edges"]) > 0

    def test_demo_uses_rawgraph_format(self):
        """Nodes should use attributes dict, not top-level x/y."""
        w = og.demo()
        for node in w.graph_data["nodes"]:
            assert isinstance(node, dict)
            assert "id" in node
            # positions live in attributes, not at top level
            if "x" in node or "y" in node:
                pytest.fail("Node positions should be in node['attributes'], not top-level")
