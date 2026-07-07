"""Tests for the Ogma JS downloader: HTTP fetch, cache, widget.js assembly."""

import os
import tarfile
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import ogma_jupyter as og
from ogma_jupyter.downloader import (
    is_ogma_cached,
    download_ogma,
    assemble_widget_js,
    build_bundle_source,
    get_cache_path,
    get_local_ogma_path,
    OGMA_VERSION,
)
from ogma_jupyter.errors import OgmaLicenseError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fake_ogma_tgz(js_content: str = "/* fake ogma */") -> bytes:
    """Create an in-memory npm tarball mimicking the Ogma package structure."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        data = js_content.encode("utf-8")
        info = tarfile.TarInfo(name="package/ogma.umd.cjs")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Cache detection
# ---------------------------------------------------------------------------

class TestOgmaCache:
    def test_not_cached_when_file_missing(self, tmp_path):
        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path):
            assert is_ogma_cached() is False

    def test_cached_when_file_exists(self, tmp_path):
        (tmp_path / f"ogma-{OGMA_VERSION}.min.js").write_text("/* ogma */")
        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path):
            assert is_ogma_cached() is True

    def test_get_cache_path_includes_version(self, tmp_path):
        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path):
            path = get_cache_path()
            assert OGMA_VERSION in path.name


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

class TestDownloadOgma:
    def test_downloads_and_caches_js(self, tmp_path):
        fake_tgz = make_fake_ogma_tgz("/* real ogma */")
        mock_response = MagicMock()
        mock_response.read.return_value = fake_tgz
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen", return_value=mock_response):
            path = download_ogma("valid-key")

        assert path.exists()
        assert path.read_text() == "/* real ogma */"

    def test_download_url_contains_license_key(self, tmp_path):
        fake_tgz = make_fake_ogma_tgz()
        mock_response = MagicMock()
        mock_response.read.return_value = fake_tgz
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        captured_urls = []

        def fake_urlopen(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen", fake_urlopen):
            download_ogma("my-secret-key")

        assert any("my-secret-key" in url for url in captured_urls)

    def test_raises_license_error_on_401(self, tmp_path):
        import urllib.error
        mock_error = urllib.error.HTTPError(
            url="http://example.com", code=401, msg="Unauthorized", hdrs={}, fp=None
        )
        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(OgmaLicenseError, match="download secret"):
                download_ogma("bad-key")

    def test_raises_license_error_on_403(self, tmp_path):
        import urllib.error
        mock_error = urllib.error.HTTPError(
            url="http://example.com", code=403, msg="Forbidden", hdrs={}, fp=None
        )
        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(OgmaLicenseError, match="download secret"):
                download_ogma("bad-key")

    def test_skips_download_if_already_cached(self, tmp_path):
        cache_file = tmp_path / f"ogma-{OGMA_VERSION}.min.js"
        cache_file.write_text("/* cached ogma */")

        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen") as mock_urlopen:
            path = download_ogma("any-key")

        mock_urlopen.assert_not_called()
        assert path.read_text() == "/* cached ogma */"


# ---------------------------------------------------------------------------
# Widget JS assembly
# ---------------------------------------------------------------------------

class TestAssembleWidgetJs:
    def test_assembles_ogma_and_core(self, tmp_path):
        ogma_path = tmp_path / "ogma.min.js"
        ogma_path.write_text("/* ogma bundle */")

        core_path = tmp_path / "widget_core.js"
        core_path.write_text("/* widget core */")

        output_path = tmp_path / "widget.js"

        assemble_widget_js(ogma_path=ogma_path, core_path=core_path, output_path=output_path)

        content = output_path.read_text()
        assert "/* ogma bundle */" in content
        assert "/* widget core */" in content

    def test_ogma_comes_before_core(self, tmp_path):
        ogma_path = tmp_path / "ogma.min.js"
        ogma_path.write_text("OGMA_FIRST")
        core_path = tmp_path / "widget_core.js"
        core_path.write_text("CORE_SECOND")
        output_path = tmp_path / "widget.js"

        assemble_widget_js(ogma_path=ogma_path, core_path=core_path, output_path=output_path)

        content = output_path.read_text()
        assert content.index("OGMA_FIRST") < content.index("CORE_SECOND")


# ---------------------------------------------------------------------------
# Local (node_modules) development fallback
# ---------------------------------------------------------------------------

class TestLocalOgmaFallback:
    def test_local_ogma_path_found_in_source_checkout(self):
        # This repo has @linkurious/ogma installed as a dev dependency, so the
        # local UMD build should be discoverable from a source checkout.
        local = get_local_ogma_path()
        assert local is not None
        assert local.name in ("ogma.umd.cjs", "ogma.umd.js")
        assert local.exists()

    def test_local_ogma_path_none_when_missing(self, tmp_path, monkeypatch):
        # Point the resolver at a file whose parents[2] has no node_modules.
        fake_file = tmp_path / "a" / "b" / "downloader.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        monkeypatch.setattr("ogma_jupyter.downloader.__file__", str(fake_file))
        assert get_local_ogma_path() is None

    def test_build_bundle_source_prepends_ogma(self, tmp_path):
        ogma_path = tmp_path / "ogma.umd.js"
        ogma_path.write_text("OGMA_UMD")
        with patch("ogma_jupyter.downloader.get_core_path") as core:
            core_file = tmp_path / "widget_core.js"
            core_file.write_text("WIDGET_CORE")
            core.return_value = core_file
            source = build_bundle_source(ogma_path)
        assert source.index("OGMA_UMD") < source.index("WIDGET_CORE")

    def test_build_bundle_source_isolates_umd_module_globals(self, tmp_path):
        """The Ogma UMD must be shadowed so a host RequireJS ``define`` does not
        divert it to the AMD branch (which breaks anywidget registration)."""
        ogma_path = tmp_path / "ogma.umd.js"
        ogma_path.write_text("OGMA_UMD")
        with patch("ogma_jupyter.downloader.get_core_path") as core:
            core_file = tmp_path / "widget_core.js"
            core_file.write_text("WIDGET_CORE")
            core.return_value = core_file
            source = build_bundle_source(ogma_path)
        # define/module/exports are shadowed as undefined around the UMD only.
        assert "var define=void 0,module=void 0,exports=void 0;" in source
        shield = source.index("var define=void 0")
        assert shield < source.index("OGMA_UMD") < source.index("WIDGET_CORE")
        # The core must remain outside the isolation IIFE so it reads the global.
        assert source.index("})();") < source.index("WIDGET_CORE")


# ---------------------------------------------------------------------------
# Local assembled bundle file (class-level _esm source)
# ---------------------------------------------------------------------------

from ogma_jupyter.downloader import ensure_local_bundle_file  # noqa: E402


class TestEnsureLocalBundleFile:
    def _setup_core(self, tmp_path):
        core = tmp_path / "widget_core.js"
        core.write_text("CORE_V1")
        return core

    def test_assembles_from_local_ogma(self, tmp_path, monkeypatch):
        ogma = tmp_path / "ogma.umd.js"
        ogma.write_text("OGMA_UMD")
        core = self._setup_core(tmp_path)
        monkeypatch.setattr("ogma_jupyter.downloader.CACHE_DIR", tmp_path / "cache")
        monkeypatch.setattr("ogma_jupyter.downloader.get_local_ogma_path", lambda: ogma)
        monkeypatch.setattr("ogma_jupyter.downloader.get_core_path", lambda: core)

        path = ensure_local_bundle_file()
        assert path is not None
        content = path.read_text()
        assert content.index("OGMA_UMD") < content.index("CORE_V1")

    def test_returns_none_without_local_ogma_or_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ogma_jupyter.downloader.CACHE_DIR", tmp_path / "cache")
        monkeypatch.setattr("ogma_jupyter.downloader.get_local_ogma_path", lambda: None)
        assert ensure_local_bundle_file() is None

    def test_reassembles_when_core_is_newer(self, tmp_path, monkeypatch):
        import os
        import time

        ogma = tmp_path / "ogma.umd.js"
        ogma.write_text("OGMA_UMD")
        core = tmp_path / "widget_core.js"
        core.write_text("CORE_V1")
        cache = tmp_path / "cache"
        monkeypatch.setattr("ogma_jupyter.downloader.CACHE_DIR", cache)
        monkeypatch.setattr("ogma_jupyter.downloader.get_local_ogma_path", lambda: ogma)
        monkeypatch.setattr("ogma_jupyter.downloader.get_core_path", lambda: core)

        first = ensure_local_bundle_file()
        assert "CORE_V1" in first.read_text()

        # Rebuild the core with newer mtime; bundle must be reassembled.
        time.sleep(0.01)
        core.write_text("CORE_V2")
        os.utime(core, (time.time() + 5, time.time() + 5))

        second = ensure_local_bundle_file()
        assert "CORE_V2" in second.read_text()

    def test_uses_cache_when_up_to_date(self, tmp_path, monkeypatch):
        ogma = tmp_path / "ogma.umd.js"
        ogma.write_text("OGMA_UMD")
        core = tmp_path / "widget_core.js"
        core.write_text("CORE_V1")
        cache = tmp_path / "cache"
        monkeypatch.setattr("ogma_jupyter.downloader.CACHE_DIR", cache)
        monkeypatch.setattr("ogma_jupyter.downloader.get_local_ogma_path", lambda: ogma)
        monkeypatch.setattr("ogma_jupyter.downloader.get_core_path", lambda: core)

        first = ensure_local_bundle_file()
        # Tamper with the cache to detect whether it is rewritten. Keep the
        # current format marker so only the mtime freshness check is exercised.
        from ogma_jupyter.downloader import BUNDLE_FORMAT_MARKER

        sentinel = BUNDLE_FORMAT_MARKER + "\nSENTINEL_CACHE"
        first.write_text(sentinel)
        second = ensure_local_bundle_file()
        assert second.read_text() == sentinel

    def test_rebuilds_when_bundle_format_marker_outdated(self, tmp_path, monkeypatch):
        ogma = tmp_path / "ogma.umd.js"
        ogma.write_text("OGMA_UMD")
        core = tmp_path / "widget_core.js"
        core.write_text("CORE_V1")
        cache = tmp_path / "cache"
        monkeypatch.setattr("ogma_jupyter.downloader.CACHE_DIR", cache)
        monkeypatch.setattr("ogma_jupyter.downloader.get_local_ogma_path", lambda: ogma)
        monkeypatch.setattr("ogma_jupyter.downloader.get_core_path", lambda: core)

        # Simulate a bundle assembled by an older version (no format marker),
        # newer than the sources so the mtime check alone would reuse it.
        from ogma_jupyter.downloader import BUNDLE_FORMAT_MARKER, get_bundle_path

        cache.mkdir(parents=True, exist_ok=True)
        stale = get_bundle_path()
        stale.write_text("OGMA_UMD\n;\nCORE_V1")  # legacy format, no marker

        rebuilt = ensure_local_bundle_file().read_text()
        assert rebuilt.splitlines()[0] == BUNDLE_FORMAT_MARKER
        assert "var define=void 0,module=void 0,exports=void 0;" in rebuilt


# ---------------------------------------------------------------------------
# set_license integration (with mocked download)
# ---------------------------------------------------------------------------

class TestSetLicenseIntegration:
    def test_set_license_triggers_download_if_not_cached(self, tmp_path):
        fake_tgz = make_fake_ogma_tgz()
        mock_response = MagicMock()
        mock_response.read.return_value = fake_tgz
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen", return_value=mock_response) as mock_dl:
            og.set_license("a-key", download=True)

        mock_dl.assert_called_once()

    def test_set_license_skips_download_if_cached(self, tmp_path):
        (tmp_path / f"ogma-{OGMA_VERSION}.min.js").write_text("/* ogma */")

        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen") as mock_dl:
            og.set_license("a-key", download=True)

        mock_dl.assert_not_called()


# ---------------------------------------------------------------------------
# Download-secret resolution
# ---------------------------------------------------------------------------

from ogma_jupyter import config as _config  # noqa: E402


class TestDownloadSecretResolution:
    @pytest.fixture(autouse=True)
    def _reset(self, monkeypatch):
        monkeypatch.setattr(_config, "_license_key", "")
        monkeypatch.setattr(_config, "_download_secret", "")
        monkeypatch.delenv("OGMA_DOWNLOAD_SECRET", raising=False)
        monkeypatch.delenv("OGMA_LICENSE_KEY", raising=False)

    def test_explicit_arg_wins(self):
        assert _config.get_download_secret("explicit") == "explicit"

    def test_configured_download_secret(self, monkeypatch):
        monkeypatch.setattr(_config, "_download_secret", "cfg-secret")
        assert _config.get_download_secret() == "cfg-secret"

    def test_env_var(self, monkeypatch):
        monkeypatch.setenv("OGMA_DOWNLOAD_SECRET", "env-secret")
        assert _config.get_download_secret() == "env-secret"

    def test_license_fallback_enabled_by_default(self, monkeypatch):
        monkeypatch.setattr(_config, "_license_key", "the-license")
        assert _config.get_download_secret() == "the-license"

    def test_license_fallback_can_be_disabled(self, monkeypatch):
        monkeypatch.setattr(_config, "_license_key", "the-license")
        assert _config.get_download_secret(allow_license_fallback=False) == ""


# ---------------------------------------------------------------------------
# Lazy auto-download on widget render
# ---------------------------------------------------------------------------

class TestLazyBundleResolution:
    @pytest.fixture(autouse=True)
    def _reset(self, monkeypatch):
        monkeypatch.setattr(_config, "_license_key", "")
        monkeypatch.setattr(_config, "_download_secret", "")
        monkeypatch.delenv("OGMA_DOWNLOAD_SECRET", raising=False)
        # Force the lazy path by hiding the local node_modules Ogma build.
        monkeypatch.setattr(
            "ogma_jupyter.downloader.get_local_ogma_path", lambda: None
        )
        import ogma_jupyter.widget as _widget
        monkeypatch.setattr(_widget, "_local_bundle_source", None)
        monkeypatch.setattr(_widget, "_failed_download_secrets", set())

    def test_bare_license_does_not_trigger_download(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_config, "_license_key", "just-a-license")
        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen") as mock_dl:
            from ogma_jupyter.widget import _resolve_bundle_source
            assert _resolve_bundle_source() is None
        mock_dl.assert_not_called()

    def test_download_secret_triggers_download(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OGMA_DOWNLOAD_SECRET", "real-secret")
        fake_tgz = make_fake_ogma_tgz("/* fake ogma umd */")
        mock_response = MagicMock()
        mock_response.read.return_value = fake_tgz
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen",
                   return_value=mock_response) as mock_dl:
            from ogma_jupyter.widget import _resolve_bundle_source
            source = _resolve_bundle_source()
        mock_dl.assert_called_once()
        assert source is not None
        assert "/* fake ogma umd */" in source

