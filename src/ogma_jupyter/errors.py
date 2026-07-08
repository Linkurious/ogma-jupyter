"""Custom exceptions for ogma-jupyter with helpful error messages.

All exceptions include actionable fix suggestions to help users resolve issues
quickly without searching documentation.
"""


class OgmaError(Exception):
    """Base exception for all ogma-jupyter errors.

    All ogma-jupyter exceptions inherit from this class, making it easy to
    catch any library-specific error.

    Examples
    --------
    >>> try:
    ...     # ogma-jupyter operation
    ...     pass
    ... except OgmaError as e:
    ...     print(f"Ogma error: {e}")
    """

    pass


class OgmaLicenseError(OgmaError):
    """Raised when the Ogma license key is missing or invalid.

    This error occurs when:
    - No license key is provided to the widget constructor
    - The OGMA_LICENSE_KEY environment variable is not set
    - The provided license key is invalid or expired

    Examples
    --------
    >>> from ogma_jupyter.errors import OgmaLicenseError
    >>> raise OgmaLicenseError("No license key found")
    Traceback (most recent call last):
        ...
    ogma_jupyter.errors.OgmaLicenseError: No license key found
    """

    pass


class OgmaDataError(OgmaError):
    """Raised when graph data format is invalid.

    This error occurs when the provided data doesn't match the expected
    graph format. Error messages include specific guidance on how to
    fix the data format.

    Examples
    --------
    >>> from ogma_jupyter.errors import OgmaDataError
    >>> raise OgmaDataError(
    ...     "Expected nodes as list of dicts, got DataFrame. "
    ...     "Use from_dataframe() instead."
    ... )
    Traceback (most recent call last):
        ...
    ogma_jupyter.errors.OgmaDataError: Expected nodes as list of dicts...
    """

    pass


class OgmaRenderError(OgmaError):
    """Raised when widget rendering fails.

    This error occurs when there's a problem initializing or rendering
    the Ogma visualization, such as WebGL context issues or container
    sizing problems.

    Examples
    --------
    >>> from ogma_jupyter.errors import OgmaRenderError
    >>> raise OgmaRenderError("Failed to initialize WebGL context")
    Traceback (most recent call last):
        ...
    ogma_jupyter.errors.OgmaRenderError: Failed to initialize WebGL context
    """

    pass
