from typing import Awaitable, Callable

ReadAll = Callable[[], Awaitable[list[dict]]]
WriteAll = Callable[[list[dict]], Awaitable[None]]

CopyFile = Callable[[str, str], Awaitable[None]]
DeleteFile = Callable[[str], Awaitable[None]]
RenameFile = Callable[[str, str], Awaitable[None]]
ListFilePaths = Callable[[str], Awaitable[list[str]]]

SearchFn = Callable[[str, int], Awaitable[list[dict]]]
FetchFn = Callable[[str], Awaitable[dict | None]]

LlmExtractFn = Callable[[str], Awaitable[dict | None]]
