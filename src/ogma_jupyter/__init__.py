"""Ogma Jupyter - Interactive graph visualization for Jupyter notebooks."""

from pathlib import Path

from . import rules
from ._version import __version__
from .config import _maybe_show_welcome
from .errors import OgmaDataError, OgmaError, OgmaLicenseError, OgmaRenderError
from .widget import OgmaWidget

_maybe_show_welcome()

# Module-level license key — set once, used by all subsequent OgmaWidget instances
_license_key: str = ""


def set_license(
    key: str,
    download: bool = False,
) -> None:
    """Set the Ogma license key for the current session.

    Call this once at the top of your notebook. All subsequent
    OgmaWidget instances will use this key automatically.

    Parameters
    ----------
    key : str
        Your Ogma license key. It unlocks the rendered graph in the browser and
        authenticates the one-time download of the Ogma library.
    download : bool, optional
        If True, immediately download and cache the Ogma JS bundle using ``key``.
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
        from .downloader import ensure_bundle
        ensure_bundle(key)


def set_ogma_path(path: str) -> None:
    """Load Ogma from a local file instead of downloading it.

    Use this when you already have an Ogma UMD build on disk (for example in an
    offline or air-gapped environment) and want to skip the license-gated
    download entirely. No license key or network access is required in this
    mode.

    Call this once at the top of your notebook, before creating any widgets.

    Parameters
    ----------
    path : str
        Path to an Ogma UMD build (``ogma.umd.cjs`` or ``ogma.umd.js``), or to a
        directory that contains one (e.g. an unpacked ``@linkurious/ogma`` npm
        package). ``~`` is expanded.

    Notes
    -----
    Alternatively, set the ``OGMA_JS_PATH`` environment variable to the same
    value. Downloading with a license key remains the default when neither is
    configured.

    Examples
    --------
    >>> import ogma_jupyter as og
    >>> og.set_ogma_path("~/ogma/ogma.umd.cjs")
    >>> og.demo()
    """
    from . import config as _config
    _config._ogma_path = path


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
    "set_ogma_path",
    "demo",
    "get_example_path",
]
