from app.document_processing import chunk_text, chunk_text_with_metadata, extract_pages


def test_extract_pages_plain_text():
    pages = extract_pages("notes.txt", "text/plain", b"Hello construction world")
    assert len(pages) == 1
    assert pages[0][0] == "Hello construction world"
    assert pages[0][1] is None


def test_chunk_text_with_metadata_preserves_page():
    pages = [("alpha " * 50, 1), ("beta " * 50, 2)]
    chunks = chunk_text_with_metadata(pages, chunk_size=40, overlap=5)
    assert chunks
    assert all("content" in c and "page_number" in c for c in chunks)
    assert {c["page_number"] for c in chunks} == {1, 2}


def test_chunk_text_empty_input():
    assert chunk_text("") == []
    assert chunk_text_with_metadata([("   ", 1)]) == []


def test_chunk_text_overlap_progresses():
    text = "word " * 200
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1
    # Overlap should not produce identical successive windows for long text
    assert chunks[0] != chunks[1]
