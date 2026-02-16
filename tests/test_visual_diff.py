"""Unit tests for scripts/visual-diff.py."""

import importlib.util
import os

import pytest

# Pillow is a required dependency; import unconditionally
from PIL import Image


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


vd = load_script('visual-diff.py')

# Check whether scikit-image is available (for SSIM tests)
try:
    import numpy as np
    from skimage.metrics import structural_similarity as ssim
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False

skip_without_skimage = pytest.mark.skipif(
    not HAS_SKIMAGE,
    reason="scikit-image not installed"
)


# ---------------------------------------------------------------------------
# Pixel similarity tests
# ---------------------------------------------------------------------------

class TestPixelSimilarity:
    """Tests for pixel-level similarity calculation."""

    def test_identical_images_100_percent(self, sample_image_red, sample_image_red_copy):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        similarity = vd.calculate_pixel_similarity(img1, img2)
        assert similarity == 100.0, \
            f"Identical images should have 100% pixel similarity, got {similarity}"

    def test_completely_different_images_low_score(self, sample_image_red, sample_image_blue):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_blue)
        similarity = vd.calculate_pixel_similarity(img1, img2)
        assert similarity < 5.0, \
            f"Red vs blue images should have very low similarity, got {similarity}%"

    def test_slightly_different_images_high_score(self, sample_image_red, sample_image_slightly_different):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_slightly_different)
        similarity = vd.calculate_pixel_similarity(img1, img2)
        # 95 of 100 rows are identical (95%), within tolerance
        assert similarity > 90.0, \
            f"Mostly-similar images should have >90% similarity, got {similarity}%"
        assert similarity < 100.0, \
            f"Slightly different images should not be 100%, got {similarity}%"

    def test_similarity_returns_float(self, sample_image_red, sample_image_red_copy):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        result = vd.calculate_pixel_similarity(img1, img2)
        assert isinstance(result, float), f"Expected float, got {type(result)}"


# ---------------------------------------------------------------------------
# SSIM tests (require scikit-image)
# ---------------------------------------------------------------------------

class TestSSIM:
    """Tests for SSIM (Structural Similarity Index) calculation."""

    @skip_without_skimage
    def test_ssim_identical_images_score_1(self, sample_image_red, sample_image_red_copy):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        score, diff_map = vd.calculate_ssim(img1, img2)
        assert abs(score - 1.0) < 0.001, \
            f"SSIM of identical images should be ~1.0, got {score}"

    @skip_without_skimage
    def test_ssim_slightly_different_above_09(self, sample_image_red, sample_image_slightly_different):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_slightly_different)
        score, diff_map = vd.calculate_ssim(img1, img2)
        assert score > 0.9, \
            f"SSIM of slightly different images should be >0.9, got {score}"

    @skip_without_skimage
    def test_ssim_very_different_below_05(self, sample_image_red, sample_image_blue):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_blue)
        score, diff_map = vd.calculate_ssim(img1, img2)
        assert score < 0.5, \
            f"SSIM of very different images should be <0.5, got {score}"

    @skip_without_skimage
    def test_ssim_returns_tuple(self, sample_image_red, sample_image_red_copy):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        result = vd.calculate_ssim(img1, img2)
        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
        assert len(result) == 2, f"Expected 2-tuple (score, diff_map), got {len(result)}"

    @skip_without_skimage
    def test_ssim_diff_map_is_numpy_array(self, sample_image_red, sample_image_blue):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_blue)
        score, diff_map = vd.calculate_ssim(img1, img2)
        assert hasattr(diff_map, 'shape'), "diff_map should be a numpy array"

    def test_ssim_raises_without_skimage(self, sample_image_red, sample_image_red_copy):
        """If scikit-image is not available, calculate_ssim should raise RuntimeError."""
        if HAS_SKIMAGE:
            pytest.skip("scikit-image is installed; cannot test missing-dependency path")
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        with pytest.raises(RuntimeError, match="scikit-image"):
            vd.calculate_ssim(img1, img2)


# ---------------------------------------------------------------------------
# Region-based analysis tests
# ---------------------------------------------------------------------------

class TestRegionAnalysis:
    """Tests for region-based (horizontal band) similarity analysis."""

    def test_divides_image_into_correct_number_of_regions(
        self, sample_image_red, sample_image_red_copy
    ):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        num_regions = 4
        regions = vd.calculate_region_scores(img1, img2, num_regions, metric="pixel")
        assert len(regions) == num_regions, \
            f"Expected {num_regions} regions, got {len(regions)}"

    def test_region_entries_have_expected_keys(
        self, sample_image_red, sample_image_red_copy
    ):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        regions = vd.calculate_region_scores(img1, img2, 3, metric="pixel")
        for region in regions:
            assert "label" in region, "Region entry missing 'label' key"
            assert "score" in region, "Region entry missing 'score' key"
            assert "metric" in region, "Region entry missing 'metric' key"

    def test_identical_images_all_regions_100(
        self, sample_image_red, sample_image_red_copy
    ):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        regions = vd.calculate_region_scores(img1, img2, 4, metric="pixel")
        for region in regions:
            assert region["score"] == 100.0, \
                f"Region '{region['label']}' should be 100% for identical images, got {region['score']}"

    def test_top_region_detects_difference(
        self, sample_image_red, sample_image_slightly_different
    ):
        """The slightly-different image has blue pixels in top rows.
        The top region should have lower similarity than bottom regions."""
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_slightly_different)
        regions = vd.calculate_region_scores(img1, img2, 4, metric="pixel")
        # First region (top) covers rows 0-24, which includes the 5 different rows
        # Last region (bottom) should be 100% identical
        top_score = regions[0]["score"]
        bottom_score = regions[-1]["score"]
        assert bottom_score > top_score, \
            f"Bottom region ({bottom_score}%) should have higher similarity than top ({top_score}%)"

    def test_region_labels_include_top_and_bottom(
        self, sample_image_red, sample_image_red_copy
    ):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        regions = vd.calculate_region_scores(img1, img2, 4, metric="pixel")
        labels = [r["label"] for r in regions]
        assert any("top" in label.lower() for label in labels), \
            f"Expected a region labeled with 'top', got: {labels}"
        assert any("bottom" in label.lower() for label in labels), \
            f"Expected a region labeled with 'bottom', got: {labels}"

    @skip_without_skimage
    def test_region_analysis_with_ssim_metric(
        self, sample_image_red, sample_image_red_copy
    ):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        regions = vd.calculate_region_scores(img1, img2, 3, metric="ssim")
        for region in regions:
            assert region["metric"] == "ssim", \
                f"Expected metric='ssim', got '{region['metric']}'"
            assert abs(region["score"] - 1.0) < 0.001, \
                f"SSIM for identical region should be ~1.0, got {region['score']}"


# ---------------------------------------------------------------------------
# Threshold pass/fail logic tests
# ---------------------------------------------------------------------------

class TestThresholdLogic:
    """Tests for pass/fail threshold determination."""

    def test_pixel_pass_above_threshold(self, sample_image_red, sample_image_red_copy):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        similarity = vd.calculate_pixel_similarity(img1, img2)
        threshold = 95.0
        status = "pass" if similarity >= threshold else "fail"
        assert status == "pass", \
            f"100% similarity should pass threshold of {threshold}%"

    def test_pixel_fail_below_threshold(self, sample_image_red, sample_image_blue):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_blue)
        similarity = vd.calculate_pixel_similarity(img1, img2)
        threshold = 95.0
        status = "pass" if similarity >= threshold else "fail"
        assert status == "fail", \
            f"Very low similarity ({similarity}%) should fail threshold of {threshold}%"

    @skip_without_skimage
    def test_ssim_pass_above_threshold(self, sample_image_red, sample_image_red_copy):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        score, _ = vd.calculate_ssim(img1, img2)
        threshold = 0.95
        status = "pass" if score >= threshold else "fail"
        assert status == "pass", \
            f"SSIM {score} should pass threshold of {threshold}"

    @skip_without_skimage
    def test_ssim_fail_below_threshold(self, sample_image_red, sample_image_blue):
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_blue)
        score, _ = vd.calculate_ssim(img1, img2)
        threshold = 0.95
        status = "pass" if score >= threshold else "fail"
        assert status == "fail", \
            f"SSIM {score} should fail threshold of {threshold}"


# ---------------------------------------------------------------------------
# Different image size handling tests
# ---------------------------------------------------------------------------

class TestDifferentSizes:
    """Tests for handling images of different dimensions."""

    def test_pixel_similarity_handles_different_sizes(
        self, sample_image_red, sample_image_small
    ):
        """Should not crash when images have different dimensions."""
        img1 = Image.open(sample_image_red)   # 100x100
        img2 = Image.open(sample_image_small)  # 50x50
        similarity = vd.calculate_pixel_similarity(img1, img2)
        assert isinstance(similarity, float), "Should return a float"
        # Both are red, so after resize they should be very similar
        assert similarity > 90.0, \
            f"Resized same-color images should be similar, got {similarity}%"

    @skip_without_skimage
    def test_ssim_handles_different_sizes(self, sample_image_red, sample_image_small):
        """SSIM should handle images of different dimensions by resizing."""
        img1 = Image.open(sample_image_red)   # 100x100
        img2 = Image.open(sample_image_small)  # 50x50
        score, diff_map = vd.calculate_ssim(img1, img2)
        assert isinstance(score, float), "Should return a float score"
        # Both are red, so SSIM after resize should be very high
        assert score > 0.9, \
            f"Same-color images should have high SSIM after resize, got {score}"

    def test_region_analysis_handles_different_sizes(
        self, sample_image_red, sample_image_small
    ):
        """Region analysis should handle images of different dimensions."""
        img1 = Image.open(sample_image_red)   # 100x100
        img2 = Image.open(sample_image_small)  # 50x50
        regions = vd.calculate_region_scores(img1, img2, 4, metric="pixel")
        assert len(regions) == 4, f"Expected 4 regions, got {len(regions)}"
        for region in regions:
            assert isinstance(region["score"], float)


# ---------------------------------------------------------------------------
# Diff image generation tests
# ---------------------------------------------------------------------------

class TestDiffImageGeneration:
    """Tests for visual diff image generation."""

    def test_generate_diff_identical_images(self, sample_image_red, sample_image_red_copy):
        """Diff of identical images should produce an image with no red highlights."""
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_red_copy)
        diff = vd.generate_diff_image(img1, img2)
        assert isinstance(diff, Image.Image), "Should return a PIL Image"
        assert diff.size == img1.size, "Diff image should match input dimensions"

    def test_generate_diff_different_images(self, sample_image_red, sample_image_blue):
        """Diff of very different images should produce a non-empty diff."""
        img1 = Image.open(sample_image_red)
        img2 = Image.open(sample_image_blue)
        diff = vd.generate_diff_image(img1, img2)
        assert isinstance(diff, Image.Image), "Should return a PIL Image"
        assert diff.size == img1.size, "Diff image should match input dimensions"

    def test_generate_diff_handles_different_sizes(
        self, sample_image_red, sample_image_small
    ):
        """Diff should handle images of different sizes."""
        img1 = Image.open(sample_image_red)   # 100x100
        img2 = Image.open(sample_image_small)  # 50x50
        diff = vd.generate_diff_image(img1, img2)
        assert isinstance(diff, Image.Image), "Should return a PIL Image"
        # Output should match img1 size (the reference)
        assert diff.size == img1.size
