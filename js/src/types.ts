import type { AnyModel } from "@anywidget/types";
import type { RawGraph } from "@linkurious/ogma";

// Serializable rule descriptors produced by ogma_jupyter.rules.*
// They mirror the ogma.rules.* API and are reconstructed on the JS side.
export interface MapRule {
    type: "map";
    field: string;
    values: Record<string, unknown>;
    fallback?: unknown;
}

export interface SliceRule {
    type: "slices";
    field: string;
    values: { nbSlices: number; min: number; max: number } | unknown[];
    stops?: { min?: number; max?: number } | number[];
    fallback?: unknown;
    reverse?: boolean;
}

export interface TemplateRule {
    type: "template";
    template: string;
}

export type RuleDescriptor = MapRule | SliceRule | TemplateRule;

// A single style rule synced from Python (widget.add_style_rule).
export interface StyleRuleSpec {
    nodeAttributes?: Record<string, unknown>;
    edgeAttributes?: Record<string, unknown>;
}

// Initial layout config carried by the graph_layout traitlet.
export interface LayoutSpec {
    name: string;
    [option: string]: unknown;
}

// Custom message sent from Python via widget.send(...).
export interface RunLayoutMessage {
    type: "run_layout";
    name: string;
    options?: Record<string, unknown>;
}

// Active node-grouping spec (synced traitlet); see NodeGroupingOptions in
// grouping.ts. null means "no grouping".
export interface NodeGroupingSpec {
    key: string | string[];
    selectorKey?: string;
    idPrefix?: string;
    data?: Record<string, unknown>;
    dataAggregate?: Record<string, unknown>;
    label?: string;
    edgeDataAggregate?: Record<string, unknown>;
    showContents?: boolean;
    padding?: number;
    groupLayout?: { name: string; params?: Record<string, unknown> };
    enabled?: boolean;
}

// Active edge-grouping spec (synced traitlet); see EdgeGroupingOptions in
// grouping.ts. null means "no grouping".
export interface EdgeGroupingSpec {
    key?: string | string[];
    selectorKey?: string;
    dataAggregate?: Record<string, unknown>;
    label?: string;
    separateEdgesByDirection?: boolean;
    enabled?: boolean;
}

// Global layout run on every group update (ogma.transformations.onGroupsUpdated),
// see OgmaWidget.on_groups_updated. null clears it.
export interface GroupsLayoutSpec {
    name: string;
    params?: Record<string, unknown>;
}

// ogma.transformations.setAnimation options, see
// OgmaWidget.set_transformation_animation.
export interface TransformationAnimationSpec {
    duration?: number;
    easing?: string;
}

// A style class declared from Python (widget.add_class).
export interface StyleClassSpec {
    name: string;
    nodeAttributes?: Record<string, unknown>;
    edgeAttributes?: Record<string, unknown>;
}

// Custom message sent by OgmaWidget.highlight() / clear_highlight().
export interface HighlightMessage {
    type: "highlight";
    className: string;
    nodes?: unknown[];
    edges?: unknown[];
    duration?: number;
}

// Entries appended to the `_pending_ops` traitlet by OgmaWidget.add_nodes(),
// add_edges() and add_graph(). Each carries a monotonic `seq` so the frontend
// can pick up only what it hasn't applied yet.
export interface PendingOpBase {
    seq: number;
}
export interface AddNodesOp extends PendingOpBase {
    kind: "add_nodes";
    nodes: RawGraph["nodes"];
}
export interface AddEdgesOp extends PendingOpBase {
    kind: "add_edges";
    edges: RawGraph["edges"];
}
export interface AddGraphOp extends PendingOpBase {
    kind: "add_graph";
    graph: RawGraph;
}
export type PendingOp = AddNodesOp | AddEdgesOp | AddGraphOp;

export type CustomMessage =
    | RunLayoutMessage
    | HighlightMessage
    | { type: "trigger_groups_updated" }
    | { type: string; [key: string]: unknown };

// Synced traitlets exposed by OgmaWidget (see src/ogma_jupyter/widget.py).
export interface WidgetModel {
    graph_data: RawGraph;
    _license_key: string;
    style_rules: StyleRuleSpec[];
    graph_layout: LayoutSpec | null;
    // Widget container height in pixels (see OgmaWidget.height in widget.py).
    height: number;
    // Names of Ogma events (see ogma.events.on) Python currently wants to
    // receive, kept in sync by OgmaWidget.on()/off().
    event_subscriptions: string[];
    // Active node grouping (see OgmaWidget.group_nodes) or null.
    node_grouping: NodeGroupingSpec | null;
    // Active edge grouping (see OgmaWidget.group_edges) or null.
    edge_grouping: EdgeGroupingSpec | null;
    // Options forwarded to ogma.setOptions (see OgmaWidget.set_options).
    ogma_options: Record<string, unknown>;
    // Layout run on group updates (see OgmaWidget.on_groups_updated) or null.
    groups_layout: GroupsLayoutSpec | null;
    // Transformation animation (see OgmaWidget.set_transformation_animation) or null.
    transformation_animation: TransformationAnimationSpec | null;
    // Style classes (see OgmaWidget.add_class).
    style_classes: StyleClassSpec[];
    // Append-only queue of add_nodes/add_edges/add_graph mutations. The
    // frontend tracks which `seq` values it has already applied.
    _pending_ops: PendingOp[];
    // Node hover tooltip: null=off, true=default template (id + JSON data),
    // string=HTML template with {{path.to.field}} placeholders.
    node_tooltip: boolean | string | null;
}

export type OgmaModel = AnyModel<WidgetModel>;
