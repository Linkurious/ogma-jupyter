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
    3. Raise informative error with setup instructions

    Parameters
    ----------
    provided_key : str, optional
        License key provided directly to the widget constructor.
        Takes precedence over environment variable.

    Returns
    -------
    str
        The resolved Ogma license key.

    Raises
    ------
    OgmaLicenseError
        If no license key is found. The error message includes
        instructions for both environment variable and constructor
        approaches.

    Examples
    --------
    >>> # With environment variable set
    >>> import os
    >>> os.environ['OGMA_LICENSE_KEY'] = 'your-key'
    >>> key = get_license_key()

    >>> # With explicit key
    >>> key = get_license_key('your-key')

    >>> # Without any key (raises error)
    >>> key = get_license_key()  # doctest: +SKIP
    OgmaLicenseError: No Ogma license key found...
    """
    if provided_key:
        return provided_key

    env_key = os.environ.get("OGMA_LICENSE_KEY")
    if env_key:
        return env_key

    raise OgmaLicenseError(
        "No Ogma license key found.\n\n"
        "Set the OGMA_LICENSE_KEY environment variable:\n"
        "    export OGMA_LICENSE_KEY='your-key-here'\n\n"
        "Or in Python before importing:\n"
        "    import os\n"
        "    os.environ['OGMA_LICENSE_KEY'] = 'your-key-here'\n\n"
        "Or pass it directly to the widget:\n"
        "    widget = OgmaWidget(license_key='your-key-here')\n\n"
        "Get your license key from: https://get.linkurio.us"
    )


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
