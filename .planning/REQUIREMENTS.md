# Requirements: Ogma Jupyter

**Defined:** 2026-02-10
**Core Value:** Full Ogma functionality accessible through a Pythonic API with bidirectional data flow between Python and the visualization.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Installation & Platform

- [ ] **INST-01**: User can install package via pip
- [ ] **INST-02**: Package works in JupyterLab
- [ ] **INST-03**: Package works in classic Jupyter Notebook
- [ ] **INST-04**: Package works in VSCode notebooks
- [ ] **INST-05**: Package works in Google Colab
- [ ] **INST-06**: Package works in Databricks notebooks

### Graph Data

- [ ] **DATA-01**: User can create graph from Python dicts/lists
- [ ] **DATA-02**: User can load graph from NetworkX Graph object
- [ ] **DATA-03**: User can load nodes/edges from Pandas DataFrames
- [ ] **DATA-04**: User can update graph data dynamically after initial render
- [ ] **DATA-05**: Large graphs (10K+ nodes) transfer efficiently via binary buffers

### Visualization

- [ ] **VIZ-01**: User sees interactive WebGL graph rendered in notebook cell
- [ ] **VIZ-02**: User can pan and zoom the visualization
- [ ] **VIZ-03**: User can set node/edge colors, sizes, and shapes
- [ ] **VIZ-04**: User can apply data-driven styling (map data values to visual properties)
- [ ] **VIZ-05**: User can apply layout algorithms (force-directed, hierarchical, etc.)
- [ ] **VIZ-06**: User can export visualization as PNG or SVG

### Interactivity

- [ ] **INT-01**: User receives click events on nodes/edges in Python
- [ ] **INT-02**: User receives selection change events in Python
- [ ] **INT-03**: User receives hover events in Python
- [ ] **INT-04**: User can get currently selected nodes/edges in Python
- [ ] **INT-05**: User can set selection from Python (bidirectional)
- [ ] **INT-06**: User can access full Ogma event API from Python
- [ ] **INT-07**: User can create custom UI controls (sliders, buttons) that affect the graph

### Annotations

- [ ] **ANN-01**: User can add text labels to nodes and edges
- [ ] **ANN-02**: User can show tooltips on hover
- [ ] **ANN-03**: User can add overlay annotations (arrows, callouts, highlights)
- [ ] **ANN-04**: User can use annotation layers via @linkurious/ogma-annotations
- [ ] **ANN-05**: User can integrate D3 visualizations as annotation layers

### Grouping

- [ ] **GRP-01**: User can draw visual boundaries around node clusters
- [ ] **GRP-02**: User can collapse/expand groups interactively
- [ ] **GRP-03**: User can create nested hierarchical groups
- [ ] **GRP-04**: User can control grouping programmatically from Python

### Python API

- [ ] **API-01**: API uses Pythonic conventions (snake_case, method chaining)
- [ ] **API-02**: API mirrors Ogma JavaScript API structure for familiarity
- [ ] **API-03**: Full Ogma API accessible from Python (feature parity goal)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Integration

- **ADV-01**: Graph database connectors (Neo4j, Neptune)
- **ADV-02**: Streaming data updates for real-time graphs
- **ADV-03**: Multi-graph views (small multiples)

### Collaboration

- **COLLAB-01**: Share interactive graphs as standalone HTML files
- **COLLAB-02**: Embed in documentation/dashboards

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Native mobile apps | Web notebooks only, not mobile development |
| Spark/PySpark distributed processing | Focus on standard Python data structures first |
| Real-time multi-user collaboration | Single-user notebook experience for v1 |
| Graph database query interface | Users handle data loading; we visualize |
| Custom WebGL shaders | Use Ogma's built-in rendering capabilities |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INST-01 | — | Pending |
| INST-02 | — | Pending |
| INST-03 | — | Pending |
| INST-04 | — | Pending |
| INST-05 | — | Pending |
| INST-06 | — | Pending |
| DATA-01 | — | Pending |
| DATA-02 | — | Pending |
| DATA-03 | — | Pending |
| DATA-04 | — | Pending |
| DATA-05 | — | Pending |
| VIZ-01 | — | Pending |
| VIZ-02 | — | Pending |
| VIZ-03 | — | Pending |
| VIZ-04 | — | Pending |
| VIZ-05 | — | Pending |
| VIZ-06 | — | Pending |
| INT-01 | — | Pending |
| INT-02 | — | Pending |
| INT-03 | — | Pending |
| INT-04 | — | Pending |
| INT-05 | — | Pending |
| INT-06 | — | Pending |
| INT-07 | — | Pending |
| ANN-01 | — | Pending |
| ANN-02 | — | Pending |
| ANN-03 | — | Pending |
| ANN-04 | — | Pending |
| ANN-05 | — | Pending |
| GRP-01 | — | Pending |
| GRP-02 | — | Pending |
| GRP-03 | — | Pending |
| GRP-04 | — | Pending |
| API-01 | — | Pending |
| API-02 | — | Pending |
| API-03 | — | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 0
- Unmapped: 35 ⚠️

---
*Requirements defined: 2026-02-10*
*Last updated: 2026-02-10 after initial definition*
