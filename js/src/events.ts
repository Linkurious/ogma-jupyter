import type { Ogma } from "@linkurious/ogma";

import { serializeEventPayload } from "./serialize";
import type { OgmaModel } from "./types";

type OgmaEvents = {
    on: (name: string, cb: (payload: unknown) => void) => void;
    off: (name: string, cb: (payload: unknown) => void) => void;
};

/**
 * Bridges Python `widget.on(event_name, handler)` calls to Ogma's own
 * `ogma.events.on(...)` API. `sync()` is called whenever the synced
 * `event_subscriptions` list changes, and (un)subscribes JS-side listeners to
 * match it — one `ogma.events.on` registration per event name, regardless of
 * how many Python handlers are attached to it (Python-side fan-out is handled
 * in `OgmaWidget._dispatch_message`). Any event name accepted by
 * `ogma.events.on` works (click, doubleclick, mouseover, nodesDragEnd,
 * layoutEnd, nodesSelected, ...) — nothing is hardcoded here.
 */
export function createEventBridge(ogma: Ogma, model: OgmaModel) {
    const events = ogma.events as unknown as OgmaEvents;
    const listeners = new Map<string, (payload: unknown) => void>();

    function subscribe(eventName: string): void {
        if (listeners.has(eventName)) return;
        const handler = (payload: unknown): void => {
            model.send({
                type: "ogma_event",
                event: eventName,
                payload: serializeEventPayload(payload),
            });
        };
        events.on(eventName, handler);
        listeners.set(eventName, handler);
    }

    function unsubscribe(eventName: string): void {
        const handler = listeners.get(eventName);
        if (!handler) return;
        events.off(eventName, handler);
        listeners.delete(eventName);
    }

    function sync(eventNames: string[]): void {
        const wanted = new Set(eventNames ?? []);
        for (const eventName of Array.from(listeners.keys())) {
            if (!wanted.has(eventName)) unsubscribe(eventName);
        }
        for (const eventName of wanted) subscribe(eventName);
    }

    function destroy(): void {
        for (const eventName of Array.from(listeners.keys())) unsubscribe(eventName);
    }

    return { sync, destroy };
}
