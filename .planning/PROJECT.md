# Ogma Jupyter

## What This Is

A Python library that brings Ogma's WebGL graph visualization capabilities to Jupyter notebooks and Databricks. Data scientists can create, interact with, and analyze graph visualizations entirely in Python — no JavaScript required.

## Core Value

Full Ogma functionality accessible through a Pythonic API with bidirectional data flow between Python and the visualization.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Clean pip installation experience
- [ ] Pythonic API that mirrors Ogma's JavaScript API
- [ ] Render interactive Ogma visualizations in notebook cells
- [ ] Bidirectional data flow — selections/interactions accessible in Python
- [ ] Custom UI controls (sliders, buttons) that interact with the graph
- [ ] Works in both Jupyter notebooks and Databricks
- [ ] Feature parity with JavaScript Ogma API

### Out of Scope

- Native mobile support — web notebooks only
- Spark/PySpark distributed processing — standard Python data structures
- Real-time collaboration features — single-user notebook experience

## Context

**Current state:** A hacky proof-of-concept exists showing JSON data can be passed to a Jupyter cell to render Ogma visualizations. A customer has also built a full web app inside a Databricks cell. Both approaches require JavaScript code and don't support getting data back to Python.

**Problems to solve:**
1. Too much boilerplate code to render a graph
2. No clean installation path
3. One-way data flow — visualization is just an illustration
4. Users must write JavaScript to access Ogma features

**Ogma:** Commercial WebGL graph visualization library. Developers currently embed it in web applications using JavaScript/TypeScript. This library will expose Ogma to the Python data science ecosystem.

**Target users:**
- Existing Ogma customers who want notebook-based workflows
- Data scientists new to Ogma who work primarily in Python

## Constraints

- **Licensing**: Ogma is commercial — users need an Ogma license
- **Platform**: Must work in standard Jupyter (JupyterLab, classic) and Databricks notebooks
- **API design**: Should feel familiar to users who know Ogma's JavaScript API

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pythonic wrapper over JS API | Users who know Ogma JS will find Python version familiar | — Pending |
| Bidirectional data flow | Enables analysis workflows, not just visualization | — Pending |
| pip-installable package | Standard Python distribution, easy adoption | — Pending |

---
*Last updated: 2026-02-10 after initialization*
