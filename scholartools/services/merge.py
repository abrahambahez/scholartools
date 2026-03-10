from pathlib import Path

from scholartools.models import DateField, LibraryCtx, MergeResult, Reference
from scholartools.services.duplicates import is_duplicate

_REQUIRED = ("id", "type", "title", "author", "issued")

_BIBTEX_MAP = {
    "journal": "container-title",
    "booktitle": "container-title",
    "pages": "page",
}


def _normalize_fields(record: dict) -> dict:
    ref = Reference.model_validate(record)
    known = ref.model_fields_set | {
        "id",
        "type",
        "title",
        "author",
        "issued",
        "DOI",
        "URL",
        "added_at",
        "_file",
        "_warnings",
    }
    extra = ref.model_extra or {}

    mapped: dict = {}
    for bibtex_key, csl_key in _BIBTEX_MAP.items():
        if bibtex_key in extra and csl_key not in extra:
            mapped[csl_key] = extra[bibtex_key]

    if "year" in extra and not record.get("issued"):
        try:
            year = int(extra["year"])
            mapped["issued"] = DateField(**{"date-parts": [[year]]}).model_dump(
                by_alias=True, exclude_none=True
            )
        except (ValueError, TypeError):
            pass

    clean = ref.model_dump(mode="json", by_alias=True, exclude_none=True)
    clean.pop("_warnings", None)
    for bibtex_key in _BIBTEX_MAP:
        clean.pop(bibtex_key, None)
    clean.pop("year", None)
    clean.update(mapped)
    return clean


def _validate_schema(record: dict) -> str | None:
    for field in _REQUIRED:
        if not record.get(field):
            return f"missing required field: {field}"
    return None


async def merge(omit: list[str] | None, ctx: LibraryCtx) -> MergeResult:
    try:
        staged_records = await ctx.staging_read_all()
        library_records = await ctx.read_all()
    except Exception as exc:
        return MergeResult(promoted=[], errors={"_load": str(exc)}, skipped=[])

    omit_set = set(omit or [])
    library_refs = [Reference.model_validate(r) for r in library_records]

    promoted_keys: list[str] = []
    errors: dict[str, str] = {}
    skipped: list[str] = []
    promoted_records: list[dict] = []
    files_to_delete: list[str] = []

    for record in staged_records:
        citekey = record.get("id", "")

        if citekey in omit_set:
            skipped.append(citekey)
            continue

        normalized = _normalize_fields(record)

        ref = Reference.model_validate(normalized)
        dup_key = is_duplicate(ref, library_refs)
        if dup_key:
            errors[citekey] = f"duplicate of {dup_key}"
            continue

        schema_error = _validate_schema(normalized)
        if schema_error:
            errors[citekey] = schema_error
            continue

        file_path: str | None = None
        if file_rec := normalized.get("_file"):
            file_path = file_rec.get("path")

        if file_path:
            src = file_path
            dest = str(Path(ctx.files_dir) / f"{citekey}{Path(file_path).suffix}")
            try:
                await ctx.copy_file(src, dest)
                normalized["_file"] = {**normalized["_file"], "path": dest}
                files_to_delete.append(src)
            except Exception as exc:
                errors[citekey] = f"file archival failed: {exc}"
                continue

        promoted_keys.append(citekey)
        promoted_records.append(normalized)

    if promoted_records:
        promoted_ids = {r["id"] for r in promoted_records}
        new_library = library_records + promoted_records
        await ctx.write_all(new_library)

        remaining_staged = [
            r for r in staged_records if r.get("id") not in promoted_ids
        ]
        await ctx.staging_write_all(remaining_staged)

        for file_path in files_to_delete:
            await ctx.staging_delete_file(file_path)

    return MergeResult(promoted=promoted_keys, errors=errors, skipped=skipped)
