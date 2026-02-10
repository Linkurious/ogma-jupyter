"""Ogma Jupyter - Interactive graph visualization for Jupyter notebooks.

This library brings Ogma's WebGL graph visualization capabilities to
Jupyter notebooks, JupyterLab, Google Colab, Databricks, and VSCode
notebooks. Create, interact with, and analyze graph visualizations
entirely in Python.

Quick Start
-----------
>>> import ogma_jupyter as og
>>> widget = og.OgmaWidget()
>>> widget.graph_data = {
...     'nodes': [{'id': 'a'}, {'id': 'b'}],
...     'edges': [{'source': 'a', 'target': 'b'}]
... }
>>> widget  # doctest: +SKIP

Or try the built-in demo:

>>> import ogma_jupyter as og
>>> og.demo()  # doctest: +SKIP

Classes
-------
OgmaWidget
    Main widget class for rendering Ogma graph visualizations.

Functions
---------
demo
    Create a demo widget with sample graph data.

Exceptions
----------
OgmaError
    Base exception for all ogma-jupyter errors.
OgmaLicenseError
    Raised when the Ogma license key is missing or invalid.
OgmaDataError
    Raised when graph data format is invalid.
OgmaRenderError
    Raised when widget rendering fails.

Notes
-----
Requires an Ogma license key. Set via OGMA_LICENSE_KEY environment
variable or pass directly to OgmaWidget constructor.

See Also
--------
https://doc.linkurious.com/ogma/latest/ : Ogma documentation
https://anywidget.dev : anywidget framework documentation
"""

from ._version import __version__
from .errors import OgmaDataError, OgmaError, OgmaLicenseError, OgmaRenderError
from .widget import OgmaWidget

# Show welcome message on first import
from .config import _maybe_show_welcome

_maybe_show_welcome()


def demo() -> OgmaWidget:
    """Create a demo widget with sample graph data.

    Returns a widget displaying a simple triangle graph with three
    nodes and three edges. Useful for quick testing and as a starting
    point for exploration.

    Returns
    -------
    OgmaWidget
        Widget instance with pre-populated sample graph data.

    Examples
    --------
    >>> import ogma_jupyter as og
    >>> widget = og.demo()
    >>> widget  # Display in notebook  # doctest: +SKIP

    The demo graph contains:
    - 3 nodes labeled A, B, and C
    - 3 edges forming a triangle (A-B, B-C, C-A)
    """
    return OgmaWidget(
        graph_data={
            "nodes": [
                {"id": "a", "data": {"label": "Node A"}},
                {"id": "b", "data": {"label": "Node B"}},
                {"id": "c", "data": {"label": "Node C"}},
            ],
            "edges": [
                {"id": "e1", "source": "a", "target": "b"},
                {"id": "e2", "source": "b", "target": "c"},
                {"id": "e3", "source": "c", "target": "a"},
            ],
        }
    )


__all__ = [
    "__version__",
    "OgmaWidget",
    "OgmaError",
    "OgmaLicenseError",
    "OgmaDataError",
    "OgmaRenderError",
    "demo",
]
