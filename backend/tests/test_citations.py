from app.citations import validate_source_citations


def test_keeps_citations_that_match_retrieved_sources():
    answer = "The BOQ lists the activity [Source 1] and its rate [Source 2]."
    assert validate_source_citations(answer, 2) == answer


def test_marks_citation_above_available_source_count():
    answer = "The specification says this [Source 3]."
    assert validate_source_citations(answer, 2) == (
        "The specification says this [Unverified citation: Source 3]."
    )


def test_marks_source_citations_when_no_sources_were_retrieved():
    assert validate_source_citations("As shown [Source 1].", 0) == (
        "As shown [Unverified citation: Source 1]."
    )


def test_marks_zero_and_negative_source_numbers():
    answer = "Bad refs [Source 0] and [Source  -1]."
    assert validate_source_citations(answer, 2) == (
        "Bad refs [Unverified citation: Source 0] and [Source  -1]."
    )
