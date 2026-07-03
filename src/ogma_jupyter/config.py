"""License key state and configuration for ogma-jupyter."""

import os
from typing import Optional

# Module-level license key — set via og.set_license() or OGMA_LICENSE_KEY env var
_license_key: str = ""

# Module-level Ogma download secret — set via og.set_license(download_secret=...)
# or the OGMA_DOWNLOAD_SECRET env var. Distinct from the runtime license key.
_download_secret: str = ""

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


def get_download_secret(
    provided_secret: Optional[str] = None,
    allow_license_fallback: bool = True,
) -> str:
    """Resolve the Ogma download secret used to authenticate the package download.

    Priority: provided arg > og.set_license(download_secret=...) >
    OGMA_DOWNLOAD_SECRET env var > (optionally) the license key.

    The download secret is distinct from the runtime license key. The license key
    is only used as a last-resort fallback when ``allow_license_fallback`` is True
    (e.g. for an explicit ``set_license(..., download=True)`` call). The lazy
    auto-download on widget render passes ``allow_license_fallback=False`` so that
    merely configuring a runtime license never triggers a network request — a
    dedicated download secret (env var or ``download_secret=``) is required.

    Parameters
    ----------
    provided_secret : str, optional
        Secret passed directly (e.g. to og.set_license()).
    allow_license_fallback : bool
        If True, fall back to the resolved license key when no dedicated download
        secret is configured.

    Returns
    -------
    str
        Resolved download secret, or empty string if none is configured.
    """
    if provided_secret:
        return provided_secret
    if _download_secret:
        return _download_secret
    env_secret = os.environ.get("OGMA_DOWNLOAD_SECRET")
    if env_secret:
        return env_secret
    if allow_license_fallback:
        return get_license_key()
    return ""


def _maybe_show_welcome() -> None:
    """Show a welcome message once per Python session."""
    global _welcome_shown
    if _welcome_shown or os.environ.get("OGMA_JUPYTER_NO_WELCOME"):
        return
    print("Welcome to Ogma Jupyter! Run og.demo() to see an example.")
    _welcome_shown = True

