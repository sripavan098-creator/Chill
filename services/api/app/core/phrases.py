"""Spoken challenge phrases.

A v0.5 challenge asks the speaker to say a specific phrase, not just to make a
sound. The server generates the phrase, stores it with the nonce, and later
compares what the speaker actually said against it.

Matching is deliberately lenient. Speech-to-text on a phone microphone
mis-hears words, drops small numbers and mis-orders them, and transcribes the
same utterance differently across models. A strict equality check would lock
owners out for reasons unrelated to identity, which pushes them to the PIN
fallback and weakens the voice layer's usefulness. So the phrase is accepted
when its distinguishing words are present, allowing for the words the assistant
adds around them ("hey chill, ...").

This is not a liveness detector. A determined attacker can read the phrase
aloud over a replayed recording; the phrase raises the cost of a blind replay
and is honest about being one layer, not the boundary.
"""

from __future__ import annotations

import re
import secrets

# Small numbers are hard for STT to transcribe reliably, so each word is a
# distinct, common, phonetically spread item.
CODE_WORDS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf")

# Words the speaker is expected to say before the code. They are ignored during
# matching: the STT model may drop the wake word or render it differently, and
# a missing "hey chill" says nothing about identity.
FILLER_WORDS = frozenset(
    {
        "hey",
        "hi",
        "hello",
        "chill",
        "okay",
        "ok",
        "the",
        "is",
        "your",
        "my",
        "code",
        "word",
        "please",
        "say",
    }
)

_WORD_RE = re.compile(r"[a-z0-9]+")


def generate_phrase() -> str:
    """Return a phrase like ``Hey Chill, your code is alpha bravo charlie``.

    Three distinct words give 210 ordered combinations, which is enough to make
    guessing the phrase in advance impractical without needing a longer code
    that is harder to say and to transcribe.
    """
    words = secrets.SystemRandom().sample(CODE_WORDS, 3)
    return f"Hey Chill, your code is {words[0]} {words[1]} {words[2]}"


def code_words(phrase: str) -> list[str]:
    """Return the distinguishing (non-filler) words of a phrase."""
    return [
        word for word in _WORD_RE.findall(phrase.lower()) if word not in FILLER_WORDS
    ]


def matches(phrase: str, transcript: str) -> bool:
    """Return whether `transcript` says `phrase`.

    The distinguishing words of the phrase must all appear in the transcript.
    Order is not required: Whisper and Vosk reorder short digit/word sequences
    often enough that requiring it would reject genuine attempts. Extra words
    are ignored.
    """
    expected = code_words(phrase)
    if not expected:
        return False
    heard = set(_WORD_RE.findall(transcript.lower()))
    return all(word in heard for word in expected)
