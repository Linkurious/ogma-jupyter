"""Tests for OgmaWidget layout: run_layout() method and JS message."""

import pytest
from unittest.mock import patch

from ogma_jupyter import OgmaWidget
from ogma_jupyter.errors import OgmaDataError
from ogma_jupyter.widget import VALID_LAYOUTS
from conftest import SAMPLE_GRAPH, capture_messages


# ---------------------------------------------------------------------------
# Valid layout names
# ---------------------------------------------------------------------------

class TestValidLayouts:
    def test_valid_layouts_is_defined(self):
        assert isinstance(VALID_LAYOUTS, (set, frozenset, list, tuple))
        assert len(VALID_LAYOUTS) > 0

    def test_common_layouts_are_valid(self):
        for name in ["force", "hierarchical", "radial", "sequential", "grid"]:
            assert name in VALID_LAYOUTS, f"Expected '{name}' in VALID_LAYOUTS"


# ---------------------------------------------------------------------------
# run_layout() sends correct message
# ---------------------------------------------------------------------------

class TestRunLayout:
    def test_run_layout_sends_message(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.run_layout("force")
        assert len(msgs) == 1
        assert msgs[0]["type"] == "run_layout"
        assert msgs[0]["name"] == "force"

    def test_run_layout_includes_empty_options_by_default(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.run_layout("force")
        assert msgs[0]["options"] == {}

    def test_run_layout_passes_options(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.run_layout("force", duration=300, steps=100)
        assert msgs[0]["options"] == {"duration": 300, "steps": 100}

    def test_run_hierarchical_with_direction(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.run_layout("hierarchical", direction="LR")
        assert msgs[0]["name"] == "hierarchical"
        assert msgs[0]["options"]["direction"] == "LR"

    def test_all_valid_layouts_send_message(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        for layout_name in VALID_LAYOUTS:
            with capture_messages(w) as msgs:
                w.run_layout(layout_name)
            assert msgs[0]["name"] == layout_name


# ---------------------------------------------------------------------------
# run_layout() validation
# ---------------------------------------------------------------------------

class TestRunLayoutValidation:
    def test_raises_on_unknown_layout_name(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError, match="Unknown layout"):
            w.run_layout("not_a_real_layout")

    def test_error_message_mentions_valid_layouts(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError) as exc_info:
            w.run_layout("foobar")
        # Error should be helpful — mention what's valid
        assert any(name in str(exc_info.value) for name in VALID_LAYOUTS)

    def test_raises_on_empty_layout_name(self):
        w = OgmaWidget()
        with pytest.raises((OgmaDataError, ValueError)):
            w.run_layout("")


# ---------------------------------------------------------------------------
# layout traitlet (initial layout at construction)
# ---------------------------------------------------------------------------

class TestLayoutTraitlet:
    def test_default_graph_layout_is_none(self):
        w = OgmaWidget()
        assert w.graph_layout is None

    def test_graph_layout_set_at_construction(self):
        w = OgmaWidget(graph_layout={"name": "force"})
        assert w.graph_layout == {"name": "force"}

    def test_graph_layout_traitlet_is_synced(self):
        trait = OgmaWidget.class_traits()["graph_layout"]
        assert trait.metadata.get("sync") is True
