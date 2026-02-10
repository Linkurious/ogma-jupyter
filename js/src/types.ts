// anywidget model interface
export interface Model {
    get(name: string): any;
    set(name: string, value: any): void;
    save_changes(): void;
    on(event: string, callback: () => void): void;
}

// Render context from anywidget
export interface RenderContext {
    model: Model;
    el: HTMLElement;
}

// Graph data structure matching Python traitlet
export interface GraphData {
    nodes: Array<{ id: string; data?: Record<string, any> }>;
    edges: Array<{ source: string; target: string; data?: Record<string, any> }>;
}
