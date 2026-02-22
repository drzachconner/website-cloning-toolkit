"""Unit tests for scripts/qa-check.py."""

import importlib.util
import os
import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Import the script module using importlib (handles hyphenated filename)
# ---------------------------------------------------------------------------

def load_script(name):
    """Load a Python script from the scripts/ directory by filename."""
    path = os.path.join(os.path.dirname(__file__), '..', 'scripts', name)
    path = os.path.abspath(path)
    module_name = name.replace('-', '_').replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qa = load_script('qa-check.py')

# Import BeautifulSoup for creating soup objects in tests
from bs4 import BeautifulSoup

PASS = qa.PASS
FAIL = qa.FAIL
WARN = qa.WARN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_check(check_fn, html_text, config=None):
    """Run a single qa-check function on an HTML string.

    The qa-check functions expect (html_text, soup, page_path, config).
    We provide a dummy page_path and an empty config by default.
    """
    if config is None:
        config = {}
    soup = BeautifulSoup(html_text, "html.parser")
    dummy_path = Path("/tmp/test-page.html")
    return check_fn(html_text, soup, dummy_path, config)


# ---------------------------------------------------------------------------
# Tests: Missing DOCTYPE
# ---------------------------------------------------------------------------

class TestDoctypeCheck:
    """Tests for DOCTYPE detection."""

    def test_detects_missing_doctype(self, sample_html_invalid):
        result = _run_check(qa.check_doctype, sample_html_invalid)
        assert result["status"] == FAIL, \
            "Should detect missing DOCTYPE in invalid HTML"

    def test_passes_with_doctype(self, sample_html_valid):
        result = _run_check(qa.check_doctype, sample_html_valid)
        assert result["status"] == PASS, \
            "Should pass for HTML with DOCTYPE"


# ---------------------------------------------------------------------------
# Tests: Missing lang attribute
# ---------------------------------------------------------------------------

class TestLangAttribute:
    """Tests for <html lang> attribute detection."""

    def test_detects_missing_lang(self, sample_html_invalid):
        result = _run_check(qa.check_html_lang, sample_html_invalid)
        assert result["status"] == FAIL, \
            "Should detect missing lang attribute"

    def test_passes_with_lang(self, sample_html_valid):
        result = _run_check(qa.check_html_lang, sample_html_valid)
        assert result["status"] == PASS, \
            "Should pass for HTML with lang attribute"


# ---------------------------------------------------------------------------
# Tests: Multiple h1 elements
# ---------------------------------------------------------------------------

class TestSingleH1:
    """Tests for single <h1> requirement."""

    def test_detects_multiple_h1(self, sample_html_invalid):
        result = _run_check(qa.check_single_h1, sample_html_invalid)
        assert result["status"] == FAIL, \
            "Should detect multiple h1 elements"

    def test_passes_with_single_h1(self, sample_html_valid):
        result = _run_check(qa.check_single_h1, sample_html_valid)
        assert result["status"] == PASS, \
            "Should pass for single h1"

    def test_detects_zero_h1(self):
        html = "<html><body><h2>No h1 here</h2></body></html>"
        result = _run_check(qa.check_single_h1, html)
        assert result["status"] == FAIL, "Should detect zero h1 elements"


# ---------------------------------------------------------------------------
# Tests: Heading hierarchy violations
# ---------------------------------------------------------------------------

class TestHeadingHierarchy:
    """Tests for heading level skip detection (e.g., h1 -> h3)."""

    def test_detects_h1_to_h3_skip(self, sample_html_invalid):
        # Invalid HTML has h1, h1, h3 -- the h1->h3 skip should be detected
        result = _run_check(qa.check_heading_hierarchy, sample_html_invalid)
        assert result["status"] == FAIL, \
            "Should detect heading hierarchy skip (h1 -> h3)"

    def test_passes_valid_hierarchy(self, sample_html_valid):
        # Valid HTML has h1, h2 -- valid progression
        result = _run_check(qa.check_heading_hierarchy, sample_html_valid)
        assert result["status"] == PASS, \
            "Should pass for valid heading hierarchy"

    def test_allows_going_back_up(self):
        html = "<html><body><h1>A</h1><h2>B</h2><h3>C</h3><h2>D</h2></body></html>"
        result = _run_check(qa.check_heading_hierarchy, html)
        assert result["status"] == PASS, \
            "Should allow going from h3 back to h2"

    def test_detects_h2_to_h4_skip(self):
        html = "<html><body><h1>A</h1><h2>B</h2><h4>C</h4></body></html>"
        result = _run_check(qa.check_heading_hierarchy, html)
        assert result["status"] == FAIL, \
            "Should detect h2 -> h4 skip"


# ---------------------------------------------------------------------------
# Tests: Inline style tags
# ---------------------------------------------------------------------------

class TestInlineStyleTags:
    """Tests for <style> tag detection."""

    def test_detects_inline_style_tags(self, sample_html_invalid):
        result = _run_check(qa.check_no_inline_style_tags, sample_html_invalid)
        assert result["status"] == FAIL, \
            "Should detect inline <style> tags"

    def test_passes_without_inline_styles(self, sample_html_valid):
        result = _run_check(qa.check_no_inline_style_tags, sample_html_valid)
        assert result["status"] == PASS, \
            "Should pass for HTML without inline <style> tags"


# ---------------------------------------------------------------------------
# Tests: Missing external stylesheet
# ---------------------------------------------------------------------------

class TestExternalStylesheet:
    """Tests for external stylesheet link detection."""

    def test_detects_missing_stylesheet(self, sample_html_invalid):
        result = _run_check(qa.check_external_stylesheet, sample_html_invalid)
        assert result["status"] == FAIL, \
            "Should detect missing external stylesheet link"

    def test_passes_with_stylesheet(self, sample_html_valid):
        result = _run_check(qa.check_external_stylesheet, sample_html_valid)
        assert result["status"] == PASS, \
            "Should pass for HTML with external stylesheet"


# ---------------------------------------------------------------------------
# Tests: Missing favicon
# ---------------------------------------------------------------------------

class TestFavicon:
    """Tests for favicon link detection."""

    def test_detects_missing_favicon(self, sample_html_invalid):
        result = _run_check(qa.check_favicon, sample_html_invalid)
        assert result["status"] == FAIL, \
            "Should detect missing favicon link"

    def test_passes_with_favicon(self, sample_html_valid):
        result = _run_check(qa.check_favicon, sample_html_valid)
        assert result["status"] == PASS, \
            "Should pass for HTML with favicon link"


# ---------------------------------------------------------------------------
# Tests: Placeholder text
# ---------------------------------------------------------------------------

class TestPlaceholderText:
    """Tests for placeholder text detection."""

    def test_detects_lorem_ipsum(self, sample_html_invalid):
        result = _run_check(qa.check_no_placeholder_text, sample_html_invalid)
        assert result["status"] == FAIL, \
            "Should detect 'Lorem ipsum' placeholder text"

    def test_passes_without_placeholder(self, sample_html_valid):
        result = _run_check(qa.check_no_placeholder_text, sample_html_valid)
        assert result["status"] == PASS, \
            "Should pass for HTML without placeholder text"


# ---------------------------------------------------------------------------
# Tests: Absolute URLs to original domain
# ---------------------------------------------------------------------------

class TestAbsoluteUrls:
    """Tests for absolute URL detection to the original domain."""

    def test_detects_absolute_urls(self, sample_html_invalid):
        config = {"original_domain": "original-domain.com"}
        result = _run_check(qa.check_no_absolute_original_urls, sample_html_invalid, config)
        assert result["status"] == FAIL, \
            "Should detect absolute URLs to original domain"

    def test_passes_with_relative_urls(self, sample_html_valid):
        config = {"original_domain": "original-domain.com"}
        result = _run_check(qa.check_no_absolute_original_urls, sample_html_valid, config)
        assert result["status"] == PASS, \
            "Should pass for HTML with relative URLs only"

    def test_warns_when_no_domain_configured(self, sample_html_valid):
        result = _run_check(qa.check_no_absolute_original_urls, sample_html_valid)
        assert result["status"] == WARN, \
            "Should warn when no original_domain is configured"


# ---------------------------------------------------------------------------
# Tests: Valid HTML passes all checks
# ---------------------------------------------------------------------------

class TestAllChecksPassing:
    """Tests that valid HTML passes every check."""

    def test_valid_html_passes_all_structure_checks(self, sample_html_valid):
        for check_fn in [qa.check_doctype, qa.check_html_lang,
                         qa.check_single_h1, qa.check_heading_hierarchy,
                         qa.check_valid_html]:
            result = _run_check(check_fn, sample_html_valid)
            assert result["status"] == PASS, \
                f"Valid HTML should pass {check_fn.__name__}, got {result['status']}: {result.get('detail')}"

    def test_valid_html_passes_all_css_checks(self, sample_html_valid):
        for check_fn in [qa.check_no_inline_style_tags, qa.check_external_stylesheet]:
            result = _run_check(check_fn, sample_html_valid)
            assert result["status"] == PASS, \
                f"Valid HTML should pass {check_fn.__name__}, got {result['status']}: {result.get('detail')}"

    def test_valid_html_passes_favicon(self, sample_html_valid):
        result = _run_check(qa.check_favicon, sample_html_valid)
        assert result["status"] == PASS

    def test_valid_html_passes_no_placeholder(self, sample_html_valid):
        result = _run_check(qa.check_no_placeholder_text, sample_html_valid)
        assert result["status"] == PASS

    def test_valid_html_passes_title(self, sample_html_valid):
        result = _run_check(qa.check_title, sample_html_valid)
        assert result["status"] == PASS

    def test_valid_html_passes_meta_description(self, sample_html_valid):
        result = _run_check(qa.check_meta_description, sample_html_valid)
        assert result["status"] == PASS


# ---------------------------------------------------------------------------
# Tests: Auto-fix adds missing viewport meta
# ---------------------------------------------------------------------------

class TestAutoFixViewportMeta:
    """Tests for the auto-fix that adds missing viewport meta tag."""

    def test_apply_fixes_adds_viewport_meta(self, tmp_path):
        """The apply_fixes function should add a viewport meta tag when missing."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>No viewport</title>
    <link rel="stylesheet" href="../css/style.css">
    <link rel="icon" href="../images/favicon.ico">
</head>
<body>
    <h1>Test</h1>
</body>
</html>"""
        page_path = tmp_path / "test.html"
        page_path.write_text(html, encoding="utf-8")

        soup = BeautifulSoup(html, "html.parser")
        # Verify no viewport meta initially
        assert soup.find("meta", attrs={"name": "viewport"}) is None

        updated_text, was_fixed = qa.apply_fixes(page_path, html, soup, [])
        assert was_fixed, "apply_fixes should have made changes"
        assert "viewport" in updated_text.lower(), \
            "Fixed HTML should contain viewport meta tag"

    def test_apply_fixes_does_not_modify_complete_html(self, tmp_path, sample_html_valid):
        """apply_fixes should not modify HTML that already has viewport meta and no issues."""
        page_path = tmp_path / "test.html"
        page_path.write_text(sample_html_valid, encoding="utf-8")

        soup = BeautifulSoup(sample_html_valid, "html.parser")
        updated_text, was_fixed = qa.apply_fixes(page_path, sample_html_valid, soup, [])
        assert not was_fixed, "apply_fixes should not modify already-complete HTML"


# ---------------------------------------------------------------------------
# Tests: run_checks integration
# ---------------------------------------------------------------------------

class TestRunChecks:
    """Tests for the run_checks function that orchestrates all checks."""

    def test_run_checks_returns_results_list(self, tmp_path, sample_html_valid):
        page_path = tmp_path / "test.html"
        page_path.write_text(sample_html_valid, encoding="utf-8")
        results, html_text, soup = qa.run_checks(page_path, {})
        assert isinstance(results, list), "run_checks should return a list of results"
        assert len(results) > 0, "Should have at least one check result"

    def test_run_checks_result_format(self, tmp_path, sample_html_valid):
        page_path = tmp_path / "test.html"
        page_path.write_text(sample_html_valid, encoding="utf-8")
        results, _, _ = qa.run_checks(page_path, {})
        for result in results:
            assert "check" in result, "Each result should have a 'check' key"
            assert "category" in result, "Each result should have a 'category' key"
            assert "status" in result, "Each result should have a 'status' key"
            assert result["status"] in (PASS, FAIL, WARN), \
                f"Status should be pass/fail/warn, got: {result['status']}"

    def test_run_checks_on_invalid_html_has_failures(self, tmp_path, sample_html_invalid):
        page_path = tmp_path / "bad.html"
        page_path.write_text(sample_html_invalid, encoding="utf-8")
        results, _, _ = qa.run_checks(page_path, {})
        failures = [r for r in results if r["status"] == FAIL]
        assert len(failures) > 0, "Invalid HTML should produce at least one failure"
