import type { Ogma } from "@linkurious/ogma";

// Explicit mapping from the layout names accepted by the Python API
// (widget.run_layout / VALID_LAYOUTS in widget.py) to the exact method names
// exposed by Ogma 6's `ogma.layouts` API. Keys are lower-case; lookups are
// case-insensitive. This is the single source of truth on the JS side — there
// is no identity fallback, so only these names resolve and anything else is
// rejected with a warning.
//
// Ogma 6 ships two distinct force-directed layouts: `force` (Barnes-Hut) and
// `forceLink` (ForceLink). `forceatlas2` is kept as a backwards-compatible
// alias for `forceLink`.
const LAYOUT_METHODS: Record<string, string> = {
    force: "force",
    forcelink: "forceLink",
    forceatlas2: "forceLink",
    hierarchical: "hierarchical",
    sequential: "sequential",
    radial: "radial",
    concentric: "concentric",
    grid: "grid",
};

type LayoutMethod = (options?: Record<string, unknown>) => Promise<unknown>;

function resolveLayout(ogma: Ogma, name: string): LayoutMethod | null {
    const method = LAYOUT_METHODS[name.toLowerCase()];
    if (!method) {
        return null;
    }
    const layouts = ogma.layouts as unknown as Record<string, unknown>;
    const fn = layouts[method];
    return typeof fn === "function" ? (fn.bind(ogma.layouts) as LayoutMethod) : null;
}

/**
 * Run an Ogma layout algorithm by name, passing through options coming from
 * Python (e.g. `duration`, `direction`). The view is re-centered on completion
 * unless the caller explicitly sets `locate`.
 */
export async function runLayout(
    ogma: Ogma,
    name: string,
    options: Record<string, unknown> = {},
): Promise<void> {
    const layout = resolveLayout(ogma, name);
    if (!layout) {
        console.warn(`[ogma-jupyter] Unknown layout "${name}" - ignoring.`);
        return;
    }
    try {
        await layout({ locate: true, ...options });
    } catch (error) {
        console.error(`[ogma-jupyter] Layout "${name}" failed:`, error);
    }
}
