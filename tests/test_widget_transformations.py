"""Tests for OgmaWidget transformation helpers: on_groups_updated(),
set_transformation_animation() and trigger_groups_updated()."""

import pytest
from conftest import SAMPLE_GRAPH, capture_messages

from ogma_jupyter import OgmaWidget
from ogma_jupyter.errors import OgmaDataError


class TestOnGroupsUpdated:
    def test_defaults_to_none(self):
        assert OgmaWidget().groups_layout is None

    def test_sets_layout_spec(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.on_groups_updated("force", gpu=True)
        assert w.groups_layout == {"name": "force", "params": {"gpu": True}}

    def test_converts_snake_case(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.on_groups_updated("hierarchical", layer="level", level_distance=50)
        assert w.groups_layout == {
            "name": "hierarchical",
            "params": {"layer": "level", "levelDistance": 50},
        }

    def test_unknown_option_warns(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with pytest.warns(UserWarning, match="bogus"):
            w.on_groups_updated("force", bogus=1)

    def test_unknown_layout_raises(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with pytest.raises(OgmaDataError):
            w.on_groups_updated("nope")

    def test_clear(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        w.on_groups_updated("force")
        w.on_groups_updated()
        assert w.groups_layout is None


class TestTransformationAnimation:
    def test_sets_spec(self):
        w = OgmaWidget()
        w.set_transformation_animation(duration=200, easing="quadraticInOut")
        assert w.transformation_animation == {"duration": 200, "easing": "quadraticInOut"}

    def test_no_argument_clears(self):
        w = OgmaWidget()
        w.set_transformation_animation(duration=200)
        w.set_transformation_animation()
        assert w.transformation_animation is None


class TestTriggerGroupsUpdated:
    def test_sends_message(self):
        w = OgmaWidget(graph_data=SAMPLE_GRAPH)
        with capture_messages(w) as msgs:
            w.trigger_groups_updated()
        assert msgs == [{"type": "trigger_groups_updated"}]


class TestOptions:
    def test_constructor_options(self):
        w = OgmaWidget(options={"backgroundColor": "#08090a"})
        assert w.ogma_options == {"backgroundColor": "#08090a"}

    def test_set_options_merges(self):
        w = OgmaWidget(options={"backgroundColor": "#08090a"})
        w.set_options({"interactions": {"zoom": {"onDoubleClick": True}}})
        assert w.ogma_options == {
            "backgroundColor": "#08090a",
            "interactions": {"zoom": {"onDoubleClick": True}},
        }

    def test_set_options_rejects_non_dict(self):
        with pytest.raises(OgmaDataError):
            OgmaWidget().set_options(["nope"])
