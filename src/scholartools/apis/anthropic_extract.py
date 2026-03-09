import base64
import json
import re
from pathlib import Path

import anthropic

from scholartools.ports import LlmExtractFn

_PROMPT = (
    "Extract bibliographic metadata from this document. "
    "Return only a JSON object with these fields (omit fields you cannot find): "
    "title (string), author (list of {family, given}), "
    "issued ({date-parts: [[year]]} or {date-parts: [[year, month, day]]}), "
    "DOI (string), URL (string), publisher (string), "
    "container-title (journal/book title string), type (CSL type string). "
    "Return only valid JSON, no explanation."
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def make_llm_extractor(api_key: str | None, model: str) -> LlmExtractFn:
    client = anthropic.AsyncAnthropic(api_key=api_key)

    async def extract(file_path: str) -> dict | None:
        try:
            pdf_data = base64.standard_b64encode(Path(file_path).read_bytes()).decode()
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_data,
                                },
                            },
                            {"type": "text", "text": _PROMPT},
                        ],
                    }
                ],
            )
            raw = response.content[0].text
            match = _JSON_RE.search(raw)
            if match:
                return json.loads(match.group())
        except (anthropic.APIError, OSError, json.JSONDecodeError, ValueError):
            pass
        return None

    return extract
