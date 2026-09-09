// Converts Ogma event payloads (which may contain Node/Edge instances,
// NodeList/EdgeList collections, and native DOM events) into plain
// JSON-serializable data, so arbitrary Ogma events can be forwarded to
// Python via model.send().

interface OgmaElementLike {
    getId: () => unknown;
    getData: (path?: string) => unknown;
    isNode?: boolean;
    isEdge?: boolean;
}

interface OgmaCollectionLike {
    toArray: () => unknown[];
    map: (fn: (item: unknown) => unknown) => unknown;
}

function isOgmaElement(value: unknown): value is OgmaElementLike {
    if (!value || typeof value !== "object") return false;
    const candidate = value as Partial<OgmaElementLike>;
    return (
        typeof candidate.getId === "function" &&
        typeof candidate.getData === "function" &&
        (candidate.isNode === true || candidate.isEdge === true)
    );
}

function isOgmaCollection(value: unknown): value is OgmaCollectionLike {
    if (!value || typeof value !== "object") return false;
    const candidate = value as Partial<OgmaCollectionLike>;
    return typeof candidate.toArray === "function" && typeof candidate.map === "function";
}

function serializeElement(element: OgmaElementLike): Record<string, unknown> {
    return {
        id: element.getId(),
        isNode: element.isNode === true,
        isEdge: element.isEdge === true,
        data: element.getData(),
    };
}

// Recursively converts an Ogma event payload value into plain JSON data:
// - Node/Edge instances become `{ id, isNode, isEdge, data }`.
// - NodeList/EdgeList (and mixed element lists) become arrays of the above.
// - Native DOM `Event` objects (e.g. `domEvent`) are dropped — not
//   serializable and rarely needed from Python.
// - Everything else (numbers, strings, booleans, plain objects, arrays) is
//   copied as-is.
function serializeValue(value: unknown): unknown {
    if (value === null || value === undefined) return null;
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
        return value.toArray().map((item) => serializeElement(item as OgmaElementLike));
    }
    if (valueType === "object") {
        if (typeof Event !== "undefined" && value instanceof Event) return undefined;
        const out: Record<string, unknown> = {};
        for (const key of Object.keys(value as Record<string, unknown>)) {
            if (key === "domEvent") continue;
            const serialized = serializeValue((value as Record<string, unknown>)[key]);
            if (serialized !== undefined) out[key] = serialized;
        }
        return out;
    }
    return undefined;
}

/** Serialize a full Ogma event payload into a plain JSON-serializable object. */
export function serializeEventPayload(payload: unknown): Record<string, unknown> {
    const serialized = serializeValue(payload);
    if (serialized && typeof serialized === "object" && !Array.isArray(serialized)) {
        return serialized as Record<string, unknown>;
    }
    return { value: serialized };
}
