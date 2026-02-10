# Stack Research

**Domain:** Jupyter Widget wrapping JavaScript visualization library (WebGL graph viz)
**Researched:** 2026-02-10
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| anywidget | ^0.9.21 | Widget framework | Modern approach eliminating cookiecutter complexity. Simpler than traditional ipywidgets, cross-platform (Jupyter, JupyterLab, Colab, VSCode, marimo, Databricks). Used by mapwidget, ipyniivue, and growing ecosystem. No need for npm/webpack during development. |
| ipywidgets | ^8.1.8 | Underlying widget protocol | anywidget extends ipywidgets, ensuring compatibility with existing Jupyter ecosystem. Required dependency. |
| traitlets | ^5.14.3 | Bidirectional state sync | Foundation for Python-JS state management. sync=True traitlets automatically synchronize between Python and JavaScript. Preferred over custom messages per anywidget best practices. |
| Python | >=3.10 | Runtime | Matches hatchling requirements, Databricks Runtime 13.0+ compatibility, modern typing features. Drop 3.8/3.9 for cleaner typing syntax. |

### Build System

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| hatchling | ^1.28.0 | Python build backend | Modern, standards-compliant (PEP 517/518). Single pyproject.toml configuration. Recommended by Python Packaging Authority for 2025+. |
| hatch-jupyter-builder | ^0.9.1 | Jupyter-specific build hooks | Handles JavaScript compilation during Python package build. Triggers npm/esbuild during `pip install`. |
| esbuild | ^0.24.x | JavaScript bundler | Extremely fast (Golang-based), zero JS dependencies. Recommended by anywidget docs. Handles TypeScript, bundles Ogma library with widget code. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @anywidget/types | ^0.2.0 | TypeScript types | Always - provides type safety for model.get/set in JS code |
| @anywidget/vite | latest | Vite plugin | Only if using Vite instead of esbuild (for React/Svelte frameworks) |
| pytest-ipywidgets | ^1.57.2 | Widget testing | Integration tests with browser automation |
| playwright | ^1.x | Browser automation | E2E and visual regression testing |
| ruff | latest | Linting/formatting | Python code quality (replaces flake8, black, isort) |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Node.js LTS (20.x/22.x) | JavaScript tooling | Required for esbuild, npm dependencies |
| hatch | Python project management | Optional but recommended - manages environments, builds |
| pre-commit | Git hooks | Code quality enforcement before commits |
| mkdocs-material | Documentation | Modern Python documentation (optional) |

## Installation

```bash
# Core Python dependencies (pyproject.toml)
[project]
name = "ogma-jupyter"
requires-python = ">=3.10"
dependencies = [
    "anywidget>=0.9.21",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-ipywidgets>=1.57",
    "playwright>=1.40",
    "ruff>=0.4",
]

[build-system]
requires = ["hatchling", "hatch-jupyter-builder>=0.9"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.jupyter-builder]
dependencies = ["hatch-jupyter-builder"]
build-function = "hatch_jupyter_builder.npm_builder"
ensured-targets = ["ogma_jupyter/static/widget.js"]

[tool.hatch.build.hooks.jupyter-builder.build-kwargs]
npm = "npm"
build_cmd = "build"
```

```bash
# JavaScript dependencies (package.json)
{
  "devDependencies": {
    "@anywidget/types": "^0.2.0",
    "esbuild": "^0.24.0",
    "typescript": "^5.4"
  },
  "scripts": {
    "build": "esbuild --bundle --format=esm --outdir=ogma_jupyter/static src/widget.ts",
    "dev": "esbuild --bundle --format=esm --outdir=ogma_jupyter/static src/widget.ts --watch"
  }
}
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| anywidget | ipywidgets cookiecutter | Never for new projects. Legacy approach with complex webpack/babel setup. Only if you need features not yet in anywidget (unlikely). |
| anywidget | Panel/HoloViz | If building dashboard-first rather than widget-first. Panel wraps widgets but adds overhead. |
| esbuild | Vite | If using React/Svelte with HMR requirements. Vite has better framework integration but slower. |
| esbuild | Rollup | Never - slower, more configuration, no advantage for this use case. |
| hatchling | setuptools | Never for new projects. Legacy, more configuration, worse dependency resolution. |
| hatchling | Poetry | If team has strong Poetry preference. Poetry works but hatchling better integrated with Jupyter ecosystem. |
| traitlets | Pydantic + MimeBundleDescriptor | Experimental. Could use Pydantic models with anywidget experimental features, but traitlets more stable and documented. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| ipywidgets cookiecutter template | Complex webpack/babel setup, steep learning curve, maintenance burden. The cookiecutter approach "can be a steep learning curve for developers unfamiliar with the prescribed front-end tooling (yarn, Webpack, Babel, ESLint, Jest)" | anywidget |
| webpack | Slow, complex configuration, heavy. JupyterLab is migrating away from webpack (Issue #15035). | esbuild |
| setup.py / setuptools | Legacy packaging, harder to maintain, worse resolver | hatchling + pyproject.toml |
| Custom comm messages | State doesn't persist without active kernel, ordering complexity | traitlets with sync=True |
| jupyter-packaging | Deprecated in favor of hatch-jupyter-builder | hatch-jupyter-builder |
| RequireJS / AMD modules | Legacy Jupyter Notebook 6.x pattern. Modern anywidget uses ES modules. | ESM format |

## Stack Patterns by Variant

**If bundling a commercial JS library (Ogma):**
- Bundle Ogma into widget.js using esbuild
- License key handling via Python config, passed to JS as trait
- Keep Ogma version pinned in package.json for reproducibility

**If supporting Databricks:**
- Verify widget works in Databricks Runtime 13.0+
- Some ipywidgets do not work in Runtime 15.0 - test explicitly
- Use anywidget (built on ipywidgets) for best compatibility
- Avoid dependencies on specific Jupyter extensions

**If hot module reload (HMR) during development:**
- Set `ANYWIDGET_HMR=1` environment variable
- Use esbuild --watch mode
- anywidget watches for changes to bundled output

**If TypeScript for type safety:**
- Use @anywidget/types for model typing
- Configure tsconfig.json with moduleResolution: "bundler"
- esbuild handles TypeScript compilation automatically

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| anywidget@0.9.x | ipywidgets@8.x | anywidget extends ipywidgets, tight coupling |
| anywidget@0.9.x | traitlets@5.x | Required for state sync |
| hatchling@1.28 | Python 3.10-3.14 | Drop 3.8/3.9 for modern typing |
| hatch-jupyter-builder@0.9 | hatchling@1.x | Plugin compatibility |
| Databricks Runtime 13.0+ | ipywidgets@8.x | Official support, some 15.0 issues noted |
| JupyterLab 4.x | ipywidgets@8.x | Current stable |
| VSCode Notebooks | anywidget@0.9.x | Full support |
| Google Colab | anywidget@0.9.x | Full support |
| marimo | anywidget@0.9.x | Full support |

## Project Structure (Recommended)

Based on ipyniivue and mapwidget patterns:

```
ogma-jupyter/
├── pyproject.toml           # All Python config
├── package.json             # JS dependencies
├── tsconfig.json            # TypeScript config
├── src/
│   └── widget.ts            # TypeScript widget frontend
├── ogma_jupyter/
│   ├── __init__.py
│   ├── widget.py            # Python widget class
│   └── static/              # Built JS assets (generated)
│       └── widget.js
├── examples/
│   └── basic.ipynb          # Usage examples
├── tests/
│   ├── test_widget.py       # Unit tests
│   └── e2e/                 # Playwright tests
│       └── test_visual.py
└── docs/                    # Optional documentation
```

## Sources

- [anywidget PyPI](https://pypi.org/project/anywidget/) - Version 0.9.21, November 2025 (HIGH confidence)
- [anywidget bundling docs](https://anywidget.dev/en/bundling/) - esbuild recommendation (HIGH confidence)
- [anywidget "The Good Parts"](https://anywidget.dev/en/jupyter-widgets-the-good-parts/) - Best practices for state sync (HIGH confidence)
- [ipywidgets PyPI](https://pypi.org/project/ipywidgets/) - Version 8.1.8, November 2025 (HIGH confidence)
- [traitlets PyPI](https://pypi.org/project/traitlets/) - Version 5.14.3 (HIGH confidence)
- [hatchling PyPI](https://pypi.org/project/hatchling/) - Version 1.28.0, November 2025 (HIGH confidence)
- [hatch-jupyter-builder GitHub](https://github.com/jupyterlab/hatch-jupyter-builder) - Build patterns (HIGH confidence)
- [ipyniivue GitHub](https://github.com/niivue/ipyniivue) - WebGL + anywidget reference implementation (HIGH confidence)
- [mapwidget GitHub](https://github.com/opengeos/mapwidget) - Multi-library anywidget pattern (HIGH confidence)
- [Databricks ipywidgets docs](https://docs.databricks.com/aws/en/notebooks/ipywidgets) - Runtime compatibility (MEDIUM confidence - verify current runtime)
- [pytest-ipywidgets PyPI](https://pypi.org/project/pytest-ipywidgets/) - Version 1.57.2, February 2026 (HIGH confidence)
- [@anywidget/types npm](https://www.npmjs.com/package/@anywidget/types) - Version 0.2.0 (HIGH confidence)

---
*Stack research for: ogma-jupyter (Jupyter widget wrapping commercial WebGL graph visualization library)*
*Researched: 2026-02-10*
