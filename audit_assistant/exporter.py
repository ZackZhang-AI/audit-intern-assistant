from __future__ import annotations

from io import BytesIO
from typing import Iterable

import pandas as pd

from .models import DocumentSuggestion


EXPORT_COLUMNS = [
    "original_filename",
    "document_type",
    "audit_cycle",
    "counterparty",
    "date",
    "amount",
    "document_number",
    "suggested_filename",
    "suggested_folder",
    "confidence",
    "review_note",
]


def suggestions_to_dataframe(suggestions: Iterable[DocumentSuggestion]) -> pd.DataFrame:
    rows = []
    for suggestion in suggestions:
        row = suggestion.to_dict()
        rows.append({column: row.get(column, "") for column in EXPORT_COLUMNS})
    return pd.DataFrame(rows, columns=EXPORT_COLUMNS)


def to_excel_bytes(frame: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="归档建议", index=False)
    return output.getvalue()

