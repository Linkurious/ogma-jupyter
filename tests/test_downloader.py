"""Tests for the Ogma JS downloader: HTTP fetch, cache, widget.js assembly."""

import os
import zipfile
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import ogma_jupyter as og
from ogma_jupyter.downloader import (
    is_ogma_cached,
    download_ogma,
    assemble_widget_js,
    get_cache_path,
    OGMA_VERSION,
)
from ogma_jupyter.errors import OgmaLicenseError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fake_ogma_zip(js_content: str = "/* fake ogma */") -> bytes:
    """Create an in-memory zip that mimics the Ogma npm package structure."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("package/dist/ogma.min.js", js_content)
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
        fake_zip = make_fake_ogma_zip("/* real ogma */")
        mock_response = MagicMock()
        mock_response.read.return_value = fake_zip
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen", return_value=mock_response):
            path = download_ogma("valid-key")

        assert path.exists()
        assert path.read_text() == "/* real ogma */"

    def test_download_url_contains_license_key(self, tmp_path):
        fake_zip = make_fake_ogma_zip()
        mock_response = MagicMock()
        mock_response.read.return_value = fake_zip
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
            with pytest.raises(OgmaLicenseError, match="license key"):
                download_ogma("bad-key")

    def test_raises_license_error_on_403(self, tmp_path):
        import urllib.error
        mock_error = urllib.error.HTTPError(
            url="http://example.com", code=403, msg="Forbidden", hdrs={}, fp=None
        )
        with patch("ogma_jupyter.downloader.CACHE_DIR", tmp_path), \
             patch("ogma_jupyter.downloader.urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(OgmaLicenseError, match="license key"):
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
# set_license integration (with mocked download)
# ---------------------------------------------------------------------------

class TestSetLicenseIntegration:
    def test_set_license_triggers_download_if_not_cached(self, tmp_path):
        fake_zip = make_fake_ogma_zip()
        mock_response = MagicMock()
        mock_response.read.return_value = fake_zip
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
