"""Main OgmaWidget class for Jupyter notebook graph visualization."""

import pathlib
import warnings
from typing import Any, Callable, Dict, List, Optional, Union

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



def _layout_spec(layout: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build a ``{"name", "params"}`` layout spec from a name or an options dict.

    Validates the name against :data:`VALID_LAYOUTS` and normalises the options
    the same way :meth:`OgmaWidget.run_layout` does.
    """
    if isinstance(layout, str):
        name, options = layout, {}
    elif isinstance(layout, dict) and "name" in layout:
        options = dict(layout)
        name = options.pop("name")
    else:
        raise OgmaDataError(
            f"layout must be a name or a dict with a 'name' key, got {layout!r}"
        )
    if name not in VALID_LAYOUTS:
        raise OgmaDataError(
            f"Unknown layout '{name}'. Valid layouts: {', '.join(sorted(VALID_LAYOUTS))}"
        )
    return {"name": name, "params": _normalize_layout_options(name, options)}


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


def _check_nodes(nodes: Any) -> None:
    """Validate a list of nodes for add_nodes()/add_graph()."""
    if not isinstance(nodes, list):
        raise OgmaDataError(
            f"nodes must be a list, got {type(nodes).__name__}"
        )
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise OgmaDataError(
                f"Each node must be a dict, got {type(node).__name__} at index {i}"
            )


def _check_edges(edges: Any) -> None:
    """Validate a list of edges for add_edges()/add_graph()."""
    if not isinstance(edges, list):
        raise OgmaDataError(
            f"edges must be a list, got {type(edges).__name__}"
        )
    for i, edge in enumerate(edges):
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
    height : int, optional
        Widget height in pixels. Defaults to 700.
    options : dict, optional
        Ogma options forwarded to ``ogma.setOptions()``, e.g.
        ``{"backgroundColor": "#08090a"}``. See :meth:`set_options`.

    Notes
    -----
    Use :meth:`on` to receive any Ogma event (click, hover, drag, selection,
    layout, ...) in Python::

        def on_click(evt):
            if evt["target"]:
                print("clicked", evt["target"]["id"])

        widget.on("click", on_click)
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

    # Widget container height in pixels
    height = traitlets.Int(700).tag(sync=True)

    # Names of Ogma events (see ogma.events.on) currently subscribed to; the JS
    # side syncs its ogma.events.on()/off() calls to match this list. Populated
    # by on()/off()/once(), not meant to be set directly.
    event_subscriptions = traitlets.List(traitlets.Unicode()).tag(sync=True)

    # Active node grouping spec (``{"key": "data.<path>"}``) or ``None``. Kept
    # as a synced traitlet — not a custom message — so it survives the
    # "spec set before the widget is displayed" case, which would otherwise
    # drop the message on the floor. Populated by group_nodes()/ungroup_nodes().
    node_grouping = traitlets.Any(None, allow_none=True).tag(sync=True)

    # Active edge grouping spec (see group_edges() for the shape) or ``None``.
    # Synced for the same reason as ``node_grouping``. Populated by
    # group_edges()/ungroup_edges().
    edge_grouping = traitlets.Any(None, allow_none=True).tag(sync=True)

    # Options forwarded to ``ogma.setOptions()`` (background colour,
    # interactions, ...). Populated by the ``options`` argument / set_options().
    ogma_options = traitlets.Dict({}).tag(sync=True)

    # Global layout run by ``ogma.transformations.onGroupsUpdated`` every time
    # the node groups change (``{"name": ..., "params": {...}}``) or ``None``.
    # Populated by on_groups_updated().
    groups_layout = traitlets.Any(None, allow_none=True).tag(sync=True)

    # ``ogma.transformations.setAnimation`` options (``duration``/``easing``)
    # or ``None``. Populated by set_transformation_animation().
    transformation_animation = traitlets.Any(None, allow_none=True).tag(sync=True)

    # Style classes created with ``ogma.styles.createClass``; list of
    # ``{"name", "nodeAttributes", "edgeAttributes"}``. Populated by add_class().
    style_classes = traitlets.List(traitlets.Dict()).tag(sync=True)

    # Append-only queue of imperative graph mutations produced by add_nodes(),
    # add_edges() and add_graph(). Each entry carries a monotonic ``seq`` field
    # so the JS side can pick up only the ones it hasn't applied yet, whether
    # they were enqueued before or after the widget was displayed.
    _pending_ops = traitlets.List(traitlets.Dict()).tag(sync=True)

    # Node hover tooltip spec. ``None`` disables it, ``True`` shows a default
    # tooltip (node id + data as JSON) and a str is treated as an HTML template
    # with ``{{path.to.field}}`` placeholders resolved against the node's data
    # (``id`` maps to ``node.getId()``, everything else to ``node.getData()``).
    # Populated by show_node_tooltip()/hide_node_tooltip().
    node_tooltip = traitlets.Any(None, allow_none=True).tag(sync=True)

    def __init__(
        self,
        graph_data: Optional[Dict] = None,
        license_key: Optional[str] = None,
        height: int = 700,
        options: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._license_key = get_license_key(license_key)
        self.height = height
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
        if options is not None:
            self.set_options(options)
        # Python-side handlers per event name (JS holds only one listener per
        # event name; fan-out to multiple Python callbacks happens here).
        self._event_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.on_msg(self._dispatch_message)

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

    def group_nodes(
        self,
        key: Union[str, List[str]],
        selector_key: Optional[str] = None,
        id_prefix: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        data_aggregate: Optional[Dict[str, Dict[str, Any]]] = None,
        label: Optional[str] = None,
        edge_data_aggregate: Optional[Dict[str, Dict[str, Any]]] = None,
        show_contents: Optional[bool] = None,
        padding: Optional[float] = None,
        group_layout: Optional[Union[str, Dict[str, Any]]] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        """Group nodes by one or more data property paths.

        Wraps ``ogma.transformations.addNodeGrouping``. Nodes whose value at
        ``key`` is missing (``None``) are left ungrouped, so a precomputed
        "group id or ``None``" field is the simplest way to express any custom
        grouping logic from Python. Calling again replaces the active grouping
        — except when only ``enabled`` changes, which toggles it in place (see
        :meth:`enable_node_grouping`).

        Every meta-node carries at least ``data.groupId``, ``data.count``
        (number of grouped nodes) and ``data.label`` (the rendered ``label``).

        Parameters
        ----------
        key : str or list of str
            Data property path(s) to group by, e.g. ``"data.department"``.
            Several paths are joined with ``-`` into one group id.
        selector_key : str, optional
            Data-property path whose truthy value keeps a node in the grouping.
            Maps to Ogma's ``selector``.
        id_prefix : str, optional
            Meta-node ids become ``f"{id_prefix}{group_id}"``, so they can be
            recognised in event payloads. Ogma assigns ids when omitted.
        data : dict, optional
            Static data merged into every meta-node's ``data``.
        data_aggregate : dict, optional
            Aggregations over the grouped nodes, same spec as
            :meth:`group_edges` (``count``, ``sum``, ``min``, ``max``, ``avg``,
            ``first``, ``last``, ``collect``).
        label : str, optional
            Meta-node text template with ``{{groupId}}`` / ``{{<data field>}}``
            placeholders, e.g. ``"{{count}} victims of {{groupId}}"``.
            Defaults to the group id.
        edge_data_aggregate : dict, optional
            Aggregations written to the ``data`` of the meta-edges linking
            groups to the rest of the graph (Ogma's ``edgeGenerator``).
            ``data.count`` is always added.
        show_contents : bool, optional
            Forwarded to Ogma's ``showContents`` (draw the sub-nodes inside
            their group).
        padding : float, optional
            Forwarded to Ogma's ``padding``.
        group_layout : str or dict, optional
            Layout run inside each open group (Ogma's ``onGroupUpdate``):
            a layout name (``"grid"``) or ``{"name": "grid", **params}``.
        enabled : bool, optional
            Forwarded to Ogma's ``enabled``.

        Examples
        --------
        >>> widget.group_nodes(key="data.department")
        >>> widget.group_nodes(
        ...     key="data.victimOf",
        ...     id_prefix="victims-",
        ...     label="{{count}} victims ({{groupId}})",
        ...     show_contents=True,
        ...     group_layout="grid",
        ...     enabled=False,
        ... )
        """
        spec: Dict[str, Any] = {"key": list(key) if isinstance(key, (list, tuple)) else key}
        if selector_key is not None:
            spec["selectorKey"] = selector_key
        if id_prefix is not None:
            spec["idPrefix"] = id_prefix
        if data is not None:
            spec["data"] = dict(data)
        if data_aggregate is not None:
            spec["dataAggregate"] = {k: dict(v) for k, v in data_aggregate.items()}
        if label is not None:
            spec["label"] = label
        if edge_data_aggregate is not None:
            spec["edgeDataAggregate"] = {k: dict(v) for k, v in edge_data_aggregate.items()}
        if show_contents is not None:
            spec["showContents"] = show_contents
        if padding is not None:
            spec["padding"] = padding
        if group_layout is not None:
            spec["groupLayout"] = _layout_spec(group_layout)
        if enabled is not None:
            spec["enabled"] = enabled
        self.node_grouping = spec

    def enable_node_grouping(self, enabled: bool = True) -> None:
        """Enable (or, with ``enabled=False``, disable) the active node grouping.

        Mirrors the grouping transformation's ``enable()``/``disable()``: the
        grouping keeps its options and Ogma animates the transition (see
        :meth:`set_transformation_animation`).

        Raises
        ------
        OgmaDataError
            If no node grouping is active (call :meth:`group_nodes` first).
        """
        if self.node_grouping is None:
            raise OgmaDataError("No active node grouping; call group_nodes() first")
        self.node_grouping = {**self.node_grouping, "enabled": bool(enabled)}

    def disable_node_grouping(self) -> None:
        """Disable the active node grouping, keeping its options."""
        self.enable_node_grouping(False)

    @property
    def node_grouping_enabled(self) -> bool:
        """Whether a node grouping is active and enabled."""
        return self.node_grouping is not None and self.node_grouping.get("enabled", True)

    def ungroup_nodes(self) -> None:
        """Remove all node groupings."""
        self.node_grouping = None

    def group_edges(
        self,
        key: Optional[Union[str, List[str]]] = None,
        selector_key: Optional[str] = None,
        data_aggregate: Optional[Dict[str, Dict[str, Any]]] = None,
        label: Optional[str] = None,
        separate_edges_by_direction: Optional[bool] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        """Merge parallel edges into a single meta-edge.

        Edges sharing the same source/target pair are collapsed into one
        meta-edge via Ogma's edge-grouping transformation
        (``ogma.transformations.addEdgeGrouping``). Calling again while an
        edge grouping is already active replaces it (no stacking).

        Ogma's ``selector``, ``groupIdFunction`` and ``generator`` options are
        function-valued and cannot cross the widget bridge; instead, pass the
        serialisable equivalents below and the JavaScript side builds the
        closures. Visual attributes (width, color, ...) on the resulting
        meta-edges are expected to be driven by style rules bound to the
        aggregated ``data.*`` fields — the generator never writes to
        ``attributes`` other than ``text`` (the group id).

        Every meta-edge carries at least:

        - ``data.subEdges``: list of merged edge ids.
        - ``data.count``: number of merged edges (add an entry with output key
          ``"count"`` in ``data_aggregate`` to override).
        - ``data.<last segment of key>``: the shared ``key`` value (when
          ``key`` is set).

        Parameters
        ----------
        key : str or list of str, optional
            Data-property path(s) used to build the ``groupIdFunction``, e.g.
            ``"data.kind"`` or ``["data.kind", "data.AUTH_TYPE"]``. Edges are
            grouped only when they are parallel *and* share these values.
            When omitted, all parallel edges are grouped together.
        selector_key : str, optional
            Data-property path whose truthy value keeps an edge in the
            grouping; edges with a falsy value are left ungrouped. Maps to
            Ogma's ``selector``.
        data_aggregate : dict, optional
            Extra values to compute on the meta-edge's ``data``. Each entry
            maps an output field name to an operation spec::

                {"count":       {"op": "count"}}
                {"totalWeight": {"op": "sum",  "field": "data.weight"}}
                {"maxTime":     {"op": "max",  "field": "data.TIME"}}
                {"firstKind":   {"op": "first","field": "data.kind"}}
                {"weights":     {"op": "collect", "field": "data.weight"}}

            Supported ops: ``count``, ``sum``, ``min``, ``max``, ``avg``,
            ``first``, ``last``, ``collect``. Non-numeric values are skipped
            for numeric ops. ``count`` and ``collect`` accept an optional
            ``field``; the others require one.
        label : str, optional
            Meta-edge text template with ``{{groupId}}`` / ``{{<data field>}}``
            placeholders. Defaults to the group id; ``""`` leaves meta-edges
            unlabelled.
        separate_edges_by_direction : bool, optional
            Forwarded to Ogma's ``separateEdgesByDirection``.
        enabled : bool, optional
            Forwarded to Ogma's ``enabled``.

        Examples
        --------
        >>> widget.group_edges()  # merge parallel edges, meta-edge gets data.count
        >>> widget.group_edges(
        ...     key="data.kind",
        ...     data_aggregate={"totalWeight": {"op": "sum", "field": "data.weight"}},
        ... )
        >>> # Then drive width from the aggregated data via a style rule:
        >>> widget.add_style_rule(edge_attributes={
        ...     "width": rules.slices(field="data.count",
        ...                           values={"nbSlices": 4, "min": 1, "max": 8}),
        ... })
        """
        msg: Dict[str, Any] = {}
        if key is not None:
            msg["key"] = list(key) if isinstance(key, (list, tuple)) else key
        if selector_key is not None:
            msg["selectorKey"] = selector_key
        if data_aggregate is not None:
            msg["dataAggregate"] = {k: dict(v) for k, v in data_aggregate.items()}
        if label is not None:
            msg["label"] = label
        if separate_edges_by_direction is not None:
            msg["separateEdgesByDirection"] = separate_edges_by_direction
        if enabled is not None:
            msg["enabled"] = enabled
        self.edge_grouping = msg

    def ungroup_edges(self) -> None:
        """Remove any active edge grouping."""
        self.edge_grouping = None

    def set_options(self, options: Dict[str, Any]) -> None:
        """Merge ``options`` into the Ogma options (``ogma.setOptions``).

        Keys are Ogma's camelCase option names; nested dicts are forwarded
        as-is.

        Examples
        --------
        >>> widget.set_options({
        ...     "backgroundColor": "#08090a",
        ...     "interactions": {"zoom": {"onDoubleClick": True}},
        ... })
        """
        if not isinstance(options, dict):
            raise OgmaDataError(f"options must be a dict, got {type(options).__name__}")
        self.ogma_options = {**self.ogma_options, **options}

    def on_groups_updated(self, name: Optional[str] = None, **options: Any) -> None:
        """Run a layout every time the node groups change.

        Mirrors ``ogma.transformations.onGroupsUpdated(() => ({layout, params}))``:
        the layout runs after a grouping is enabled, disabled or changes
        membership, and after :meth:`trigger_groups_updated`. Call with no
        ``name`` to clear it.

        Parameters
        ----------
        name : str, optional
            Layout name, same values as :meth:`run_layout`.
        **options
            Layout options, same conversion and validation as
            :meth:`run_layout`.

        Examples
        --------
        >>> widget.on_groups_updated("force", gpu=True)
        >>> widget.on_groups_updated("hierarchical", layer="level", level_distance=50)
        """
        if name is None:
            self.groups_layout = None
            return
        self.groups_layout = _layout_spec({"name": name, **options})

    def set_transformation_animation(
        self,
        duration: Optional[int] = None,
        easing: Optional[str] = None,
    ) -> None:
        """Animate transformation updates (``ogma.transformations.setAnimation``).

        Call with no argument to restore Ogma's default (no animation).

        Examples
        --------
        >>> widget.set_transformation_animation(duration=200, easing="quadraticInOut")
        """
        spec: Dict[str, Any] = {}
        if duration is not None:
            spec["duration"] = duration
        if easing is not None:
            spec["easing"] = easing
        self.transformation_animation = spec or None

    def trigger_groups_updated(self) -> None:
        """Re-run the :meth:`on_groups_updated` layout now.

        Mirrors ``ogma.transformations.triggerGroupsUpdated()`` followed by a
        transformation refresh, so the layout runs even when no group changed
        (e.g. after switching it from ``force`` to ``hierarchical``).
        """
        self.send({"type": "trigger_groups_updated"})

    def add_class(
        self,
        name: str,
        node_attributes: Optional[Dict] = None,
        edge_attributes: Optional[Dict] = None,
    ) -> None:
        """Declare a style class (``ogma.styles.createClass``).

        Classes take precedence over style rules. Declaring an existing name
        updates it in place. Values can be static or ``ogma_jupyter.rules``
        descriptors, as in :meth:`add_style_rule`. Elements get the class
        through :meth:`highlight`.

        Examples
        --------
        >>> widget.add_class(
        ...     "dimmed",
        ...     node_attributes={"opacity": 0.2, "text": {"content": ""}},
        ...     edge_attributes={"opacity": 0.2, "layer": -1},
        ... )
        """
        if not name:
            raise OgmaDataError("Class name cannot be empty")
        if node_attributes is not None and not isinstance(node_attributes, dict):
            raise OgmaDataError("node_attributes must be a dict")
        if edge_attributes is not None and not isinstance(edge_attributes, dict):
            raise OgmaDataError("edge_attributes must be a dict")
        spec: Dict[str, Any] = {"name": name}
        if node_attributes is not None:
            spec["nodeAttributes"] = node_attributes
        if edge_attributes is not None:
            spec["edgeAttributes"] = edge_attributes
        self.style_classes = [c for c in self.style_classes if c["name"] != name] + [spec]

    def highlight(
        self,
        nodes: Optional[List[Any]] = None,
        edges: Optional[List[Any]] = None,
        class_name: str = "dimmed",
        duration: int = 0,
    ) -> None:
        """Put ``class_name`` on every element except ``nodes``/``edges``.

        Ids refer to raw (non-virtual) elements: a meta-node or meta-edge
        produced by a grouping stays highlighted as soon as one of its
        sub-elements is listed, so highlighting works the same whether a
        grouping is enabled or not. Passing no ids clears the class.

        Parameters
        ----------
        nodes, edges : list, optional
            Ids of the elements to keep highlighted.
        class_name : str, default ``"dimmed"``
            A class declared with :meth:`add_class`.
        duration : int, default ``0``
            Class transition duration, in milliseconds.

        Examples
        --------
        >>> widget.highlight(nodes=["a", "b"], edges=["e1"], duration=250)
        """
        self.send({
            "type": "highlight",
            "className": class_name,
            "nodes": list(nodes or []),
            "edges": list(edges or []),
            "duration": duration,
        })

    def clear_highlight(self, class_name: str = "dimmed", duration: int = 0) -> None:
        """Remove ``class_name`` from every element."""
        self.highlight(class_name=class_name, duration=duration)

    def _enqueue_op(self, op: Dict[str, Any]) -> None:
        """Append a mutation to ``_pending_ops`` with a monotonic ``seq`` tag."""
        current = list(self._pending_ops)
        last_seq = current[-1]["seq"] if current else 0
        op = {"seq": last_seq + 1, **op}
        self._pending_ops = current + [op]

    def add_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """Add nodes to the graph without touching the existing ones.

        Wraps Ogma's ``ogma.addNodes(nodes)``. Safe to call before *or* after
        the widget is displayed — each call is appended to a synced queue and
        the frontend replays any queue entries it hasn't seen yet on next
        render/change. This is the preferred alternative to reassigning
        ``widget.graph_data`` for incremental growth (e.g. click-to-expand),
        since it avoids re-sending the whole graph on every step.

        Parameters
        ----------
        nodes : list of dict
            Nodes in Ogma's RawGraph format (each entry needs at least an
            ``id``; ``attributes`` and ``data`` are passed through as-is).

        Examples
        --------
        >>> widget.add_nodes([{"id": "z", "data": {"label": "Zoe"}}])
        """
        _check_nodes(nodes)
        self._enqueue_op({"kind": "add_nodes", "nodes": nodes})

    def add_edges(self, edges: List[Dict[str, Any]]) -> None:
        """Add edges to the graph without touching the existing ones.

        Wraps Ogma's ``ogma.addEdges(edges)``. Same queuing semantics as
        :meth:`add_nodes`. All ``source``/``target`` ids must already exist in
        the graph (either from the initial ``graph_data`` or from a prior
        :meth:`add_nodes` call), otherwise Ogma raises on the JS side.

        Parameters
        ----------
        edges : list of dict
            Edges in Ogma's RawGraph format (each entry needs ``source`` and
            ``target``; ``id`` and ``data`` are passed through as-is).

        Examples
        --------
        >>> widget.add_edges([{"id": "e10", "source": "a", "target": "z"}])
        """
        _check_edges(edges)
        self._enqueue_op({"kind": "add_edges", "edges": edges})

    def add_graph(self, graph: Dict[str, Any]) -> None:
        """Add both nodes and edges in a single atomic step.

        Wraps Ogma's ``ogma.addGraph(graph)``. Semantically equivalent to
        ``add_nodes(graph["nodes"])`` followed by ``add_edges(graph["edges"])``,
        but applied as a single Ogma call so any edge whose endpoints are among
        the just-added nodes is accepted.

        Parameters
        ----------
        graph : dict
            ``{"nodes": [...], "edges": [...]}`` in Ogma's RawGraph format.

        Examples
        --------
        >>> widget.add_graph({
        ...     "nodes": [{"id": "z"}],
        ...     "edges": [{"id": "e10", "source": "a", "target": "z"}],
        ... })
        """
        _check_graph_data(graph)
        graph = _normalize_graph_data(graph)
        self._enqueue_op({"kind": "add_graph", "graph": graph})

    def show_node_tooltip(self, template: Any = True) -> None:
        """Show a floating tooltip when hovering a node.

        Wraps Ogma's ``ogma.tools.tooltip.onNodeHover``.

        Parameters
        ----------
        template : bool or str, default ``True``
            ``True`` uses a built-in template that renders the node id and its
            ``data`` payload as pretty-printed JSON. A str is treated as an
            HTML template with ``{{path.to.field}}`` placeholders resolved
            against ``{"id": node.getId(), **node.getData()}``. Substituted
            values are HTML-escaped; the template itself is not, so you can
            use tags like ``<b>``/``<br>`` freely.

        Examples
        --------
        >>> widget.show_node_tooltip()  # id + full data as JSON
        >>> widget.show_node_tooltip("<b>{{id}}</b><br>role: {{role}}")
        """
        if template is False or template is None:
            self.node_tooltip = None
            return
        if template is not True and not isinstance(template, str):
            raise OgmaDataError(
                "template must be True, None, False, or a str, "
                f"got {type(template).__name__}"
            )
        self.node_tooltip = template

    def hide_node_tooltip(self) -> None:
        """Remove any active node hover tooltip."""
        self.node_tooltip = None

    def on(self, event_name: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to an Ogma event and receive its payload in Python.

        Mirrors Ogma's own ``ogma.events.on(eventName, listener)`` API — any
        event name it accepts works here too (``click``, ``doubleclick``,
        ``mouseover``, ``mouseout``, ``nodesDragEnd``, ``nodesSelected``,
        ``layoutEnd``, ...); see the Ogma events documentation for the full
        list and each event's payload shape:
        https://doc.linkurio.us/ogma/latest/api.html#Ogma-events-on

        Node/Edge instances, NodeList/EdgeList collections, and other Ogma
        objects in the payload are converted to plain dicts/lists
        (``{"id": ..., "isNode": ..., "isEdge": ..., "data": ...}``) before
        reaching ``handler``. Native DOM events (e.g. ``domEvent``) are
        dropped — they cannot be serialized.

        Parameters
        ----------
        event_name : str
            Name of the Ogma event to subscribe to.
        handler : callable
            Called with the serialized event payload (a dict) each time the
            event fires. Multiple handlers may be registered for the same
            event name.

        Examples
        --------
        >>> def on_click(evt):
        ...     if evt["target"]:
        ...         print("clicked", evt["target"]["id"])
        >>> widget.on("click", on_click)
        """
        if not event_name:
            raise OgmaDataError("event_name cannot be empty")
        self._event_handlers.setdefault(event_name, []).append(handler)
        if event_name not in self.event_subscriptions:
            self.event_subscriptions = self.event_subscriptions + [event_name]

    def off(
        self,
        event_name: str,
        handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """Unsubscribe from an Ogma event.

        Parameters
        ----------
        event_name : str
            Name of the Ogma event to unsubscribe from.
        handler : callable, optional
            The specific handler to remove. When omitted, all handlers for
            ``event_name`` are removed.
        """
        handlers = self._event_handlers.get(event_name)
        if not handlers:
            return
        if handler is None:
            handlers.clear()
        else:
            # `==` (not `is`) so `widget.off("click", some_list.append)` works —
            # bound methods compare equal by (__self__, __func__) but are a new
            # object on every attribute access, so identity would never match.
            handlers[:] = [h for h in handlers if h != handler]
        if not handlers:
            del self._event_handlers[event_name]
            self.event_subscriptions = [e for e in self.event_subscriptions if e != event_name]

    def once(self, event_name: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to an Ogma event for a single occurrence, then auto-unsubscribe.

        Mirrors ``ogma.events.once(eventName, listener)``. See :meth:`on` for
        the payload shape and available event names.
        """

        def _once_handler(payload: Dict[str, Any]) -> None:
            self.off(event_name, _once_handler)
            handler(payload)

        self.on(event_name, _once_handler)

    def _dispatch_message(self, widget: "OgmaWidget", msg: Any, buffers: Any) -> None:
        """Route JS -> Python custom messages to the registered event handlers."""
        if not isinstance(msg, dict) or msg.get("type") != "ogma_event":
            return
        event_name = msg.get("event")
        payload = msg.get("payload", {})
        for handler in list(self._event_handlers.get(event_name, [])):
            handler(payload)

