import type { Ogma, NodeGrouping, EdgeGrouping } from "@linkurious/ogma";

import { resolveLayoutName } from "./layouts";

type Grouping = NodeGrouping<unknown, unknown>;
type EdgeGroupingHandle = EdgeGrouping<unknown, unknown>;

/**
 * Strip a single leading `data.` segment and split the remaining property path
 * into the array form accepted by `node.getData()`, so nested paths such as
 * `data.address.city` resolve correctly.
 */
function toDataPath(key: string): string[] {
    const path = key.startsWith("data.") ? key.slice("data.".length) : key;
    return path.split(".");
}

/** Normalise a single path or a list of paths into `getData()` path arrays. */
function toDataPaths(key: string | string[]): string[][] {
    return (Array.isArray(key) ? key : [key]).map(toDataPath);
}

/**
 * Build a group id from the values at `paths`, joined with `-`. Returns
 * `undefined` (element left ungrouped) when any of the values is missing.
 */
function groupIdFromPaths(
    element: { getData: (path: string[]) => unknown },
    paths: string[][],
): string | undefined {
    let id = "";
    for (let i = 0; i < paths.length; i++) {
        const value = element.getData(paths[i]);
        if (value === undefined || value === null) return undefined;
        id += i === 0 ? String(value) : `-${String(value)}`;
    }
    return id;
}

/**
 * Plain-text `{{path}}` interpolation against a flat context, used for
 * meta-node / meta-edge labels. Missing values render as an empty string.
 */
function renderLabel(template: string, ctx: Record<string, unknown>): string {
    return template.replace(/\{\{\s*([^}]+?)\s*\}\}/g, (_, path: string) => {
        let cur: unknown = ctx;
        for (const key of path.split(".")) {
            if (cur == null || typeof cur !== "object") return "";
            cur = (cur as Record<string, unknown>)[key];
        }
        return cur == null ? "" : String(cur);
    });
}

/** Evaluate an aggregate spec map over an Ogma NodeList/EdgeList. */
function aggregateInto(
    data: Record<string, unknown>,
    entries: [string, AggregateOp][],
    list: { getId: () => unknown; getData: (path: string[]) => unknown },
): void {
    for (const [outKey, spec] of entries) {
        const values =
            "field" in spec && spec.field
                ? (list.getData(toDataPath(spec.field)) as unknown[])
                : (list.getId() as unknown[]);
        data[outKey] = reduceAggregate(spec, values);
    }
}

/** Layout spec run inside each open group (`onGroupUpdate`). */
export interface GroupLayoutSpec {
    name: string;
    params?: Record<string, unknown>;
}

/**
 * Options accepted by `applyGrouping`. Pure JSON so it crosses the anywidget
 * bridge — Ogma's function-valued options (`groupIdFunction`, `nodeGenerator`,
 * `edgeGenerator`, `onGroupUpdate`) are synthesised here.
 */
export interface NodeGroupingOptions {
    /** Data path(s) building the group id; nodes with a missing value stay ungrouped. */
    key: string | string[];
    /** Data path whose truthy value keeps a node in the grouping (`selector`). */
    selectorKey?: string;
    /** Prefix of the meta-node id (`<idPrefix><groupId>`); Ogma assigns ids when omitted. */
    idPrefix?: string;
    /** Static data merged into every meta-node. */
    data?: Record<string, unknown>;
    /** Aggregations over the grouped nodes; `data.count` is always added. */
    dataAggregate?: Record<string, AggregateOp>;
    /** Meta-node label template, `{{groupId}}` + any meta-node data field. Defaults to the group id. */
    label?: string;
    /** Aggregations written to the meta-edges' `data`; `data.count` is always added. */
    edgeDataAggregate?: Record<string, AggregateOp>;
    /** Forwarded to Ogma. */
    showContents?: boolean;
    /** Forwarded to Ogma. */
    padding?: number;
    /** Layout run inside each open group (`onGroupUpdate`). */
    groupLayout?: GroupLayoutSpec;
    /** Forwarded to Ogma. */
    enabled?: boolean;
}

/** Ensure `count` is part of an aggregate map and return it as entries. */
function withCount(
    aggregate: Record<string, AggregateOp> | undefined,
): [string, AggregateOp][] {
    const out: Record<string, AggregateOp> = { ...(aggregate ?? {}) };
    if (!("count" in out)) out.count = { op: "count" };
    return Object.entries(out);
}

/**
 * Group nodes that share the value(s) at `key` into a single meta-node, using
 * Ogma's node-grouping transformation.
 *
 * Any previously-applied grouping is destroyed first so repeated calls (and
 * `group_nodes` → `group_nodes` with a different key) don't stack.
 *
 * @returns the NodeGrouping handle created on this call, or `null` on failure.
 */
export async function applyGrouping(
    ogma: Ogma,
    options: NodeGroupingOptions,
    previous: Grouping | null,
): Promise<Grouping | null> {
    await removeGrouping(previous);

    const {
        key,
        selectorKey,
        idPrefix,
        data: staticData,
        dataAggregate,
        label,
        edgeDataAggregate,
        showContents,
        padding,
        groupLayout,
        enabled,
    } = options;
    const paths = toDataPaths(key);
    const selectorPath = selectorKey ? toDataPath(selectorKey) : null;
    const nodeEntries = withCount(dataAggregate);
    const edgeEntries = edgeDataAggregate ? withCount(edgeDataAggregate) : null;
    try {
        const grouping = ogma.transformations.addNodeGrouping({
            ...(selectorPath
                ? { selector: (node) => Boolean(node.getData(selectorPath)) }
                : {}),
            groupIdFunction: (node) => groupIdFromPaths(node, paths),
            nodeGenerator: (nodes, groupId) => {
                const data: Record<string, unknown> = { groupId, ...staticData };
                aggregateInto(data, nodeEntries, nodes);
                const text = label === undefined ? groupId : renderLabel(label, data);
                data.label = text;
                return {
                    ...(idPrefix !== undefined ? { id: `${idPrefix}${groupId}` } : {}),
                    data,
                    attributes: { text },
                };
            },
            ...(edgeEntries
                ? {
                      edgeGenerator: (edges) => {
                          const data: Record<string, unknown> = {};
                          aggregateInto(data, edgeEntries, edges);
                          return { data };
                      },
                  }
                : {}),
            ...(groupLayout
                ? {
                      onGroupUpdate: () =>
                          ({
                              layout: resolveLayoutName(groupLayout.name),
                              params: groupLayout.params ?? {},
                          }) as never,
                  }
                : {}),
            ...(showContents !== undefined ? { showContents } : {}),
            ...(padding !== undefined ? { padding } : {}),
            ...(enabled !== undefined ? { enabled } : {}),
        });
        await grouping.whenApplied();
        void ogma.view.locateGraph();
        return grouping;
    } catch (error) {
        console.error(`[ogma-jupyter] Grouping by "${String(key)}" failed:`, error);
        return null;
    }
}

/**
 * Enable/disable an existing node or edge grouping in place, keeping its
 * options (and the animated transition Ogma runs on toggle).
 */
export async function setGroupingEnabled(
    grouping: Grouping | EdgeGroupingHandle | null,
    enabled: boolean,
): Promise<void> {
    if (!grouping || grouping.isEnabled() === enabled) return;
    try {
        await (enabled ? grouping.enable() : grouping.disable());
    } catch (error) {
        console.error("[ogma-jupyter] Grouping toggle failed:", error);
    }
}

/** Destroy an active node grouping, restoring the individual nodes. */
export async function removeGrouping(
    grouping: Grouping | null,
): Promise<void> {
    if (!grouping) return;
    try {
        await grouping.destroy();
    } catch (error) {
        console.error("[ogma-jupyter] Ungrouping failed:", error);
    }
}

/**
 * A single aggregation applied to the nodes/edges in a group, producing one
 * value placed under `data[<outputKey>]` on the meta-node/meta-edge. All specs are pure JSON
 * so they cross the anywidget bridge — evaluation happens JS-side.
 *
 * - `count`: number of elements in the group; `field` is ignored.
 * - `sum` | `min` | `max` | `avg`: numeric reduction over `list.getData(field)`.
 *   Non-numeric values are skipped; the result is `null` when no numeric value
 *   is available (except `sum`, which stays at `0`).
 * - `first` | `last`: the corresponding value from `list.getData(field)`.
 * - `collect`: the array `list.getData(field)` (or element ids when `field` is omitted).
 */
export type AggregateOp =
    | { op: "count"; field?: string }
    | { op: "sum" | "min" | "max" | "avg"; field: string }
    | { op: "first" | "last"; field: string }
    | { op: "collect"; field?: string };

/** @deprecated kept for backwards compatibility, use `AggregateOp`. */
export type EdgeAggregateOp = AggregateOp;

/**
 * Options accepted by `applyEdgeGrouping`. Everything is serialisable so it can
 * cross the anywidget bridge — function-valued Ogma options (`selector`,
 * `groupIdFunction`, `generator`) are synthesised on this side from these
 * declarative fields.
 */
export interface EdgeGroupingOptions {
    /**
     * Data-property path(s) used to build the `groupIdFunction`, e.g.
     * `data.country`. Several paths are joined with `-` into one group id.
     */
    key?: string | string[];
    /**
     * Data-property path whose truthy value keeps an edge in the grouping.
     * Edges whose value is falsy/undefined are left ungrouped.
     */
    selectorKey?: string;
    /**
     * Aggregations written to the meta-edge's `data`. `data.count` is always
     * added automatically unless the caller overrides it here. Style rules
     * (e.g. `rules.slices(field="data.count")`) map these values to visual
     * attributes, which is the Ogma-idiomatic pattern — don't write to
     * `attributes` from the generator.
     */
    dataAggregate?: Record<string, AggregateOp>;
    /**
     * Meta-edge text template (`{{groupId}}` + any meta-edge data field).
     * Defaults to the group id; `""` leaves meta-edges unlabelled.
     */
    label?: string;
    /** Forwarded to Ogma. */
    separateEdgesByDirection?: boolean;
    /** Forwarded to Ogma. */
    enabled?: boolean;
}

function toNumberOrNull(value: unknown): number | null {
    const n = typeof value === "number" ? value : Number(value);
    return Number.isFinite(n) ? n : null;
}

function reduceAggregate(spec: AggregateOp, values: unknown[]): unknown {
    switch (spec.op) {
        case "count":
            return values.length;
        case "collect":
            return values;
        case "first":
            return values.length > 0 ? values[0] : null;
        case "last":
            return values.length > 0 ? values[values.length - 1] : null;
        case "sum": {
            let acc = 0;
            for (const v of values) {
                const n = toNumberOrNull(v);
                if (n !== null) acc += n;
            }
            return acc;
        }
        case "min":
        case "max":
        case "avg": {
            const nums: number[] = [];
            for (const v of values) {
                const n = toNumberOrNull(v);
                if (n !== null) nums.push(n);
            }
            if (nums.length === 0) return null;
            if (spec.op === "min") return Math.min(...nums);
            if (spec.op === "max") return Math.max(...nums);
            return nums.reduce((a, b) => a + b, 0) / nums.length;
        }
    }
}

/**
 * Merge edges into meta-edges using Ogma's edge-grouping transformation.
 *
 * With no options, all parallel edges (same source/target pair) are collapsed.
 * With `key`, edges are also required to share the value(s) at that data path
 * (or every one of those paths, when a list is given).
 *
 * Every meta-edge carries at least:
 * - `data.subEdges`: array of merged edge ids.
 * - `data.count`: number of merged edges (unless overridden via `dataAggregate`).
 * - `data.<keyField>`: the shared `key` value(s) (when `key` is set).
 * - `attributes.text`: the group id, or the rendered `label` template.
 *
 * Anything else — meta-edge width, colour, etc. — is expected to be driven by
 * style rules bound to these `data.*` fields, not written directly to
 * `attributes`.
 *
 * Any previously-applied edge grouping is destroyed first so repeated calls
 * don't stack.
 *
 * @returns the EdgeGrouping handle created on this call, or `null` on failure.
 */
export async function applyEdgeGrouping(
    ogma: Ogma,
    options: EdgeGroupingOptions,
    previous: EdgeGroupingHandle | null,
): Promise<EdgeGroupingHandle | null> {
    await removeEdgeGrouping(previous);
    const {
        key,
        selectorKey,
        dataAggregate,
        label,
        separateEdgesByDirection,
        enabled,
    } = options ?? {};

    const keyPaths = key ? toDataPaths(key) : null;
    const selectorPath = selectorKey ? toDataPath(selectorKey) : null;
    const aggregateEntries = withCount(dataAggregate);

    try {
        const grouping = ogma.transformations.addEdgeGrouping({
            ...(selectorPath
                ? { selector: (edge) => Boolean(edge.getData(selectorPath)) }
                : {}),
            ...(keyPaths
                ? { groupIdFunction: (edge) => groupIdFromPaths(edge, keyPaths) }
                : {}),
            generator: (edges, groupId) => {
                const data: Record<string, unknown> = {
                    subEdges: edges.getId(),
                };
                if (keyPaths) {
                    for (const path of keyPaths) {
                        const values = edges.getData(path) as unknown[];
                        data[path[path.length - 1]] = Array.isArray(values) ? values[0] : values;
                    }
                }
                aggregateInto(data, aggregateEntries, edges);
                return {
                    data,
                    attributes: {
                        text: label === undefined ? groupId : renderLabel(label, { groupId, ...data }),
                    },
                };
            },
            ...(separateEdgesByDirection !== undefined
                ? { separateEdgesByDirection }
                : {}),
            ...(enabled !== undefined ? { enabled } : {}),
        });
        await grouping.whenApplied();
        return grouping;
    } catch (error) {
        console.error("[ogma-jupyter] Edge grouping failed:", error);
        return null;
    }
}

/** Destroy an active edge grouping, restoring the individual edges. */
export async function removeEdgeGrouping(
    grouping: EdgeGroupingHandle | null,
): Promise<void> {
    if (!grouping) return;
    try {
        await grouping.destroy();
    } catch (error) {
        console.error("[ogma-jupyter] Edge ungrouping failed:", error);
    }
}
