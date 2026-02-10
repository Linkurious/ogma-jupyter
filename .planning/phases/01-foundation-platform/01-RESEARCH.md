# Phase 1: Foundation & Platform - Research

**Researched:** 2026-02-10
**Domain:** Jupyter widget packaging, anywidget framework, cross-platform notebook compatibility
**Confidence:** HIGH

## Summary

Phase 1 establishes the pip-installable package foundation that renders Ogma WebGL graph visualizations across all target notebook environments. The core challenge is creating a widget that works identically in JupyterLab, classic Notebook, VSCode, Google Colab, and Databricks while providing excellent developer experience from first install.

The anywidget framework (0.9.21+) is the definitive choice, eliminating the complexity of traditional ipywidgets cookiecutter templates. Combined with hatchling and hatch-jupyter-builder for Python packaging, and esbuild for JavaScript bundling, this stack provides modern, maintainable infrastructure. The Ogma commercial library bundles into the widget.js output, with license key handling via environment variable.

**Primary recommendation:** Use anywidget + hatchling + esbuild stack. Focus on getting a minimal "hello Ogma" widget working across all platforms before adding features. Invest heavily in error messages and first-run experience per user decisions.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Developer Experience:**
- Detailed error messages with fix suggestions - not just "Invalid format" but "Expected nodes as list of dicts, got DataFrame. Use from_dataframe() instead."
- Comprehensive docstrings with params, returns, and examples - shows in IDE autocomplete
- Bundled example notebooks included in the package - users can copy and run them
- Welcome message on first run: "Welcome to Ogma Jupyter! Run og.demo() to see an example." - helps new users get started

### Claude's Discretion

- Ogma license key integration approach (environment variable, constructor arg, or config file)
- Package naming and import structure
- Platform testing priority and minimum version requirements
- Internal architecture and module organization

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within phase scope.

</user_constraints>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anywidget | ^0.9.21 | Widget framework | Modern approach eliminating cookiecutter complexity. Cross-platform (Jupyter, JupyterLab, Colab, VSCode, Databricks). Used by mapwidget, ipyniivue, growing ecosystem. |
| ipywidgets | ^8.1.8 | Underlying widget protocol | anywidget extends ipywidgets, ensuring compatibility with existing Jupyter ecosystem. Required dependency. |
| traitlets | ^5.14.3 | Bidirectional state sync | Foundation for Python-JS state management. `sync=True` traitlets automatically synchronize between Python and JavaScript. |
| Python | >=3.10 | Runtime | Matches JupyterLab 4.x requirements, Databricks Runtime 13.0+ compatibility, modern typing features. |

### Build System

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hatchling | ^1.28.0 | Python build backend | Modern, PEP 517/518 compliant. Single pyproject.toml configuration. Recommended by Python Packaging Authority. |
| hatch-jupyter-builder | ^0.9.1 | Jupyter build hooks | Handles JavaScript compilation during Python package build. Triggers npm/esbuild during `pip install`. |
| esbuild | ^0.24.x | JavaScript bundler | Extremely fast (Golang-based). Recommended by anywidget docs. Handles TypeScript, bundles Ogma with widget code. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @anywidget/types | ^0.2.0 | TypeScript types | Always - provides type safety for model.get/set in JS code |
| pytest | ^8.0 | Python testing | Unit tests for widget creation, trait validation |
| ruff | ^0.4 | Linting/formatting | Python code quality (replaces flake8, black, isort) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| anywidget | ipywidgets cookiecutter | Never. Complex webpack/babel setup, steep learning curve. |
| esbuild | Vite | Only if using React/Svelte with HMR. Vite slower but better framework integration. |
| hatchling | Poetry | Only if team has strong Poetry preference. Hatchling better integrated with Jupyter. |

**Installation (pyproject.toml):**
```toml
[project]
name = "ogma-jupyter"
requires-python = ">=3.10"
dependencies = [
    "anywidget>=0.9.21",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.4",
]

[build-system]
requires = ["hatchling>=1.28", "hatch-jupyter-builder>=0.9"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.jupyter-builder]
dependencies = ["hatch-jupyter-builder"]
build-function = "hatch_jupyter_builder.npm_builder"
ensured-targets = ["src/ogma_jupyter/static/widget.js"]

[tool.hatch.build.hooks.jupyter-builder.build-kwargs]
npm = "npm"
build_cmd = "build"
```

**JavaScript (package.json):**
```json
{
  "devDependencies": {
    "@anywidget/types": "^0.2.0",
    "esbuild": "^0.24.0",
    "typescript": "^5.4"
  },
  "scripts": {
    "build": "esbuild --bundle --format=esm --outdir=src/ogma_jupyter/static js/src/index.ts",
    "dev": "esbuild --bundle --format=esm --outdir=src/ogma_jupyter/static js/src/index.ts --watch"
  }
}
```

## Architecture Patterns

### Recommended Project Structure

Based on ipyniivue pattern with src layout:

```
ogma-jupyter/
├── src/
│   └── ogma_jupyter/           # Python package (src layout)
│       ├── __init__.py         # Public API, welcome message logic
│       ├── widget.py           # OgmaWidget class (anywidget.AnyWidget)
│       ├── config.py           # License key, configuration management
│       ├── errors.py           # Custom exceptions with helpful messages
│       ├── _version.py         # Package version (single source)
│       └── static/             # Compiled JS assets (git-ignored, built)
│           └── widget.js
├── js/
│   └── src/
│       ├── index.ts            # Entry point, exports render()
│       └── types.ts            # TypeScript definitions
├── examples/                   # Bundled notebooks (shipped with package)
│   ├── 01-quickstart.ipynb
│   └── 02-basic-graph.ipynb
├── tests/
│   ├── test_widget.py
│   └── test_config.py
├── pyproject.toml
├── package.json
├── tsconfig.json
└── README.md
```

**Structure Rationale:**
- **src/ layout**: Prevents accidental imports of uninstalled package; recommended by Python packaging authorities
- **js/ separate from Python**: Clean separation of concerns; JS has its own build system
- **static/ inside package**: Bundled assets deployed with pip install; anywidget references via `_esm` path
- **examples/ bundled**: Users can access via `ogma_jupyter.get_example_path()` per locked decision

### Pattern 1: anywidget Widget Definition

**What:** Define widget class extending `anywidget.AnyWidget` with ESM path and synchronized traits.

**When to use:** Always for the main widget.

**Example:**
```python
# Source: anywidget.dev/en/getting-started/
import pathlib
import anywidget
import traitlets

class OgmaWidget(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "static" / "widget.js"

    # Graph data as synchronized trait
    graph_data = traitlets.Dict({
        'nodes': [],
        'edges': []
    }).tag(sync=True)

    # License key passed to JS
    _license_key = traitlets.Unicode('').tag(sync=True)
```

### Pattern 2: ESM render() Function

**What:** JavaScript module exporting render function that receives model and element.

**When to use:** Always for widget frontend.

**Example:**
```typescript
// Source: anywidget.dev/en/getting-started/
import Ogma from '@linkurious/ogma';  // Bundled via esbuild

interface Model {
    get(name: string): any;
    set(name: string, value: any): void;
    save_changes(): void;
    on(event: string, callback: () => void): void;
}

function render({ model, el }: { model: Model; el: HTMLElement }) {
    const licenseKey = model.get('_license_key');
    const ogma = new Ogma({
        container: el,
        // Ogma options with license key if required
    });

    // React to Python pushing graph data
    model.on('change:graph_data', () => {
        const data = model.get('graph_data');
        ogma.setGraph(data);
    });

    // Return cleanup function for WebGL context
    return () => {
        ogma.destroy();
    };
}

export default { render };
```

### Pattern 3: Configuration Management

**What:** Load license key from environment variable with constructor fallback.

**When to use:** For Ogma license key integration.

**Recommendation (Claude's Discretion):** Environment variable primary, constructor arg fallback.

```python
# Source: 12-factor principles, python-dotenv patterns
import os
from typing import Optional

def get_license_key(provided_key: Optional[str] = None) -> str:
    """
    Get Ogma license key from environment or constructor argument.

    Priority:
    1. Explicitly provided key (constructor arg)
    2. OGMA_LICENSE_KEY environment variable
    3. Raise informative error

    Parameters
    ----------
    provided_key : str, optional
        License key provided directly to constructor

    Returns
    -------
    str
        The Ogma license key

    Raises
    ------
    OgmaLicenseError
        If no license key found, with instructions to set one
    """
    if provided_key:
        return provided_key

    env_key = os.environ.get('OGMA_LICENSE_KEY')
    if env_key:
        return env_key

    raise OgmaLicenseError(
        "No Ogma license key found.\n\n"
        "Set the OGMA_LICENSE_KEY environment variable:\n"
        "    export OGMA_LICENSE_KEY='your-key-here'\n\n"
        "Or pass it directly:\n"
        "    widget = OgmaWidget(license_key='your-key-here')\n\n"
        "Get your key from: https://get.linkurio.us"
    )
```

### Pattern 4: First-Run Welcome Message

**What:** Show welcome message on first import with demo instruction.

**When to use:** Per locked decision - helps new users get started.

```python
# Source: User decision from CONTEXT.md
import os
import pathlib

_WELCOME_SHOWN_FILE = pathlib.Path.home() / '.ogma_jupyter_welcome'

def _maybe_show_welcome():
    """Show welcome message on first run."""
    if _WELCOME_SHOWN_FILE.exists():
        return

    print("Welcome to Ogma Jupyter! Run og.demo() to see an example.")

    # Mark as shown
    try:
        _WELCOME_SHOWN_FILE.touch()
    except OSError:
        pass  # Best effort - don't fail if we can't write

# Called in __init__.py at import time
_maybe_show_welcome()
```

### Pattern 5: Helpful Error Messages

**What:** Custom exceptions with actionable fix suggestions.

**When to use:** Per locked decision - all user-facing errors.

```python
# Source: User decision from CONTEXT.md
class OgmaError(Exception):
    """Base exception for ogma-jupyter errors."""
    pass

class OgmaLicenseError(OgmaError):
    """Raised when license key is missing or invalid."""
    pass

class OgmaDataError(OgmaError):
    """Raised when data format is invalid."""
    pass

def validate_graph_data(data):
    """Validate graph data with helpful error messages."""
    if not isinstance(data, dict):
        raise OgmaDataError(
            f"Expected graph data as dict, got {type(data).__name__}.\n\n"
            "Provide data as:\n"
            "    {'nodes': [...], 'edges': [...]}\n\n"
            "Or use from_networkx() for NetworkX graphs."
        )

    if 'nodes' not in data:
        raise OgmaDataError(
            "Graph data missing 'nodes' key.\n\n"
            "Expected format:\n"
            "    {'nodes': [{'id': 'n1'}, ...], 'edges': [...]}"
        )
```

### Anti-Patterns to Avoid

- **Hardcoding license key in source:** Security risk, prevents sharing notebooks. Use environment variable.
- **Skipping cleanup function:** WebGL contexts leak, causing blank canvases after 8+ widgets.
- **Bundling Ogma without proper licensing:** Ensure Ogma is obtained through proper npm registry with API key.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Widget framework | Custom comm layer | anywidget | Handles all Jupyter environments automatically |
| Python packaging | setup.py scripts | hatchling + pyproject.toml | Modern PEP-compliant, single config file |
| JS bundling | Manual script concat | esbuild | Fast, handles TypeScript, tree-shaking |
| Cross-platform compat | Platform-specific code | anywidget | Built-in support for all targets |
| Widget state sync | Custom JSON messaging | traitlets with sync=True | Automatic, handles serialization |

**Key insight:** anywidget exists specifically to solve the "Jupyter widget for JS library" problem. It has been battle-tested across Colab, Databricks, VSCode, and all Jupyter variants.

## Common Pitfalls

### Pitfall 1: Version Mismatch Between Python and JavaScript

**What goes wrong:** "Error displaying widget: model not found" appears despite correct code.

**Why it happens:** The `_model_module_version` in Python must exactly match JavaScript. JupyterLab and kernel may be in different environments.

**How to avoid:**
- Use single source of truth for version in `_version.py`
- anywidget handles this automatically - just use `pathlib.Path` for _esm
- Test installation in fresh environment before release

**Warning signs:** Widget displays blank area, "Module X not found" in console.

**Phase 1 action:** Implement version management from day 1.

### Pitfall 2: WebGL Context Limits

**What goes wrong:** After 8-16 widgets in notebook, older visualizations go blank.

**Why it happens:** Browsers limit WebGL contexts to 8-16 active. Oldest contexts are forcibly destroyed.

**How to avoid:**
- Return cleanup function from render() that calls `ogma.destroy()`
- anywidget calls cleanup automatically when widget is removed
- Document to users that many simultaneous visualizations have limits

**Warning signs:** Earlier visualizations blank while later ones work.

**Phase 1 action:** Implement cleanup function in initial widget.

### Pitfall 3: Messages Lost Before Widget Display

**What goes wrong:** Initial data doesn't appear but subsequent updates work.

**Why it happens:** Comm channel established asynchronously. Messages sent before view renders are lost.

**How to avoid:**
- Use traitlets for initial state (buffered correctly)
- Never send custom messages in `__init__`
- Set initial graph_data as trait default or in constructor

**Warning signs:** Works individually but fails on "Run All".

**Phase 1 action:** Initialize all state via traits, not custom messages.

### Pitfall 4: Databricks Runtime Compatibility

**What goes wrong:** Widget works in JupyterLab but fails in Databricks.

**Why it happens:** Databricks Runtime 15.0 had ipywidgets issues. Runtime 15.2 downgraded to ipywidgets 7.7.2.

**How to avoid:**
- Use anywidget which has simpler compatibility story
- Test on actual Databricks clusters, not just local Jupyter
- Document supported Databricks Runtime versions

**Warning signs:** "Stale widget" errors, widget doesn't render.

**Phase 1 action:** Test on Databricks Runtime 13.0+ during development.

## Code Examples

### Complete Minimal Widget

```python
# src/ogma_jupyter/widget.py
# Source: anywidget.dev/en/getting-started/ + ipyniivue patterns
import pathlib
import anywidget
import traitlets
from .config import get_license_key
from .errors import OgmaDataError

class OgmaWidget(anywidget.AnyWidget):
    """
    Interactive Ogma graph visualization widget for Jupyter notebooks.

    Parameters
    ----------
    graph_data : dict, optional
        Initial graph with 'nodes' and 'edges' keys.
        Nodes: [{'id': 'n1', ...}, ...]
        Edges: [{'source': 'n1', 'target': 'n2', ...}, ...]
    license_key : str, optional
        Ogma license key. Falls back to OGMA_LICENSE_KEY env var.

    Examples
    --------
    >>> widget = OgmaWidget()
    >>> widget.graph_data = {
    ...     'nodes': [{'id': 'a'}, {'id': 'b'}],
    ...     'edges': [{'source': 'a', 'target': 'b'}]
    ... }
    >>> widget
    """

    _esm = pathlib.Path(__file__).parent / "static" / "widget.js"

    # Synchronized state
    graph_data = traitlets.Dict({'nodes': [], 'edges': []}).tag(sync=True)
    _license_key = traitlets.Unicode('').tag(sync=True)

    def __init__(self, graph_data=None, license_key=None, **kwargs):
        super().__init__(**kwargs)
        self._license_key = get_license_key(license_key)
        if graph_data:
            self.graph_data = graph_data
```

### Complete JavaScript Widget

```typescript
// js/src/index.ts
// Source: anywidget.dev + Ogma API patterns
import Ogma from '@linkurious/ogma';

interface Model {
    get(name: string): any;
    set(name: string, value: any): void;
    save_changes(): void;
    on(event: string, callback: () => void): void;
}

interface Context {
    model: Model;
    el: HTMLElement;
}

function render({ model, el }: Context) {
    // Set container size
    el.style.width = '100%';
    el.style.height = '400px';

    // Initialize Ogma
    const ogma = new Ogma({
        container: el,
    });

    // Load initial graph if present
    const initialData = model.get('graph_data');
    if (initialData.nodes.length > 0) {
        ogma.setGraph(initialData);
        ogma.view.locateGraph();
    }

    // React to graph data changes from Python
    model.on('change:graph_data', () => {
        const data = model.get('graph_data');
        ogma.setGraph(data);
        ogma.view.locateGraph();
    });

    // Cleanup function - CRITICAL for WebGL
    return () => {
        ogma.destroy();
    };
}

export default { render };
```

### Package Entry Point

```python
# src/ogma_jupyter/__init__.py
# Source: User decisions from CONTEXT.md
"""
Ogma Jupyter - Interactive graph visualization for Jupyter notebooks.

Examples
--------
>>> import ogma_jupyter as og
>>> widget = og.OgmaWidget()
>>> widget.graph_data = {'nodes': [{'id': 'a'}], 'edges': []}
>>> widget
"""

from ._version import __version__
from .widget import OgmaWidget
from .errors import OgmaError, OgmaLicenseError, OgmaDataError

# Welcome message on first run
from .config import _maybe_show_welcome
_maybe_show_welcome()

def demo():
    """
    Create a demo widget with sample graph.

    Returns
    -------
    OgmaWidget
        Widget with example graph data ready to display.

    Examples
    --------
    >>> import ogma_jupyter as og
    >>> og.demo()
    """
    return OgmaWidget(graph_data={
        'nodes': [
            {'id': 'a', 'data': {'label': 'Node A'}},
            {'id': 'b', 'data': {'label': 'Node B'}},
            {'id': 'c', 'data': {'label': 'Node C'}},
        ],
        'edges': [
            {'source': 'a', 'target': 'b'},
            {'source': 'b', 'target': 'c'},
            {'source': 'c', 'target': 'a'},
        ]
    })

__all__ = [
    '__version__',
    'OgmaWidget',
    'OgmaError',
    'OgmaLicenseError',
    'OgmaDataError',
    'demo',
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ipywidgets cookiecutter | anywidget | 2023 | Dramatically simpler widget development |
| webpack | esbuild | 2023-2024 | 10-100x faster builds, simpler config |
| setup.py | pyproject.toml + hatchling | 2022-2023 | Single config file, modern standards |
| RequireJS/AMD | ES modules | 2022+ | anywidget uses ESM exclusively |
| jupyter-packaging | hatch-jupyter-builder | 2023 | Better integration with modern Python |

**Deprecated/outdated:**
- **ipywidgets cookiecutter template**: Complex webpack/babel setup, steep learning curve
- **setup.py**: Legacy packaging, use pyproject.toml instead
- **jupyter-packaging**: Replaced by hatch-jupyter-builder

## Platform-Specific Notes

### Recommendation: Testing Priority Order (Claude's Discretion)

1. **JupyterLab 4.x** (PRIMARY): Most feature-complete, best debugging
2. **Google Colab**: Large user base, some limitations on custom widgets
3. **Databricks Runtime 13.0+**: Enterprise target, test on actual clusters
4. **VSCode Notebooks**: Growing user base, full anywidget support
5. **Classic Notebook 7.x**: Less common for new projects, anywidget handles

### Minimum Version Requirements (Claude's Discretion)

| Platform | Minimum Version | Notes |
|----------|-----------------|-------|
| Python | 3.10 | Modern typing, JupyterLab 4 requirement |
| JupyterLab | 4.0 | Current stable, ipywidgets 8.x |
| ipywidgets | 8.0 | anywidget requirement |
| Databricks | Runtime 13.0 | GA ipywidgets support |
| VSCode Jupyter | 2024.1+ | Current extension versions |
| Google Colab | Current | Always current, limited control |

## Package Naming Recommendation (Claude's Discretion)

**Package name:** `ogma-jupyter`
**Import name:** `ogma_jupyter`
**Short alias convention:** `import ogma_jupyter as og`

**Rationale:**
- Follows PEP 423 naming conventions (lowercase, hyphen for package, underscore for import)
- Clear association with Jupyter ecosystem
- Short alias mirrors pandas (`pd`), numpy (`np`) convention

## Open Questions

1. **Ogma NPM Registry Access**
   - What we know: Ogma uses private npm registry with API key in package.json URL
   - What's unclear: How to handle this in open-source pyproject.toml
   - Recommendation: Document that users need Ogma license; provide setup script that configures npm registry

2. **Bundling Ogma Version**
   - What we know: Ogma should be bundled into widget.js via esbuild
   - What's unclear: Optimal approach for version updates
   - Recommendation: Pin Ogma version in package.json, document upgrade process

3. **Colab ipywidgets Version**
   - What we know: Colab has historically had ipywidgets version constraints
   - What's unclear: Current Colab ipywidgets version in 2026
   - Recommendation: Test during development, document any limitations

## Sources

### Primary (HIGH confidence)

- [anywidget Getting Started](https://anywidget.dev/en/getting-started/) - Widget patterns, render function
- [anywidget Bundling](https://anywidget.dev/en/bundling/) - esbuild configuration
- [ipyniivue GitHub](https://github.com/niivue/ipyniivue) - WebGL + anywidget reference implementation
- [hatch-jupyter-builder GitHub](https://github.com/jupyterlab/hatch-jupyter-builder) - Build hook configuration
- [JupyterLab PyPI](https://pypi.org/project/jupyterlab/) - Python version requirements
- [Ogma Documentation](https://doc.linkurious.com/ogma/latest/) - API patterns

### Secondary (MEDIUM confidence)

- [PEP 8](https://peps.python.org/pep-0008/) - Python naming conventions
- [PEP 423](https://peps.python.org/pep-0423/) - Package naming conventions
- [Databricks ipywidgets docs](https://docs.databricks.com/en/notebooks/ipywidgets.html) - Runtime compatibility
- [python-dotenv patterns](https://pypi.org/project/python-dotenv/) - Environment variable handling

### Tertiary (LOW confidence - verify during implementation)

- Google Colab ipywidgets version - test during development
- Databricks Runtime 15.x specific compatibility - test on actual clusters

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - anywidget/hatchling/esbuild well documented
- Architecture: HIGH - follows established ipyniivue/mapwidget patterns
- Platform compatibility: MEDIUM - need to verify on actual platforms during development
- Ogma licensing: MEDIUM - need to verify npm registry setup with Linkurious

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (30 days - stable ecosystem)
