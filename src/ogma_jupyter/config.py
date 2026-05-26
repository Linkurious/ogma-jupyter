"""License key state and configuration for ogma-jupyter."""

import os
from typing import Optional

# Module-level license key — set via og.set_license() or OGMA_LICENSE_KEY env var
_license_key: str = ""

# Session-level welcome flag — avoids repeated welcome messages per Python session
_welcome_shown: bool = False


def get_license_key(provided_key: Optional[str] = None) -> str:
    """Resolve the Ogma license key.

    Priority: constructor arg > og.set_license() > OGMA_LICENSE_KEY env var.

    Parameters
    ----------
    provided_key : str, optional
        Key passed directly to the widget constructor.

    Returns
    -------
    str
        Resolved license key, or empty string if not configured.
    """
    if provided_key:
        return provided_key
    if _license_key:
        return _license_key
    return os.environ.get("OGMA_LICENSE_KEY", "")


def _maybe_show_welcome() -> None:
    """Show a welcome message once per Python session."""
    global _welcome_shown
    if _welcome_shown or os.environ.get("OGMA_JUPYTER_NO_WELCOME"):
        return
    print("Welcome to Ogma Jupyter! Run og.demo() to see an example.")
    _welcome_shown = True

