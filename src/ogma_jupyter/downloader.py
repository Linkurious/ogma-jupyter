"""Ogma JS bundle downloader and widget.js assembler.

Downloads the Ogma JavaScript bundle from the Linkurious distribution
center (authenticated via license key), caches it locally, and assembles
it with the pre-built widget_core.js into the final widget.js.
"""

import io
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .errors import OgmaLicenseError

# Ogma version to download — keep in sync with package.json
OGMA_VERSION = "6.0.0"

# Local cache directory for the downloaded Ogma JS bundle
CACHE_DIR = Path.home() / ".cache" / "ogma_jupyter"

# Distribution URL — {version} and {key} are substituted at download time.
# Placeholder: replace with actual Linkurious distribution URL.
OGMA_DOWNLOAD_URL = "https://get.linkurio.us/ogma/{version}/ogma.zip?key={key}"

# Path inside the downloaded zip to the minified JS bundle
OGMA_JS_PATH_IN_ZIP = "package/dist/ogma.min.js"


def get_cache_path() -> Path:
    """Return the local cache path for the Ogma JS bundle."""
    return CACHE_DIR / f"ogma-{OGMA_VERSION}.min.js"


def is_ogma_cached() -> bool:
    """Return True if the Ogma JS bundle is already cached locally."""
    return get_cache_path().exists()


def download_ogma(license_key: str) -> Path:
    """Download the Ogma JS bundle and cache it locally.

    If already cached, returns the cached path immediately without
    making any network request.

    Parameters
    ----------
    license_key : str
        Ogma license key used to authenticate the download.

    Returns
    -------
    Path
        Path to the cached Ogma JS file.

    Raises
    ------
    OgmaLicenseError
        If the license key is rejected (HTTP 401 or 403).
    """
    cache_path = get_cache_path()
    if cache_path.exists():
        return cache_path

    url = OGMA_DOWNLOAD_URL.format(version=OGMA_VERSION, key=license_key)

    try:
        with urllib.request.urlopen(url) as response:
            zip_data = response.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise OgmaLicenseError(
                f"Invalid or missing Ogma license key (HTTP {e.code}). "
                f"Get your key at https://get.linkurio.us/"
            ) from e
        raise

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        js_content = zf.read(OGMA_JS_PATH_IN_ZIP).decode("utf-8")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(js_content, encoding="utf-8")
    return cache_path


def assemble_widget_js(ogma_path: Path, core_path: Path, output_path: Path) -> None:
    """Combine the Ogma bundle and widget core into the final widget.js.

    Parameters
    ----------
    ogma_path : Path
        Path to the downloaded ogma.min.js bundle.
    core_path : Path
        Path to widget_core.js (the pre-built anywidget wrapper, no Ogma).
    output_path : Path
        Destination path for the assembled widget.js.
    """
    ogma_content = ogma_path.read_text(encoding="utf-8")
    core_content = core_path.read_text(encoding="utf-8")
    output_path.write_text(ogma_content + "\n" + core_content, encoding="utf-8")
