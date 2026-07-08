"""Tests for ogma_jupyter.rules: serializable rule descriptors."""

import pytest
from ogma_jupyter import rules


# ---------------------------------------------------------------------------
# rules.map — categorical data → value
# ---------------------------------------------------------------------------

class TestRulesMap:
    def test_returns_dict_with_type(self):
        rule = rules.map(field="data.country", values={"France": "blue"})
        assert rule["type"] == "map"

    def test_contains_field(self):
        rule = rules.map(field="data.country", values={"France": "blue"})
        assert rule["field"] == "data.country"

    def test_contains_values(self):
        rule = rules.map(field="data.country", values={"France": "blue", "Italy": "green"})
        assert rule["values"] == {"France": "blue", "Italy": "green"}

    def test_fallback_optional(self):
        rule = rules.map(field="data.country", values={"France": "blue"})
        assert "fallback" not in rule or rule["fallback"] is None

    def test_fallback_included_when_provided(self):
        rule = rules.map(field="data.country", values={"France": "blue"}, fallback="gray")
        assert rule["fallback"] == "gray"

    def test_fallback_can_be_list(self):
        rule = rules.map(field="data.country", values={}, fallback=["white", "black"])
        assert rule["fallback"] == ["white", "black"]

    def test_full_example(self):
        rule = rules.map(
            field="data.country",
            values={"France": "blue", "Italy": "green", "Spain": "red"},
            fallback="gray",
        )
        assert rule == {
            "type": "map",
            "field": "data.country",
            "values": {"France": "blue", "Italy": "green", "Spain": "red"},
            "fallback": "gray",
        }

    def test_raises_when_field_missing(self):
        with pytest.raises(TypeError):
            rules.map(values={"a": "b"})

    def test_raises_when_values_not_dict(self):
        with pytest.raises((TypeError, ValueError)):
            rules.map(field="data.x", values="not-a-dict")


# ---------------------------------------------------------------------------
# rules.slices — numerical range → value
# ---------------------------------------------------------------------------

class TestRulesSlices:
    def test_returns_dict_with_type(self):
        rule = rules.slices(field="data.score", values={"nbSlices": 3, "min": 1, "max": 10})
        assert rule["type"] == "slices"

    def test_contains_field(self):
        rule = rules.slices(field="data.score", values={"nbSlices": 3, "min": 1, "max": 10})
        assert rule["field"] == "data.score"

    def test_values_as_object(self):
        values = {"nbSlices": 5, "min": 2, "max": 20}
        rule = rules.slices(field="data.score", values=values)
        assert rule["values"] == values

    def test_values_as_array(self):
        rule = rules.slices(field="data.score", values=["blue", "green", "red"])
        assert rule["values"] == ["blue", "green", "red"]

    def test_stops_as_object(self):
        rule = rules.slices(
            field="data.score",
            values={"nbSlices": 3, "min": 1, "max": 10},
            stops={"min": 0, "max": 100},
        )
        assert rule["stops"] == {"min": 0, "max": 100}

    def test_stops_as_array(self):
        rule = rules.slices(
            field="data.height",
            values=["blue", "green", "brown"],
            stops=[0, 100],
        )
        assert rule["stops"] == [0, 100]

    def test_fallback_included_when_provided(self):
        rule = rules.slices(field="data.score", values=["a", "b"], fallback="gray")
        assert rule["fallback"] == "gray"

    def test_reverse_flag(self):
        rule = rules.slices(field="data.score", values=["a", "b"], reverse=True)
        assert rule["reverse"] is True

    def test_full_example(self):
        rule = rules.slices(
            field="data.employees",
            values={"nbSlices": 5, "min": 2, "max": 10},
            stops={"min": 1, "max": 1000},
            fallback=1,
        )
        assert rule == {
            "type": "slices",
            "field": "data.employees",
            "values": {"nbSlices": 5, "min": 2, "max": 10},
            "stops": {"min": 1, "max": 1000},
            "fallback": 1,
        }

    def test_raises_when_field_missing(self):
        with pytest.raises(TypeError):
            rules.slices(values=["a", "b"])


# ---------------------------------------------------------------------------
# rules.template — text template from data properties
# ---------------------------------------------------------------------------

class TestRulesTemplate:
    def test_returns_dict_with_type(self):
        rule = rules.template("{{name}}")
        assert rule["type"] == "template"

    def test_contains_template_string(self):
        rule = rules.template("Age: {{age}}\nName: {{name}}")
        assert rule["template"] == "Age: {{age}}\nName: {{name}}"

    def test_full_example(self):
        rule = rules.template("{{name}} ({{age}})")
        assert rule == {"type": "template", "template": "{{name}} ({{age}})"}

    def test_raises_when_not_string(self):
        with pytest.raises((TypeError, ValueError)):
            rules.template(123)

    def test_empty_template_allowed(self):
        rule = rules.template("")
        assert rule["template"] == ""
