"""Tests for OgmaWidget style rules: add_style_rule(), style_rules traitlet."""

import pytest
from ogma_jupyter import OgmaWidget, rules
from ogma_jupyter.errors import OgmaDataError

from conftest import SAMPLE_GRAPH


# ---------------------------------------------------------------------------
# style_rules traitlet defaults
# ---------------------------------------------------------------------------

class TestStyleRulesDefault:
    def test_empty_by_default(self):
        w = OgmaWidget()
        assert w.style_rules == []

    def test_can_be_set_at_construction(self):
        rule = {"nodeAttributes": {"color": "red"}}
        w = OgmaWidget(style_rules=[rule])
        assert w.style_rules == [rule]


# ---------------------------------------------------------------------------
# add_style_rule() — node attributes
# ---------------------------------------------------------------------------

class TestAddStyleRuleNodes:
    def test_static_node_color(self):
        w = OgmaWidget()
        w.add_style_rule(node_attributes={"color": "red"})
        assert len(w.style_rules) == 1
        assert w.style_rules[0]["nodeAttributes"]["color"] == "red"

    def test_map_rule_on_node_color(self):
        w = OgmaWidget()
        color_rule = rules.map(field="data.type", values={"person": "blue", "org": "green"})
        w.add_style_rule(node_attributes={"color": color_rule})
        stored = w.style_rules[0]["nodeAttributes"]["color"]
        assert stored["type"] == "map"
        assert stored["field"] == "data.type"

    def test_slices_rule_on_node_radius(self):
        w = OgmaWidget()
        size_rule = rules.slices(field="data.score", values={"nbSlices": 3, "min": 2, "max": 10})
        w.add_style_rule(node_attributes={"radius": size_rule})
        stored = w.style_rules[0]["nodeAttributes"]["radius"]
        assert stored["type"] == "slices"

    def test_template_rule_on_node_text(self):
        w = OgmaWidget()
        text_rule = rules.template("{{label}}")
        w.add_style_rule(node_attributes={"text": {"content": text_rule}})
        stored = w.style_rules[0]["nodeAttributes"]["text"]["content"]
        assert stored["type"] == "template"
        assert stored["template"] == "{{label}}"

    def test_multiple_node_attributes(self):
        w = OgmaWidget()
        w.add_style_rule(node_attributes={
            "color": rules.map(field="data.type", values={"person": "blue"}),
            "radius": rules.slices(field="data.score", values=["sm", "md", "lg"]),
        })
        rule = w.style_rules[0]["nodeAttributes"]
        assert "color" in rule
        assert "radius" in rule


# ---------------------------------------------------------------------------
# add_style_rule() — edge attributes
# ---------------------------------------------------------------------------

class TestAddStyleRuleEdges:
    def test_static_edge_color(self):
        w = OgmaWidget()
        w.add_style_rule(edge_attributes={"color": "gray"})
        assert w.style_rules[0]["edgeAttributes"]["color"] == "gray"

    def test_map_rule_on_edge_color(self):
        w = OgmaWidget()
        color_rule = rules.map(field="data.type", values={"owns": "red", "works": "blue"})
        w.add_style_rule(edge_attributes={"color": color_rule})
        stored = w.style_rules[0]["edgeAttributes"]["color"]
        assert stored["type"] == "map"


# ---------------------------------------------------------------------------
# add_style_rule() — combined node + edge
# ---------------------------------------------------------------------------

class TestAddStyleRuleCombined:
    def test_node_and_edge_in_same_rule(self):
        w = OgmaWidget()
        w.add_style_rule(
            node_attributes={"color": "blue"},
            edge_attributes={"color": "gray"},
        )
        rule = w.style_rules[0]
        assert "nodeAttributes" in rule
        assert "edgeAttributes" in rule

    def test_multiple_rules_accumulate(self):
        w = OgmaWidget()
        w.add_style_rule(node_attributes={"color": "blue"})
        w.add_style_rule(node_attributes={"radius": 10})
        assert len(w.style_rules) == 2


# ---------------------------------------------------------------------------
# add_style_rule() — validation
# ---------------------------------------------------------------------------

class TestAddStyleRuleValidation:
    def test_raises_when_no_attributes_provided(self):
        w = OgmaWidget()
        with pytest.raises((ValueError, OgmaDataError)):
            w.add_style_rule()

    def test_raises_when_node_attributes_not_dict(self):
        w = OgmaWidget()
        with pytest.raises((TypeError, OgmaDataError)):
            w.add_style_rule(node_attributes="red")


# ---------------------------------------------------------------------------
# Style rules sync to JS (traitlet is synced)
# ---------------------------------------------------------------------------

class TestStyleRulesSync:
    def test_style_rules_traitlet_is_synced(self):
        """style_rules should have sync=True so it reaches the JS side."""
        import traitlets
        trait = OgmaWidget.class_traits()["style_rules"]
        assert trait.metadata.get("sync") is True
