"""Migrate an existing local library to a new directory and upload blobs to S3.

Usage:
    uv run python scripts/migrate_library.py --from-dir /old/library/dir
    uv run python scripts/migrate_library.py --from-dir /old/library/dir --upload-blobs
    uv run python scripts/migrate_library.py \\
        --from-dir /old/library/dir --upload-blobs --dry-run
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate scholartools library to remote-enabled dir"
    )
    parser.add_argument(
        "--from-dir", required=True, type=Path, help="Old library_dir path"
    )
    parser.add_argument(
        "--upload-blobs", action="store_true", help="Upload linked files to S3 blobs"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print actions without executing"
    )
    args = parser.parse_args()

    from_dir = args.from_dir.resolve()
    if not from_dir.exists():
        print(f"error: --from-dir does not exist: {from_dir}")
        sys.exit(1)

    import scholartools as st
    from scholartools.config import load_settings

    settings = load_settings()
    to_dir = settings.local.library_dir.resolve()

    if from_dir == to_dir:
        print("error: --from-dir and configured library_dir are the same")
        sys.exit(1)

    print(f"from : {from_dir}")
    print(f"to   : {to_dir}")
    print()

    src_lib = from_dir / "library.json"
    dst_lib = to_dir / "library.json"
    if not src_lib.exists():
        print(f"error: library.json not found in {from_dir}")
        sys.exit(1)

    if dst_lib.exists():
        print(f"warning: {dst_lib} already exists — will be overwritten")

    if not args.dry_run:
        to_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_lib, dst_lib)
    print(f"{'[dry-run] ' if args.dry_run else ''}copied library.json")

    src_files = from_dir / "files"
    dst_files = to_dir / "files"
    if src_files.exists():
        if not args.dry_run:
            if dst_files.exists():
                shutil.rmtree(dst_files)
            shutil.copytree(src_files, dst_files)
        print(f"{'[dry-run] ' if args.dry_run else ''}copied files/")
    else:
        print("no files/ directory found — skipping")

    src_staging = from_dir / "staging.json"
    dst_staging = to_dir / "staging.json"
    if src_staging.exists():
        if not args.dry_run:
            shutil.copy2(src_staging, dst_staging)
        print(f"{'[dry-run] ' if args.dry_run else ''}copied staging.json")

    src_staging_dir = from_dir / "staging"
    dst_staging_dir = to_dir / "staging"
    if src_staging_dir.exists():
        if not args.dry_run:
            if dst_staging_dir.exists():
                shutil.rmtree(dst_staging_dir)
            shutil.copytree(src_staging_dir, dst_staging_dir)
        print(f"{'[dry-run] ' if args.dry_run else ''}copied staging/")

    if not args.dry_run:
        st.reset()

    if not args.dry_run:
        print("\ncreating snapshot...")
        st.create_snapshot()
        print("snapshot uploaded")

    if args.upload_blobs:
        print("\nuploading blobs...")
        page = 1
        total = uploaded = skipped = errors = 0
        while True:
            result = st.list_references(page=page)
            for row in result.references:
                total += 1
                ref = st.get_reference(row.citekey).reference
                if not ref or not ref.file_record:
                    skipped += 1
                    continue
                file_path = ref.file_record.path
                if not Path(file_path).exists():
                    print(f"  missing file: {row.citekey} → {file_path}")
                    errors += 1
                    continue
                if args.dry_run:
                    print(f"  [dry-run] link_file {row.citekey} → {file_path}")
                    uploaded += 1
                    continue
                r = st.link_file(row.citekey, file_path)
                if r.ok:
                    uploaded += 1
                else:
                    print(f"  error: {row.citekey}: {r.error}")
                    errors += 1
            if page >= result.pages:
                break
            page += 1
        print(
            f"blobs: {uploaded} uploaded, {skipped} skipped (no file), "
            f"{errors} errors (of {total} records)"
        )

    if not args.dry_run:
        print("\npushing change log...")
        push_result = st.push()
        print(
            f"push: {push_result.entries_pushed} entries, "
            f"{len(push_result.errors)} errors"
        )
        if push_result.errors:
            for e in push_result.errors:
                print(f"  {e}")

    print("\ndone.")


if __name__ == "__main__":
    main()
