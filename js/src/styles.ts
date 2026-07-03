import type { Ogma, StyleRule } from "@linkurious/ogma";
import type { RuleDescriptor, StyleRuleSpec } from "./types";

/**
 * Strip a single leading `data.` segment from a property path.
 *
 * The Python API (and the example notebooks) reference data fields with a
 * `data.` prefix, e.g. `field="data.role"` or `"{{data.name}}"`. Ogma, however,
 * resolves rule fields and template placeholders *within* the data object
 * (`node.getData("role")`), so the prefix must be removed before handing the
 * path to Ogma. Only one leading segment is stripped, so genuinely nested
 * `data.<x>` paths keep working.
 */
function normalizeField(field: string): string {
    return field.startsWith("data.") ? field.slice("data.".length) : field;
}

/** Strip the leading `data.` from each `{{ ... }}` placeholder in a template. */
function normalizeTemplate(template: string): string {
    return template.replace(/\{\{\s*data\./g, "{{");
}

/** Return the rule descriptor if this plain object describes one, else null. */
function asRuleDescriptor(value: Record<string, unknown>): RuleDescriptor | null {
    switch (value.type) {
        case "map":
        case "slices":
            return typeof value.field === "string"
                ? (value as unknown as RuleDescriptor)
                : null;
        case "template":
            return typeof value.template === "string"
                ? (value as unknown as RuleDescriptor)
                : null;
        default:
            return null;
    }
}

/** Reconstruct an ogma.rules.* function from a serialized descriptor. */
function buildRule(
    ogma: Ogma,
    descriptor: RuleDescriptor,
): (element: unknown) => unknown {
    switch (descriptor.type) {
        case "map": {
            const options: Record<string, unknown> = {
                field: normalizeField(descriptor.field),
                values: descriptor.values,
            };
            if (descriptor.fallback !== undefined) {
                options.fallback = descriptor.fallback;
            }
            return ogma.rules.map(options as never) as never;
        }
        case "slices": {
            const options: Record<string, unknown> = {
                field: normalizeField(descriptor.field),
                values: descriptor.values,
            };
            if (descriptor.stops !== undefined) options.stops = descriptor.stops;
            if (descriptor.fallback !== undefined) options.fallback = descriptor.fallback;
            if (descriptor.reverse !== undefined) options.reverse = descriptor.reverse;
            return ogma.rules.slices(options as never) as never;
        }
        case "template":
            return ogma.rules.template(normalizeTemplate(descriptor.template)) as never;
    }
}

/**
 * Recursively convert an attribute value. Rule descriptors become live
 * ogma.rules functions; arrays and plain objects are walked so descriptors
 * nested under keys such as `text.content` are also converted; everything
 * else is passed through unchanged.
 */
function convertValue(ogma: Ogma, value: unknown): unknown {
    if (Array.isArray(value)) {
        return value.map((item) => convertValue(ogma, item));
    }
    if (value !== null && typeof value === "object") {
        const record = value as Record<string, unknown>;
        const descriptor = asRuleDescriptor(record);
        if (descriptor) {
            return buildRule(ogma, descriptor);
        }
        const out: Record<string, unknown> = {};
        for (const key of Object.keys(record)) {
            out[key] = convertValue(ogma, record[key]);
        }
        return out;
    }
    return value;
}

function convertAttributes(
    ogma: Ogma,
    attributes: Record<string, unknown>,
): Record<string, unknown> {
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(attributes)) {
        out[key] = convertValue(ogma, attributes[key]);
    }
    return out;
}

/**
 * Apply the full list of style rules synced from Python.
 *
 * Python accumulates rules and re-syncs the entire list on every change, so we
 * destroy the rules added on the previous call and rebuild from scratch to keep
 * Ogma in sync without duplicating rules.
 *
 * @returns the StyleRule handles created on this call.
 */
export function applyStyleRules(
    ogma: Ogma,
    styleRules: StyleRuleSpec[] | undefined,
    previous: StyleRule[],
): StyleRule[] {
    for (const rule of previous) {
        // destroy() is async; we don't need to await it before rebuilding.
        void rule.destroy();
    }

    const applied: StyleRule[] = [];
    for (const spec of styleRules ?? []) {
        const definition: Record<string, unknown> = {};
        if (spec.nodeAttributes) {
            definition.nodeAttributes = convertAttributes(ogma, spec.nodeAttributes);
        }
        if (spec.edgeAttributes) {
            definition.edgeAttributes = convertAttributes(ogma, spec.edgeAttributes);
        }
        applied.push(ogma.styles.addRule(definition as never));
    }
    return applied;
}
