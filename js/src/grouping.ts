import type { Ogma, NodeGrouping } from "@linkurious/ogma";

type Grouping = NodeGrouping<unknown, unknown>;

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
