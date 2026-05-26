"""Main OgmaWidget class for Jupyter notebook graph visualization."""

import pathlib
from typing import Any, Dict, Optional

import anywidget
import traitlets

from .config import get_license_key
from .errors import OgmaDataError

# Valid Ogma layout algorithm names
VALID_LAYOUTS: frozenset = frozenset({
    "force",
    "forceatlas2",
    "hierarchical",
    "radial",
    "sequential",
    "concentric",
    "grid",
})


def _check_graph_data(data: Any) -> None:
    """Validate graph_data structure, raising OgmaDataError for invalid input."""
    if not isinstance(data, dict):
        raise OgmaDataError(
            f"graph_data must be a dict with 'nodes' and 'edges' keys, "
            f"got {type(data).__name__}"
        )
    if "nodes" not in data:
        raise OgmaDataError("graph_data must have a 'nodes' key")
    if "edges" not in data:
        raise OgmaDataError("graph_data must have an 'edges' key")
    if not isinstance(data["nodes"], list):
        raise OgmaDataError(
            f"graph_data['nodes'] must be a list, got {type(data['nodes']).__name__}"
        )
    if not isinstance(data["edges"], list):
        raise OgmaDataError(
            f"graph_data['edges'] must be a list, got {type(data['edges']).__name__}"
        )
    for i, node in enumerate(data["nodes"]):
        if not isinstance(node, dict):
            raise OgmaDataError(
                f"Each node must be a dict, got {type(node).__name__} at index {i}"
            )
    for i, edge in enumerate(data["edges"]):
        if not isinstance(edge, dict):
            raise OgmaDataError(
                f"Each edge must be a dict, got {type(edge).__name__} at index {i}"
            )
        if "source" not in edge:
            raise OgmaDataError(f"Each edge must have a 'source' key, missing at index {i}")
        if "target" not in edge:
            raise OgmaDataError(f"Each edge must have a 'target' key, missing at index {i}")


class OgmaWidget(anywidget.AnyWidget):
    """Interactive Ogma graph visualization widget for Jupyter notebooks.

    Parameters
    ----------
    graph_data : dict, optional
        Initial graph data matching Ogma's RawGraph format::

            {
                "nodes": [{"id": "a", "attributes": {"x": 0, "y": 0}, "data": {...}}, ...],
                "edges": [{"source": "a", "target": "b", "data": {...}}, ...]
            }

    license_key : str, optional
        Ogma license key. Falls back to ``og.set_license()`` value,
        then ``OGMA_LICENSE_KEY`` environment variable.
    style_rules : list, optional
        Initial list of style rule dicts (use ``ogma_jupyter.rules`` helpers).
    graph_layout : dict, optional
        Initial layout config, e.g. ``{"name": "force"}``.
    """

    _esm = pathlib.Path(__file__).parent / "static" / "widget.js"

    # Graph data in Ogma's RawGraph format
    graph_data = traitlets.Any({"nodes": [], "edges": []}).tag(sync=True)

    # License key passed to Ogma({license: key}) in JS
    _license_key = traitlets.Unicode("").tag(sync=True)

    # Style rules: list of dicts with nodeAttributes / edgeAttributes
    style_rules = traitlets.Any([]).tag(sync=True)

    # Initial layout config sent to JS on load
    graph_layout = traitlets.Any(None).tag(sync=True)

    def __init__(
        self,
        graph_data: Optional[Dict] = None,
        license_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._license_key = get_license_key(license_key)
        if graph_data is not None:
            self.graph_data = graph_data

    @traitlets.validate("graph_data")
    def _validate_graph_data(self, proposal: Dict) -> Any:
        data = proposal["value"]
        _check_graph_data(data)
        return data

    def add_style_rule(
        self,
        node_attributes: Optional[Dict] = None,
        edge_attributes: Optional[Dict] = None,
    ) -> None:
        """Add a style rule to the visualization.

        Parameters
        ----------
        node_attributes : dict, optional
            Node visual attributes. Values can be static (e.g. ``"red"``)
            or rule descriptors from ``ogma_jupyter.rules``.
        edge_attributes : dict, optional
            Edge visual attributes. Same format as node_attributes.

        Examples
        --------
        >>> from ogma_jupyter import rules
        >>> widget.add_style_rule(
        ...     node_attributes={
        ...         "color": rules.map(field="data.type", values={"person": "blue"}),
        ...         "radius": rules.slices(field="data.score", values=["sm", "md", "lg"]),
        ...     }
        ... )
        """
        if node_attributes is None and edge_attributes is None:
            raise ValueError(
                "At least one of node_attributes or edge_attributes must be provided"
            )
        if node_attributes is not None and not isinstance(node_attributes, dict):
            raise OgmaDataError("node_attributes must be a dict")
        if edge_attributes is not None and not isinstance(edge_attributes, dict):
            raise OgmaDataError("edge_attributes must be a dict")

        rule: Dict = {}
        if node_attributes is not None:
            rule["nodeAttributes"] = node_attributes
        if edge_attributes is not None:
            rule["edgeAttributes"] = edge_attributes

        # Create a new list to trigger traitlets change detection
        self.style_rules = self.style_rules + [rule]

    def run_layout(self, name: str, **options: Any) -> None:
        """Run a layout algorithm on the graph.

        Parameters
        ----------
        name : str
            Layout algorithm name. One of: force, forceatlas2, hierarchical,
            radial, sequential, concentric, grid.
        **options
            Layout-specific options, e.g. ``duration=300``, ``direction="LR"``.

        Raises
        ------
        OgmaDataError
            If the layout name is not recognised.

        Examples
        --------
        >>> widget.run_layout("force", duration=300)
        >>> widget.run_layout("hierarchical", direction="LR")
        """
        if not name:
            raise OgmaDataError("Layout name cannot be empty")
        if name not in VALID_LAYOUTS:
            raise OgmaDataError(
                f"Unknown layout '{name}'. "
                f"Valid layouts: {', '.join(sorted(VALID_LAYOUTS))}"
            )
        self.send({"type": "run_layout", "name": name, "options": options})

    def group_nodes(self, key: str) -> None:
        """Group nodes by a data property path.

        Parameters
        ----------
        key : str
            Data property path to group by, e.g. ``"data.department"``.

        Examples
        --------
        >>> widget.group_nodes(key="data.department")
        """
        self.send({"type": "group_nodes", "key": key})

    def ungroup_nodes(self) -> None:
        """Remove all node groupings."""
        self.send({"type": "ungroup_nodes"})

