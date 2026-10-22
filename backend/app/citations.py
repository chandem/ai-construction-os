import re


_SOURCE_CITATION_PATTERN = re.compile(r"\[Source\s+(\d+)\]")


def validate_source_citations(answer: str, source_count: int) -> str:
    """Mark inline source references that do not exist in the retrieved source list."""
    available_count = max(0, source_count)

    def replace(match: re.Match[str]) -> str:
        source_number = int(match.group(1))
        if 1 <= source_number <= available_count:
            return match.group(0)
        return f"[Unverified citation: Source {source_number}]"

    return _SOURCE_CITATION_PATTERN.sub(replace, answer)
