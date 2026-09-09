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
async function applyGrouping(ogma, key, previous) {
  await removeGrouping(previous);
  const path = toDataPath(key);
  try {
    const grouping = ogma.transformations.addNodeGrouping({
      groupIdFunction: (node) => {
        const value = node.getData(path);
        return value === void 0 || value === null ? void 0 : String(value);
      },
      nodeGenerator: (_nodes, groupId) => ({
        data: { label: groupId },
        attributes: { text: groupId }
      })
    });
    await grouping.whenApplied();
    void ogma.view.locateGraph();
    return grouping;
  } catch (error) {
    console.error(`[ogma-jupyter] Grouping by "${key}" failed:`, error);
    return null;
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
  let styleRuleHandles = [];
  let nodeGrouping = null;
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
    await runInitialLayout();
  })();
  typedModel.on("change:graph_data", () => void loadGraph());
  typedModel.on("change:style_rules", applyStyles);
  typedModel.on("change:graph_layout", () => void runInitialLayout());
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
    } else if (msg.type === "group_nodes") {
      const { key } = msg;
      void applyGrouping(ogma, key, nodeGrouping).then((handle) => {
        nodeGrouping = handle;
      });
    } else if (msg.type === "ungroup_nodes") {
      void removeGrouping(nodeGrouping);
      nodeGrouping = null;
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
