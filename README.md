# ogma-jupyter

Interactive Ogma graph visualization for Jupyter notebooks.

## Installation

```bash
pip install ogma-jupyter
```

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
