import type { Edge, Node, Ogma, StyleClass } from "@linkurious/ogma";

import { convertAttributes } from "./styles";
import type { HighlightMessage, StyleClassSpec } from "./types";

/**
 * Sync the style classes declared from Python (`widget.add_class`) with
 * `ogma.styles.createClass`. Existing classes are updated in place so the
 * elements that already carry them keep them; classes no longer declared are
 * destroyed.
 */
export function applyStyleClasses(
    ogma: Ogma,
    specs: StyleClassSpec[] | undefined,
    previous: Map<string, StyleClass>,
): Map<string, StyleClass> {
    const next = new Map<string, StyleClass>();
    for (const spec of specs ?? []) {
        const definition = {
            nodeAttributes: spec.nodeAttributes
                ? convertAttributes(ogma, spec.nodeAttributes)
                : null,
            edgeAttributes: spec.edgeAttributes
                ? convertAttributes(ogma, spec.edgeAttributes)
                : null,
        };
        const existing = previous.get(spec.name);
        next.set(
            spec.name,
            existing
                ? existing.update(definition as never)
                : ogma.styles.createClass({ name: spec.name, ...definition } as never),
        );
    }
    for (const [name, styleClass] of previous) {
        if (!next.has(name)) void styleClass.destroy();
    }
    return next;
}

type Element = Node | Edge;

/**
 * True when `element` is kept, or is a meta-element (node/edge grouping)
 * containing a kept element at any depth — so highlighting raw ids also keeps
 * the meta-nodes and meta-edges that currently stand for them.
 */
function isKept(element: Element, keep: Set<unknown>, memo: Map<unknown, boolean>): boolean {
    const id = element.getId();
    if (keep.has(id)) return true;
    if (!element.isVirtual()) return false;
    const cached = memo.get(id);
    if (cached !== undefined) return cached;
    memo.set(id, false); // cycle guard
    const subs = element.isNode
        ? (element as Node).getSubNodes()
        : (element as Edge).getSubEdges();
    let kept = false;
    if (subs) {
        const list = subs.toArray() as Element[];
        for (let i = 0; i < list.length && !kept; i++) kept = isKept(list[i], keep, memo);
    }
    memo.set(id, kept);
    return kept;
}

/**
 * Put `className` on every visible element *except* the given node/edge ids
 * (and the meta-elements covering them), and take it off those. An empty
 * selection clears the class everywhere.
 */
export async function highlight(ogma: Ogma, msg: HighlightMessage): Promise<void> {
    const { className, nodes = [], edges = [], duration = 0 } = msg;
    const styleClass = ogma.styles.getClass(className);
    if (!styleClass) {
        console.warn(`[ogma-jupyter] highlight: unknown class "${className}".`);
        return;
    }
    const animation = { duration, easing: "quadraticInOut" } as const;
    const allNodes = ogma.getNodes();
    const allEdges = ogma.getEdges();
    if (nodes.length === 0 && edges.length === 0) {
        await Promise.all([
            allNodes.removeClass(className, animation),
            allEdges.removeClass(className, animation),
        ]);
        return;
    }
    const keepNodes = new Set<unknown>(nodes);
    const keepEdges = new Set<unknown>(edges);
    const nodeMemo = new Map<unknown, boolean>();
    const edgeMemo = new Map<unknown, boolean>();
    const keptNodes = allNodes.filter((n) => isKept(n, keepNodes, nodeMemo));
    const keptEdges = allEdges.filter((e) => isKept(e, keepEdges, edgeMemo));
    await Promise.all([
        allNodes.subtract(keptNodes).addClass(className, animation),
        allEdges.subtract(keptEdges).addClass(className, animation),
        keptNodes.removeClass(className, animation),
        keptEdges.removeClass(className, animation),
    ]);
}
