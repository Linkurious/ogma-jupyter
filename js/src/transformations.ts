import type { Ogma } from "@linkurious/ogma";

import { resolveLayoutName } from "./layouts";
import type { GroupsLayoutSpec, TransformationAnimationSpec } from "./types";

/**
 * Mirror `ogma.transformations.onGroupsUpdated`: run `spec` as the global
 * layout every time the node groups change (grouping enabled/disabled, nodes
 * entering/leaving a group, `triggerGroupsUpdated()`). `null` clears it.
 */
export function applyGroupsLayout(ogma: Ogma, spec: GroupsLayoutSpec | null): void {
    if (!spec) {
        ogma.transformations.onGroupsUpdated(() => null);
        return;
    }
    const layout = resolveLayoutName(spec.name);
    const params = spec.params ?? {};
    ogma.transformations.onGroupsUpdated(() => ({ layout, params }) as never);
}

/** Mirror `ogma.transformations.setAnimation`. `null` restores Ogma's default (no animation). */
export function applyTransformationAnimation(
    ogma: Ogma,
    spec: TransformationAnimationSpec | null,
): void {
    ogma.transformations.setAnimation((spec ?? { duration: 0 }) as never);
}

/**
 * Mirror `ogma.transformations.triggerGroupsUpdated()`, then refresh the
 * pipeline so the `onGroupsUpdated` layout runs right away rather than on the
 * next unrelated transformation update.
 */
export async function triggerGroupsUpdated(ogma: Ogma): Promise<void> {
    ogma.transformations.triggerGroupsUpdated();
    const [first] = ogma.transformations.getList();
    if (!first) return;
    try {
        await first.refresh();
    } catch (error) {
        console.error("[ogma-jupyter] Transformation refresh failed:", error);
    }
}
