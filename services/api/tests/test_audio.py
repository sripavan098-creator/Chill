"""Audio pipeline tests: decoding, resampling, voice activity and quality."""

from __future__ import annotations

import io
import math
import struct
import wave

import numpy as np
import pytest

from app.core.audio import (
    TARGET_SAMPLE_RATE,
    AudioDecodeError,
    analyse,
    decode_audio,
    detect_speech,
    fingerprint,
    prepare,
    resample,
)
from tests.conftest import silence_wav, synth_speech


def wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(
            np.clip(np.round(samples * 32767), -32768, 32767).astype("<i2").tobytes()
        )
    return buffer.getvalue()


def test_decode_wav_returns_mono_float() -> None:
    samples, rate = decode_audio(synth_speech(seed=1))
    assert rate == TARGET_SAMPLE_RATE
    assert samples.ndim == 1
    assert samples.dtype == np.float32
    assert 0.0 < float(np.max(np.abs(samples))) <= 1.0


def test_decode_rejects_garbage() -> None:
    with pytest.raises(AudioDecodeError):
        decode_audio(b"\xff\xfe\x00\x01 not audio at all")


def test_decode_rejects_empty() -> None:
    with pytest.raises(AudioDecodeError):
        decode_audio(b"")


def test_resample_changes_length_proportionally() -> None:
    samples = np.sin(2 * math.pi * 220 * np.arange(8000) / 8000).astype(np.float32)
    out = resample(samples, 8000, TARGET_SAMPLE_RATE)
    assert out.size == pytest.approx(16_000, rel=0.02)


def test_resample_is_a_noop_at_target_rate() -> None:
    samples = np.zeros(1000, dtype=np.float32)
    out = resample(samples, TARGET_SAMPLE_RATE, TARGET_SAMPLE_RATE)
    assert out is not samples
    assert np.array_equal(out, samples)


def test_detect_speech_finds_the_signal_not_the_silence() -> None:
    silence = np.zeros(TARGET_SAMPLE_RATE // 2, dtype=np.float32)
    tone = 0.5 * np.sin(2 * math.pi * 200 * np.arange(TARGET_SAMPLE_RATE) / TARGET_SAMPLE_RATE)
    samples = np.concatenate([silence, tone.astype(np.float32), silence])

    start, end, snr = detect_speech(samples, TARGET_SAMPLE_RATE)

    # The detected region must sit around the tone (frame granularity means it
    # can start one hop early) and exclude the silent head and tail.
    assert 0 < start < silence.size
    assert silence.size < end < samples.size
    assert snr > 20.0


def test_detect_speech_returns_nothing_for_silence() -> None:
    silence = np.zeros(TARGET_SAMPLE_RATE, dtype=np.float32)
    start, end, snr = detect_speech(silence, TARGET_SAMPLE_RATE)
    assert (start, end) == (0, 0)
    assert snr == 0.0


def test_analyse_trims_surrounding_silence() -> None:
    silence = np.zeros(TARGET_SAMPLE_RATE, dtype=np.float32)
    tone = (
        0.5 * np.sin(2 * math.pi * 200 * np.arange(TARGET_SAMPLE_RATE) / TARGET_SAMPLE_RATE)
    ).astype(np.float32)
    samples = np.concatenate([silence, tone, silence])

    trimmed, report = analyse(samples, TARGET_SAMPLE_RATE)

    assert trimmed.size < samples.size
    assert report.duration_ms == pytest.approx(3000, abs=20)
    assert report.speech_ms < report.duration_ms


def test_quality_reports_silence_as_unusable() -> None:
    _, report = analyse(np.zeros(TARGET_SAMPLE_RATE, dtype=np.float32), TARGET_SAMPLE_RATE)
    problems = report.problems(min_speech_ms=300, min_snr_db=3.0, max_clipping=0.05)
    assert "silent" in problems
    assert "too_little_speech" in problems


def test_quality_flags_clipping() -> None:
    clipped = np.ones(TARGET_SAMPLE_RATE, dtype=np.float32)
    _, report = analyse(clipped, TARGET_SAMPLE_RATE)
    assert report.clipping_ratio > 0.9
    assert "clipping" in report.problems(
        min_speech_ms=300, min_snr_db=3.0, max_clipping=0.05
    )


def test_prepare_accepts_speech_like_audio() -> None:
    decoded = prepare(synth_speech(seed=7))
    assert decoded.sample_rate == TARGET_SAMPLE_RATE
    assert decoded.quality.problems(
        min_speech_ms=300, min_snr_db=3.0, max_clipping=0.05
    ) == []


def test_prepare_rejects_silence_at_the_quality_gate() -> None:
    decoded = prepare(silence_wav())
    problems = decoded.quality.problems(
        min_speech_ms=300, min_snr_db=3.0, max_clipping=0.05
    )
    assert problems


def test_fingerprint_is_stable_and_content_addressed() -> None:
    samples = np.linspace(-0.5, 0.5, 5000, dtype=np.float32)
    assert fingerprint(samples, TARGET_SAMPLE_RATE) == fingerprint(
        samples, TARGET_SAMPLE_RATE
    )
    assert fingerprint(samples, TARGET_SAMPLE_RATE) != fingerprint(
        samples + 0.1, TARGET_SAMPLE_RATE
    )


def test_fingerprint_ignores_container_but_not_content() -> None:
    """The digest covers decoded samples, so the same PCM in two containers matches."""
    samples = np.array([1000, -2000, 3000, -4000] * 1000, dtype="<i2")
    pcm = samples.tobytes()
    as_wav = wav_bytes(samples.astype(np.float32) / 32768.0, TARGET_SAMPLE_RATE)

    from_wav, _ = decode_audio(as_wav)
    from_raw, _ = decode_audio(pcm)

    assert fingerprint(from_wav, TARGET_SAMPLE_RATE) == fingerprint(
        from_raw, TARGET_SAMPLE_RATE
    )
    assert fingerprint(from_raw, TARGET_SAMPLE_RATE) != fingerprint(
        from_raw + 0.05, TARGET_SAMPLE_RATE
    )


def test_decode_accepts_headerless_pcm() -> None:
    """Some recorders hand back raw PCM; the fallback must not crash."""
    raw = struct.pack("<2000h", *([1000] * 2000))
    samples, rate = decode_audio(raw)
    assert rate == TARGET_SAMPLE_RATE
    assert samples.size == 2000
