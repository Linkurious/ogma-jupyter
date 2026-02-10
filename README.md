# ogma-jupyter

[![PyPI version](https://badge.fury.io/py/ogma-jupyter.svg)](https://badge.fury.io/py/ogma-jupyter)
[![Python versions](https://img.shields.io/pypi/pyversions/ogma-jupyter.svg)](https://pypi.org/project/ogma-jupyter/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Interactive Ogma graph visualization for Jupyter notebooks.

## Installation

```bash
pip install ogma-jupyter
```

## Ogma License Configuration

Ogma is a commercial graph visualization library from Linkurious. To use the full visualization capabilities, you need:

1. An Ogma license key
2. Access to the Linkurious npm registry (for development builds)

### Setting the License Key

Set the `OGMA_LICENSE_KEY` environment variable:

```bash
export OGMA_LICENSE_KEY="your-license-key-here"
```

Or pass it directly to the widget:

```python
widget = og.OgmaWidget(license_key="your-license-key-here")
```

### Configuring npm Registry for Development

If you're building from source and need access to the `@linkurious/ogma` package, create a `.npmrc` file in the project root:

```npmrc
@linkurious:registry=https://npm.linkurio.us/
//npm.linkurio.us/:_authToken=YOUR_LINKURIOUS_AUTH_TOKEN
```

Contact Linkurious or visit the [Linkurious customer portal](https://get.linkurio.us) to obtain:
- Your Ogma license key
- Your npm registry authentication token

### Development Without Ogma

The widget includes a graceful fallback when Ogma is not available. You can develop and test the Python package infrastructure without having Ogma configured - the widget will display a placeholder indicating that Ogma needs to be configured.

## Quick Start

```python
import ogma_jupyter as og

# Create a simple graph widget
widget = og.OgmaWidget()
widget.graph_data = {
    'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}],
    'edges': [
        {'source': 'a', 'target': 'b'},
        {'source': 'b', 'target': 'c'},
        {'source': 'c', 'target': 'a'}
    ]
}
widget

# Or use the demo function
og.demo()
```

## Examples

Bundled example notebooks are included in the package:

- **[01-quickstart.ipynb](examples/01-quickstart.ipynb)** - Quick introduction to ogma-jupyter
- **[02-basic-graph.ipynb](examples/02-basic-graph.ipynb)** - Creating graphs with node/edge attributes

To find the examples directory in your installation:

```python
import ogma_jupyter as og
print(og.get_example_path())
```

You can copy the examples to your workspace to experiment with them.

## Supported Platforms

ogma-jupyter works in:

- **JupyterLab** - Full support
- **VSCode notebooks** - Full support
- **Google Colab** - Full support
- **Databricks notebooks** - Supported (requires Ogma license)
- **Classic Jupyter Notebook** - Full support

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/Linkurious/ogma-jupyter.git
cd ogma-jupyter

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Building JavaScript

```bash
# Install npm dependencies
npm install

# Build the widget JavaScript
npm run build

# Watch mode for development
npm run dev
```

## License

MIT
