from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


_IMPORT_ERROR = (
    "Defacing reports require nibabel, nilearn, and nireports in the active "
    "Python environment. If you are using Python 3.9, install a Python-3.9-"
    "compatible nireports release because current nireports releases require "
    "Python 3.10+."
)


@dataclass(frozen=True)
class DefaceReportPaths:
    html: Path
    mosaic_svg: Path


def build_defacemask_stem(path: str | Path, source_suffix: str | None = None) -> str:
    stem = strip_image_suffix(path)
    suffix = source_suffix or stem.rsplit("_", 1)[-1]
    suffix_token = f"_{suffix}"
    if stem.endswith(suffix_token):
        stem = stem[: -len(suffix_token)]
    return f"{stem}_mod-{suffix}_defacemask"


def strip_image_suffix(path: str | Path) -> str:
    """Remove NIfTI suffixes while preserving the rest of the filename."""
    name = Path(path).name
    if name.endswith(".nii.gz"):
        return name[:-7]
    if name.endswith(".nii"):
        return name[:-4]
    return Path(name).stem


def build_report_paths(
    report_dir: str | Path,
    image_relpath: str | Path,
    source_suffix: str | None = None,
) -> DefaceReportPaths:
    relpath = Path(image_relpath)
    stem = build_defacemask_stem(relpath, source_suffix=source_suffix)
    report_dir = Path(report_dir)
    figures_dir = report_dir / "figures" / relpath.parent
    return DefaceReportPaths(
        html=report_dir / f"{stem}.html",
        mosaic_svg=figures_dir / f"{stem}.svg",
    )


def validate_nireports() -> None:
    _load_nireports_dependencies()


def write_deface_report(
    *,
    original_image: Any,
    mask_image: Any,
    report_dir: str | Path,
    image_relpath: str | Path,
    source_suffix: str | None = None,
    title: str | None = None,
) -> DefaceReportPaths:
    plot_mosaic = _load_nireports_dependencies()

    image_relpath = str(image_relpath)
    report_paths = build_report_paths(report_dir, image_relpath, source_suffix=source_suffix)
    report_paths.html.parent.mkdir(parents=True, exist_ok=True)
    report_paths.mosaic_svg.parent.mkdir(parents=True, exist_ok=True)

    report_title = title or build_defacemask_stem(image_relpath, source_suffix=source_suffix)

    with TemporaryDirectory(prefix="skullduggery-report-") as temp_dir:
        temp_dir_path = Path(temp_dir)
        original_path = temp_dir_path / "original.nii.gz"
        mask_path = temp_dir_path / "mask.nii.gz"
        original_image.to_filename(original_path)
        mask_image.to_filename(mask_path)

        plot_mosaic(
            str(original_path),
            out_file=str(report_paths.mosaic_svg),
            overlay_mask=str(mask_path),
            bbox_mask_file=str(mask_path),
            title=f"Defacing mask: {report_title}",
            views=("axial", "sagittal", "coronal"),
        )

    _write_report_page(report_paths, image_relpath=image_relpath, title=report_title)
    return report_paths


def _write_report_page(report_paths: DefaceReportPaths, *, image_relpath: str, title: str) -> None:
    mosaic_href = report_paths.mosaic_svg.relative_to(report_paths.html.parent).as_posix()
    report_paths.html.write_text(
        "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '  <meta charset="utf-8">',
                f"  <title>{escape(title)}</title>",
                "  <style>",
                "    body { font-family: sans-serif; margin: 2rem auto; max-width: 72rem; line-height: 1.5; }",
                "    h1, h2 { line-height: 1.2; }",
                "    section { margin-top: 2rem; }",
                "    object { width: 100%; min-height: 28rem; border: 0; }",
                "    code { font-size: 0.95rem; }",
                "  </style>",
                "</head>",
                "<body>",
                "  <main>",
                f"    <h1>{escape(title)}</h1>",
                f"    <p><code>{escape(image_relpath)}</code></p>",
                "    <section>",
                "      <h2>Defacing Mosaic</h2>",
                "      <p>The red overlay shows the warped defacing mask used for this image.</p>",
                f'      <object type="image/svg+xml" data="{escape(mosaic_href)}"></object>',
                "    </section>",
                "  </main>",
                "</body>",
                "</html>",
            ]
        ),
        encoding="utf-8",
    )


def _load_nireports_dependencies() -> Any:
    try:
        from nireports.reportlets.mosaic import plot_mosaic
    except ModuleNotFoundError as exc:
        raise RuntimeError(f"{_IMPORT_ERROR} Missing module: {exc.name}.") from exc

    return plot_mosaic
