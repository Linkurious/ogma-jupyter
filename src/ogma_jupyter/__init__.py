"""Ogma Jupyter - Interactive graph visualization for Jupyter notebooks."""

from pathlib import Path
from typing import Optional

from ._version import __version__
from .errors import OgmaDataError, OgmaError, OgmaLicenseError, OgmaRenderError
from .widget import OgmaWidget
from . import rules
from .config import _maybe_show_welcome

_maybe_show_welcome()

# Module-level license key — set once, used by all subsequent OgmaWidget instances
_license_key: str = ""


def set_license(
    key: str,
    download: bool = False,
    download_secret: Optional[str] = None,
) -> None:
    """Set the Ogma license key for the current session.

    Call this once at the top of your notebook. All subsequent
    OgmaWidget instances will use this key automatically.

    Parameters
    ----------
    key : str
        Your Ogma runtime license key (passed to ``new Ogma({license})`` in the
        browser).
    download : bool, optional
        If True, immediately download and cache the Ogma JS bundle.
        Defaults to False (download happens lazily on first widget render).
    download_secret : str, optional
        Secret used to authenticate the Ogma package download — distinct from the
        runtime license ``key``. Resolved in this order: this argument, the
        ``OGMA_DOWNLOAD_SECRET`` environment variable, then ``key`` itself as a
        fallback.

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
    if download_secret is not None:
        _config._download_secret = download_secret

    if download:
        secret = _config.get_download_secret(download_secret)
        if secret:
            from .downloader import ensure_bundle
            ensure_bundle(secret)


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
