"""Backfill uid and uid_confidence for all records missing those fields.

Usage:
    uv run python scripts/backfill_uid.py [--dry-run] [--verbose]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scholartools.config import load_settings
from scholartools.models import Reference
from scholartools.services.uid import compute_uid


def _backfill_file(path: Path, dry_run: bool, verbose: bool, force: bool) -> int:
    if not path.exists():
        if verbose:
            print(f"skip (not found): {path}")
        return 0

    records = json.loads(path.read_text())
    updated = 0

    for record in records:
        if record.get("uid") and not force:
            continue
        ref = Reference.model_validate(record)
        u, conf = compute_uid(ref)
        record["uid"] = u
        record["uid_confidence"] = conf
        updated += 1
        if verbose:
            print(f"  {record.get('id', '?')} → {u} ({conf})")

    if updated and not dry_run:
        path.write_text(json.dumps(records, indent=2, ensure_ascii=False))

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill uid for library and staging records"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="compute but do not write"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="print each updated record"
    )
    parser.add_argument(
        "--force", action="store_true", help="recompute uid even if already present"
    )
    args = parser.parse_args()

    s = load_settings()
    files = [s.local.library_file, s.local.staging_file]

    total = 0
    for path in files:
        if args.verbose:
            print(f"processing: {path}")
        count = _backfill_file(
            path, dry_run=args.dry_run, verbose=args.verbose, force=args.force
        )
        if args.verbose:
            print(f"  updated {count} record(s)")
        total += count

    suffix = " (dry run)" if args.dry_run else ""
    print(f"backfill complete{suffix}: {total} record(s) updated")


if __name__ == "__main__":
    main()
