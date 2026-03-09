# ADR-001: Hexagonal Architecture with Result Types at the Public Boundary

## status
Accepted

## context
scholartools is consumed by AI agents, not humans. Agents call functions, read structured outputs, and cannot gracefully handle Python exceptions. The library must also support multiple storage backends (local, S3+DynamoDB, MongoDB+GCS) without changing the agent-facing interface. Standard layered architecture couples business logic to I/O and propagates exceptions upward — both are problems for agent reliability and backend flexibility.

## decision
Use Hexagonal Architecture (Ports & Adapters):
- Domain core (models, business logic) is pure Pydantic — no I/O
- Ports are `Protocol` interfaces defining what adapters must implement
- Services are async and interact with the domain only through injected port instances
- Adapters implement ports and own all I/O
- The public API (`__init__.py`) is the primary port: sync wrappers that wire config → adapters → services

Every public function returns a typed Result model. Exceptions are caught at the adapter boundary and surfaced as error fields in the result. The public API never raises.

## alternatives considered

**Standard DDD layered architecture**: simpler to explain, but couples service layer to concrete infrastructure and propagates exceptions to callers. Rejected because agents cannot catch exceptions reliably and backend swapping requires touching service code.

**Simple flat modules**: fast to write, impossible to test without real I/O, and impossible to swap backends. Rejected.

**FastAPI-style dependency injection framework**: overkill for a library. Manual injection at `__init__.py` wiring is sufficient and keeps the import graph simple. Rejected.

## consequences
Positive:
- Services are fully testable with mocked ports — no filesystem or network needed
- Adding a new backend requires only a new adapter file, zero service changes
- Agents get deterministic, typed results with no exception handling required
- Adding MCP or REST interface is just a new primary adapter

Negative:
- More files and indirection than a flat design
- Developers must understand the port/adapter distinction to contribute correctly
- Dependency injection is manual — wiring errors surface at runtime, not import time

Neutral:
- All result types must be explicitly defined in models.py — the schema grows with features
