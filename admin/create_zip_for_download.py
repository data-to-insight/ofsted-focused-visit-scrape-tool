#!/usr/bin/env python3

"""
Create zip of repo ./docs folder, with repo name as the root folder inside the zip
This grabs everything incl private sections so we can also make edits locally if easier for some
- obv careful when saving not to overwrite existing in case people have made edits locally not yet in repo! 

Default out: repo_root/dev/<DATESTAMP>_<REPO>_docs.zip
Inside zip: <REPO>/<docs_subfolders_and_files...>
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None


def find_repo_root(start: Path) -> Path:
    # 1) try git (best)
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start),
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(r.stdout.strip()).resolve()
    except Exception:
        pass

    # 2) walk up looking for .git
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".git").exists():
            return p
    raise RuntimeError("Could not find repo root (no git and no .git folder found)")


def london_now_stamp() -> str:
    if ZoneInfo is not None:
        try:
            now = datetime.now(ZoneInfo("Europe/London"))
            return now.strftime("%Y%m%d") # or ("%Y%m%d_%H%M%S")
        except Exception:
            pass
    return datetime.now().strftime("%Y%m%d")


def should_skip(path: Path) -> bool:
    name = path.name
    if name in {".DS_Store", "Thumbs.db"}:
        return True
    if "__pycache__" in path.parts:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--docs-dir",
        default=None,
        help="Docs folder to zip default is <repo_root>/export_data/inspection_reports",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Where to write zip default is <repo_root>/",
    )
    ap.add_argument(
        "--stamp",
        default=None,
        help="Override datestamp prefix default EU-Ldn time",
    )
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = find_repo_root(script_dir)
    repo_name = repo_root.name

    docs_dir = Path(args.docs_dir).resolve() if args.docs_dir else (repo_root / "export_data/inspection_reports")
    if not docs_dir.exists() or not docs_dir.is_dir():
        raise FileNotFoundError(f"export_data/inspection_reports folder not found: {docs_dir}")

    out_dir = Path(args.out_dir).resolve() if args.out_dir else (repo_root / "")
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = args.stamp or london_now_stamp()
    zip_path = out_dir / f"{stamp}_{repo_name}.zip"

    files_added = 0
    dirs_added = 0

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as z:
        for p in sorted(docs_dir.rglob("*")):
            if should_skip(p):
                continue

            rel = p.relative_to(docs_dir)

            # arcname inside zip start with repo name not mkdocs default docs/
            # makes it a bit cleaner locally
            # arc = PurePosixPath(repo_name) / PurePosixPath(rel.as_posix())

            # without repo name to avoid the zip folder name doubling name\name
            arc = PurePosixPath(rel.as_posix())

            if p.is_dir():
                # keep empty dirs (i want to see full structure regardless)
                if not any(p.iterdir()):
                    z.writestr(str(arc) + "/", "")
                    dirs_added += 1
                continue

            if p.is_file():
                z.write(p, arcname=str(arc))
                files_added += 1

    print(f"Created: {zip_path}")
    print(f"Added files: {files_added}, empty dirs also kept: {dirs_added}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise