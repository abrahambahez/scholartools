import json
import shutil
from pathlib import Path

from scholartools.ports import (
    CopyFile,
    DeleteFile,
    ListFilePaths,
    ReadAll,
    RenameFile,
    WriteAll,
)


def make_storage(library_path: str) -> tuple[ReadAll, WriteAll]:
    path = Path(library_path)

    async def read_all() -> list[dict]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    async def write_all(records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp.json")
        tmp.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.rename(path)

    return read_all, write_all


def make_filestore(
    files_dir: str,
) -> tuple[CopyFile, DeleteFile, RenameFile, ListFilePaths]:
    base = Path(files_dir)

    async def copy_file(src: str, dest: str) -> None:
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    async def delete_file(file_path: str) -> None:
        Path(file_path).unlink(missing_ok=True)

    async def rename_file(old_path: str, new_path: str) -> None:
        Path(old_path).rename(new_path)

    async def list_file_paths(dir_path: str) -> list[str]:
        d = Path(dir_path)
        if not d.exists():
            return []
        return sorted(str(f) for f in d.iterdir() if f.is_file())

    return copy_file, delete_file, rename_file, list_file_paths
