# ADR-002: Two-Stage PDF Extraction (pdfplumber → LLM Vision Fallback)

## status
Accepted

## context
scholartools must extract bibliographic metadata from PDFs and ebooks provided by the human. PDFs come in two fundamentally different forms: text-based (selectable text embedded in the file) and image-based (scanned pages, no embedded text). A single extraction strategy cannot handle both reliably. The tool must also avoid heavyweight dependencies like Tesseract for OCR.

## decision
Use a two-stage extraction pipeline:

1. **pdfplumber** (primary): extract text from the first N pages, parse metadata fields (title, authors, abstract, DOI, journal, year) using pattern matching and heuristics. Fast, offline, no API cost.

2. **Anthropic SDK / Claude vision** (fallback): if pdfplumber yields insufficient metadata (confidence below threshold, missing required fields, or garbled text), send the PDF to Claude via the Files API. Claude can read the full PDF visually and return structured metadata as JSON.

The `ExtractResult` model includes `method_used` (`"pdfplumber"` or `"llm"`) and a `confidence` float so callers can decide how to handle uncertain extractions.

## alternatives considered

**pdfplumber only**: fails completely on scanned PDFs. Rejected.

**Tesseract OCR**: handles scanned PDFs but requires a system-level binary dependency, is slow, and still requires a metadata parsing layer on top of raw OCR text. Rejected.

**LLM vision only**: works universally but incurs API cost and latency on every extraction, including trivial text-based PDFs. Rejected.

**pypdf**: simpler API than pdfplumber but weaker layout handling and table extraction. pdfplumber is built on pdfminer and handles structured academic papers more reliably. Rejected.

## consequences
Positive:
- Handles both text-based and scanned PDFs without a system OCR dependency
- Fast path (pdfplumber) has zero API cost and works offline
- Confidence field gives agents actionable signal about extraction quality
- Claude vision is already a project dependency (Anthropic SDK) — no new dependency added

Negative:
- LLM fallback requires an Anthropic API key and network access
- Two-stage logic adds complexity to `extract.py`
- Confidence scoring for pdfplumber extraction requires calibration

Neutral:
- `method_used` field in `ExtractResult` creates a minor schema difference between extraction paths
