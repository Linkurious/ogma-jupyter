// js/src/styles.ts
function normalizeField(field) {
  return field.startsWith("data.") ? field.slice("data.".length) : field;
}
function normalizeTemplate(template) {
  return template.replace(/\{\{\s*data\./g, "{{");
}
function asRuleDescriptor(value) {
  switch (value.type) {
    case "map":
    case "slices":
      return typeof value.field === "string" ? value : null;
    case "template":
      return typeof value.template === "string" ? value : null;
    default:
      return null;
  }
}
function buildRule(ogma, descriptor) {
  switch (descriptor.type) {
    case "map": {
      const options = {
        field: normalizeField(descriptor.field),
        values: descriptor.values
      };
      if (descriptor.fallback !== void 0) {
        options.fallback = descriptor.fallback;
      }
      return ogma.rules.map(options);
    }
    case "slices": {
      const options = {
        field: normalizeField(descriptor.field),
        values: descriptor.values
      };
      if (descriptor.stops !== void 0) options.stops = descriptor.stops;
      if (descriptor.fallback !== void 0) options.fallback = descriptor.fallback;
      if (descriptor.reverse !== void 0) options.reverse = descriptor.reverse;
      return ogma.rules.slices(options);
    }
    case "template":
      return ogma.rules.template(normalizeTemplate(descriptor.template));
  }
}
function convertValue(ogma, value) {
  if (Array.isArray(value)) {
    return value.map((item) => convertValue(ogma, item));
  }
  if (value !== null && typeof value === "object") {
    const record = value;
    const descriptor = asRuleDescriptor(record);
    if (descriptor) {
      return buildRule(ogma, descriptor);
    }
    const out = {};
    for (const key of Object.keys(record)) {
      out[key] = convertValue(ogma, record[key]);
    }
    return out;
  }
  return value;
}
function convertAttributes(ogma, attributes) {
  const out = {};
  for (const key of Object.keys(attributes)) {
    out[key] = convertValue(ogma, attributes[key]);
  }
  return out;
}
function applyStyleRules(ogma, styleRules, previous) {
  for (const rule of previous) {
    void rule.destroy();
  }
  const applied = [];
  for (const spec of styleRules ?? []) {
    const definition = {};
    if (spec.nodeAttributes) {
      definition.nodeAttributes = convertAttributes(ogma, spec.nodeAttributes);
    }
    if (spec.edgeAttributes) {
      definition.edgeAttributes = convertAttributes(ogma, spec.edgeAttributes);
    }
    applied.push(ogma.styles.addRule(definition));
  }
  return applied;
}

// js/src/layouts.ts
var LAYOUT_METHODS = {
  force: "force",
  forcelink: "forceLink",
  forceatlas2: "forceLink",
  hierarchical: "hierarchical",
  sequential: "sequential",
  radial: "radial",
  concentric: "concentric",
  grid: "grid"
};
function resolveLayoutName(name) {
  return LAYOUT_METHODS[name.toLowerCase()] ?? name;
}
function resolveLayout(ogma, name) {
  const method = LAYOUT_METHODS[name.toLowerCase()];
  if (!method) {
    return null;
  }
  const layouts = ogma.layouts;
  const fn = layouts[method];
  return typeof fn === "function" ? fn.bind(ogma.layouts) : null;
}
async function runLayout(ogma, name, options = {}) {
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

// js/src/grouping.ts
function toDataPath(key) {
  const path = key.startsWith("data.") ? key.slice("data.".length) : key;
  return path.split(".");
}
function toDataPaths(key) {
  return (Array.isArray(key) ? key : [key]).map(toDataPath);
}
function groupIdFromPaths(element, paths) {
  let id = "";
  for (let i = 0; i < paths.length; i++) {
    const value = element.getData(paths[i]);
    if (value === void 0 || value === null) return void 0;
    id += i === 0 ? String(value) : `-${String(value)}`;
  }
  return id;
}
function renderLabel(template, ctx) {
  return template.replace(/\{\{\s*([^}]+?)\s*\}\}/g, (_, path) => {
    let cur = ctx;
    for (const key of path.split(".")) {
      if (cur == null || typeof cur !== "object") return "";
      cur = cur[key];
    }
    return cur == null ? "" : String(cur);
  });
}
function aggregateInto(data, entries, list) {
  for (const [outKey, spec] of entries) {
    const values = "field" in spec && spec.field ? list.getData(toDataPath(spec.field)) : list.getId();
    data[outKey] = reduceAggregate(spec, values);
  }
}
function withCount(aggregate) {
  const out = { ...aggregate ?? {} };
  if (!("count" in out)) out.count = { op: "count" };
  return Object.entries(out);
}
async function applyGrouping(ogma, options, previous) {
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
    enabled
  } = options;
  const paths = toDataPaths(key);
  const selectorPath = selectorKey ? toDataPath(selectorKey) : null;
  const nodeEntries = withCount(dataAggregate);
  const edgeEntries = edgeDataAggregate ? withCount(edgeDataAggregate) : null;
  try {
    const grouping = ogma.transformations.addNodeGrouping({
      ...selectorPath ? { selector: (node) => Boolean(node.getData(selectorPath)) } : {},
      groupIdFunction: (node) => groupIdFromPaths(node, paths),
      nodeGenerator: (nodes, groupId) => {
        const data = { groupId, ...staticData };
        aggregateInto(data, nodeEntries, nodes);
        const text = label === void 0 ? groupId : renderLabel(label, data);
        data.label = text;
        return {
          ...idPrefix !== void 0 ? { id: `${idPrefix}${groupId}` } : {},
          data,
          attributes: { text }
        };
      },
      ...edgeEntries ? {
        edgeGenerator: (edges) => {
          const data = {};
          aggregateInto(data, edgeEntries, edges);
          return { data };
        }
      } : {},
      ...groupLayout ? {
        onGroupUpdate: () => ({
          layout: resolveLayoutName(groupLayout.name),
          params: groupLayout.params ?? {}
        })
      } : {},
      ...showContents !== void 0 ? { showContents } : {},
      ...padding !== void 0 ? { padding } : {},
      ...enabled !== void 0 ? { enabled } : {}
    });
    await grouping.whenApplied();
    void ogma.view.locateGraph();
    return grouping;
  } catch (error) {
    console.error(`[ogma-jupyter] Grouping by "${String(key)}" failed:`, error);
    return null;
  }
}
async function setGroupingEnabled(grouping, enabled) {
  if (!grouping || grouping.isEnabled() === enabled) return;
  try {
    await (enabled ? grouping.enable() : grouping.disable());
  } catch (error) {
    console.error("[ogma-jupyter] Grouping toggle failed:", error);
  }
}
async function removeGrouping(grouping) {
  if (!grouping) return;
  try {
    await grouping.destroy();
  } catch (error) {
    console.error("[ogma-jupyter] Ungrouping failed:", error);
  }
}
function toNumberOrNull(value) {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}
function reduceAggregate(spec, values) {
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
      const nums = [];
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
async function applyEdgeGrouping(ogma, options, previous) {
  await removeEdgeGrouping(previous);
  const {
    key,
    selectorKey,
    dataAggregate,
    label,
    separateEdgesByDirection,
    enabled
  } = options ?? {};
  const keyPaths = key ? toDataPaths(key) : null;
  const selectorPath = selectorKey ? toDataPath(selectorKey) : null;
  const aggregateEntries = withCount(dataAggregate);
  try {
    const grouping = ogma.transformations.addEdgeGrouping({
      ...selectorPath ? { selector: (edge) => Boolean(edge.getData(selectorPath)) } : {},
      ...keyPaths ? { groupIdFunction: (edge) => groupIdFromPaths(edge, keyPaths) } : {},
      generator: (edges, groupId) => {
        const data = {
          subEdges: edges.getId()
        };
        if (keyPaths) {
          for (const path of keyPaths) {
            const values = edges.getData(path);
            data[path[path.length - 1]] = Array.isArray(values) ? values[0] : values;
          }
        }
        aggregateInto(data, aggregateEntries, edges);
        return {
          data,
          attributes: {
            text: label === void 0 ? groupId : renderLabel(label, { groupId, ...data })
          }
        };
      },
      ...separateEdgesByDirection !== void 0 ? { separateEdgesByDirection } : {},
      ...enabled !== void 0 ? { enabled } : {}
    });
    await grouping.whenApplied();
    return grouping;
  } catch (error) {
    console.error("[ogma-jupyter] Edge grouping failed:", error);
    return null;
  }
}
async function removeEdgeGrouping(grouping) {
  if (!grouping) return;
  try {
    await grouping.destroy();
  } catch (error) {
    console.error("[ogma-jupyter] Edge ungrouping failed:", error);
  }
}

// js/src/classes.ts
function applyStyleClasses(ogma, specs, previous) {
  const next = /* @__PURE__ */ new Map();
  for (const spec of specs ?? []) {
    const definition = {
      nodeAttributes: spec.nodeAttributes ? convertAttributes(ogma, spec.nodeAttributes) : null,
      edgeAttributes: spec.edgeAttributes ? convertAttributes(ogma, spec.edgeAttributes) : null
    };
    const existing = previous.get(spec.name);
    next.set(
      spec.name,
      existing ? existing.update(definition) : ogma.styles.createClass({ name: spec.name, ...definition })
    );
  }
  for (const [name, styleClass] of previous) {
    if (!next.has(name)) void styleClass.destroy();
  }
  return next;
}
function isKept(element, keep, memo) {
  const id = element.getId();
  if (keep.has(id)) return true;
  if (!element.isVirtual()) return false;
  const cached = memo.get(id);
  if (cached !== void 0) return cached;
  memo.set(id, false);
  const subs = element.isNode ? element.getSubNodes() : element.getSubEdges();
  let kept = false;
  if (subs) {
    const list = subs.toArray();
    for (let i = 0; i < list.length && !kept; i++) kept = isKept(list[i], keep, memo);
  }
  memo.set(id, kept);
  return kept;
}
async function highlight(ogma, msg) {
  const { className, nodes = [], edges = [], duration = 0 } = msg;
  const styleClass = ogma.styles.getClass(className);
  if (!styleClass) {
    console.warn(`[ogma-jupyter] highlight: unknown class "${className}".`);
    return;
  }
  const animation = { duration, easing: "quadraticInOut" };
  const allNodes = ogma.getNodes();
  const allEdges = ogma.getEdges();
  if (nodes.length === 0 && edges.length === 0) {
    await Promise.all([
      allNodes.removeClass(className, animation),
      allEdges.removeClass(className, animation)
    ]);
    return;
  }
  const keepNodes = new Set(nodes);
  const keepEdges = new Set(edges);
  const nodeMemo = /* @__PURE__ */ new Map();
  const edgeMemo = /* @__PURE__ */ new Map();
  const keptNodes = allNodes.filter((n) => isKept(n, keepNodes, nodeMemo));
  const keptEdges = allEdges.filter((e) => isKept(e, keepEdges, edgeMemo));
  await Promise.all([
    allNodes.subtract(keptNodes).addClass(className, animation),
    allEdges.subtract(keptEdges).addClass(className, animation),
    keptNodes.removeClass(className, animation),
    keptEdges.removeClass(className, animation)
  ]);
}

// js/src/transformations.ts
function applyGroupsLayout(ogma, spec) {
  if (!spec) {
    ogma.transformations.onGroupsUpdated(() => null);
    return;
  }
  const layout = resolveLayoutName(spec.name);
  const params = spec.params ?? {};
  ogma.transformations.onGroupsUpdated(() => ({ layout, params }));
}
function applyTransformationAnimation(ogma, spec) {
  ogma.transformations.setAnimation(spec ?? { duration: 0 });
}
async function triggerGroupsUpdated(ogma) {
  ogma.transformations.triggerGroupsUpdated();
  const [first] = ogma.transformations.getList();
  if (!first) return;
  try {
    await first.refresh();
  } catch (error) {
    console.error("[ogma-jupyter] Transformation refresh failed:", error);
  }
}

// js/src/serialize.ts
function isOgmaElement(value) {
  if (!value || typeof value !== "object") return false;
  const candidate = value;
  return typeof candidate.getId === "function" && typeof candidate.getData === "function" && (candidate.isNode === true || candidate.isEdge === true);
}
function isOgmaCollection(value) {
  if (!value || typeof value !== "object") return false;
  const candidate = value;
  return typeof candidate.toArray === "function" && typeof candidate.map === "function";
}
function serializeElement(element) {
  return {
    id: element.getId(),
    isNode: element.isNode === true,
    isEdge: element.isEdge === true,
    data: element.getData()
  };
}
function serializeValue(value) {
  if (value === null || value === void 0) return null;
  const valueType = typeof value;
  if (valueType === "number" || valueType === "string" || valueType === "boolean") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(serializeValue);
  }
  if (isOgmaElement(value)) {
    return serializeElement(value);
  }
  if (isOgmaCollection(value)) {
    return value.toArray().map((item) => serializeElement(item));
  }
  if (valueType === "object") {
    if (typeof Event !== "undefined" && value instanceof Event) return void 0;
    const out = {};
    for (const key of Object.keys(value)) {
      if (key === "domEvent") continue;
      const serialized = serializeValue(value[key]);
      if (serialized !== void 0) out[key] = serialized;
    }
    return out;
  }
  return void 0;
}
function serializeEventPayload(payload) {
  const serialized = serializeValue(payload);
  if (serialized && typeof serialized === "object" && !Array.isArray(serialized)) {
    return serialized;
  }
  return { value: serialized };
}

// js/src/events.ts
function createEventBridge(ogma, model) {
  const events = ogma.events;
  const listeners = /* @__PURE__ */ new Map();
  function subscribe(eventName) {
    if (listeners.has(eventName)) return;
    const handler = (payload) => {
      model.send({
        type: "ogma_event",
        event: eventName,
        payload: serializeEventPayload(payload)
      });
    };
    events.on(eventName, handler);
    listeners.set(eventName, handler);
  }
  function unsubscribe(eventName) {
    const handler = listeners.get(eventName);
    if (!handler) return;
    events.off(eventName, handler);
    listeners.delete(eventName);
  }
  function sync(eventNames) {
    const wanted = new Set(eventNames ?? []);
    for (const eventName of Array.from(listeners.keys())) {
      if (!wanted.has(eventName)) unsubscribe(eventName);
    }
    for (const eventName of wanted) subscribe(eventName);
  }
  function destroy() {
    for (const eventName of Array.from(listeners.keys())) unsubscribe(eventName);
  }
  return { sync, destroy };
}

// js/src/index.ts
var render = ({ model, el }) => {
  const typedModel = model;
  el.style.width = "100%";
  const applyHeight = () => {
    const height = `${typedModel.get("height") ?? 700}px`;
    el.style.height = height;
    el.style.minHeight = height;
  };
  applyHeight();
  if (!document.getElementById("ogma-jupyter-styles")) {
    const style = document.createElement("style");
    style.id = "ogma-jupyter-styles";
    style.textContent = `
.ogma-jupyter-tooltip {
    background: rgba(30, 30, 40, 0.92);
    color: #f6f8fa;
    padding: 6px 10px;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    font: 12px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif;
    max-width: 320px;
    word-break: break-word;
    pointer-events: none;
}
.ogma-jupyter-tooltip b { color: #ffd166; }
.ogma-jupyter-tooltip pre {
    margin: 4px 0 0;
    padding: 0;
    background: transparent;
    color: inherit;
    font: 11px/1.35 ui-monospace, SFMono-Regular, Menlo, monospace;
    white-space: pre-wrap;
}
`;
    document.head.appendChild(style);
  }
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
    el.innerHTML = '<div><strong>Ogma library not loaded.</strong><br>Configure your license key, e.g.<br><code>og.set_license("&lt;license&gt;")</code><br>or set the <code>OGMA_LICENSE_KEY</code> environment variable, then re-run this cell.</div>';
    return;
  }
  const ogma = new Ogma({ container: el });
  const applyOptions = () => {
    const options = typedModel.get("ogma_options");
    if (options && Object.keys(options).length > 0) {
      ogma.setOptions(options);
    }
  };
  applyOptions();
  let styleRuleHandles = [];
  let nodeGrouping = null;
  let nodeGroupingSpec = null;
  let nodeGroupingQueue = Promise.resolve();
  let edgeGrouping = null;
  let styleClasses = /* @__PURE__ */ new Map();
  const eventBridge = createEventBridge(ogma, typedModel);
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
  const loadGraph = async () => {
    const data = typedModel.get("graph_data");
    if (data && Array.isArray(data.nodes) && data.nodes.length > 0) {
      await ogma.setGraph(data);
      await ogma.view.locateGraph();
    }
  };
  const applyStyles = () => {
    styleRuleHandles = applyStyleRules(
      ogma,
      typedModel.get("style_rules"),
      styleRuleHandles
    );
  };
  const sameSpecIgnoringEnabled = (a, b) => {
    if (!a) return false;
    const { enabled: _a, ...restA } = a;
    const { enabled: _b, ...restB } = b;
    return JSON.stringify(restA) === JSON.stringify(restB);
  };
  const applyNodeGroupingFromModel = () => {
    const spec = typedModel.get("node_grouping");
    nodeGroupingQueue = nodeGroupingQueue.then(async () => {
      if (!spec) {
        await removeGrouping(nodeGrouping);
        nodeGrouping = null;
        nodeGroupingSpec = null;
        return;
      }
      if (nodeGrouping && sameSpecIgnoringEnabled(nodeGroupingSpec, spec)) {
        await setGroupingEnabled(nodeGrouping, spec.enabled ?? true);
      } else {
        nodeGrouping = await applyGrouping(
          ogma,
          spec,
          nodeGrouping
        );
      }
      nodeGroupingSpec = spec;
    });
  };
  const applyStyleClassesFromModel = () => {
    styleClasses = applyStyleClasses(
      ogma,
      typedModel.get("style_classes"),
      styleClasses
    );
  };
  const applyGroupsLayoutFromModel = () => {
    applyGroupsLayout(
      ogma,
      typedModel.get("groups_layout")
    );
  };
  const applyTransformationAnimationFromModel = () => {
    applyTransformationAnimation(
      ogma,
      typedModel.get("transformation_animation")
    );
  };
  const applyEdgeGroupingFromModel = () => {
    const spec = typedModel.get("edge_grouping");
    if (!spec) {
      void removeEdgeGrouping(edgeGrouping);
      edgeGrouping = null;
      return;
    }
    void applyEdgeGrouping(
      ogma,
      spec,
      edgeGrouping
    ).then((handle) => {
      edgeGrouping = handle;
    });
  };
  let appliedOpSeq = 0;
  let pendingOpsQueue = Promise.resolve();
  const applyPendingOps = () => {
    pendingOpsQueue = pendingOpsQueue.then(async () => {
      const ops = typedModel.get("_pending_ops") ?? [];
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
  const HTML_ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  };
  const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => HTML_ESCAPES[c] ?? c);
  const renderTemplate = (tmpl, ctx) => tmpl.replace(/\{\{\s*([^}]+?)\s*\}\}/g, (_, path) => {
    let cur = ctx;
    for (const key of path.split(".")) {
      if (cur == null || typeof cur !== "object") return "";
      cur = cur[key];
    }
    if (cur == null) return "";
    const s = typeof cur === "object" ? JSON.stringify(cur, null, 2) : String(cur);
    return escapeHtml(s);
  });
  ogma.tools.tooltip.onNodeHover(
    (node) => {
      const spec = typedModel.get("node_tooltip");
      if (!spec) return "";
      const data = node.getData() ?? {};
      const ctx = { id: node.getId(), ...data };
      if (spec === true) {
        return `<b>${escapeHtml(String(ctx.id))}</b><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
      }
      return renderTemplate(spec, ctx);
    },
    { className: "ogma-jupyter-tooltip" }
  );
  const runInitialLayout = async () => {
    const layout = typedModel.get("graph_layout");
    if (layout && layout.name) {
      const { name, ...options } = layout;
      await runLayout(ogma, name, options);
    }
  };
  void (async () => {
    await loadGraph();
    applyStyles();
    applyStyleClassesFromModel();
    applyTransformationAnimationFromModel();
    applyGroupsLayoutFromModel();
    applyNodeGroupingFromModel();
    applyEdgeGroupingFromModel();
    applyPendingOps();
    await runInitialLayout();
  })();
  typedModel.on("change:graph_data", () => void loadGraph());
  typedModel.on("change:style_rules", applyStyles);
  typedModel.on("change:style_classes", applyStyleClassesFromModel);
  typedModel.on("change:ogma_options", applyOptions);
  typedModel.on("change:groups_layout", applyGroupsLayoutFromModel);
  typedModel.on("change:transformation_animation", applyTransformationAnimationFromModel);
  typedModel.on("change:graph_layout", () => void runInitialLayout());
  typedModel.on("change:node_grouping", applyNodeGroupingFromModel);
  typedModel.on("change:edge_grouping", applyEdgeGroupingFromModel);
  typedModel.on("change:_pending_ops", applyPendingOps);
  typedModel.on("change:height", () => {
    applyHeight();
    ogma.view.forceResize();
  });
  typedModel.on(
    "change:event_subscriptions",
    () => eventBridge.sync(typedModel.get("event_subscriptions") ?? [])
  );
  eventBridge.sync(typedModel.get("event_subscriptions") ?? []);
  typedModel.on("msg:custom", (msg) => {
    if (!msg) return;
    if (msg.type === "run_layout") {
      const { name, options } = msg;
      void runLayout(ogma, name, options ?? {});
    } else if (msg.type === "highlight") {
      void highlight(ogma, msg);
    } else if (msg.type === "trigger_groups_updated") {
      void nodeGroupingQueue.then(() => triggerGroupsUpdated(ogma));
    }
  });
  return () => {
    resizeObserver.disconnect();
    eventBridge.destroy();
    ogma.destroy();
  };
};
var src_default = { render };
export {
  src_default as default
};
