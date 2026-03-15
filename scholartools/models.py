from datetime import datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

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
    added_at: datetime | None = None
    uid: str | None = None
    uid_confidence: Literal["authoritative", "semantic"] | None = None

    blob_ref: str | None = None
    file_record: FileRecord | None = Field(None, alias="_file")
    warnings: list[str] = Field(default_factory=list, alias="_warnings")
    field_timestamps: dict[str, str] = Field(
        default_factory=dict, alias="_field_timestamps"
    )


class ApiSource(TypedDict):
    name: str
    search: SearchFn
    fetch: FetchFn


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
    files_dir: str
    staging_read_all: ReadAll | None = None
    staging_write_all: WriteAll | None = None
    staging_copy_file: CopyFile | None = None
    staging_delete_file: DeleteFile | None = None
    staging_dir: str | None = None
    api_sources: list[ApiSource]
    llm_extract: LlmExtractFn | None = None
    citekey_settings: CitekeySettings = Field(default_factory=CitekeySettings)
    peers_dir: str | None = None
    data_dir: str | None = None
    admin_peer_id: str = "_admin"
    admin_device_id: str = "_admin"
    sync_config: "SyncConfig | None" = None


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
    files: list[FileRow]
    total: int
    page: int = 1
    pages: int = 1


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

    @computed_field
    @property
    def staging_file(self) -> Path:
        return self.library_dir / "staging.json"

    @computed_field
    @property
    def staging_dir(self) -> Path:
        return self.library_dir / "staging"

    @computed_field
    @property
    def peers_dir(self) -> Path:
        return self.library_dir / "peers"


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    enabled: bool = True


def _default_sources() -> list[SourceConfig]:
    return [
        SourceConfig(name="crossref"),
        SourceConfig(name="semantic_scholar"),
        SourceConfig(name="arxiv"),
        SourceConfig(name="openalex"),
        SourceConfig(name="doaj"),
        SourceConfig(name="google_books"),
    ]


class ApiSettings(BaseModel):
    email: str | None = None
    sources: list[SourceConfig] = Field(default_factory=_default_sources)


class LlmSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = "claude-sonnet-4-6"


class SyncConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str | None = None
    bucket: str
    access_key: str
    secret_key: str


class Settings(BaseModel):
    backend: str = "local"
    local: LocalSettings = Field(default_factory=LocalSettings)
    apis: ApiSettings = Field(default_factory=ApiSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    citekey: CitekeySettings = Field(default_factory=CitekeySettings)
    sync: SyncConfig | None = None


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


class DeviceIdentity(BaseModel):
    device_id: str
    public_key: str
    registered_at: datetime
    revoked_at: datetime | None = None
    role: str = "peer"


class PeerRecord(BaseModel):
    peer_id: str
    devices: list[DeviceIdentity]
    signature: str | None = None


class PeerIdentity(BaseModel):
    peer_id: str
    device_id: str
    public_key: str


class PeerInitResult(BaseModel):
    identity: PeerIdentity | None = None
    error: str | None = None


class PeerRegisterResult(BaseModel):
    peer_id: str | None = None
    error: str | None = None


class PeerAddDeviceResult(BaseModel):
    peer_id: str | None = None
    error: str | None = None


class PeerRevokeDeviceResult(BaseModel):
    revoked: bool = False
    error: str | None = None


class PeerRevokeResult(BaseModel):
    revoked: bool = False
    error: str | None = None


class VerifyEntryResult(BaseModel):
    verified: bool = False
    error: str | None = None


class ChangeLogEntry(BaseModel):
    op: str
    uid: str
    uid_confidence: str
    citekey: str
    data: dict = Field(default_factory=dict)
    blob_ref: str | None = None
    peer_id: str
    device_id: str
    timestamp_hlc: str
    signature: str


class ConflictRecord(BaseModel):
    uid: str
    field: str
    local_value: Any
    local_timestamp_hlc: str
    remote_value: Any
    remote_timestamp_hlc: str
    remote_peer_id: str


class PushResult(BaseModel):
    entries_pushed: int = 0
    errors: list[str] = Field(default_factory=list)


class PullResult(BaseModel):
    applied_count: int = 0
    rejected_count: int = 0
    conflicted_count: int = 0
    errors: list[str] = Field(default_factory=list)


class Result(BaseModel):
    ok: bool = True
    error: str | None = None


class PrefetchResult(BaseModel):
    fetched: int
    already_cached: int
    errors: list[str]
