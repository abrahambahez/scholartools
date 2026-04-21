from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from loretools.ports import (
    CopyFile,
    DeleteFile,
    ListFilePaths,
    ReadAll,
    RenameFile,
    WriteAll,
)


class Author(BaseModel):
    family: str | None = None
    given: str | None = None
    literal: str | None = None


class DateField(BaseModel):
    model_config = ConfigDict(extra="allow")
    date_parts: list[list[int]] | None = Field(None, alias="date-parts")


class FileRecord(BaseModel):
    path: str
    mime_type: str
    size_bytes: int
    added_at: str


class Reference(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    type: str
    title: str | None = None
    author: list[Author] | None = None
    issued: DateField | None = None
    DOI: str | None = None
    URL: str | None = None
    added_at: datetime | None = None
    uid: str | None = None
    uid_confidence: Literal["authoritative", "semantic"] | None = None

    file_record: FileRecord | None = Field(None, alias="_file")
    warnings: list[str] = Field(default_factory=list, alias="_warnings")


class CitekeySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pattern: str = "{author[2]}{year}"
    separator: str = "_"
    etal: str = "_etal"
    disambiguation_suffix: str = "letters"

    @field_validator("pattern")
    @classmethod
    def _check_pattern(cls, v: str) -> str:
        import re

        tokens = re.findall(r"\{[^}]+\}", v)
        if not tokens:
            raise ValueError("pattern must contain at least one token")
        for token in tokens:
            if not re.fullmatch(r"\{author\[\d+\]\}|\{year\}", token):
                raise ValueError(f"unknown pattern token: {token}")
        return v

    @field_validator("separator")
    @classmethod
    def _check_separator(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9_-]{1,3}", v):
            raise ValueError("separator must match [a-z0-9_-]{1,3}")
        return v

    @field_validator("etal")
    @classmethod
    def _check_etal(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9_-]{1,8}", v):
            raise ValueError("etal must match [a-z0-9_-]{1,8}")
        return v

    @field_validator("disambiguation_suffix")
    @classmethod
    def _check_disambiguation(cls, v: str) -> str:
        import re

        if v != "letters" and not re.fullmatch(r"title[1-9]", v):
            raise ValueError("disambiguation_suffix must be 'letters' or 'title[1-9]'")
        return v


class LibraryCtx(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    read_all: ReadAll
    write_all: WriteAll
    copy_file: CopyFile
    delete_file: DeleteFile
    rename_file: RenameFile
    list_file_paths: ListFilePaths
    sources_raw_dir: str
    sources_read_dir: str
    staging_read_all: ReadAll | None = None
    staging_write_all: WriteAll | None = None
    staging_copy_file: CopyFile | None = None
    staging_delete_file: DeleteFile | None = None
    staging_dir: str | None = None
    citekey_settings: CitekeySettings = Field(default_factory=CitekeySettings)


class AddResult(BaseModel):
    citekey: str | None = None
    error: str | None = None


class GetResult(BaseModel):
    reference: Reference | None = None
    error: str | None = None


class ReferenceRow(BaseModel):
    citekey: str
    title: str | None = None
    authors: str | None = None
    year: int | None = None
    doi: str | None = None
    uid: str | None = None
    has_file: bool = False
    has_warnings: bool = False


class FileRow(BaseModel):
    citekey: str
    path: str
    mime_type: str
    size_bytes: int


class ListResult(BaseModel):
    references: list[ReferenceRow]
    total: int
    page: int = 1
    pages: int = 1


class UpdateResult(BaseModel):
    citekey: str | None = None
    error: str | None = None


class RenameResult(BaseModel):
    old_key: str | None = None
    new_key: str | None = None
    error: str | None = None


class DeleteResult(BaseModel):
    deleted: bool
    error: str | None = None


class ExtractResult(BaseModel):
    reference: Reference | None = None
    confidence: float | None = None
    error: str | None = None
    agent_extraction_needed: bool = False
    file_path: str | None = None


class AttachResult(BaseModel):
    citekey: str | None = None
    file_record: FileRecord | None = None
    error: str | None = None


class DetachResult(BaseModel):
    detached: bool = False
    error: str | None = None


class GetFileResult(BaseModel):
    path: str | None = None
    error: str | None = None


class MoveResult(BaseModel):
    new_path: str | None = None
    error: str | None = None


class FilesListResult(BaseModel):
    files: list[FileRow]
    total: int
    page: int = 1
    pages: int = 1


class LocalSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    library_dir: Path = Field(default_factory=Path.cwd)

    @computed_field
    @property
    def library_file(self) -> Path:
        return self.library_dir / "library.json"

    @computed_field
    @property
    def sources_dir(self) -> Path:
        return self.library_dir / "sources"

    @computed_field
    @property
    def sources_raw_dir(self) -> Path:
        return self.sources_dir / "raw"

    @computed_field
    @property
    def sources_read_dir(self) -> Path:
        return self.sources_dir / "read"

    @computed_field
    @property
    def staging_file(self) -> Path:
        return self.library_dir / "staging.json"

    @computed_field
    @property
    def staging_dir(self) -> Path:
        return self.library_dir / "staging"


class Settings(BaseModel):
    local: LocalSettings = Field(default_factory=LocalSettings)
    citekey: CitekeySettings = Field(default_factory=CitekeySettings)


class StageResult(BaseModel):
    citekey: str | None = None
    error: str | None = None


class ListStagedResult(BaseModel):
    references: list[ReferenceRow]
    total: int
    page: int = 1
    pages: int = 1


class DeleteStagedResult(BaseModel):
    deleted: bool
    error: str | None = None


class MergeResult(BaseModel):
    promoted: list[str]
    errors: dict[str, str]
    skipped: list[str]


class Result(BaseModel):
    ok: bool = True
    error: str | None = None


class ReindexResult(BaseModel):
    repaired: int
    already_ok: int
    not_found: int


class ReadResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    citekey: str
    output_path: str | None = None
    format: Literal["md", "txt"] | None = None
    method: Literal["pymupdf4llm", "pymupdf", "markitdown"] | None = None
    quality_score: float | None = None
    page_count: int | None = None
    error: str | None = None


class ReadBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: list[ReadResult]
    total_read: int
    total_failed: int
