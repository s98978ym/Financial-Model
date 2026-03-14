from src.evals.source_intel import extract_keyword_excerpt


def test_extract_keyword_excerpt_returns_matching_sentence() -> None:
    text = (
        "Partner programs often improve pipeline quality. "
        "Strong partner enablement increases partner-sourced revenue and shortens sales cycles. "
        "Teams that invest in enablement tend to retain more productive partners."
    )

    excerpt = extract_keyword_excerpt(text, ["partner-sourced revenue", "sales cycles"])

    assert "partner-sourced revenue" in excerpt
    assert "sales cycles" in excerpt


def test_extract_keyword_excerpt_falls_back_to_leading_text() -> None:
    text = "This report summarizes market conditions and investment pacing over multiple years."

    excerpt = extract_keyword_excerpt(text, ["unmatched keyword"])

    assert excerpt.startswith("This report summarizes")
