import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from scholartools.models import (
    DeleteStagedResult,
    FileRecord,
    LibraryCtx,
    ListStagedResult,
    Reference,
    StageResult,
)
from scholartools.services import citekeys
from scholartools.services.list_helpers import paginate, to_reference_row


async def stage_reference(
    ref: Reference, file_path: Path | None, ctx: LibraryCtx
) -> StageResult:
    try:
        records = await ctx.staging_read_all()
        existing_ids = {r["id"] for r in records if "id" in r}

        ref_dict = ref.model_dump(by_alias=True, exclude_none=True)
        ref_dict.pop("_warnings", None)

        key = citekeys.generate(ref_dict)
        key = citekeys.resolve_collision(key, existing_ids)
        ref_dict["id"] = key
        ref_dict["added_at"] = datetime.now(timezone.utc).isoformat()

        if file_path is not None:
            src = Path(file_path).resolve()
            dest = str(Path(ctx.staging_dir) / src.name)
            await ctx.staging_copy_file(str(src), dest)
            mime, _ = mimetypes.guess_type(str(src))
            ref_dict["_file"] = FileRecord(
                path=dest,
                mime_type=mime or "application/octet-stream",
                size_bytes=src.stat().st_size,
                added_at=datetime.now(timezone.utc).isoformat(),
            ).model_dump()

        records.append(ref_dict)
        await ctx.staging_write_all(records)
        return StageResult(citekey=key)
    except Exception as exc:
        return StageResult(error=str(exc))


async def list_staged(ctx: LibraryCtx, page: int = 1) -> ListStagedResult:
    try:
        records = await ctx.staging_read_all()
        sorted_records = sorted(records, key=lambda r: r.get("id", ""))
        rows = [to_reference_row(r) for r in sorted_records]
        items, page, pages = paginate(rows, page)
        return ListStagedResult(
            references=items, total=len(rows), page=page, pages=pages
        )
    except Exception:
        return ListStagedResult(references=[], total=0)


async def delete_staged(citekey: str, ctx: LibraryCtx) -> DeleteStagedResult:
    try:
        records = await ctx.staging_read_all()
        target = next((r for r in records if r.get("id") == citekey), None)
        if target is None:
            return DeleteStagedResult(deleted=False, error=f"not found: {citekey}")

        file_path = None
        if file_rec := target.get("_file"):
            file_path = file_rec.get("path")

        filtered = [r for r in records if r.get("id") != citekey]
        await ctx.staging_write_all(filtered)

        if file_path:
            await ctx.staging_delete_file(file_path)

        return DeleteStagedResult(deleted=True)
    except Exception as exc:
        return DeleteStagedResult(deleted=False, error=str(exc))
