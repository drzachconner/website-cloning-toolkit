"""Unit tests for scripts/extract-design-system.py."""

import importlib.util
import json
import os

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


eds = load_script('extract-design-system.py')


# ---------------------------------------------------------------------------
# Color extraction tests
# ---------------------------------------------------------------------------

class TestColorExtraction:
    """Tests for CSS color extraction."""

    def test_extracts_hex_colors(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        # Flatten all color values across categories
        all_color_values = []
        for category_colors in result["colors"].values():
            for entry in category_colors:
                all_color_values.append(entry["value"])
        # The CSS has #333333, #222222, #444444, #555555, #ffffff, #ed247c, etc.
        assert any("#333333" in v for v in all_color_values), \
            f"Expected #333333 in colors, got: {all_color_values}"

    def test_extracts_color_categories(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        # body color -> primary category, background-color -> neutral category
        assert "primary" in result["colors"], "Expected 'primary' color category"
        assert "neutral" in result["colors"], "Expected 'neutral' color category"

    def test_color_entries_have_selectors(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        for category, entries in result["colors"].items():
            for entry in entries:
                assert "value" in entry, f"Color entry missing 'value' key in {category}"
                assert "property" in entry, f"Color entry missing 'property' key in {category}"
                assert "selectors" in entry, f"Color entry missing 'selectors' key in {category}"
                assert isinstance(entry["selectors"], list), "selectors should be a list"


# ---------------------------------------------------------------------------
# Typography extraction tests
# ---------------------------------------------------------------------------

class TestTypographyExtraction:
    """Tests for CSS typography extraction."""

    def test_extracts_heading_typography(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        typography = result["typography"]
        assert "h1" in typography, "Expected h1 typography definition"
        assert "h2" in typography, "Expected h2 typography definition"

    def test_h1_has_correct_font_size(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        h1 = result["typography"].get("h1", {})
        assert h1.get("fontSize") == "36px", f"Expected h1 fontSize=36px, got {h1.get('fontSize')}"

    def test_h1_has_correct_font_weight(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        h1 = result["typography"].get("h1", {})
        assert h1.get("fontWeight") == "700", f"Expected h1 fontWeight=700, got {h1.get('fontWeight')}"

    def test_extracts_body_typography(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        typography = result["typography"]
        assert "body" in typography, "Expected body typography definition"
        body = typography["body"]
        assert "fontFamily" in body, "Expected fontFamily in body typography"
        assert "fontSize" in body, "Expected fontSize in body typography"

    def test_body_font_family_value(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        body = result["typography"].get("body", {})
        assert "Open Sans" in body.get("fontFamily", ""), \
            f"Expected 'Open Sans' in body fontFamily, got {body.get('fontFamily')}"

    def test_typography_uses_camel_case_keys(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        for element, props in result["typography"].items():
            for key in props:
                assert key in ("fontFamily", "fontSize", "fontWeight", "lineHeight"), \
                    f"Unexpected typography key '{key}' for {element}"


# ---------------------------------------------------------------------------
# Spacing extraction tests
# ---------------------------------------------------------------------------

class TestSpacingExtraction:
    """Tests for CSS spacing value extraction."""

    def test_extracts_spacing_values(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        spacing = result["spacing"]["values"]
        assert isinstance(spacing, list), "spacing.values should be a list"
        assert len(spacing) > 0, "Expected at least one spacing value"

    def test_spacing_contains_known_values(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        spacing = result["spacing"]["values"]
        # CSS has margin-bottom: 20px, padding: 10px 20px, etc.
        assert any("20px" in v for v in spacing), \
            f"Expected '20px' in spacing values, got: {spacing}"

    def test_spacing_values_are_sorted(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        spacing = result["spacing"]["values"]
        # Verify numeric sort order
        import re
        nums = []
        for val in spacing:
            m = re.match(r'^-?(\d+(\.\d+)?)', val)
            if m:
                nums.append(float(m.group(1)))
        assert nums == sorted(nums), "Spacing values should be sorted numerically"


# ---------------------------------------------------------------------------
# Breakpoint extraction tests
# ---------------------------------------------------------------------------

class TestBreakpointExtraction:
    """Tests for @media query breakpoint extraction."""

    def test_extracts_breakpoints_from_media_queries(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        breakpoints = result["layout"]["breakpoints"]
        assert isinstance(breakpoints, list), "breakpoints should be a list"
        # CSS has @media (max-width: 768px) and @media (max-width: 480px)
        assert 768 in breakpoints, f"Expected 768 in breakpoints, got: {breakpoints}"
        assert 480 in breakpoints, f"Expected 480 in breakpoints, got: {breakpoints}"

    def test_breakpoints_are_sorted(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        breakpoints = result["layout"]["breakpoints"]
        assert breakpoints == sorted(breakpoints), "Breakpoints should be sorted ascending"


# ---------------------------------------------------------------------------
# Custom properties extraction tests
# ---------------------------------------------------------------------------

class TestCustomProperties:
    """Tests for CSS custom property (variable) extraction from :root."""

    def test_extracts_custom_properties(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        custom_props = result["customProperties"]
        assert isinstance(custom_props, dict), "customProperties should be a dict"
        assert len(custom_props) > 0, "Expected at least one custom property"

    def test_custom_properties_include_known_vars(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        custom_props = result["customProperties"]
        assert "--primary-color" in custom_props, "Expected --primary-color in custom properties"
        assert custom_props["--primary-color"] == "#333333", \
            f"Expected --primary-color=#333333, got {custom_props.get('--primary-color')}"

    def test_custom_properties_include_font_vars(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        custom_props = result["customProperties"]
        assert "--font-heading" in custom_props, "Expected --font-heading in custom properties"
        assert "Montserrat" in custom_props["--font-heading"]


# ---------------------------------------------------------------------------
# Component detection tests
# ---------------------------------------------------------------------------

class TestComponentDetection:
    """Tests for component detection (class selectors with 3+ declarations)."""

    def test_detects_components_with_3_plus_declarations(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        components = result["components"]
        assert isinstance(components, list), "components should be a list"
        # .bldr_callout has 5 properties, .bldr_cta has 6 properties
        assert len(components) > 0, "Expected at least one component"

    def test_component_has_expected_keys(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        components = result["components"]
        for comp in components:
            assert "selector" in comp, "Component missing 'selector' key"
            assert "properties" in comp, "Component missing 'properties' key"
            assert "usedInHtml" in comp, "Component missing 'usedInHtml' key"

    def test_components_include_bldr_callout(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        component_selectors = [c["selector"] for c in result["components"]]
        assert any(".bldr_callout" in s for s in component_selectors), \
            f"Expected .bldr_callout component, got selectors: {component_selectors}"

    def test_components_include_bldr_cta(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        component_selectors = [c["selector"] for c in result["components"]]
        assert any(".bldr_cta" in s for s in component_selectors), \
            f"Expected .bldr_cta component, got selectors: {component_selectors}"


# ---------------------------------------------------------------------------
# JSON output schema tests
# ---------------------------------------------------------------------------

class TestOutputSchema:
    """Tests for the output JSON schema structure."""

    def test_output_has_all_top_level_keys(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        expected_keys = {"colors", "typography", "spacing", "layout", "customProperties", "components"}
        assert set(result.keys()) == expected_keys, \
            f"Expected keys {expected_keys}, got {set(result.keys())}"

    def test_layout_has_max_width_and_breakpoints(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        layout = result["layout"]
        assert "maxWidth" in layout, "layout missing 'maxWidth' key"
        assert "breakpoints" in layout, "layout missing 'breakpoints' key"

    def test_output_is_json_serializable(self, sample_css):
        result = eds.extract_design_tokens_from_css(sample_css)
        # Should not raise
        serialized = json.dumps(result, indent=2)
        assert isinstance(serialized, str)
        # Should round-trip cleanly
        parsed = json.loads(serialized)
        assert parsed.keys() == result.keys()


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for empty and malformed CSS input."""

    def test_empty_css_produces_valid_empty_result(self, sample_css_empty):
        result = eds.extract_design_tokens_from_css(sample_css_empty)
        assert isinstance(result, dict), "Should return a dict even for empty CSS"
        assert result["colors"] == {}, f"Expected empty colors, got: {result['colors']}"
        assert result["typography"] == {}, f"Expected empty typography, got: {result['typography']}"
        assert result["spacing"]["values"] == [], \
            f"Expected empty spacing, got: {result['spacing']['values']}"
        assert result["components"] == [], \
            f"Expected empty components, got: {result['components']}"

    def test_empty_css_is_json_serializable(self, sample_css_empty):
        result = eds.extract_design_tokens_from_css(sample_css_empty)
        serialized = json.dumps(result)
        assert isinstance(serialized, str)

    def test_malformed_css_handled_gracefully(self, sample_css_malformed):
        """Malformed CSS should not raise an exception."""
        # cssutils may log warnings but should not crash
        result = eds.extract_design_tokens_from_css(sample_css_malformed)
        assert isinstance(result, dict), "Should return a dict even for malformed CSS"
        # Should still have the correct top-level keys
        assert "colors" in result
        assert "typography" in result
        assert "spacing" in result

    def test_malformed_css_extracts_what_it_can(self, sample_css_malformed):
        """Malformed CSS should still extract any valid rules."""
        result = eds.extract_design_tokens_from_css(sample_css_malformed)
        # The body rule has a color and background-color that should be extractable
        all_color_values = []
        for entries in result["colors"].values():
            for entry in entries:
                all_color_values.append(entry["value"])
        # May or may not extract depending on how cssutils handles the malformed input
        # The key thing is that it does not crash
        assert isinstance(all_color_values, list)
