# spec: 015-minio-migration

## context

The S3 adapter (`adapters/s3_sync.py`) uses boto3 + botocore for 6 operations. This pulls in ~15MB for the full AWS SDK surface. scholartools only needs S3-compatible object storage. `SyncConfig.endpoint` already signals support for non-AWS backends (MinIO, Cloudflare R2, Backblaze B2). The current dev environment has 8 conditional test failures because boto3 is not installed.

ADR-005 accepted: replace boto3 with the MinIO Python SDK (~500KB). All 6 operations have direct equivalents. One breaking consequence: no AWS credential auto-discovery — `access_key`/`secret_key` must be explicit in `SyncConfig`.

## objective

Replace boto3/botocore with MinIO SDK. Eliminate 8 dev test failures. Maintain full S3-compatible backend support with no public API or model changes.

## acceptance criteria

- when the adapter is instantiated with `SyncConfig`, the system must use MinIO SDK (not boto3) for all 6 operations
- when `exists()` is called on a missing key, the system must return `False` by catching `S3Error` with code `NoSuchKey`/`404`
- when `exists()` is called on a present key, the system must return `True`
- when all S3 unit tests run without boto3 installed, the system must pass with zero conditional skips
- when `SyncConfig.endpoint` is an AWS S3 URL, the system must authenticate and operate correctly
- when `SyncConfig.endpoint` is a MinIO URL, the system must authenticate and operate correctly

## tasks

- [ ] task-01: pyproject.toml — add `minio>=7.0.0`, remove boto3 from optional sync extra (blocks: none)

- [ ] task-02: adapters/s3_sync.py — replace boto3 with MinIO SDK (blocks: task-01)
  - `_client(config)` → `Minio(endpoint_host, access_key, secret_key, secure=bool)`
  - `upload_file` → `fput_object(bucket, key, path)`
  - `download_file` → `fget_object(bucket, key, path)`
  - `get_paginator(...).paginate(...)` → `list_objects(bucket, prefix=prefix, recursive=True)`
  - `head_object` → `stat_object(bucket, key)` (raises `S3Error` on miss)
  - `put_object(Body=BytesIO)` → `put_object(bucket, key, stream, length)`
  - `exists()`: catch `minio.error.S3Error`, return `False`; return `True` on success

- [ ] task-03: update unit tests — mock MinIO client, drop botocore mocks (blocks: task-02)
  - `tests/unit/test_s3_sync.py`, `tests/unit/test_s3_upload_bytes.py`
  - MockS3 in integration tests must not import boto3

- [ ] task-04: run full test suite, confirm 8 pre-existing boto3 failures are resolved (blocks: task-03)
  - `uv run pytest tests/unit` must pass with zero skips
  - `uv run pytest --run-integration` must pass S3 integration scenarios

## risks

1. **AWS credential auto-discovery removed** — users with `~/.aws/credentials` or IAM roles must now set explicit creds in `SyncConfig`. Document in README.
2. **Error type change** — bare `except Exception` in `exists()` currently masks all errors. MinIO SDK raises `S3Error`; the new catch must be specific.
3. **MinIO endpoint URL format** — MinIO client takes host without scheme (e.g. `play.min.io:9000`), not a full URL. `SyncConfig.endpoint` may need stripping in `_client()`.
