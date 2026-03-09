# ADR-003: httpx over requests for External HTTP

## status
Accepted

## context
scholartools services fan out across multiple external APIs simultaneously (Crossref, Semantic Scholar, OpenAlex). Services are async-first. A synchronous-only HTTP client would require threads or process pools to achieve parallelism, adding complexity and overhead. The HTTP client is also used in adapters for cloud backends (DynamoDB, MongoDB, GCS SDKs handle their own transport, but direct REST adapters need it).

## decision
Use `httpx` as the sole HTTP client across the project. httpx is async-native (via `httpx.AsyncClient`) and also provides a sync interface (`httpx.Client`) that is API-compatible with `requests`. All API clients in `src/scholartools/apis/` use `httpx.AsyncClient`. The sync public API wraps the async services with `asyncio.run()` — httpx plays well with this pattern.

## alternatives considered

**requests**: synchronous only. Parallel API fan-out would require `concurrent.futures.ThreadPoolExecutor`, adding boilerplate and thread management. Familiar but wrong tool for async services. Rejected.

**aiohttp**: async-native but has a different API from requests and requires more boilerplate for client setup and response handling. httpx has better ergonomics and a sync fallback. Rejected.

**requests + requests-futures**: adds parallelism to requests via threads, but is a workaround rather than a solution. Rejected.

## consequences
Positive:
- Async fan-out across multiple APIs with `asyncio.gather()` — no threads needed
- Single HTTP client for all external calls — no mixing of sync/async transports
- API-compatible with requests — familiar interface for contributors
- Built-in timeout, retry hooks, and connection pooling

Negative:
- httpx is less battle-tested than requests in some edge cases
- Contributors unfamiliar with async Python may find `AsyncClient` context managers surprising

Neutral:
- Cloud backend SDKs (boto3, pymongo, google-cloud-storage) manage their own HTTP transport independently
