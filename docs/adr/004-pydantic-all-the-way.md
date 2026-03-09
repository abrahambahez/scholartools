# ADR-004: Pydantic for All Modeling — No Separate Domain Objects

## status
Accepted

## context
In strict DDD, domain entities are plain Python objects with no serialization concern. A separate layer of DTOs or serialization models handles I/O. This separation is valuable in large systems where the domain model and its wire representation diverge significantly. scholartools's core entity — the `Reference` — maps directly to CSL-JSON, a well-defined open standard. The divergence between domain model and serialization format is minimal.

## decision
Use Pydantic v2 models for everything: domain entities (`Reference`, `FileRecord`), result types (`SearchResult`, `ExtractResult`, etc.), configuration (`Settings`), and API response shapes. No plain Python dataclasses or separate DTO layer.

All models live in `src/scholartools/models.py`. No inline model definitions elsewhere in the codebase.

## alternatives considered

**Pure Python dataclasses for domain, Pydantic for serialization**: clean separation in theory, doubles the number of model types in practice, requires mapping code between layers. The added complexity is not justified at this scale. Rejected.

**TypedDict for API responses**: lightweight but no validation, no default values, no serialization methods. Agents need validated, normalized data — TypedDict provides no guarantees. Rejected.

**attrs**: comparable to Pydantic in ergonomics but less ecosystem support, no built-in JSON schema generation (useful for MCP tool definitions later). Rejected.

## consequences
Positive:
- Single source of truth for every data shape in the system
- Free JSON serialization/deserialization via `.model_dump()` and `.model_validate()`
- Pydantic validation catches bad data at system boundaries (external APIs, user input)
- JSON Schema generation from models — directly usable for MCP tool definitions in future
- Less code: no mapping functions between domain objects and DTOs

Negative:
- Pydantic models carry serialization concerns into the domain layer — a DDD purist would object
- Model changes propagate everywhere — no buffer layer between domain and I/O

Neutral:
- All model changes require updating `models.py` — a single file becomes the schema registry for the whole project
