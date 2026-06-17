from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DocumentSuggestion:
    original_filename: str
    document_type: str
    audit_cycle: str
    counterparty: str
    date: str
    amount: int | float | None
    document_number: str
    suggested_filename: str
    suggested_folder: str
    confidence: float
    review_note: str
    extracted_text: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

