import type { Model, RenderContext, GraphData } from './types';

// Ogma instance type (any since @linkurious/ogma may not be installed)
type OgmaInstance = any;

// Try to load Ogma - will fail gracefully if not configured
let Ogma: any = null;

try {
    // Dynamic import marked as external in build - resolved at runtime
    // @ts-ignore - Ogma may not be installed
    Ogma = (await import('@linkurious/ogma')).default;
} catch {
    // Ogma not available - will show placeholder
}

function renderPlaceholder(el: HTMLElement): void {
    el.innerHTML = `
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            border: 2px dashed #9ca3af;
            border-radius: 8px;
            font-family: system-ui, -apple-system, sans-serif;
            color: #374151;
            padding: 2rem;
            box-sizing: border-box;
        ">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="1.5">
                <circle cx="12" cy="12" r="3"/>
                <circle cx="4" cy="8" r="2"/>
                <circle cx="20" cy="8" r="2"/>
                <circle cx="4" cy="16" r="2"/>
                <circle cx="20" cy="16" r="2"/>
                <line x1="6" y1="8" x2="9" y2="10"/>
                <line x1="18" y1="8" x2="15" y2="10"/>
                <line x1="6" y1="16" x2="9" y2="14"/>
                <line x1="18" y1="16" x2="15" y2="14"/>
            </svg>
            <h3 style="margin: 1rem 0 0.5rem; font-size: 1.25rem;">Ogma Not Loaded</h3>
            <p style="margin: 0; text-align: center; max-width: 400px; line-height: 1.5;">
                Configure npm registry for <code style="background: #e5e7eb; padding: 0.125rem 0.375rem; border-radius: 4px;">@linkurious/ogma</code>
                to enable graph visualization.
            </p>
            <p style="margin: 1rem 0 0; font-size: 0.875rem; color: #6b7280;">
                See README.md for setup instructions.
            </p>
        </div>
    `;
}

function render({ model, el }: RenderContext) {
    // Set container size for visualization
    el.style.width = '100%';
    el.style.height = '400px';
    el.style.minHeight = '400px';

    // Show placeholder if Ogma is not available
    if (!Ogma) {
        renderPlaceholder(el);
        return () => {}; // No cleanup needed for placeholder
    }

    // Initialize Ogma instance
    const ogma: OgmaInstance = new Ogma({
        container: el,
    });

    // Load initial graph data if present
    const loadGraph = () => {
        const data: GraphData = model.get('graph_data');
        if (data.nodes.length > 0) {
            ogma.setGraph({
                nodes: data.nodes.map((n: { id: string; data?: Record<string, any> }) => ({ id: n.id, data: n.data })),
                edges: data.edges.map((e: { source: string; target: string; data?: Record<string, any> }) => ({
                    source: e.source,
                    target: e.target,
                    data: e.data
                })),
            });
            // Center view on graph
            ogma.view.locateGraph();
        }
    };

    // Load initial data
    loadGraph();

    // React to graph_data changes from Python
    model.on('change:graph_data', loadGraph);

    // CRITICAL: Return cleanup function to prevent WebGL context leaks
    // Browsers limit WebGL contexts to 8-16; without cleanup, older
    // visualizations go blank when limit is reached
    return () => {
        ogma.destroy();
    };
}

export default { render };
