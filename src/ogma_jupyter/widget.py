"""Main OgmaWidget class for Jupyter notebook graph visualization.

This module provides the core widget class that renders Ogma graph
visualizations in Jupyter notebooks, JupyterLab, Google Colab,
Databricks, and VSCode notebooks.
"""

import pathlib
from typing import Any, Dict, List, Optional, TypedDict

import anywidget
import traitlets

from .config import get_license_key


class NodeData(TypedDict, total=False):
    """Type definition for node data in graph."""

    id: str
    data: Dict[str, Any]


class EdgeData(TypedDict, total=False):
    """Type definition for edge data in graph."""

    id: str
    source: str
    target: str
    data: Dict[str, Any]


class GraphData(TypedDict, total=False):
    """Type definition for graph data structure."""

    nodes: List[NodeData]
    edges: List[EdgeData]


class OgmaWidget(anywidget.AnyWidget):
    """Interactive Ogma graph visualization widget for Jupyter notebooks.

    OgmaWidget renders an interactive graph visualization using the Ogma
    WebGL library. It supports bidirectional data flow between Python and
    the visualization, allowing you to programmatically update the graph
    and react to user interactions.

    Parameters
    ----------
    graph_data : dict, optional
        Initial graph data with 'nodes' and 'edges' keys.
        - nodes: List of dicts with at least 'id' key, e.g.,
          [{'id': 'n1', 'data': {'label': 'Node 1'}}, ...]
        - edges: List of dicts with 'source' and 'target' keys, e.g.,
          [{'source': 'n1', 'target': 'n2'}, ...]
        Defaults to empty graph {'nodes': [], 'edges': []}.
    license_key : str, optional
        Ogma license key. If not provided, falls back to the
        OGMA_LICENSE_KEY environment variable.
    **kwargs
        Additional keyword arguments passed to anywidget.AnyWidget.

    Attributes
    ----------
    graph_data : dict
        The current graph data. Updating this property will sync
        changes to the visualization automatically.

    Examples
    --------
    Create a simple graph with two connected nodes:

    >>> import ogma_jupyter as og
    >>> widget = og.OgmaWidget()
    >>> widget.graph_data = {
    ...     'nodes': [{'id': 'a'}, {'id': 'b'}],
    ...     'edges': [{'source': 'a', 'target': 'b'}]
    ... }
    >>> widget  # doctest: +SKIP

    Create a widget with initial data:

    >>> widget = og.OgmaWidget(graph_data={
    ...     'nodes': [
    ...         {'id': 'n1', 'data': {'label': 'First'}},
    ...         {'id': 'n2', 'data': {'label': 'Second'}},
    ...     ],
    ...     'edges': [
    ...         {'source': 'n1', 'target': 'n2'}
    ...     ]
    ... })

    Use explicit license key:

    >>> widget = og.OgmaWidget(license_key='your-license-key')

    Notes
    -----
    The widget requires an Ogma license key. Set it via:
    - The OGMA_LICENSE_KEY environment variable (recommended)
    - The license_key constructor parameter

    WebGL contexts are limited in browsers (typically 8-16 active).
    The widget automatically cleans up its WebGL context when removed,
    but having many simultaneous visualizations may cause older ones
    to go blank.

    See Also
    --------
    ogma_jupyter.demo : Create a demo widget with sample data.
    """

    # Path to compiled JavaScript module
    _esm = pathlib.Path(__file__).parent / "static" / "widget.js"

    # Synchronized state - changes sync bidirectionally with JavaScript
    graph_data: traitlets.Dict = traitlets.Dict({"nodes": [], "edges": []}).tag(sync=True)

    # License key passed to JavaScript for Ogma initialization
    _license_key: traitlets.Unicode = traitlets.Unicode("").tag(sync=True)

    def __init__(
        self,
        graph_data: Optional[GraphData] = None,
        license_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize an OgmaWidget instance.

        Parameters
        ----------
        graph_data : dict, optional
            Initial graph data with 'nodes' and 'edges' keys.
        license_key : str, optional
            Ogma license key. Falls back to OGMA_LICENSE_KEY env var.
        **kwargs
            Additional arguments passed to anywidget.AnyWidget.
        """
        super().__init__(**kwargs)

        # Resolve license key (may raise OgmaLicenseError)
        self._license_key = get_license_key(license_key)

        # Set initial graph data if provided
        if graph_data is not None:
            self.graph_data = graph_data
