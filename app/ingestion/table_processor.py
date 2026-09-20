import re

from app.core.logging import get_logger


logger = get_logger(__name__)


def _split_row(line: str) -> list[str]:
    """
    Split a Markdown table row while removing
    only the outer pipe characters.

    This is safer than removing every empty cell.
    """

    line = line.strip()

    if line.startswith("|"):
        line = line[1:]

    if line.endswith("|"):
        line = line[:-1]

    return [
        cell.strip()
        for cell in line.split("|")
    ]


def _is_separator(line: str) -> bool:
    return bool(
        re.fullmatch(
            r"\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*",
            line,
        )
    )


def parse_markdown_table(
    markdown_table: str,
) -> dict:

    lines = [
        line.strip()
        for line in markdown_table.strip().splitlines()
        if line.strip()
    ]

    if len(lines) < 2:
        return {
            "headers": [],
            "rows": [],
            "row_count": 0,
            "col_count": 0,
            "raw": markdown_table,
        }

    headers = _split_row(lines[0])

    separator_idx = 1

    if _is_separator(lines[1]):
        separator_idx = 2

    rows = []

    for line in lines[separator_idx:]:

        if _is_separator(line):
            continue

        row = _split_row(line)

        if not row:
            continue

        # Keep the row even if malformed. Padding/truncation
        # is handled when generating searchable text.
        rows.append(row)

    return {
        "headers": headers,
        "rows": rows,
        "row_count": len(rows),
        "col_count": len(headers),
        "raw": markdown_table,
    }


def table_to_text_representation(
    table_data: dict,
    section: str = "",
    page: int = 0,
) -> str:

    parts = []

    if section:
        parts.append(
            f"Table from {section}, Page {page}."
        )
    else:
        parts.append(
            f"Table on Page {page}."
        )

    headers = table_data.get(
        "headers",
        [],
    )

    if headers:
        parts.append(
            f"Columns: {', '.join(headers)}."
        )

    for row in table_data.get(
        "rows",
        [],
    ):

        if headers:

            values = []

            for index, value in enumerate(row):

                if index < len(headers):
                    values.append(
                        f"{headers[index]}: {value}"
                    )
                else:
                    values.append(value)

            row_text = ", ".join(values)

        else:
            row_text = ", ".join(row)

        if row_text:
            parts.append(row_text)

    return " ".join(parts)