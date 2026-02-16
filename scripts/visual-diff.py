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


def calculate_similarity(img1, img2):
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


def generate_html_report(results, output_dir):
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

    html_parts.append(f"<p class='summary'>{total} pages compared: "
                      f"{passed} passed, {failed} failed, {missing} missing</p>")

    html_parts.append("<table>")
    html_parts.append("<tr><th>Page</th><th>Similarity</th><th>Status</th></tr>")

    for r in results:
        name = r["name"]
        similarity = r.get("similarity", "N/A")
        status = r.get("status", "unknown")

        if isinstance(similarity, float):
            sim_str = f"{similarity:.1f}%"
        else:
            sim_str = str(similarity)

        status_class = status
        html_parts.append(
            f"<tr><td>{name}</td><td>{sim_str}</td>"
            f"<td><span class='status {status_class}'>{status.upper()}</span></td></tr>"
        )

    html_parts.append("</table>")

    # Detailed comparisons
    for r in results:
        name = r["name"]
        status = r.get("status", "unknown")
        similarity = r.get("similarity")

        html_parts.append("<div class='comparison'>")
        sim_str = f" - {similarity:.1f}%" if isinstance(similarity, float) else ""
        html_parts.append(f"<h2>{name}{sim_str} "
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
            html_parts.append("</div>")
        elif r.get("status") == "missing":
            html_parts.append("<p>No matching screenshot found for comparison.</p>")

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
        "--threshold", type=float, default=95.0,
        help="Similarity threshold for pass/fail (default: 95%%)"
    )
    args = parser.parse_args()

    if not os.path.isdir(args.original):
        print(f"Error: Original directory not found: {args.original}")
        sys.exit(1)

    if not os.path.isdir(args.clone):
        print(f"Error: Clone directory not found: {args.clone}")
        sys.exit(1)

    output_dir = Path(args.output)
    diff_images_dir = output_dir / "diffs"
    output_dir.mkdir(parents=True, exist_ok=True)
    diff_images_dir.mkdir(parents=True, exist_ok=True)

    # Copy originals and clones into report directory for relative links
    report_originals = output_dir / "originals"
    report_clones = output_dir / "clones"
    report_originals.mkdir(exist_ok=True)
    report_clones.mkdir(exist_ok=True)

    pairs = match_screenshots(args.original, args.clone)

    if not pairs:
        print("No screenshots found to compare.")
        sys.exit(0)

    print(f"Comparing {len(pairs)} page(s) with {args.threshold}% threshold...\n")
    print(f"{'Page':<40} {'Similarity':>10}  {'Status'}")
    print("-" * 62)

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

        similarity = calculate_similarity(orig_img, clone_img)
        status = "pass" if similarity >= args.threshold else "fail"
        print(f"{name:<40} {similarity:>9.1f}%  {status.upper()}")

        # Copy images into report dir
        import shutil
        orig_report = report_originals / orig_path.name
        clone_report = report_clones / clone_path.name
        shutil.copy2(orig_path, orig_report)
        shutil.copy2(clone_path, clone_report)

        entry = {
            "name": name,
            "similarity": similarity,
            "status": status,
            "original_rel": f"originals/{orig_path.name}",
            "clone_rel": f"clones/{clone_path.name}",
        }

        # Generate diff image if below threshold
        if similarity < 100.0:
            diff_img = generate_diff_image(orig_img, clone_img)
            diff_path = diff_images_dir / f"{name}_diff.png"
            diff_img.save(diff_path)
            entry["diff_rel"] = f"diffs/{name}_diff.png"

        results.append(entry)

    print("-" * 62)
    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = sum(1 for r in results if r.get("status") == "fail")
    missing = sum(1 for r in results if r.get("status") == "missing")

    print(f"\nSummary: {passed} passed, {failed} failed, {missing} missing "
          f"(threshold: {args.threshold}%)")

    report_path = generate_html_report(results, output_dir)
    print(f"Report: {report_path}")
    print("Done.")


if __name__ == "__main__":
    main()
