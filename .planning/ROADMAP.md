# Roadmap: Ogma Jupyter

## Overview

Transform Ogma's WebGL graph visualization from JavaScript-only to fully Pythonic. Starting with pip-installable foundation and cross-platform support, building through core data handling and visualization, adding bidirectional interactivity, and completing with advanced annotation and grouping features. Each phase delivers coherent capability that enables the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Platform** - Pip-installable package rendering Ogma in all target notebook environments
- [ ] **Phase 2: Core Data & Visualization** - Load, style, layout, and export graphs from Python data sources
- [ ] **Phase 3: Interactivity & Python API** - Bidirectional events and full API access between Python and visualization
- [ ] **Phase 4: Advanced Features** - Annotations, tooltips, grouping, and nested hierarchies

## Phase Details

### Phase 1: Foundation & Platform
**Goal**: Users can install package and render basic graphs in all target platforms
**Depends on**: Nothing (first phase)
**Requirements**: INST-01, INST-02, INST-03, INST-04, INST-05, INST-06, VIZ-01, VIZ-02, API-01, API-02
**Success Criteria** (what must be TRUE):
  1. User installs package with `pip install ogma-jupyter` and it works without npm
  2. User creates basic graph and sees interactive WebGL visualization in JupyterLab
  3. User can pan and zoom the visualization using mouse or trackpad
  4. Same notebook runs unchanged in VSCode, Google Colab, and Databricks
  5. API feels Pythonic with snake_case conventions and familiar patterns
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Package scaffold and Python core (pyproject.toml, widget.py, config.py, errors.py)
- [ ] 01-02-PLAN.md — JavaScript widget and build pipeline (TypeScript widget, esbuild, hatch-jupyter-builder)
- [ ] 01-03-PLAN.md — Developer experience and platform verification (examples, README, cross-platform testing)

### Phase 2: Core Data & Visualization
**Goal**: Users can create and style graphs from Python data sources
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, VIZ-03, VIZ-04, VIZ-05, VIZ-06
**Success Criteria** (what must be TRUE):
  1. User creates graphs from Python dicts, NetworkX graphs, or Pandas DataFrames
  2. User updates graph data dynamically after initial render
  3. User applies data-driven styling that maps data values to colors, sizes, and shapes
  4. User applies layout algorithms and exports visualizations as PNG or SVG
  5. Large graphs with 10K+ nodes load and update efficiently
**Plans**: TBD

Plans:
- [ ] TBD

### Phase 3: Interactivity & Python API
**Goal**: Users can interact with graphs and access events in Python
**Depends on**: Phase 2
**Requirements**: INT-01, INT-02, INT-03, INT-04, INT-05, INT-06, INT-07, API-03
**Success Criteria** (what must be TRUE):
  1. User receives node and edge events (clicks, hover, selection) in Python callbacks
  2. User gets currently selected nodes and edges from Python
  3. User sets selection from Python and sees visualization update
  4. User creates custom UI controls (sliders, buttons) that interact with the graph
  5. User accesses full Ogma event API from Python
**Plans**: TBD

Plans:
- [ ] TBD

### Phase 4: Advanced Features
**Goal**: Users can create sophisticated visualizations with annotations and grouping
**Depends on**: Phase 2
**Requirements**: ANN-01, ANN-02, ANN-03, ANN-04, ANN-05, GRP-01, GRP-02, GRP-03, GRP-04
**Success Criteria** (what must be TRUE):
  1. User adds text labels and tooltips to nodes and edges
  2. User adds overlay annotations (arrows, callouts, highlights)
  3. User uses Ogma annotation layers for complex visualizations
  4. User draws visual boundaries around node clusters
  5. User collapses and expands groups programmatically with nested hierarchies
**Plans**: TBD

Plans:
- [ ] TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Platform | 0/3 | Planned | - |
| 2. Core Data & Visualization | 0/TBD | Not started | - |
| 3. Interactivity & Python API | 0/TBD | Not started | - |
| 4. Advanced Features | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-10*
*Last updated: 2026-02-10*
