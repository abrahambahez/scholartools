from pathlib import Path

from pydantic import ValidationError

from scholartools.models import (
    AddResult,
    DeleteResult,
    GetResult,
    LibraryCtx,
    ListResult,
    Reference,
    RenameResult,
    UpdateResult,
)
from scholartools.services import citekeys
from scholartools.services.list_helpers import paginate, to_reference_row

_REQUIRED = ("id", "type", "title", "author", "issued")


async def add_reference(ref: dict, ctx: LibraryCtx) -> AddResult:
    records = await ctx.read_all()
    existing_ids = {r["id"] for r in records if "id" in r}

    if "id" not in ref or not ref["id"]:
        key = citekeys.generate(ref, ctx.citekey_settings)
        key = citekeys.resolve_collision(key, existing_ids, ctx.citekey_settings, ref)
        ref = {**ref, "id": key}
    elif ref["id"] in existing_ids:
        return AddResult(error=f"duplicate citekey: {ref['id']}")

    try:
        Reference.model_validate(ref)
    except ValidationError as e:
        return AddResult(error=str(e))

    records.append(ref)
    await ctx.write_all(records)
    return AddResult(citekey=ref["id"])


async def get_reference(
    ctx: LibraryCtx, citekey: str | None = None, uid: str | None = None
) -> GetResult:
    if (citekey is None) == (uid is None):
        return GetResult(error="provide exactly one of citekey or uid")
    records = await ctx.read_all()
    for r in records:
        if citekey is not None and r.get("id") == citekey:
            return GetResult(reference=_to_reference(r))
        if uid is not None and r.get("uid") == uid:
            return GetResult(reference=_to_reference(r))
    term = citekey or uid
    return GetResult(error=f"not found: {term}")


async def update_reference(citekey: str, fields: dict, ctx: LibraryCtx) -> UpdateResult:
    if "id" in fields and fields["id"] != citekey:
        return UpdateResult(error="use rename_reference to change a citekey")

    records = await ctx.read_all()
    for i, r in enumerate(records):
        if r.get("id") == citekey:
            records[i] = {**r, **fields, "id": citekey}
            await ctx.write_all(records)
            return UpdateResult(citekey=citekey)

    return UpdateResult(error=f"not found: {citekey}")


async def rename_reference(old_key: str, new_key: str, ctx: LibraryCtx) -> RenameResult:
    records = await ctx.read_all()
    existing_ids = {r["id"] for r in records if "id" in r}

    if old_key not in existing_ids:
        return RenameResult(error=f"not found: {old_key}")
    if new_key in existing_ids:
        return RenameResult(error=f"citekey already exists: {new_key}")

    for i, r in enumerate(records):
        if r.get("id") == old_key:
            updated = {**r, "id": new_key}
            if "_file" in updated:
                old_path = updated["_file"].get("path", "")
                if Path(old_path).stem == old_key:
                    new_path = str(Path(old_path).with_stem(new_key))
                    updated["_file"] = {**updated["_file"], "path": new_path}
            records[i] = updated
            await ctx.write_all(records)
            return RenameResult(old_key=old_key, new_key=new_key)

    return RenameResult(error=f"not found: {old_key}")


async def delete_reference(citekey: str, ctx: LibraryCtx) -> DeleteResult:
    records = await ctx.read_all()
    filtered = [r for r in records if r.get("id") != citekey]
    if len(filtered) == len(records):
        return DeleteResult(deleted=False, error=f"not found: {citekey}")
    await ctx.write_all(filtered)
    return DeleteResult(deleted=True)


async def filter_references(
    ctx: LibraryCtx,
    query: str | None = None,
    author: str | None = None,
    year: int | None = None,
    ref_type: str | None = None,
    has_file: bool | None = None,
    staging: bool = False,
    page: int = 1,
) -> ListResult:
    read = ctx.staging_read_all if staging else ctx.read_all
    records = await read()
    if query:
        q = query.lower()
        records = [r for r in records if q in (r.get("title") or "").lower()]
    if author:
        a = author.lower()
        records = [r for r in records if _author_matches(r, a)]
    if year is not None:
        records = [r for r in records if _get_year(r) == year]
    if ref_type is not None:
        records = [r for r in records if r.get("type") == ref_type]
    if has_file is not None:
        records = [r for r in records if ("_file" in r) == has_file]
    sorted_records = sorted(records, key=lambda r: r.get("id", ""))
    rows = [to_reference_row(r) for r in sorted_records]
    items, page, pages = paginate(rows, page)
    return ListResult(references=items, total=len(rows), page=page, pages=pages)


def _author_matches(record: dict, query: str) -> bool:
    for a in record.get("author") or []:
        family = (a.get("family") or "").lower()
        given = (a.get("given") or "").lower()
        literal = (a.get("literal") or "").lower()
        full = f"{given} {family}".strip()
        if any(query in s for s in (family, given, literal, full)):
            return True
    return False


def _get_year(record: dict) -> int | None:
    issued = record.get("issued") or {}
    parts = issued.get("date-parts") or []
    if parts and parts[0]:
        return parts[0][0]
    return None


async def list_references(ctx: LibraryCtx, page: int = 1) -> ListResult:
    records = await ctx.read_all()
    sorted_records = sorted(records, key=lambda r: r.get("id", ""))
    rows = [to_reference_row(r) for r in sorted_records]
    items, page, pages = paginate(rows, page)
    return ListResult(references=items, total=len(rows), page=page, pages=pages)


def _to_reference(record: dict) -> Reference:
    ref = Reference.model_validate(record)
    missing = [f for f in _REQUIRED if not record.get(f)]
    if missing:
        ref.warnings = [f"missing: {f}" for f in missing]
    return ref
