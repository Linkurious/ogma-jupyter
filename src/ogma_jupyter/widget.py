"""Main OgmaWidget class for Jupyter notebook graph visualization."""

import pathlib
import warnings
from typing import Any, Dict, Optional, Union

import anywidget
import traitlets

from .config import get_license_key
from .errors import OgmaDataError


def _core_esm_source() -> str:
    """Source of the packaged, Ogma-free widget core bundle (fallback default).

    Returned as a plain ``str`` (not a ``pathlib.Path``) so anywidget does not
    coerce it into a file-watching ``FileContents``. A watcher on the packaged
    core would reset every live widget's ``_esm`` back to the Ogma-free core the
    moment the file is rebuilt (e.g. ``npm run dev``, an editor save), making the
    graph disappear behind the "Ogma library not loaded" guard.
    """
    from .downloader import get_core_path

    return get_core_path().read_text(encoding="utf-8")


# Set to True once the class-level ``_esm`` default has been resolved to a fully
# assembled Ogma+core bundle. When True, instances do not need to override
# ``_esm`` at construction time (avoiding large late trait reassignments that can
# confuse some widget front-ends, e.g. VS Code).
_class_esm_has_ogma: bool = False


def _default_esm() -> Union[pathlib.Path, str]:
    """Resolve the class-level ``_esm`` default for :class:`OgmaWidget`.

    Prefers an assembled Ogma+core bundle *file* (returned as a ``pathlib.Path``,
    which anywidget serves via ``FileContents``) so the widget model is created
    already carrying Ogma — exactly like the previously bundled ``widget.js``.
    Because the bundle file contains Ogma, the ``FileContents`` watcher re-reads a
    full, working bundle even if the file is rebuilt.

    Falls back to the Ogma-free core *source string* when Ogma is not available
    locally; it can still be downloaded at runtime via
    ``og.set_license(..., download=True)`` and applied per-instance in
    :meth:`OgmaWidget.__init__`.
    """
    global _class_esm_has_ogma
    from .downloader import ensure_local_bundle_file

    bundle_file = ensure_local_bundle_file()
    if bundle_file is not None:
        _class_esm_has_ogma = True
        return bundle_file
    return _core_esm_source()


def _cached_bundle_source() -> Optional[str]:
    """Return the assembled (Ogma + core) bundle source from cache, if present.

    The commercial Ogma library is never bundled into the distributed package —
    it is downloaded at runtime and assembled into the user cache. Returns
    ``None`` when it has not been downloaded yet.
    """
    from .downloader import get_bundle_path

    bundle = get_bundle_path()
    if bundle.exists():
        return bundle.read_text(encoding="utf-8")
    return None


def _resolve_bundle_source() -> Optional[str]:
    """Resolve the assembled (Ogma + core) bundle source for a widget instance.

    Resolution order:

    1. The already-assembled bundle in the user cache (from a prior download).
    2. A repo-local Ogma UMD build from ``node_modules`` (development/testing
       convenience — no network or license key needed; never present in an
       installed distribution).
    3. A lazy download-and-assemble using the configured Ogma license key
       (``og.set_license(...)`` or the ``OGMA_LICENSE_KEY`` env var).

    Returns ``None`` when none of the above yields a bundle, in which case the
    packaged Ogma-free core is used and the JavaScript side shows an actionable
    message instead of a blank cell.
    """
    cached = _cached_bundle_source()
    if cached is not None:
        return cached

    from . import config
    from .downloader import build_bundle_source, ensure_bundle, get_local_ogma_path

    # Development/testing fallback: use the local node_modules Ogma build so the
    # repo's examples and tests render offline without a license key.
    local_ogma = get_local_ogma_path()
    if local_ogma is not None:
        global _local_bundle_source
        if _local_bundle_source is None:
            _local_bundle_source = build_bundle_source(local_ogma)
        return _local_bundle_source

    # The configured license key triggers a lazy network download on render.
    license_key = config.get_license_key()
    if not license_key or license_key in _failed_license_keys:
        return None

    try:
        bundle_path = ensure_bundle(license_key)
    except Exception as exc:  # noqa: BLE001 - surface any download/assembly issue
        _failed_license_keys.add(license_key)
        warnings.warn(
            f"Could not download the Ogma runtime bundle: {exc}. "
            "The graph will not render until Ogma is available. See "
            "og.set_license(..., download=True).",
            stacklevel=2,
        )
        return None

    return bundle_path.read_text(encoding="utf-8")


# Cached assembled source built from the local node_modules Ogma build, so it is
# read/assembled at most once per Python session.
_local_bundle_source: Optional[str] = None

# License keys that already failed this session, so repeated widget creation
# does not retry the network for a known-bad key.
_failed_license_keys: set = set()


# Valid Ogma layout algorithm names.
# "forceatlas2" is kept as a backwards-compatible alias for "forcelink"
# (Ogma 6's ForceAtlas2-style layout); both resolve to ogma.layouts.forceLink
# on the JavaScript side.
VALID_LAYOUTS: frozenset = frozenset({
    "force",
    "forcelink",
    "forceatlas2",
    "hierarchical",
    "radial",
    "sequential",
    "concentric",
    "grid",
})

# Option names (camelCase) accepted by each Ogma 6 layout, sourced from the
# layout option interfaces in @linkurious/ogma's type definitions
# (LayoutOptions + the per-layout *Options interfaces). Used by run_layout() to
# warn when an unrecognised option is passed. Callers may use snake_case in
# Python (e.g. edge_length); it is converted to camelCase before validation and
# before being sent to the JavaScript side.
#
# Options common to every layout (from LayoutOptions / IncrementalLayoutOptions).
_COMMON_LAYOUT_OPTIONS: frozenset = frozenset({
    "nodes", "edges", "easing", "duration", "skipTextDrawing", "onSync",
    "onEnd", "xs", "ys", "rs", "groups", "useWebWorker", "continuous",
    "locate", "onUpdate", "dryRun",
})
_INCREMENTAL_LAYOUT_OPTIONS: frozenset = frozenset({
    "incremental", "centralNode", "margin",
})

# Per-layout option names, keyed by the Python layout name. "forceatlas2" shares
# "forcelink"'s options (it is an alias for the same Ogma layout).
LAYOUT_OPTIONS: Dict[str, frozenset] = {
    "force": _COMMON_LAYOUT_OPTIONS | _INCREMENTAL_LAYOUT_OPTIONS | frozenset({
        "charge", "gravity", "edgeStrength", "steps", "theta", "radiusRatio",
        "edgeLength", "cx", "cy", "elasticity", "alignSiblings",
        "siblingsOffset", "autoStop", "gpu", "nodeMass", "edgeWeight",
    }),
    "forcelink": _COMMON_LAYOUT_OPTIONS | _INCREMENTAL_LAYOUT_OPTIONS | frozenset({
        "scalingRatio", "gravity", "edgeWightInfluence", "linLogMode",
        "outboundAttractionDistribution", "strongGravityMode", "slowDown",
        "alignNodeSiblings", "nodeSiblingsScale", "nodeSiblingsAngleMin",
        "autoStop", "maxIterations", "avgDistanceThreshold",
        "startingIterations", "iterationsPerRender", "barnesHutOptimize",
        "barnesHutTheta", "randomize", "randomizeFactor", "nodeMass",
        "edgeWeight",
    }),
    "hierarchical": _COMMON_LAYOUT_OPTIONS | frozenset({
        "direction", "nodeDistance", "levelDistance", "compactSiblings",
        "siblingsDistance", "compactSiblingsFunction", "componentDistance",
        "gapWidth", "layer", "siblingIndex", "decross", "arrangeComponents",
        "gridDistance", "roots", "sinks",
    }),
    "sequential": _COMMON_LAYOUT_OPTIONS | frozenset({
        "direction", "nodeDistance", "levelDistance", "componentDistance",
        "layer", "arrangeComponents", "gridDistance", "decross", "roots",
        "sinks",
    }),
    "radial": _COMMON_LAYOUT_OPTIONS | frozenset({
        "centralNode", "centerX", "centerY", "allowOverlap", "repulsion",
        "radiusDelta", "radiusRatio", "nodeGap", "maxIterations",
        "iterationsPerRender", "renderSteps", "epsilon", "randomize",
    }),
    "concentric": _COMMON_LAYOUT_OPTIONS | frozenset({
        "centralNode", "centerX", "centerY", "sortBy", "clockwise",
        "allowOverlap", "circleHopRatio",
    }),
    "grid": _COMMON_LAYOUT_OPTIONS | frozenset({
        "rows", "cols", "rowDistance", "colDistance", "sortBy",
        "sortFallbackValue", "reverse",
    }),
}
LAYOUT_OPTIONS["forceatlas2"] = LAYOUT_OPTIONS["forcelink"]


def _to_camel_case(name: str) -> str:
    """Convert a ``snake_case`` option name to ``camelCase``.

    Names without underscores (already camelCase, or single words) are returned
    unchanged, so both ``edge_length`` and ``edgeLength`` map to ``edgeLength``.
    """
    if "_" not in name:
        return name
    head, *tail = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def _normalize_layout_options(name: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Convert option keys to camelCase and warn on names unknown to the layout.

    Unknown options are still forwarded (so newly-added Ogma options keep
    working), but a warning is emitted to catch typos and non-serialisable
    options that Ogma would otherwise silently ignore.
    """
    converted = {_to_camel_case(key): value for key, value in options.items()}
    allowed = LAYOUT_OPTIONS.get(name)
    if allowed is not None:
        unknown = sorted(key for key in converted if key not in allowed)
        if unknown:
            warnings.warn(
                f"Unknown option(s) for the '{name}' layout: {', '.join(unknown)}. "
                f"They will be forwarded but Ogma may ignore them. Option names "
                f"are camelCase (snake_case is converted automatically) and must "
                f"be JSON-serialisable — function-valued options are not "
                f"supported. See the Ogma layout docs: "
                f"https://doc.linkurio.us/ogma/latest/api.html#Ogma-layouts",
                stacklevel=3,
            )
    return converted



# Node position keys that Ogma expects inside each node's "attributes" sub-object.
# When found at the node root they are lifted into "attributes" by
# _normalize_graph_data so that coordinates are not silently ignored.
POSITIONAL_KEYS: tuple = ("x", "y")


def _normalize_graph_data(data: Any) -> Any:
    """Lift root-level ``x``/``y`` node coordinates into the ``attributes`` sub-object.

    Ogma's RawGraph format expects positional attributes such as ``x`` and ``y``
    under each node's ``attributes`` key. Users commonly place them at the node
    root instead, where Ogma ignores them. This helper moves any root-level
    positional keys into ``attributes`` (without overwriting existing values)
    and emits a warning so the canonical shape is discoverable.
    """
    if not isinstance(data, dict):
        return data
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return data

    normalized_nodes = []
    lifted = False
    for node in nodes:
        if isinstance(node, dict) and any(key in node for key in POSITIONAL_KEYS):
            node = dict(node)
            attributes = dict(node.get("attributes") or {})
            for key in POSITIONAL_KEYS:
                if key in node:
                    value = node.pop(key)
                    attributes.setdefault(key, value)
            node["attributes"] = attributes
            lifted = True
        normalized_nodes.append(node)

    if not lifted:
        return data

    warnings.warn(
        "Node coordinates (x/y) were found at the node root and moved into the "
        "'attributes' sub-object. Ogma's RawGraph format expects positional "
        "attributes under 'attributes', e.g. "
        '{"id": "a", "attributes": {"x": 0, "y": 0}}.',
        stacklevel=3,
    )
    data = dict(data)
    data["nodes"] = normalized_nodes
    return data


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

    # Class-level ESM default. When Ogma is available locally (cache or the repo
    # node_modules build), this is a Path to the fully assembled Ogma+core bundle
    # file, served by anywidget via FileContents — the same mechanism as the
    # previously bundled widget.js, so the model is created already carrying Ogma.
    # When Ogma is not available locally, it falls back to the Ogma-free core
    # source string; Ogma can then be downloaded at runtime via
    # og.set_license(..., download=True) and applied per-instance in __init__.
    _esm = _default_esm()

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
        # When the class-level default already carries Ogma (assembled bundle
        # file), no per-instance override is needed — the model is born complete,
        # which avoids large late _esm reassignments that can confuse some widget
        # front-ends. Only when Ogma was unavailable at import (core-only default)
        # do we try to resolve a bundle now (e.g. after a runtime download).
        if not _class_esm_has_ogma:
            bundle_source = _resolve_bundle_source()
            if bundle_source is not None:
                self._esm = bundle_source
        if graph_data is not None:
            self.graph_data = graph_data

    @traitlets.validate("graph_data")
    def _validate_graph_data(self, proposal: Dict) -> Any:
        data = proposal["value"]
        _check_graph_data(data)
        return _normalize_graph_data(data)

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
            Layout algorithm name. One of: force, forcelink, hierarchical,
            radial, sequential, concentric, grid. (``forceatlas2`` is accepted
            as an alias for ``forcelink``.)
        **options
            Layout-specific options passed through to Ogma, e.g.
            ``duration=300`` or ``direction="LR"``. Names may be given in
            ``snake_case`` (converted to Ogma's ``camelCase`` automatically), so
            ``edge_length=30`` and ``edgeLength=30`` are equivalent. Options
            must be JSON-serialisable — function-valued options (e.g.
            ``nodeMass``) are not supported over the widget bridge. Passing an
            option name unknown to the chosen layout emits a warning (the option
            is still forwarded). See the Ogma layout docs for the full option
            list: https://doc.linkurio.us/ogma/latest/api.html#Ogma-layouts

        Raises
        ------
        OgmaDataError
            If the layout name is not recognised.

        Examples
        --------
        >>> widget.run_layout("force", duration=300, edge_length=40)
        >>> widget.run_layout("hierarchical", direction="LR")
        >>> widget.run_layout("radial", central_node="alice")
        """
        if not name:
            raise OgmaDataError("Layout name cannot be empty")
        if name not in VALID_LAYOUTS:
            raise OgmaDataError(
                f"Unknown layout '{name}'. "
                f"Valid layouts: {', '.join(sorted(VALID_LAYOUTS))}"
            )
        options = _normalize_layout_options(name, options)
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

