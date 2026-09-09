import type { StyleRule, NodeGrouping, EdgeGrouping } from "@linkurious/ogma";
import type { Render } from "@anywidget/types";

import { applyStyleRules } from "./styles";
import { runLayout } from "./layouts";
import {
    applyGrouping,
    removeGrouping,
    applyEdgeGrouping,
    removeEdgeGrouping,
} from "./grouping";
import { createEventBridge } from "./events";
import type {
    CustomMessage,
    EdgeGroupingSpec,
    LayoutSpec,
    NodeGroupingSpec,
    OgmaModel,
    PendingOp,
    RunLayoutMessage,
    WidgetModel,
} from "./types";

// Ogma is NOT bundled into this file — the @linkurious/ogma library is
// license-gated and must not be redistributed. It is downloaded at runtime and
// prepended (as its UMD build) to this module, exposing the `Ogma` constructor
// as a global. We reference that global here; the value import is intentionally
// absent so esbuild produces an Ogma-free bundle (widget_core.js).
declare const Ogma: typeof import("@linkurious/ogma").Ogma;

const render: Render<WidgetModel> = ({ model, el }) => {
    const typedModel = model as OgmaModel;

    // Set container size for visualization
    el.style.width = "100%";
    const applyHeight = (): void => {
        const height = `${typedModel.get("height") ?? 700}px`;
        el.style.height = height;
        el.style.minHeight = height;
    };
    applyHeight();

    // The commercial Ogma library is downloaded at runtime and prepended to this
    // module as a global. When it has not been downloaded yet (no license
    // configured), the global is absent — show an actionable
    // message instead of throwing and leaving a blank cell.
    if (typeof Ogma === "undefined") {
        el.style.display = "flex";
        el.style.alignItems = "center";
        el.style.justifyContent = "center";
        el.style.border = "1px solid #d0d7de";
        el.style.borderRadius = "6px";
        el.style.color = "#57606a";
        el.style.font = "13px/1.5 system-ui, sans-serif";
        el.style.textAlign = "center";
        el.style.padding = "16px";
        el.innerHTML =
            "<div><strong>Ogma library not loaded.</strong><br>" +
            "Configure your license key, e.g.<br>" +
            "<code>og.set_license(\"&lt;license&gt;\")</code><br>" +
            "or set the <code>OGMA_LICENSE_KEY</code> environment variable, " +
            "then re-run this cell.</div>";
        return;
    }

    const ogma = new Ogma({ container: el });

    // StyleRule handles from the most recent applyStyleRules() call, so they
    // can be destroyed and rebuilt whenever the synced rule list changes.
    let styleRuleHandles: StyleRule[] = [];

    // Active node-grouping transformation, kept so it can be replaced or removed
    // when new group_nodes / ungroup_nodes messages arrive.
    let nodeGrouping: NodeGrouping<unknown, unknown> | null = null;

    // Active edge-grouping transformation (parallel-edge merging), kept so it
    // can be replaced or removed when new group_edges / ungroup_edges messages
    // arrive.
    let edgeGrouping: EdgeGrouping<unknown, unknown> | null = null;

    // Forwards arbitrary ogma.events.on(...) events to Python (see OgmaWidget.on()).
    const eventBridge = createEventBridge(ogma, typedModel);

    // In Jupyter the output cell is often still being laid out when Ogma first
    // measures its container, so the WebGL canvas can initialize at 0x0 and the
    // graph renders blank. A ResizeObserver re-syncs the canvas size and re-fits
    // the view the moment the container gains real dimensions.
    let lastWidth = 0;
    let lastHeight = 0;
    const resizeObserver = new ResizeObserver((entries) => {
        const entry = entries[0];
        if (!entry) return;
        const { width, height } = entry.contentRect;
        if (width === 0 || height === 0) return;
        if (width === lastWidth && height === lastHeight) return;
        lastWidth = width;
        lastHeight = height;
        ogma.view.forceResize();
        if (ogma.getNodes().size > 0) {
            void ogma.view.locateGraph();
        }
    });
    resizeObserver.observe(el);

    const loadGraph = async (): Promise<void> => {
        // graph_data is already in Ogma's RawGraph format (id/attributes/data
        // for nodes, source/target/data for edges), so it is passed through
        // directly - keeping node attributes such as x/y intact.
        const data = typedModel.get("graph_data");
        if (data && Array.isArray(data.nodes) && data.nodes.length > 0) {
            await ogma.setGraph(data);
            await ogma.view.locateGraph();
        }
    };

    const applyStyles = (): void => {
        styleRuleHandles = applyStyleRules(
            ogma,
            typedModel.get("style_rules"),
            styleRuleHandles,
        );
    };

    const applyNodeGroupingFromModel = (): void => {
        const spec = typedModel.get("node_grouping") as NodeGroupingSpec | null;
        if (!spec) {
            void removeGrouping(nodeGrouping);
            nodeGrouping = null;
            return;
        }
        void applyGrouping(ogma, spec.key, nodeGrouping).then((handle) => {
            nodeGrouping = handle;
        });
    };

    const applyEdgeGroupingFromModel = (): void => {
        const spec = typedModel.get("edge_grouping") as EdgeGroupingSpec | null;
        if (!spec) {
            void removeEdgeGrouping(edgeGrouping);
            edgeGrouping = null;
            return;
        }
        void applyEdgeGrouping(
            ogma,
            spec as Parameters<typeof applyEdgeGrouping>[1],
            edgeGrouping,
        ).then((handle) => {
            edgeGrouping = handle;
        });
    };

    // Highest `seq` in `_pending_ops` that has already been applied. Serves as
    // the cursor for the append-only queue populated by add_nodes/add_edges/
    // add_graph on the Python side.
    let appliedOpSeq = 0;
    // Serialises applyPendingOps() calls so overlapping change events don't
    // race and skip or double-apply entries.
    let pendingOpsQueue: Promise<void> = Promise.resolve();

    const applyPendingOps = (): void => {
        pendingOpsQueue = pendingOpsQueue.then(async () => {
            const ops = (typedModel.get("_pending_ops") ?? []) as PendingOp[];
            for (const op of ops) {
                if (op.seq <= appliedOpSeq) continue;
                try {
                    if (op.kind === "add_nodes") {
                        await ogma.addNodes(op.nodes);
                    } else if (op.kind === "add_edges") {
                        await ogma.addEdges(op.edges);
                    } else if (op.kind === "add_graph") {
                        await ogma.addGraph(op.graph);
                    }
                } catch (err) {
                    console.error("[ogma-jupyter] pending op failed:", op, err);
                }
                appliedOpSeq = op.seq;
            }
        });
    };

    const runInitialLayout = async (): Promise<void> => {
        const layout: LayoutSpec | null = typedModel.get("graph_layout");
        if (layout && layout.name) {
            const { name, ...options } = layout;
            await runLayout(ogma, name, options);
        }
    };

    // Initial render: load the graph, apply styles, then run the initial layout.
    void (async () => {
        await loadGraph();
        applyStyles();
        applyNodeGroupingFromModel();
        applyEdgeGroupingFromModel();
        applyPendingOps();
        await runInitialLayout();
    })();

    // React to changes coming from Python.
    typedModel.on("change:graph_data", () => void loadGraph());
    typedModel.on("change:style_rules", applyStyles);
    typedModel.on("change:graph_layout", () => void runInitialLayout());
    typedModel.on("change:node_grouping", applyNodeGroupingFromModel);
    typedModel.on("change:edge_grouping", applyEdgeGroupingFromModel);
    typedModel.on("change:_pending_ops", applyPendingOps);
    typedModel.on("change:height", () => {
        applyHeight();
        ogma.view.forceResize();
    });
    typedModel.on("change:event_subscriptions", () =>
        eventBridge.sync(typedModel.get("event_subscriptions") ?? []),
    );
    eventBridge.sync(typedModel.get("event_subscriptions") ?? []);

    // Imperative commands sent via widget.send(...) (e.g. run_layout).
    typedModel.on("msg:custom", (msg: CustomMessage) => {
        if (!msg) return;
        if (msg.type === "run_layout") {
            const { name, options } = msg as RunLayoutMessage;
            void runLayout(ogma, name, options ?? {});
        }
    });

    // CRITICAL: Return cleanup function to prevent WebGL context leaks.
    // Browsers limit WebGL contexts to 8-16; without cleanup, older
    // visualizations go blank when the limit is reached.
    return () => {
        resizeObserver.disconnect();
        eventBridge.destroy();
        ogma.destroy();
    };
};

export default { render };
