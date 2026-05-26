"""Ogma Jupyter - Interactive graph visualization for Jupyter notebooks."""

from pathlib import Path

from ._version import __version__
from .errors import OgmaDataError, OgmaError, OgmaLicenseError, OgmaRenderError
from .widget import OgmaWidget
from . import rules
from .config import _maybe_show_welcome

_maybe_show_welcome()

# Module-level license key — set once, used by all subsequent OgmaWidget instances
_license_key: str = ""


def set_license(key: str, download: bool = False) -> None:
    """Set the Ogma license key for the current session.

    Call this once at the top of your notebook. All subsequent
    OgmaWidget instances will use this key automatically.

    Parameters
    ----------
    key : str
        Your Ogma license key.
    download : bool, optional
        If True, immediately download and cache the Ogma JS bundle.
        Defaults to False (download happens lazily on first widget render).

    Examples
    --------
    >>> import ogma_jupyter as og
    >>> og.set_license("your-license-key")
    >>> og.demo()
    """
    global _license_key
    _license_key = key

    # Sync to config module so OgmaWidget.__init__ can access it
    from . import config as _config
    _config._license_key = key

    if download and key:
        from .downloader import download_ogma, assemble_widget_js
        cache_path = download_ogma(key)
        core_path = Path(__file__).parent / "static" / "widget_core.js"
        output_path = Path(__file__).parent / "static" / "widget.js"
        if core_path.exists():
            assemble_widget_js(ogma_path=cache_path, core_path=core_path, output_path=output_path)


def get_example_path() -> Path:
    """Get the path to bundled example notebooks."""
    package_dir = Path(__file__).parent
    examples_dir = package_dir.parent.parent / "examples"

    if not examples_dir.exists():
        import importlib.resources
        try:
            with importlib.resources.as_file(
                importlib.resources.files("ogma_jupyter").joinpath("../../examples")
            ) as path:
                examples_dir = path
        except (TypeError, FileNotFoundError):
            pass

    return examples_dir.resolve()


def demo() -> OgmaWidget:
    """Create a demo widget with sample graph data (triangle of 3 nodes)."""
    return OgmaWidget(
        graph_data={
            "nodes": [
                {"id": "a", "attributes": {"x": 0, "y": -60}, "data": {"label": "Node A"}},
                {"id": "b", "attributes": {"x": -70, "y": 40}, "data": {"label": "Node B"}},
                {"id": "c", "attributes": {"x": 70, "y": 40}, "data": {"label": "Node C"}},
            ],
            "edges": [
                {"id": "e1", "source": "a", "target": "b"},
                {"id": "e2", "source": "b", "target": "c"},
                {"id": "e3", "source": "c", "target": "a"},
            ],
        }
    )


__all__ = [
    "__version__",
    "OgmaWidget",
    "OgmaError",
    "OgmaLicenseError",
    "OgmaDataError",
    "OgmaRenderError",
    "rules",
    "set_license",
    "demo",
    "get_example_path",
]
