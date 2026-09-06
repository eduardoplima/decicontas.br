"""Package the dataset bundles as release assets.

Produces one self-contained zip per format under ``dist/``, so that a reader can
download a single small file from the GitHub release page instead of cloning the
repository. BRAT is included here even though ``dataset/release/*/brat/`` is
gitignored: it is regenerated on demand from the release bundles.

Each zip unpacks to::

    decicontas-<version>/
        README.md
        DATASHEET.md
        MANIFEST.json
        decicontas/<files for that format>
        decicontas-before-correction/<files for that format>

Usage::

    uv run python -m scripts.build_release_assets              # every format
    uv run python -m scripts.build_release_assets --only jsonl # just one
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.release import paths  # noqa: E402

VERSION = "1.0.0"
RELEASE_ROOT = paths.DATASET / "release"
BUNDLES = ("decicontas", "decicontas-before-correction")
DOCS = ("README.md", "DATASHEET.md", "MANIFEST.json")

# format -> the per-bundle files it needs (a directory name means "the whole tree")
FORMATS: dict[str, tuple[str, ...]] = {
    "json": ("decicontas.json",),
    "jsonl": ("decicontas.jsonl", "dataset_info.json"),
    "conll": ("decicontas.conll",),
    "brat": ("brat",),
    "labelstudio": ("decicontas-labelstudio.json",),
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _human(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def ensure_brat() -> None:
    """Regenerate the release bundles if the (gitignored) BRAT trees are absent."""
    missing = [b for b in BUNDLES if not (RELEASE_ROOT / b / "brat").is_dir()]
    if not missing:
        return
    print(f"BRAT trees missing for {', '.join(missing)}; rebuilding the bundles...")
    from research.release import export_dataset

    export_dataset.main()


def collect(fmt: str) -> list[tuple[Path, str]]:
    """Return (source path, archive name) pairs for one format."""
    items: list[tuple[Path, str]] = []
    root = f"decicontas-{VERSION}"
    for doc in DOCS:
        src = RELEASE_ROOT / doc
        if src.exists():
            items.append((src, f"{root}/{doc}"))
    for bundle in BUNDLES:
        for member in FORMATS[fmt]:
            src = RELEASE_ROOT / bundle / member
            if src.is_dir():
                for f in sorted(src.rglob("*")):
                    if f.is_file():
                        items.append((f, f"{root}/{bundle}/{f.relative_to(RELEASE_ROOT / bundle)}"))
            elif src.is_file():
                items.append((src, f"{root}/{bundle}/{member}"))
            else:
                raise FileNotFoundError(f"expected release file: {src}")
    return items


def build(fmt: str, out_dir: Path) -> Path:
    items = collect(fmt)
    out = out_dir / f"decicontas-{VERSION}-{fmt}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src, arcname in items:
            zf.write(src, arcname)
    print(f"  {out.name:38s} {_human(out.stat().st_size):>10s}  "
          f"{len(items):5d} files  sha256={_sha256(out)[:16]}…")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=sorted(FORMATS), help="build a single format")
    ap.add_argument("--out", type=Path, default=paths.REPO_ROOT / "dist")
    args = ap.parse_args()

    formats = [args.only] if args.only else list(FORMATS)
    if "brat" in formats:
        ensure_brat()

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"Building release assets v{VERSION} into {args.out}/")
    built = [build(fmt, args.out) for fmt in formats]

    checksums = {p.name: _sha256(p) for p in built}
    (args.out / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )
    print(f"\nWrote {len(built)} asset(s) + SHA256SUMS.txt")
    print("Attach them to the GitHub release; Zenodo archives the release as the DOI record.")


if __name__ == "__main__":
    main()
