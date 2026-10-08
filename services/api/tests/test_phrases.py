"""Spoken challenge phrase generation and matching (unit)."""

from __future__ import annotations

from app.core import phrases


def test_generated_phrase_has_three_distinct_code_words() -> None:
    seen = set()
    for _ in range(200):
        phrase = phrases.generate_phrase()
        words = phrases.code_words(phrase)
        assert len(words) == 3
        assert len(set(words)) == 3
        assert all(word in phrases.CODE_WORDS for word in words)
        seen.add(phrase)
    # The generator is random, not fixed.
    assert len(seen) > 1


def test_filler_words_are_not_treated_as_code() -> None:
    assert phrases.code_words("Hey Chill, your code is alpha bravo charlie") == [
        "alpha",
        "bravo",
        "charlie",
    ]


def test_transcript_must_contain_every_code_word() -> None:
    phrase = "Hey Chill, your code is alpha bravo charlie"
    assert phrases.matches(phrase, "hey chill your code is alpha bravo charlie")
    assert not phrases.matches(phrase, "hey chill your code is alpha bravo")


def test_word_order_does_not_matter() -> None:
    phrase = "Hey Chill, your code is alpha bravo charlie"
    # STT reorders short word sequences; a reordering is still the same words.
    assert phrases.matches(phrase, "charlie alpha bravo")


def test_extra_words_are_ignored() -> None:
    phrase = "Hey Chill, your code is delta echo foxtrot"
    assert phrases.matches(phrase, "okay chill please say delta echo foxtrot now")


def test_wrong_words_do_not_match() -> None:
    phrase = "Hey Chill, your code is alpha bravo charlie"
    assert not phrases.matches(phrase, "hey chill your code is alpha bravo delta")


def test_empty_transcript_does_not_match() -> None:
    assert not phrases.matches("Hey Chill, your code is alpha bravo charlie", "")
