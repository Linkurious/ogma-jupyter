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

// Group nodes sharing the value at `key` into a single meta-node.
export interface GroupNodesMessage {
    type: "group_nodes";
    key: string;
}

// Remove any active node grouping.
export interface UngroupNodesMessage {
    type: "ungroup_nodes";
}

export type CustomMessage =
    | RunLayoutMessage
    | GroupNodesMessage
    | UngroupNodesMessage
    | { type: string; [key: string]: unknown };

// Synced traitlets exposed by OgmaWidget (see src/ogma_jupyter/widget.py).
export interface WidgetModel {
    graph_data: RawGraph;
    _license_key: string;
    style_rules: StyleRuleSpec[];
    graph_layout: LayoutSpec | null;
}

export type OgmaModel = AnyModel<WidgetModel>;
