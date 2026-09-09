import type { Ogma, NodeGrouping, EdgeGrouping } from "@linkurious/ogma";

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

/**
 * Group nodes that share the value at `key` into a single meta-node, using
 * Ogma's node-grouping transformation.
 *
 * Any previously-applied grouping is destroyed first so repeated calls (and
 * `group_nodes` → `group_nodes` with a different key) don't stack.
 *
 * @returns the NodeGrouping handle created on this call, or `null` on failure.
 */
export async function applyGrouping(
    ogma: Ogma,
    key: string,
    previous: Grouping | null,
): Promise<Grouping | null> {
    await removeGrouping(previous);

    const path = toDataPath(key);
    try {
        const grouping = ogma.transformations.addNodeGrouping({
            groupIdFunction: (node) => {
                const value = node.getData(path);
                return value === undefined || value === null
                    ? undefined
                    : String(value);
            },
            nodeGenerator: (_nodes, groupId) => ({
                data: { label: groupId },
                attributes: { text: groupId },
            }),
        });
        await grouping.whenApplied();
        void ogma.view.locateGraph();
        return grouping;
    } catch (error) {
        console.error(`[ogma-jupyter] Grouping by "${key}" failed:`, error);
        return null;
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
 * A single aggregation applied to the edges in a group, producing one value
 * placed under `data[<outputKey>]` on the meta-edge. All specs are pure JSON
 * so they cross the anywidget bridge — evaluation happens JS-side.
 *
 * - `count`: number of edges in the group; `field` is ignored.
 * - `sum` | `min` | `max` | `avg`: numeric reduction over `edges.getData(field)`.
 *   Non-numeric values are skipped; the result is `null` when no numeric value
 *   is available (except `sum`, which stays at `0`).
 * - `first` | `last`: the corresponding value from `edges.getData(field)`.
 * - `collect`: the array `edges.getData(field)` (or edge ids when `field` is omitted).
 */
export type EdgeAggregateOp =
    | { op: "count"; field?: string }
    | { op: "sum" | "min" | "max" | "avg"; field: string }
    | { op: "first" | "last"; field: string }
    | { op: "collect"; field?: string };

/**
 * Options accepted by `applyEdgeGrouping`. Everything is serialisable so it can
 * cross the anywidget bridge — function-valued Ogma options (`selector`,
 * `groupIdFunction`, `generator`) are synthesised on this side from these
 * declarative fields.
 */
export interface EdgeGroupingOptions {
    /** Data-property path used to build the `groupIdFunction`, e.g. `data.country`. */
    key?: string;
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
    dataAggregate?: Record<string, EdgeAggregateOp>;
    /** Forwarded to Ogma. */
    separateEdgesByDirection?: boolean;
    /** Forwarded to Ogma. */
    enabled?: boolean;
}

function toNumberOrNull(value: unknown): number | null {
    const n = typeof value === "number" ? value : Number(value);
    return Number.isFinite(n) ? n : null;
}

function reduceAggregate(spec: EdgeAggregateOp, values: unknown[]): unknown {
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
 * With `key`, edges are also required to share the value at that data path.
 *
 * Every meta-edge carries at least:
 * - `data.subEdges`: array of merged edge ids.
 * - `data.count`: number of merged edges (unless overridden via `dataAggregate`).
 * - `data.<keyField>`: the shared `key` value (when `key` is set).
 * - `attributes.text`: the group id.
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
        separateEdgesByDirection,
        enabled,
    } = options ?? {};

    const keyPath = key ? toDataPath(key) : null;
    const selectorPath = selectorKey ? toDataPath(selectorKey) : null;
    const keyField = keyPath ? keyPath[keyPath.length - 1] : undefined;

    const aggregate: Record<string, EdgeAggregateOp> = { ...(dataAggregate ?? {}) };
    if (!("count" in aggregate)) {
        aggregate.count = { op: "count" };
    }
    const aggregateEntries = Object.entries(aggregate);

    try {
        const grouping = ogma.transformations.addEdgeGrouping({
            ...(selectorPath
                ? { selector: (edge) => Boolean(edge.getData(selectorPath)) }
                : {}),
            ...(keyPath
                ? {
                      groupIdFunction: (edge) => {
                          const value = edge.getData(keyPath);
                          return value === undefined || value === null
                              ? undefined
                              : String(value);
                      },
                  }
                : {}),
            generator: (edges, groupId) => {
                const data: Record<string, unknown> = {
                    subEdges: edges.getId(),
                };
                if (keyField) {
                    const values = edges.getData(keyPath!) as unknown[];
                    data[keyField] = Array.isArray(values) ? values[0] : values;
                }
                for (const [outKey, spec] of aggregateEntries) {
                    const values =
                        "field" in spec && spec.field
                            ? (edges.getData(toDataPath(spec.field)) as unknown[])
                            : (edges.getId() as unknown[]);
                    data[outKey] = reduceAggregate(spec, values);
                }
                return {
                    data,
                    attributes: { text: groupId },
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
