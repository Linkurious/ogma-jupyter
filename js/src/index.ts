import { Ogma } from "@linkurious/ogma";
import type { RenderContext, GraphData } from "./types";

function render({ model, el }: RenderContext) {
  // Set container size for visualization
  el.style.width = "100%";
  el.style.height = "400px";
  el.style.minHeight = "400px";

  // Initialize Ogma instance
  const ogma = new Ogma({
    container: el,
  });

  // Load initial graph data if present
  const loadGraph = () => {
    const data: GraphData = model.get("graph_data");
    if (data.nodes.length > 0) {
      ogma.setGraph({
        nodes: data.nodes.map(
          (n: { id: string; data?: Record<string, any> }) => ({
            id: n.id,
            data: n.data,
          }),
        ),
        edges: data.edges.map(
          (e: {
            source: string;
            target: string;
            data?: Record<string, any>;
          }) => ({
            source: e.source,
            target: e.target,
            data: e.data,
          }),
        ),
      });
      // Center view on graph
      ogma.view.locateGraph();
    }
  };

  // Load initial data
  loadGraph();

  // React to graph_data changes from Python
  model.on("change:graph_data", loadGraph);

  // CRITICAL: Return cleanup function to prevent WebGL context leaks
  // Browsers limit WebGL contexts to 8-16; without cleanup, older
  // visualizations go blank when limit is reached
  return () => {
    ogma.destroy();
  };
}

export default { render };
