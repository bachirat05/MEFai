from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.table import Table
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
}


# ============================================================
# DOCX (ex docx_reader.py)
# ============================================================


def _clean_cell_text(
    text: str,
) -> str:
    return " ".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )


def _unique_values(
    values: list[str],
) -> list[str]:
    unique: list[str] = []

    for value in values:
        if (
            value
            and value not in unique
        ):
            unique.append(value)

    return unique


def _table_to_text(
    table: Table,
) -> list[str]:
    rows = [
        _unique_values(
            [
                _clean_cell_text(
                    cell.text
                )
                for cell in row.cells
            ]
        )
        for row in table.rows
    ]

    rows = [
        row
        for row in rows
        if row
    ]

    if not rows:
        return []

    headers = rows[0]
    body_rows = rows[1:]

    if not body_rows:
        return [
            " | ".join(headers)
        ]

    table_parts: list[str] = []

    for row in body_rows:
        pairs: list[str] = []

        for index, value in enumerate(row):
            if not value:
                continue

            header = (
                headers[index]
                if (
                    index < len(headers)
                    and headers[index]
                )
                else f"Colonne {index + 1}"
            )

            if value == header:
                continue

            pairs.append(
                f"{header}: {value}"
            )

        if pairs:
            table_parts.append(
                "\n".join(pairs)
            )

    return table_parts


def read_docx(
    file_path: Path,
) -> str:
    document = Document(
        str(file_path)
    )

    parts: list[str] = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            parts.append(text)

    for table in document.tables:
        parts.extend(
            _table_to_text(table)
        )

    return "\n\n".join(
        parts
    )


# ============================================================
# TXT / PDF
# ============================================================


def read_txt(
    file_path: Path,
) -> str:
    return file_path.read_text(
        encoding="utf-8",
        errors="ignore",
    )


def read_pdf(
    file_path: Path,
) -> str:
    reader = PdfReader(
        str(file_path)
    )

    pages: list[str] = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = (
            page.extract_text()
            or ""
        )

        if text.strip():
            pages.append(
                f"\n--- PAGE {page_number} ---\n"
                f"{text}"
            )

    return "\n".join(
        pages
    )


# ============================================================
# DISPATCH / DISCOVERY
# ============================================================


def read_document(
    file_path: Path,
) -> str:
    extension = (
        file_path.suffix.lower()
    )

    if extension == ".txt":
        return read_txt(file_path)

    if extension == ".pdf":
        return read_pdf(file_path)

    if extension == ".docx":
        return read_docx(file_path)

    raise ValueError(
        f"Unsupported file type: {extension}"
    )


def list_files(
    directory: Path,
) -> list[Path]:
    """List all supported files under `directory` (recursive, sorted)."""

    return sorted(
        file_path
        for file_path
        in directory.rglob("*")
        if (
            file_path.is_file()
            and file_path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )
    )