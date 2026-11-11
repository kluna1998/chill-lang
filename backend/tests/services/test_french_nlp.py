import uuid

import pytest
import spacy

from app.services import french_nlp
from app.services.french_nlp import (
    InvalidSelection,
    analyze_selection,
    get_pipeline,
    utf16_to_python,
)


def utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def analyze(text: str, selection: str, last: bool = False):
    index = text.rindex(selection) if last else text.index(selection)
    start = utf16_length(text[:index])
    return analyze_selection(
        text, uuid.uuid4(), uuid.uuid4(), start, start + utf16_length(selection)
    )


@pytest.mark.parametrize(
    "text,word,lemma,pos",
    [
        ("Je mange une pomme.", "mange", "manger", "VERB"),
        ("Elle aperçut un homme.", "aperçut", "apercevoir", "VERB"),
        ("Il était parti.", "parti", "partir", "VERB"),
        ("L'homme est arrivé.", "homme", "homme", "NOUN"),
        ("Elle se rendit compte de son erreur.", "rendit compte", None, None),
        ("Nous nous promenions dans la rue.", "promenions", "promener", "VERB"),
    ],
)
def test_french_examples(
    text: str, word: str, lemma: str | None, pos: str | None
) -> None:
    result = analyze(text, word)
    assert result.selected_text == word
    assert result.context == text
    assert result.selection_covers_full_tokens
    if lemma:
        assert result.tokens[0].lemma == lemma
        assert result.tokens[0].pos == pos
    else:
        assert [token.text for token in result.tokens] == ["rendit", "compte"]
        assert result.tokens[0].lemma == "rendre"
    for token in result.tokens:
        assert (
            text.encode("utf-16-le")[
                token.start_offset * 2 : token.end_offset * 2
            ].decode("utf-16-le")
            == token.text
        )
        assert token.dependency is not None
        assert token.head_start_offset is not None
        assert token.head_end_offset is not None
        assert (
            text.encode("utf-16-le")[
                token.head_start_offset * 2 : token.head_end_offset * 2
            ].decode("utf-16-le")
            == token.head_text
        )


def test_apostrophe_tokens_and_compound_verb_morphology() -> None:
    apostrophe = analyze("L'homme est arrivé.", "L'homme")
    assert [token.text for token in apostrophe.tokens] == ["L'", "homme"]
    assert apostrophe.tokens[0].lemma == "le"
    result = analyze("Il était parti.", "était parti")
    assert result.tokens[0].morphology["Tense"] == ["Imp"]
    assert result.tokens[1].morphology["VerbForm"] == ["Part"]


@pytest.mark.parametrize(
    "text",
    [
        "😀 Elle aperçut un homme.",
        "L’été, elle aperçut un homme.",
        "Elle aperçut un homme.\n\nElle aperçut un arbre.",
    ],
)
def test_unicode_and_repeated_selection_offsets(text: str) -> None:
    result = analyze(text, "aperçut", last=True)
    assert result.start_offset == utf16_length(text[: text.rindex("aperçut")])
    assert result.end_offset == result.start_offset + 7
    assert (
        result.context == text[text.rindex("Elle") :]
        if "\n" in text
        else "aperçut" in result.context
    )


def test_partial_token_and_multisentence_selection() -> None:
    result = analyze("Elle aperçut un homme.", "aper")
    assert result.selected_text == "aper"
    assert result.tokens[0].text == "aperçut"
    assert not result.selection_covers_full_tokens
    result = analyze("Elle mange. Nous partons.", "mange. Nous")
    assert len(result.sentences) == 2
    assert result.context == "Elle mange. Nous partons."


@pytest.mark.parametrize(
    "text,start,end",
    [
        ("", 0, 1),
        ("abc", -1, 2),
        ("abc", 2, 1),
        ("abc", 1, 1),
        ("abc", 0, 5),
        ("😀abc", 1, 3),
        ("😀abc", 0, 1),
        ("a" * 600, 0, 513),
    ],
)
def test_invalid_offsets(text: str, start: int, end: int) -> None:
    with pytest.raises(InvalidSelection):
        utf16_to_python(text, start, end)


def test_whitespace_rejected_without_model(monkeypatch: pytest.MonkeyPatch) -> None:
    def not_called():
        pytest.fail("Whitespace must be rejected before model loading")

    monkeypatch.setattr(french_nlp, "get_pipeline", not_called)
    with pytest.raises(InvalidSelection):
        analyze("a  b", "  ")


def test_window_is_bounded_and_context_truncation_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = get_pipeline()
    lengths = []

    class Recorder:
        meta = real.meta

        def __call__(self, text):
            lengths.append(len(text))
            return real(text)

    monkeypatch.setattr(french_nlp, "get_pipeline", lambda: Recorder())
    text = "bonjour " * 3000 + "Elle aperçut un homme " + "bonjour " * 3000
    result = analyze(text, "aperçut")
    assert max(lengths) <= french_nlp.MAX_WINDOW_CHARS
    assert result.context_truncated
    assert result.selected_text == "aperçut"


def test_model_reused() -> None:
    assert get_pipeline() is get_pipeline()


def test_missing_annotations_remain_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(french_nlp, "get_pipeline", lambda: spacy.blank("fr"))
    result = analyze("Bonjour.", "Bonjour")
    assert result.tokens[0].lemma is None
    assert result.tokens[0].pos is None
    assert result.tokens[0].morphology is None
    assert result.tokens[0].dependency is None
    assert result.tokens[0].head_start_offset is None
    assert result.sentences == []


@pytest.mark.xfail(
    strict=True,
    reason="fr_core_news_sm 3.8.0 predicts Pres for aperçut; expected passé simple (Past).",
)
def test_model_objective_apercut_past() -> None:
    assert analyze("Elle aperçut un homme.", "aperçut").tokens[0].morphology[
        "Tense"
    ] == ["Past"]


@pytest.mark.xfail(
    strict=True,
    reason="fr_core_news_sm 3.8.0 predicts person 3 for Je mange; expected person 1.",
)
def test_model_objective_mange_first_person() -> None:
    assert analyze("Je mange une pomme.", "mange").tokens[0].morphology["Person"] == [
        "1"
    ]


@pytest.mark.xfail(
    strict=True,
    reason="fr_core_news_sm 3.8.0 predicts Pres for promenions; expected imperfect (Imp).",
)
def test_model_objective_promenions_imperfect() -> None:
    assert analyze("Nous nous promenions dans la rue.", "promenions").tokens[
        0
    ].morphology["Tense"] == ["Imp"]
