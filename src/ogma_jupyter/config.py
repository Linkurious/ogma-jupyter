"""Configuration and license key management for ogma-jupyter.

Handles license key resolution from environment variables and constructor
arguments, plus first-run welcome message display.
"""

import os
from pathlib import Path
from typing import Optional

from .errors import OgmaLicenseError


# File marker to track if welcome message has been shown
_WELCOME_SHOWN_FILE = Path.home() / ".ogma_jupyter_welcome"


def get_license_key(provided_key: Optional[str] = None) -> str:
    """Get Ogma license key from environment or constructor argument.

    Resolves the license key using the following priority:
    1. Explicitly provided key (constructor argument)
    2. OGMA_LICENSE_KEY environment variable
    3. Return empty string (widget will show placeholder if Ogma not installed)

    The license key is only required for downloading @linkurious/ogma from
    the private npm registry. At runtime, if Ogma is not installed, the
    widget displays a helpful placeholder with setup instructions.

    Parameters
    ----------
    provided_key : str, optional
        License key provided directly to the widget constructor.
        Takes precedence over environment variable.

    Returns
    -------
    str
        The resolved Ogma license key, or empty string if not configured.

    Examples
    --------
    >>> # With environment variable set
    >>> import os
    >>> os.environ['OGMA_LICENSE_KEY'] = 'your-key'
    >>> key = get_license_key()

    >>> # With explicit key
    >>> key = get_license_key('your-key')

    >>> # Without any key (returns empty string)
    >>> key = get_license_key()
    >>> key
    ''
    """
    if provided_key:
        return provided_key

    env_key = os.environ.get("OGMA_LICENSE_KEY")
    if env_key:
        return env_key

    # No license key - widget will show placeholder if Ogma not installed
    return ""


def _maybe_show_welcome() -> None:
    """Show welcome message on first run.

    Displays a helpful message pointing users to the demo() function
    when ogma-jupyter is imported for the first time. Uses a marker
    file in the user's home directory to track if the message has
    already been shown.

    The marker file is created silently, and any errors writing it
    are ignored to avoid disrupting the user experience.
    """
    if _WELCOME_SHOWN_FILE.exists():
        return

    print("Welcome to Ogma Jupyter! Run og.demo() to see an example.")

    # Mark as shown - fail silently if we can't write
    try:
        _WELCOME_SHOWN_FILE.touch()
    except OSError:
        pass  # Best effort - don't fail if we can't write marker file
