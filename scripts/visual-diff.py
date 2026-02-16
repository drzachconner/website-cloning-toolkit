#!/usr/bin/env python3
"""Compare original and clone screenshots, generating a visual diff report."""

import argparse
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

# Optional dependencies for SSIM scoring
_HAS_SSIM = False
try:
    import numpy as np
    from skimage.metrics import structural_similarity as ssim
    _HAS_SSIM = True
except ImportError:
    pass


def calculate_pixel_similarity(img1, img2):
    """Calculate pixel-level similarity percentage between two images."""
    # Resize to match if dimensions differ
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)

    # Convert to RGB for comparison
    img1_rgb = img1.convert("RGB")
    img2_rgb = img2.convert("RGB")

    pixels1 = list(img1_rgb.getdata())
    pixels2 = list(img2_rgb.getdata())

    total_pixels = len(pixels1)
    if total_pixels == 0:
        return 0.0

    matching = 0
    for p1, p2 in zip(pixels1, pixels2):
        # Consider pixels "matching" if they're within a small tolerance
        if all(abs(a - b) <= 10 for a, b in zip(p1, p2)):
            matching += 1

    return (matching / total_pixels) * 100


# Backward-compatible alias
calculate_similarity = calculate_pixel_similarity


def calculate_ssim(img1, img2):
    """Calculate SSIM between two PIL images. Returns (score, diff_map).

    The score is a float from 0.0 to 1.0 (1.0 = identical).
    The diff_map is a numpy array with per-pixel SSIM values (same shape as input).
    """
    if not _HAS_SSIM:
        raise RuntimeError(
            "scikit-image is required for SSIM. "
            "Install with: pip install scikit-image numpy"
        )

    # Resize to match if dimensions differ
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)

    arr1 = np.array(img1.convert("RGB"))
    arr2 = np.array(img2.convert("RGB"))

    score, diff_map = ssim(arr1, arr2, full=True, channel_axis=2)
    return score, diff_map


def generate_ssim_heatmap(diff_map):
    """Convert an SSIM diff_map to a visual heatmap image (blue=similar, red=different).

    Args:
        diff_map: numpy array of SSIM values (0.0-1.0) from calculate_ssim().

    Returns:
        PIL.Image in RGB mode showing the heatmap.
    """
    # diff_map values: 1.0 = identical, 0.0 = completely different
    # Average across color channels if multi-channel
    if diff_map.ndim == 3:
        similarity = np.mean(diff_map, axis=2)
    else:
        similarity = diff_map

    # Clamp to [0, 1]
    similarity = np.clip(similarity, 0.0, 1.0)

    # Map: 1.0 (similar) -> blue, 0.0 (different) -> red
    # Red channel: high when different (low similarity)
    # Blue channel: high when similar (high similarity)
    # Green channel: peaks in the middle for a smooth gradient
    height, width = similarity.shape
    heatmap = np.zeros((height, width, 3), dtype=np.uint8)

    heatmap[:, :, 0] = ((1.0 - similarity) * 255).astype(np.uint8)  # Red
    heatmap[:, :, 1] = (np.minimum(similarity, 1.0 - similarity) * 2 * 255).astype(np.uint8)  # Green
    heatmap[:, :, 2] = (similarity * 255).astype(np.uint8)  # Blue

    return Image.fromarray(heatmap, mode="RGB")


def calculate_region_scores(img1, img2, num_regions, metric="ssim"):
    """Divide images into horizontal bands and calculate similarity per region.

    Args:
        img1: Original PIL Image.
        img2: Clone PIL Image.
        num_regions: Number of horizontal bands to divide into.
        metric: 'ssim' or 'pixel'.

    Returns:
        List of dicts with keys: label, score, metric.
    """
    # Resize to match if dimensions differ
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)

    width, height = img1.size
    band_height = height // num_regions
    regions = []

    for i in range(num_regions):
        top = i * band_height
        # Last region takes any remaining pixels
        bottom = height if i == num_regions - 1 else (i + 1) * band_height

        crop_box = (0, top, width, bottom)
        region1 = img1.crop(crop_box)
        region2 = img2.crop(crop_box)

        if i == 0:
            label = f"Region {i + 1} (top)"
        elif i == num_regions - 1:
            label = f"Region {i + 1} (bottom)"
        else:
            label = f"Region {i + 1}"

        if metric == "ssim" and _HAS_SSIM:
            score, _ = calculate_ssim(region1, region2)
            regions.append({"label": label, "score": score, "metric": "ssim"})
        else:
            score = calculate_pixel_similarity(region1, region2)
            regions.append({"label": label, "score": score, "metric": "pixel"})

    return regions


def render_html_at_breakpoints(html_path, breakpoints, output_dir):
    """Render an HTML file at multiple viewport widths using Playwright.

    Args:
        html_path: Path to the HTML file.
        breakpoints: List of viewport widths (ints).
        output_dir: Directory to save screenshots.

    Returns:
        Dict mapping width -> Path to screenshot file.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Warning: Playwright is required for responsive testing. "
              "Install with: pip install playwright && python -m playwright install chromium")
        return {}

    html_path = Path(html_path).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    screenshots = {}
    file_url = f"file://{html_path}"
    stem = html_path.stem

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in breakpoints:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(file_url, wait_until="networkidle")
            screenshot_path = output_dir / f"{stem}-{width}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            screenshots[width] = screenshot_path
            page.close()
        browser.close()

    return screenshots


def generate_diff_image(img1, img2):
    """Generate a diff image highlighting differences in red."""
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)

    img1_rgb = img1.convert("RGB")
    img2_rgb = img2.convert("RGB")

    diff = ImageChops.difference(img1_rgb, img2_rgb)

    # Create highlight image: red where pixels differ
    width, height = img1.size
    highlight = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    diff_pixels = list(diff.getdata())

    highlight_data = []
    for pixel in diff_pixels:
        total_diff = sum(pixel)
        if total_diff > 30:  # Threshold for "different"
            alpha = min(255, total_diff * 2)
            highlight_data.append((255, 0, 0, alpha))
        else:
            highlight_data.append((0, 0, 0, 0))

    highlight.putdata(highlight_data)

    # Composite: original with red overlay for diffs
    base = img1_rgb.convert("RGBA")
    composite = Image.alpha_composite(base, highlight)
    return composite.convert("RGB")


def match_screenshots(original_dir, clone_dir):
    """Match original screenshots to clone screenshots by filename."""
    original_path = Path(original_dir)
    clone_path = Path(clone_dir)

    original_files = {}
    for f in original_path.iterdir():
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            original_files[f.stem] = f

    clone_files = {}
    for f in clone_path.iterdir():
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            clone_files[f.stem] = f

    pairs = []
    matched_clones = set()

    for name, orig_file in sorted(original_files.items()):
        if name in clone_files:
            pairs.append((orig_file, clone_files[name]))
            matched_clones.add(name)
        else:
            pairs.append((orig_file, None))

    for name, clone_file in sorted(clone_files.items()):
        if name not in matched_clones:
            pairs.append((None, clone_file))

    return pairs


def generate_html_report(results, output_dir, metric="ssim", responsive_results=None):
    """Generate an HTML report with side-by-side comparisons."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>Visual Diff Report</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; ",
        "  margin: 0; padding: 20px; background: #f5f5f5; color: #333; }",
        "h1 { text-align: center; margin-bottom: 10px; }",
        ".summary { text-align: center; margin-bottom: 30px; color: #666; }",
        ".comparison { background: #fff; border-radius: 8px; padding: 20px; ",
        "  margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }",
        ".comparison h2 { margin-top: 0; }",
        ".status { display: inline-block; padding: 2px 10px; border-radius: 12px; ",
        "  font-size: 13px; font-weight: bold; }",
        ".pass { background: #d4edda; color: #155724; }",
        ".fail { background: #f8d7da; color: #721c24; }",
        ".missing { background: #fff3cd; color: #856404; }",
        ".images { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }",
        ".images figure { flex: 1; min-width: 200px; margin: 0; text-align: center; }",
        ".images img { max-width: 100%; height: auto; border: 1px solid #ddd; }",
        ".images figcaption { font-size: 12px; color: #666; margin-top: 5px; }",
        "table { width: 100%; border-collapse: collapse; margin: 20px 0; }",
        "th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #ddd; }",
        "th { background: #f8f9fa; }",
        ".region-table { margin-top: 15px; }",
        ".region-table td.score { font-family: monospace; }",
        ".responsive-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); ",
        "  gap: 15px; margin-top: 15px; }",
        ".responsive-grid figure { margin: 0; text-align: center; background: #f8f9fa; ",
        "  border-radius: 4px; padding: 10px; }",
        ".responsive-grid img { max-width: 100%; height: auto; border: 1px solid #ddd; }",
        ".responsive-grid figcaption { font-size: 12px; color: #666; margin-top: 5px; }",
        "h3 { margin-top: 20px; margin-bottom: 10px; color: #555; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Visual Diff Report</h1>",
    ]

    # Summary table
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = sum(1 for r in results if r.get("status") == "fail")
    missing = sum(1 for r in results if r.get("status") == "missing")

    metric_label = "SSIM" if metric == "ssim" else "Pixel"
    html_parts.append(f"<p class='summary'>{total} pages compared: "
                      f"{passed} passed, {failed} failed, {missing} missing "
                      f"(primary metric: {metric_label})</p>")

    # Summary table with both metrics
    html_parts.append("<table>")
    header_cols = "<tr><th>Page</th><th>Pixel Similarity</th>"
    if any(r.get("ssim_score") is not None for r in results):
        header_cols += "<th>SSIM Score</th>"
    header_cols += "<th>Status</th></tr>"
    html_parts.append(header_cols)

    for r in results:
        name = r["name"]
        similarity = r.get("similarity", "N/A")
        ssim_score = r.get("ssim_score")
        status = r.get("status", "unknown")

        if isinstance(similarity, float):
            sim_str = f"{similarity:.1f}%"
        else:
            sim_str = str(similarity)

        ssim_str = f"{ssim_score:.4f}" if ssim_score is not None else "N/A"

        status_class = status
        row = f"<tr><td>{name}</td><td>{sim_str}</td>"
        if any(r2.get("ssim_score") is not None for r2 in results):
            row += f"<td>{ssim_str}</td>"
        row += f"<td><span class='status {status_class}'>{status.upper()}</span></td></tr>"
        html_parts.append(row)

    html_parts.append("</table>")

    # Detailed comparisons
    for r in results:
        name = r["name"]
        status = r.get("status", "unknown")
        similarity = r.get("similarity")
        ssim_score = r.get("ssim_score")

        html_parts.append("<div class='comparison'>")

        # Build header with scores
        score_parts = []
        if isinstance(similarity, float):
            score_parts.append(f"Pixel: {similarity:.1f}%")
        if ssim_score is not None:
            score_parts.append(f"SSIM: {ssim_score:.4f}")
        score_str = f" - {', '.join(score_parts)}" if score_parts else ""

        html_parts.append(f"<h2>{name}{score_str} "
                          f"<span class='status {status}'>{status.upper()}</span></h2>")

        if r.get("original_rel") and r.get("clone_rel"):
            html_parts.append("<div class='images'>")
            html_parts.append(f"<figure><img src='{r['original_rel']}' alt='Original'>"
                              f"<figcaption>Original</figcaption></figure>")
            html_parts.append(f"<figure><img src='{r['clone_rel']}' alt='Clone'>"
                              f"<figcaption>Clone</figcaption></figure>")
            if r.get("diff_rel"):
                html_parts.append(f"<figure><img src='{r['diff_rel']}' alt='Diff'>"
                                  f"<figcaption>Diff (red = changed)</figcaption></figure>")
            if r.get("heatmap_rel"):
                html_parts.append(f"<figure><img src='{r['heatmap_rel']}' alt='SSIM Heatmap'>"
                                  f"<figcaption>SSIM Heatmap (blue = similar, red = different)"
                                  f"</figcaption></figure>")
            html_parts.append("</div>")
        elif r.get("status") == "missing":
            html_parts.append("<p>No matching screenshot found for comparison.</p>")

        # Region breakdown table
        regions = r.get("regions")
        if regions:
            html_parts.append("<h3>Region Breakdown</h3>")
            html_parts.append("<table class='region-table'>")
            html_parts.append("<tr><th>Region</th><th>Score</th><th>Metric</th></tr>")
            for region in regions:
                if region["metric"] == "ssim":
                    score_display = f"{region['score']:.4f}"
                else:
                    score_display = f"{region['score']:.1f}%"
                html_parts.append(
                    f"<tr><td>{region['label']}</td>"
                    f"<td class='score'>{score_display}</td>"
                    f"<td>{region['metric'].upper()}</td></tr>"
                )
            html_parts.append("</table>")

        html_parts.append("</div>")

    # Responsive comparison section
    if responsive_results:
        html_parts.append("<div class='comparison'>")
        html_parts.append("<h2>Responsive Comparisons</h2>")

        for page_name, breakpoint_data in responsive_results.items():
            html_parts.append(f"<h3>{page_name}</h3>")
            html_parts.append("<div class='responsive-grid'>")

            for bp_info in breakpoint_data:
                width = bp_info["width"]
                clone_rel = bp_info.get("clone_rel")
                orig_rel = bp_info.get("original_rel")
                bp_score = bp_info.get("score")
                bp_metric = bp_info.get("metric", "pixel")

                if bp_score is not None:
                    if bp_metric == "ssim":
                        score_label = f"SSIM: {bp_score:.4f}"
                    else:
                        score_label = f"Pixel: {bp_score:.1f}%"
                else:
                    score_label = ""

                if clone_rel:
                    html_parts.append(
                        f"<figure><img src='{clone_rel}' alt='Clone at {width}px'>"
                        f"<figcaption>{width}px {score_label}</figcaption></figure>"
                    )

                if orig_rel:
                    html_parts.append(
                        f"<figure><img src='{orig_rel}' alt='Original at {width}px'>"
                        f"<figcaption>Original {width}px</figcaption></figure>"
                    )

            html_parts.append("</div>")

        html_parts.append("</div>")

    html_parts.extend(["</body>", "</html>"])

    report_path = Path(output_dir) / "index.html"
    report_path.write_text("\n".join(html_parts), encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Compare original and clone screenshots, generating a visual diff report."
    )
    parser.add_argument(
        "--original", required=True, help="Directory containing original screenshots"
    )
    parser.add_argument(
        "--clone", required=True, help="Directory containing clone screenshots"
    )
    parser.add_argument(
        "--output", required=True, help="Output directory for diff report and images"
    )
    parser.add_argument(
        "--threshold", type=float, default=None,
        help="Similarity threshold for pass/fail. Default: 0.95 for SSIM, 95.0 for pixel"
    )
    parser.add_argument(
        "--metric", choices=["ssim", "pixel"], default="ssim",
        help="Primary comparison metric (default: ssim)"
    )
    parser.add_argument(
        "--responsive", action="store_true",
        help="Enable responsive testing at multiple viewport widths"
    )
    parser.add_argument(
        "--breakpoints", type=str, default="320,768,1024,1440",
        help="Comma-separated viewport widths for responsive testing (default: 320,768,1024,1440)"
    )
    parser.add_argument(
        "--regions", type=int, default=4,
        help="Number of horizontal regions for region-based analysis (default: 4)"
    )
    args = parser.parse_args()

    # Resolve metric and threshold
    metric = args.metric
    if metric == "ssim" and not _HAS_SSIM:
        print("Warning: scikit-image not installed. Falling back to pixel comparison.")
        print("  Install with: pip install scikit-image numpy")
        metric = "pixel"

    if args.threshold is not None:
        threshold = args.threshold
    else:
        threshold = 0.95 if metric == "ssim" else 95.0

    # Parse breakpoints
    breakpoints = [int(b.strip()) for b in args.breakpoints.split(",")]

    if not os.path.isdir(args.original):
        print(f"Error: Original directory not found: {args.original}")
        sys.exit(1)

    if not os.path.isdir(args.clone):
        print(f"Error: Clone directory not found: {args.clone}")
        sys.exit(1)

    output_dir = Path(args.output)
    diff_images_dir = output_dir / "diffs"
    heatmaps_dir = output_dir / "heatmaps"
    output_dir.mkdir(parents=True, exist_ok=True)
    diff_images_dir.mkdir(parents=True, exist_ok=True)
    heatmaps_dir.mkdir(parents=True, exist_ok=True)

    # Copy originals and clones into report directory for relative links
    report_originals = output_dir / "originals"
    report_clones = output_dir / "clones"
    report_originals.mkdir(exist_ok=True)
    report_clones.mkdir(exist_ok=True)

    pairs = match_screenshots(args.original, args.clone)

    if not pairs:
        print("No screenshots found to compare.")
        sys.exit(0)

    # Build console output header
    metric_label = "SSIM" if metric == "ssim" else "Pixel"
    threshold_str = f"{threshold:.4f}" if metric == "ssim" else f"{threshold:.1f}%"
    print(f"Comparing {len(pairs)} page(s) with {metric_label} threshold {threshold_str}...\n")

    header = f"{'Page':<40} {'Pixel %':>10}"
    if _HAS_SSIM:
        header += f"  {'SSIM':>8}"
    header += f"  {'Status'}"
    print(header)
    print("-" * (72 if _HAS_SSIM else 62))

    results = []

    for orig_path, clone_path in pairs:
        name = (orig_path or clone_path).stem

        if orig_path is None:
            print(f"{name:<40} {'N/A':>10}  MISSING (no original)")
            results.append({"name": name, "status": "missing", "similarity": "N/A"})
            continue

        if clone_path is None:
            print(f"{name:<40} {'N/A':>10}  MISSING (no clone)")
            results.append({"name": name, "status": "missing", "similarity": "N/A"})
            continue

        try:
            orig_img = Image.open(orig_path)
            clone_img = Image.open(clone_path)
        except Exception as e:
            print(f"{name:<40} {'ERROR':>10}  {e}")
            results.append({"name": name, "status": "fail", "similarity": 0.0})
            continue

        # Always calculate pixel similarity
        pixel_similarity = calculate_pixel_similarity(orig_img, clone_img)

        # Calculate SSIM if available
        ssim_score = None
        ssim_diff_map = None
        if _HAS_SSIM:
            try:
                ssim_score, ssim_diff_map = calculate_ssim(orig_img, clone_img)
            except Exception as e:
                print(f"  Warning: SSIM calculation failed for {name}: {e}")

        # Determine pass/fail based on selected metric
        if metric == "ssim" and ssim_score is not None:
            status = "pass" if ssim_score >= threshold else "fail"
        else:
            status = "pass" if pixel_similarity >= threshold else "fail"

        # Console output
        line = f"{name:<40} {pixel_similarity:>9.1f}%"
        if _HAS_SSIM:
            ssim_display = f"{ssim_score:.4f}" if ssim_score is not None else "  N/A"
            line += f"  {ssim_display:>8}"
        line += f"  {status.upper()}"
        print(line)

        # Copy images into report dir
        import shutil
        orig_report = report_originals / orig_path.name
        clone_report = report_clones / clone_path.name
        shutil.copy2(orig_path, orig_report)
        shutil.copy2(clone_path, clone_report)

        entry = {
            "name": name,
            "similarity": pixel_similarity,
            "ssim_score": ssim_score,
            "status": status,
            "original_rel": f"originals/{orig_path.name}",
            "clone_rel": f"clones/{clone_path.name}",
        }

        # Generate diff image if below 100% pixel similarity
        if pixel_similarity < 100.0:
            diff_img = generate_diff_image(orig_img, clone_img)
            diff_path = diff_images_dir / f"{name}_diff.png"
            diff_img.save(diff_path)
            entry["diff_rel"] = f"diffs/{name}_diff.png"

        # Generate SSIM heatmap if available
        if ssim_diff_map is not None:
            heatmap_img = generate_ssim_heatmap(ssim_diff_map)
            heatmap_path = heatmaps_dir / f"{name}_heatmap.png"
            heatmap_img.save(heatmap_path)
            entry["heatmap_rel"] = f"heatmaps/{name}_heatmap.png"

        # Region-based analysis
        if args.regions > 1:
            regions = calculate_region_scores(
                orig_img, clone_img, args.regions, metric=metric
            )
            entry["regions"] = regions

        results.append(entry)

    print("-" * (72 if _HAS_SSIM else 62))
    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = sum(1 for r in results if r.get("status") == "fail")
    missing = sum(1 for r in results if r.get("status") == "missing")

    print(f"\nSummary: {passed} passed, {failed} failed, {missing} missing "
          f"(metric: {metric_label}, threshold: {threshold_str})")

    # Region summary to console
    for r in results:
        regions = r.get("regions")
        if regions:
            print(f"\n  Region breakdown for {r['name']}:")
            for region in regions:
                if region["metric"] == "ssim":
                    print(f"    {region['label']:<25} SSIM: {region['score']:.4f}")
                else:
                    print(f"    {region['label']:<25} Pixel: {region['score']:.1f}%")

    # Responsive testing
    responsive_results = {}
    if args.responsive:
        print(f"\nResponsive testing at breakpoints: {breakpoints}")
        clone_path = Path(args.clone)
        original_path = Path(args.original)
        responsive_dir = output_dir / "responsive"
        responsive_dir.mkdir(parents=True, exist_ok=True)

        # Find HTML files in the clone directory
        html_files = list(clone_path.glob("*.html")) + list(clone_path.glob("*.htm"))

        if not html_files:
            print("  No HTML files found in clone directory for responsive testing.")
            print("  Responsive testing requires HTML files (not PNGs) in --clone directory.")
        else:
            for html_file in html_files:
                page_name = html_file.stem
                print(f"  Rendering {page_name} at {len(breakpoints)} breakpoints...")

                page_responsive_dir = responsive_dir / page_name
                screenshots = render_html_at_breakpoints(
                    html_file, breakpoints, page_responsive_dir
                )

                if not screenshots:
                    print(f"    Skipped (Playwright not available)")
                    continue

                breakpoint_data = []
                for width, screenshot_path in sorted(screenshots.items()):
                    # Copy screenshot into report dir
                    import shutil
                    responsive_report_dir = output_dir / "responsive_report" / page_name
                    responsive_report_dir.mkdir(parents=True, exist_ok=True)
                    report_screenshot = responsive_report_dir / screenshot_path.name
                    shutil.copy2(screenshot_path, report_screenshot)

                    bp_entry = {
                        "width": width,
                        "clone_rel": f"responsive_report/{page_name}/{screenshot_path.name}",
                    }

                    # Look for matching original screenshot with responsive naming
                    orig_responsive = original_path / f"{page_name}-{width}.png"
                    if not orig_responsive.exists():
                        # Fall back to the single original screenshot
                        orig_candidates = list(original_path.glob(f"{page_name}.*"))
                        orig_responsive = orig_candidates[0] if orig_candidates else None

                    if orig_responsive and orig_responsive.exists():
                        # Copy original responsive screenshot
                        orig_resp_report = responsive_report_dir / f"orig-{orig_responsive.name}"
                        shutil.copy2(orig_responsive, orig_resp_report)
                        bp_entry["original_rel"] = (
                            f"responsive_report/{page_name}/orig-{orig_responsive.name}"
                        )

                        # Compare
                        try:
                            clone_img = Image.open(screenshot_path)
                            orig_img = Image.open(orig_responsive)

                            if metric == "ssim" and _HAS_SSIM:
                                score, _ = calculate_ssim(orig_img, clone_img)
                                bp_entry["score"] = score
                                bp_entry["metric"] = "ssim"
                                score_display = f"SSIM: {score:.4f}"
                            else:
                                score = calculate_pixel_similarity(orig_img, clone_img)
                                bp_entry["score"] = score
                                bp_entry["metric"] = "pixel"
                                score_display = f"Pixel: {score:.1f}%"

                            print(f"    {width}px: {score_display}")
                        except Exception as e:
                            print(f"    {width}px: Error comparing - {e}")
                    else:
                        print(f"    {width}px: Screenshot captured (no original for comparison)")

                    breakpoint_data.append(bp_entry)

                responsive_results[page_name] = breakpoint_data

    report_path = generate_html_report(
        results, output_dir, metric=metric, responsive_results=responsive_results
    )
    print(f"\nReport: {report_path}")
    print("Done.")


if __name__ == "__main__":
    main()
