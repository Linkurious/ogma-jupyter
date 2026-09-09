"""Tests for OgmaWidget.show_node_tooltip() / hide_node_tooltip()."""

import pytest

from ogma_jupyter import OgmaWidget
from ogma_jupyter.errors import OgmaDataError


class TestNodeTooltip:
    def test_disabled_by_default(self):
        w = OgmaWidget()
        assert w.node_tooltip is None

    def test_show_default_enables_true(self):
        w = OgmaWidget()
        w.show_node_tooltip()
        assert w.node_tooltip is True

    def test_show_with_template_stores_string(self):
        w = OgmaWidget()
        w.show_node_tooltip("<b>{{id}}</b>")
        assert w.node_tooltip == "<b>{{id}}</b>"

    def test_show_with_false_disables(self):
        w = OgmaWidget()
        w.show_node_tooltip("<b>{{id}}</b>")
        w.show_node_tooltip(False)
        assert w.node_tooltip is None

    def test_show_with_none_disables(self):
        w = OgmaWidget()
        w.show_node_tooltip(True)
        w.show_node_tooltip(None)
        assert w.node_tooltip is None

    def test_hide_disables(self):
        w = OgmaWidget()
        w.show_node_tooltip("<b>{{id}}</b>")
        w.hide_node_tooltip()
        assert w.node_tooltip is None

    def test_rejects_non_string_template(self):
        w = OgmaWidget()
        with pytest.raises(OgmaDataError):
            w.show_node_tooltip(123)  # type: ignore[arg-type]
