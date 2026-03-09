from pathlib import Path
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, computed_field

from scholartools.ports import (
    CopyFile,
    DeleteFile,
    FetchFn,
    ListFilePaths,
    LlmExtractFn,
    ReadAll,
    RenameFile,
    SearchFn,
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

    file_record: FileRecord | None = Field(None, alias="_file")
    warnings: list[str] = Field(default_factory=list, alias="_warnings")


class ApiSource(TypedDict):
    name: str
    search: SearchFn
    fetch: FetchFn


class LibraryCtx(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    read_all: ReadAll
    write_all: WriteAll
    copy_file: CopyFile
    delete_file: DeleteFile
    rename_file: RenameFile
    list_file_paths: ListFilePaths
    files_dir: str
    api_sources: list[ApiSource]
    llm_extract: LlmExtractFn | None = None


class AddResult(BaseModel):
    citekey: str | None = None
    error: str | None = None


class GetResult(BaseModel):
    reference: Reference | None = None
    error: str | None = None


class ListResult(BaseModel):
    references: list[Reference]
    total: int


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


class SearchResult(BaseModel):
    references: list[Reference]
    sources_queried: list[str]
    total_found: int
    errors: list[str]


class FetchResult(BaseModel):
    reference: Reference | None = None
    source: str | None = None
    error: str | None = None


class ExtractResult(BaseModel):
    reference: Reference | None = None
    method_used: Literal["pdfplumber", "llm"] | None = None
    confidence: float | None = None
    error: str | None = None


class LinkResult(BaseModel):
    citekey: str | None = None
    file_record: FileRecord | None = None
    error: str | None = None


class UnlinkResult(BaseModel):
    unlinked: bool
    error: str | None = None


class MoveResult(BaseModel):
    new_path: str | None = None
    error: str | None = None


class FilesListResult(BaseModel):
    files: list[FileRecord]
    total: int


class LocalSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    library_dir: Path = Field(
        default_factory=lambda: Path.home() / ".local/share/scholartools"
    )

    @computed_field
    @property
    def library_file(self) -> Path:
        return self.library_dir / "library.json"

    @computed_field
    @property
    def files_dir(self) -> Path:
        return self.library_dir / "files"


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    enabled: bool = True
    email: str | None = None


def _default_sources() -> list[SourceConfig]:
    return [
        SourceConfig(name="crossref"),
        SourceConfig(name="semantic_scholar"),
        SourceConfig(name="arxiv"),
        SourceConfig(name="latindex"),
        SourceConfig(name="google_books"),
    ]


class ApiSettings(BaseModel):
    sources: list[SourceConfig] = Field(default_factory=_default_sources)


class LlmSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = "claude-sonnet-4-6"


class Settings(BaseModel):
    backend: str = "local"
    local: LocalSettings = Field(default_factory=LocalSettings)
    apis: ApiSettings = Field(default_factory=ApiSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
