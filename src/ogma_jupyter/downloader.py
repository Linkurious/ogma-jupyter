"""Ogma JS bundle downloader and widget.js assembler.

Downloads the Ogma UMD build from the Linkurious distribution center
(authenticated via the Ogma license key), caches it locally, and assembles it
with the pre-built, Ogma-free ``widget_core.js`` into the runtime ``widget.js``
bundle.
"""

import io
import tarfile
import urllib.error
import urllib.request
import warnings
from pathlib import Path
from typing import Optional

from .errors import OgmaLicenseError

# Ogma version to download — keep in sync with package.json
OGMA_VERSION = "6.0.5"

# Assembled-bundle format version. Bump whenever the assembly logic in
# ``build_bundle_source`` changes, so previously cached bundles produced by an
# older assembler are treated as stale and rebuilt (or re-downloaded) instead of
# being served from cache. The marker is embedded as the first line of every
# assembled bundle.
BUNDLE_FORMAT_VERSION = 2
BUNDLE_FORMAT_MARKER = f"// ogma-jupyter bundle-format v{BUNDLE_FORMAT_VERSION}"

# Local cache directory for the downloaded Ogma JS bundle
CACHE_DIR = Path.home() / ".cache" / "ogma_jupyter"

# Distribution URL — {version} and {license_key} are substituted at download
# time. The endpoint returns the Ogma npm package as a gzip-compressed tarball.
OGMA_DOWNLOAD_URL = "https://get.linkurio.us/api/get/npm/ogma/{version}/?secret={license_key}"

# Path inside the downloaded npm tarball to the UMD build. The UMD build is used
# (rather than the ESM build) because, once prepended to the widget core module,
# it exposes the `Ogma` constructor as a global that the core references.
OGMA_JS_PATH_IN_ARCHIVE = "package/ogma.umd.cjs"


def get_cache_path() -> Path:
    """Return the local cache path for the downloaded Ogma JS bundle."""
    return CACHE_DIR / f"ogma-{OGMA_VERSION}.min.js"


def get_bundle_path() -> Path:
    """Return the local cache path for the assembled widget bundle.

    This is the Ogma UMD build concatenated with the Ogma-free widget core
    (``widget_core.js``). It is what the widget loads as its ``_esm`` once a
    license key has been used to download Ogma.
    """
    return CACHE_DIR / f"widget-{OGMA_VERSION}.js"


def get_core_path() -> Path:
    """Return the path to the packaged, Ogma-free widget core bundle."""
    return Path(__file__).parent / "static" / "widget_core.js"


def get_local_ogma_path() -> Optional[Path]:
    """Return a local Ogma UMD build to use instead of downloading Ogma.

    Resolution order:

    1. A user-configured local path (``og.set_ogma_path(...)`` or the
       ``OGMA_JS_PATH`` env var). This lets users point ogma-jupyter at an Ogma
       build they already have on disk, with no license key or network access.
       The path may be a UMD file directly, or a directory containing
       ``ogma.umd.cjs`` / ``ogma.umd.js`` (e.g. an unpacked npm package).
    2. The repo-local ``@linkurious/ogma`` dev dependency from ``node_modules``
       (development/testing convenience). It is never present in an installed
       distribution (which ships no ``node_modules``), so it does not affect
       end-user behaviour.

    Returns ``None`` when no local Ogma build is available, in which case Ogma
    must still be downloaded at runtime via the configured license key.
    """
    # 1. User-configured local Ogma path (highest priority).
    from . import config

    configured = config.get_ogma_path()
    if configured:
        resolved = _resolve_configured_ogma_path(configured)
        if resolved is not None:
            return resolved
        warnings.warn(
            f"Configured Ogma path '{configured}' does not point to an Ogma UMD "
            f"build (expected a .cjs/.js file, or a directory containing "
            f"'ogma.umd.cjs' / 'ogma.umd.js'). Falling back to the default "
            f"download behaviour.",
            stacklevel=2,
        )

    # 2. Repo-local node_modules build (development/testing).
    # This file lives at <repo>/src/ogma_jupyter/downloader.py, so parents[2] is
    # the repository root in an editable/source checkout.
    repo_root = Path(__file__).resolve().parents[2]
    ogma_dir = repo_root / "node_modules" / "@linkurious" / "ogma"
    # Ogma renamed its UMD build from ``ogma.umd.js`` to ``ogma.umd.cjs`` (the
    # package's ``browser`` entry point) in newer releases; ``ogma.js`` is the
    # ESM build and is not compatible with the UMD-shadowing assembler. Try the
    # UMD candidates in order so both old and new Ogma versions work.
    for filename in ("ogma.umd.cjs", "ogma.umd.js"):
        candidate = ogma_dir / filename
        if candidate.exists():
            return candidate
    return None


def _resolve_configured_ogma_path(configured: str) -> Optional[Path]:
    """Resolve a user-configured Ogma path to a concrete UMD file, if valid.

    Accepts either a path to a UMD build file directly, or a directory
    containing ``ogma.umd.cjs`` / ``ogma.umd.js``. Returns ``None`` when the
    path does not resolve to an existing UMD build.
    """
    path = Path(configured).expanduser()
    if path.is_dir():
        for filename in ("ogma.umd.cjs", "ogma.umd.js"):
            candidate = path / filename
            if candidate.exists():
                return candidate
        return None
    if path.is_file():
        return path
    return None


def build_bundle_source(ogma_js_path: Path) -> str:
    """Assemble the widget bundle source from an Ogma UMD build and the core.

    Prepends the Ogma UMD build to the Ogma-free ``widget_core.js`` so the UMD
    wrapper exposes the ``Ogma`` global that the core references. A separating
    newline and semicolon guard against ASI edge cases.

    The Ogma UMD build is wrapped so that ``define``, ``module`` and ``exports``
    are shadowed as ``undefined`` while it runs. anywidget evaluates this bundle
    as an ES module, but notebook frontends (VS Code, classic Notebook,
    JupyterLab) expose a global RequireJS ``define``. Without shadowing, the UMD
    wrapper detects that AMD ``define`` and takes the AMD branch, calling an
    anonymous ``define()`` that throws ("Mismatched anonymous define") instead of
    assigning the ``Ogma`` global. That exception aborts evaluation of the whole
    ``_esm`` module, so anywidget itself fails to register and the frontend
    reports the misleading "No version of module anywidget is registered".
    Forcing the UMD down its ``globalThis``/``self`` branch makes the ``Ogma``
    global available to the core regardless of the host frontend.
    """
    ogma_content = ogma_js_path.read_text(encoding="utf-8")
    core_content = get_core_path().read_text(encoding="utf-8")
    isolated_ogma = (
        "(function(){\n"
        "var define=void 0,module=void 0,exports=void 0;\n"
        f"{ogma_content}\n"
        "})();"
    )
    return BUNDLE_FORMAT_MARKER + "\n" + isolated_ogma + "\n;\n" + core_content


def _bundle_format_is_current(bundle_path: Path) -> bool:
    """Return True if the cached bundle was produced by the current assembler.

    Reads only the first line (the format marker) to avoid loading the whole
    multi-megabyte bundle just to validate it.
    """
    try:
        with bundle_path.open("r", encoding="utf-8") as fh:
            first_line = fh.readline().strip()
    except OSError:
        return False
    return first_line == BUNDLE_FORMAT_MARKER


def ensure_local_bundle_file() -> Optional[Path]:
    """Ensure an assembled Ogma+core bundle *file* exists in the cache, offline.

    Returns the path to the assembled bundle when Ogma is available locally —
    either from a previously assembled/downloaded cache file, or by assembling
    the repo-local ``node_modules`` Ogma build (development/testing). Returns
    ``None`` when Ogma is not locally available (no cache, no ``node_modules``),
    in which case it must still be downloaded at runtime via
    ``og.set_license(..., download=True)``.

    Producing a *file* (rather than an in-memory string) lets the widget point
    its class-level ``_esm`` at a stable ``Path``, so the widget model is created
    already carrying Ogma — the same mechanism as the previously bundled
    ``widget.js``, which avoids large late ``_esm`` reassignments during widget
    construction.
    """
    bundle_path = get_bundle_path()
    local_ogma = get_local_ogma_path()

    if bundle_path.exists():
        # Reassemble if the widget core or the local Ogma build is newer than the
        # cached bundle, so JS rebuilds (npm run build) take effect without a
        # manual cache purge. Also reassemble if the cached bundle was produced by
        # an older assembler (missing the current format marker). When no local
        # Ogma is present (installed distribution using a downloaded bundle), keep
        # the existing cache.
        bundle_mtime = bundle_path.stat().st_mtime
        core_mtime = get_core_path().stat().st_mtime
        ogma_mtime = local_ogma.stat().st_mtime if local_ogma is not None else 0
        if (
            _bundle_format_is_current(bundle_path)
            and bundle_mtime >= core_mtime
            and bundle_mtime >= ogma_mtime
        ):
            return bundle_path

    if local_ogma is None:
        # Cannot (re)assemble locally; return an existing (possibly stale) cache
        # if present, otherwise signal that a download is required.
        return bundle_path if bundle_path.exists() else None

    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(build_bundle_source(local_ogma), encoding="utf-8")
    return bundle_path


def is_ogma_cached() -> bool:
    """Return True if the Ogma JS bundle is already cached locally."""
    return get_cache_path().exists()


def download_ogma(license_key: str) -> Path:
    """Download the Ogma UMD build and cache it locally.

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

    url = OGMA_DOWNLOAD_URL.format(version=OGMA_VERSION, license_key=license_key)

    try:
        with urllib.request.urlopen(url) as response:
            archive_data = response.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise OgmaLicenseError(
                f"Invalid or missing Ogma license key (HTTP {e.code}). "
                f"Get your license key at https://get.linkurio.us/"
            ) from e
        raise

    with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:gz") as tf:
        member = tf.extractfile(OGMA_JS_PATH_IN_ARCHIVE)
        if member is None:
            raise OgmaLicenseError(
                f"Ogma download archive did not contain "
                f"'{OGMA_JS_PATH_IN_ARCHIVE}'."
            )
        js_content = member.read().decode("utf-8")

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
    # The Ogma UMD bundle is an expression statement; a separating newline plus
    # semicolon guards against ASI edge cases when the core module follows.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ogma_content = ogma_path.read_text(encoding="utf-8")
    core_content = core_path.read_text(encoding="utf-8")
    output_path.write_text(ogma_content + "\n;\n" + core_content, encoding="utf-8")


def ensure_bundle(license_key: str) -> Path:
    """Download Ogma (if needed) and assemble the widget bundle in the cache.

    Combines the license-gated Ogma UMD bundle with the packaged,
    Ogma-free ``widget_core.js`` and writes the result to :func:`get_bundle_path`
    (inside the user cache directory, never the installed package). Subsequent
    calls reuse the cached artifacts.

    Parameters
    ----------
    license_key : str
        Ogma license key used to authenticate the Ogma download.

    Returns
    -------
    Path
        Path to the assembled widget bundle.

    Raises
    ------
    OgmaLicenseError
        If the license key is rejected during download.
    """
    ogma_path = download_ogma(license_key)
    bundle_path = get_bundle_path()
    assemble_widget_js(
        ogma_path=ogma_path,
        core_path=get_core_path(),
        output_path=bundle_path,
    )
    return bundle_path
