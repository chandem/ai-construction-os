from io import BytesIO
from pathlib import Path


def extract_text(filename: str, content_type: str, data: bytes) -> tuple[str, int | None]:
    """Extract searchable text from common construction document formats."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf" or content_type == "application/pdf":
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\\n\\n".join(pages), len(reader.pages)

    if suffix == ".docx":
        from docx import Document
        doc = Document(BytesIO(data))
        return "\\n".join(p.text for p in doc.paragraphs), None

    if suffix in {".xlsx", ".xls"}:
        import openpyxl
        workbook = openpyxl.load_workbook(BytesIO(data), data_only=True, read_only=True)
        lines: list[str] = []
        for sheet in workbook.worksheets:
            lines.append(f"[Sheet: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                values = [str(v) for v in row if v is not None]
                if values:
                    lines.append(" | ".join(values))
        return "\\n".join(lines), None

    if suffix in {".txt", ".csv"} or content_type.startswith("text/"):
        return data.decode("utf-8", errors="replace"), None

    raise ValueError("Unsupported document format")


def chunk_text(text: str, chunk_size: int = 1800, overlap: int = 250) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks
