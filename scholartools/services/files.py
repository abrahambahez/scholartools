"""Gestión de archivos vinculados a referencias.

A diferencia del scholartools original, no copia archivos — solo registra
la ruta absoluta del archivo existente en librero/. El manejo físico
de archivos queda en manos de los scripts de la bóveda.
"""

import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from scholartools.models import (
    FileRecord,
    FileRow,
    FilesListResult,
    LibraryCtx,
    LinkResult,
    MoveResult,
    UnlinkResult,
)
from scholartools.services.list_helpers import paginate


async def link_file(citekey: str, file_path: str, ctx: LibraryCtx) -> LinkResult:
    records = await ctx.read_all()
    for r in records:
        if r.get("id") == citekey:
            src = Path(file_path).resolve()
            if not src.exists():
                return LinkResult(error=f"file not found: {file_path}")

            record = FileRecord(
                path=str(src),
                mime_type=_detect_mime(str(src)),
                size_bytes=src.stat().st_size,
                added_at=datetime.now(timezone.utc).isoformat(),
            )
            r["_file"] = record.model_dump()
            await ctx.write_all(records)
            return LinkResult(citekey=citekey, file_record=record)

    return LinkResult(error=f"not found: {citekey}")


async def unlink_file(citekey: str, ctx: LibraryCtx) -> UnlinkResult:
    records = await ctx.read_all()
    for r in records:
        if r.get("id") == citekey:
            if not r.get("_file"):
                return UnlinkResult(unlinked=False, error="no file linked")
            r.pop("_file", None)
            await ctx.write_all(records)
            return UnlinkResult(unlinked=True)

    return UnlinkResult(unlinked=False, error=f"not found: {citekey}")


async def move_file(citekey: str, dest_name: str, ctx: LibraryCtx) -> MoveResult:
    """Actualiza el path registrado en _file (el rename físico lo hace rename_citekey.py)."""
    records = await ctx.read_all()
    for r in records:
        if r.get("id") == citekey:
            if not r.get("_file"):
                return MoveResult(error="no file linked")
            files_dir = Path(ctx.files_dir)
            new_path = str((files_dir / dest_name).resolve())
            r["_file"]["path"] = new_path
            await ctx.write_all(records)
            return MoveResult(new_path=new_path)

    return MoveResult(error=f"not found: {citekey}")


async def list_files(ctx: LibraryCtx, page: int = 1) -> FilesListResult:
    records = await ctx.read_all()
    rows = sorted(
        [
            FileRow(citekey=r["id"], **r["_file"])
            for r in records
            if r.get("_file") and r.get("id")
        ],
        key=lambda f: f.citekey,
    )
    items, page, pages = paginate(rows, page)
    return FilesListResult(files=items, total=len(rows), page=page, pages=pages)


def _detect_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"
