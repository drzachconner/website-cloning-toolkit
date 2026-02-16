"""Pytest configuration and shared fixtures for the website-cloning-toolkit test suite."""

import os
import struct
import zlib
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests that require external services (Playwright, network)"
    )


# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_html_valid():
    """Minimal valid HTML page that passes all QA checks."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Test Page - Sample</title>
    <meta name="description" content="A sample page for testing.">
    <link rel="stylesheet" href="../css/style.css">
    <link rel="icon" href="../images/favicon.ico">
</head>
<body>
    <div class="entry-content cf">
        <h1>Main Heading</h1>
        <p>This is a paragraph of real content for testing purposes.</p>
        <h2>Sub Heading</h2>
        <p>More content under the subheading with <a href="/contact-us/">a link</a>.</p>
        <img src="../images/photo.jpg" alt="A photo">
    </div>
</body>
</html>"""


@pytest.fixture
def sample_html_invalid():
    """HTML page with multiple QA issues for testing detection."""
    return """<html>
<head>
    <title>Bad Page</title>
    <style>
        body { color: red; }
    </style>
</head>
<body>
    <div class="content">
        <h1>First Heading</h1>
        <h1>Second Heading - duplicate</h1>
        <h3>Skipped h2</h3>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
        <p style="color: blue;">Inline styled paragraph.</p>
        <img src="https://original-domain.com/images/photo.jpg" alt="Absolute URL">
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Sample CSS fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_css():
    """CSS content with colors, typography, spacing, components, and custom properties."""
    return """\
:root {
    --primary-color: #333333;
    --accent-color: #ed247c;
    --bg-color: #ffffff;
    --font-heading: 'Montserrat', sans-serif;
    --font-body: 'Open Sans', sans-serif;
}

body {
    font-family: 'Open Sans', sans-serif;
    font-size: 16px;
    font-weight: 400;
    line-height: 1.6;
    color: #333333;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}

h1 {
    font-family: 'Montserrat', sans-serif;
    font-size: 36px;
    font-weight: 700;
    line-height: 1.2;
    color: #222222;
    margin-bottom: 20px;
}

h2 {
    font-family: 'Montserrat', sans-serif;
    font-size: 28px;
    font-weight: 600;
    line-height: 1.3;
    color: #333333;
    margin-bottom: 15px;
}

h3 {
    font-family: 'Montserrat', sans-serif;
    font-size: 22px;
    font-weight: 600;
    color: #444444;
}

.entry-content {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px 30px;
}

.bldr_callout {
    font-style: italic;
    border-left: 3px solid #999999;
    padding: 10px 20px;
    margin: 20px 0;
    color: #555555;
}

.bldr_cta {
    display: inline-block;
    background-color: #ed247c;
    color: #ffffff;
    padding: 12px 24px;
    text-decoration: none;
    border-radius: 4px;
    font-weight: 600;
}

.bldr_cta:hover {
    background-color: #d11e6c;
}

a {
    color: #0066cc;
    text-decoration: underline;
}

a:hover {
    color: #004499;
}

@media (max-width: 768px) {
    h1 { font-size: 28px; }
    h2 { font-size: 22px; }
    .entry-content { padding: 10px 15px; }
}

@media (max-width: 480px) {
    body { font-size: 14px; }
}
"""


@pytest.fixture
def sample_css_empty():
    """Empty CSS content."""
    return ""


@pytest.fixture
def sample_css_malformed():
    """Malformed CSS that should be handled gracefully."""
    return """\
body {
    color: #333;
    font-size: 16px
    /* missing semicolon above */
    background-color: #fff;
}

h1 {
    font-size: 36px;
/* unclosed rule
.broken {
    color: red;
"""


# ---------------------------------------------------------------------------
# Temporary directory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_css_file(tmp_path, sample_css):
    """Write sample CSS to a temp file and return the path."""
    css_file = tmp_path / "style.css"
    css_file.write_text(sample_css, encoding="utf-8")
    return css_file


@pytest.fixture
def temp_html_dir(tmp_path, sample_html_valid):
    """Write sample HTML files to a temp directory and return the path."""
    html_dir = tmp_path / "pages"
    html_dir.mkdir()
    (html_dir / "index.html").write_text(sample_html_valid, encoding="utf-8")
    return html_dir


# ---------------------------------------------------------------------------
# Sample image fixtures
# ---------------------------------------------------------------------------

def _create_solid_png(width, height, r, g, b):
    """Create a minimal valid PNG file as bytes with a solid color.

    Uses raw zlib-compressed IDAT chunks -- no Pillow dependency needed
    for fixture creation itself.
    """
    def _chunk(chunk_type, data):
        raw = chunk_type + data
        return struct.pack(">I", len(data)) + raw + struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)

    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    ihdr = _chunk(b'IHDR', ihdr_data)

    # IDAT -- raw image data: each row starts with filter byte 0 (None)
    raw_rows = b''
    for _ in range(height):
        raw_rows += b'\x00' + bytes([r, g, b]) * width
    idat_data = zlib.compress(raw_rows)
    idat = _chunk(b'IDAT', idat_data)

    # IEND
    iend = _chunk(b'IEND', b'')

    return signature + ihdr + idat + iend


@pytest.fixture
def sample_image_red(tmp_path):
    """Create a small solid red 100x100 PNG and return the path."""
    path = tmp_path / "red.png"
    path.write_bytes(_create_solid_png(100, 100, 255, 0, 0))
    return path


@pytest.fixture
def sample_image_blue(tmp_path):
    """Create a small solid blue 100x100 PNG and return the path."""
    path = tmp_path / "blue.png"
    path.write_bytes(_create_solid_png(100, 100, 0, 0, 255))
    return path


@pytest.fixture
def sample_image_red_copy(tmp_path):
    """Create a second identical red 100x100 PNG (for identical-image tests)."""
    path = tmp_path / "red_copy.png"
    path.write_bytes(_create_solid_png(100, 100, 255, 0, 0))
    return path


@pytest.fixture
def sample_image_slightly_different(tmp_path):
    """Create a 100x100 PNG that is mostly red but with a few blue pixels."""
    # Build mostly-red image with ~5% blue pixels along top rows
    width, height = 100, 100
    raw_rows = b''
    for y in range(height):
        raw_rows += b'\x00'  # filter byte
        for x in range(width):
            if y < 5:  # top 5 rows are blue
                raw_rows += bytes([0, 0, 255])
            else:
                raw_rows += bytes([255, 0, 0])
    idat_data = zlib.compress(raw_rows)

    signature = b'\x89PNG\r\n\x1a\n'

    def _chunk(chunk_type, data):
        raw = chunk_type + data
        return struct.pack(">I", len(data)) + raw + struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)

    ihdr = _chunk(b'IHDR', struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    idat = _chunk(b'IDAT', idat_data)
    iend = _chunk(b'IEND', b'')

    path = tmp_path / "slightly_different.png"
    path.write_bytes(signature + ihdr + idat + iend)
    return path


@pytest.fixture
def sample_image_small(tmp_path):
    """Create a small 50x50 red PNG (different size from 100x100 fixtures)."""
    path = tmp_path / "small.png"
    path.write_bytes(_create_solid_png(50, 50, 255, 0, 0))
    return path
