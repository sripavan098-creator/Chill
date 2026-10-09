"""Audio decoding, voice activity detection and sample quality.

The mobile app uploads whatever container the platform recorder produced (m4a
on iOS/Android, webm or wav elsewhere), so the backend has to normalise before
it can embed anything. This module decodes to mono 16 kHz float32, trims
leading and trailing silence, and reports measurements the API uses to reject
unusable samples.

Nothing here writes to disk or logs audio content: the samples live in the
request-scoped arrays and are dropped when the request ends.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TARGET_SAMPLE_RATE = 16_000

# Voice activity detection. Frames are 20 ms with a 10 ms hop, which is short
# enough to catch a clipped word boundary without being expensive.
FRAME_MS = 20
HOP_MS = 10
# A frame counts as speech when its energy clears the noise floor by this
# factor, or reaches this fraction of the loudest frame. Both anchors matter:
# the noise-floor term copes with a quiet recording in a noisy room, the
# peak term copes with continuous speech that never drops to a real pause.
SPEECH_FLOOR_MULTIPLIER = 3.0
SPEECH_PEAK_FRACTION = 0.1
MIN_SPEECH_RUN_MS = 100
# Silence kept around the detected speech so the encoder does not see a hard cut.
PADDING_MS = 150


class AudioDecodeError(ValueError):
    """Raised when the uploaded bytes cannot be interpreted as audio."""


@dataclass(frozen=True)
class QualityReport:
    """Measurements for one decoded sample."""

    duration_ms: int
    speech_ms: int
    speech_ratio: float
    snr_db: float
    clipping_ratio: float
    peak: float

    def problems(self, *, min_speech_ms: int, min_snr_db: float, max_clipping: float) -> list[str]:
        """Return human-readable reasons this sample is unusable."""
        issues: list[str] = []
        if self.speech_ms < min_speech_ms:
            issues.append("too_little_speech")
        if self.snr_db < min_snr_db:
            issues.append("too_noisy")
        if self.clipping_ratio > max_clipping:
            issues.append("clipping")
        if self.peak < 0.01:
            issues.append("silent")
        return issues


@dataclass(frozen=True)
class DecodedAudio:
    """A decoded, trimmed, mono sample plus its quality measurements."""

    samples: np.ndarray
    sample_rate: int
    quality: QualityReport


def _decode_with_av(data: bytes) -> tuple[np.ndarray, int]:
    import av

    try:
        container = av.open(_BytesReader(data), format=None)
    except Exception as exc:  # noqa: BLE001 - any decoder failure is the same to callers
        raise AudioDecodeError("Could not decode the audio container.") from exc

    try:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise AudioDecodeError("The upload contains no audio stream.")

        chunks: list[np.ndarray] = []
        for frame in container.decode(stream):
            array = frame.to_ndarray()
            # PyAV returns (channels, samples) for planar formats and
            # (1, samples) for packed ones. Collapse to mono either way.
            if array.ndim == 2:
                array = array.mean(axis=0)
            chunks.append(array.astype(np.float32))

        if not chunks:
            raise AudioDecodeError("The audio stream was empty.")

        samples = np.concatenate(chunks)
        # Integer PCM arrives as int16/int32 scaled to full range.
        if stream.format.name in {"s16", "s16p"}:
            samples = samples / 32768.0
        elif stream.format.name in {"s32", "s32p"}:
            samples = samples / 2147483648.0
        elif stream.format.name in {"u8", "u8p"}:
            samples = (samples - 128.0) / 128.0

        return samples.astype(np.float32), int(stream.rate)
    finally:
        container.close()


class _BytesReader:
    """Minimal file-like object so PyAV can read from memory."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk = self._data[self._offset :]
            self._offset = len(self._data)
            return chunk
        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._offset = offset
        elif whence == 1:
            self._offset += offset
        else:
            self._offset = max(len(self._data) + offset, 0)
        return self._offset

    def tell(self) -> int:
        return self._offset

    def close(self) -> None:  # pragma: no cover - PyAV calls this defensively
        pass


def _decode_raw_pcm(data: bytes) -> tuple[np.ndarray, int]:
    """Fallback for headerless 16-bit little-endian PCM at the target rate."""
    if len(data) % 2 != 0:
        raise AudioDecodeError("Could not decode the audio container.")
    samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    if samples.size == 0:
        raise AudioDecodeError("The audio stream was empty.")
    return samples, TARGET_SAMPLE_RATE


def decode_audio(data: bytes) -> tuple[np.ndarray, int]:
    """Decode arbitrary audio bytes to mono float32.

    Returns the samples and their original sample rate. Raises
    `AudioDecodeError` when the bytes are not recognisable audio.
    """
    if not data:
        raise AudioDecodeError("The sample is empty.")

    try:
        return _decode_with_av(data)
    except AudioDecodeError:
        # Raw PCM has no container for PyAV to sniff; try it as a last resort.
        return _decode_raw_pcm(data)


def _resample_numpy(
    samples: np.ndarray, source_rate: int, target_rate: int
) -> np.ndarray:
    """Linear-interpolation resampler.

    Used when torchaudio is not installed (the `speaker` extra is optional), so
    decoding a non-16 kHz recording does not fail on a base install. Lower
    quality than the sinc resampler, which is why torchaudio is preferred when
    present.
    """
    if samples.size == 0 or source_rate <= 0 or target_rate <= 0:
        return samples.astype(np.float32)
    duration = samples.size / source_rate
    target_count = max(int(round(duration * target_rate)), 1)
    source_positions = np.arange(samples.size, dtype=np.float64)
    target_positions = np.linspace(0.0, samples.size - 1, target_count)
    return np.interp(target_positions, source_positions, samples).astype(np.float32)


def resample(samples: np.ndarray, source_rate: int, target_rate: int = TARGET_SAMPLE_RATE):
    """Resample to the target rate.

    Prefers torchaudio's sinc resampler and falls back to linear interpolation
    when the optional `speaker` extra is not installed.
    """
    if source_rate == target_rate:
        return samples.astype(np.float32)

    try:
        import torch
        import torchaudio
    except ImportError:
        return _resample_numpy(samples, source_rate, target_rate)

    tensor = torch.from_numpy(samples.astype(np.float32))
    resampled = torchaudio.functional.resample(tensor, source_rate, target_rate)
    return resampled.numpy().astype(np.float32)


def _frame_energies(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, int]:
    frame = max(int(sample_rate * FRAME_MS / 1000), 1)
    hop = max(int(sample_rate * HOP_MS / 1000), 1)
    if samples.size < frame:
        return np.array([float(np.sqrt(np.mean(samples**2)))], dtype=np.float32), hop

    # Sliding RMS without materialising a 2-D view of the whole signal.
    squared = np.square(samples, dtype=np.float64)
    cumulative = np.concatenate(([0.0], np.cumsum(squared)))
    starts = np.arange(0, samples.size - frame + 1, hop)
    energy = (cumulative[starts + frame] - cumulative[starts]) / frame
    return np.sqrt(energy).astype(np.float32), hop


def detect_speech(samples: np.ndarray, sample_rate: int) -> tuple[int, int, float]:
    """Return (start, end, snr_db) for the speech region of a sample.

    Uses an energy threshold set relative to the noise floor, so it adapts to
    the recording level instead of assuming a fixed volume.
    """
    energies, hop = _frame_energies(samples, sample_rate)
    if energies.size == 0:
        return 0, samples.size, 0.0

    noise_floor = float(np.percentile(energies, 20))
    peak = float(np.max(energies))
    # Take the lower of the two anchors. Using the higher would mean a
    # recording with no real pauses (where the noise floor sits close to the
    # peak) has no frame above threshold and reports no speech at all.
    threshold = max(
        min(noise_floor * SPEECH_FLOOR_MULTIPLIER, peak * SPEECH_PEAK_FRACTION), 1e-4
    )

    is_speech = energies > threshold
    min_run = max(int(MIN_SPEECH_RUN_MS / HOP_MS), 1)

    # Keep runs of speech long enough to be a word.
    runs: list[tuple[int, int]] = []
    start_index: int | None = None
    for index, active in enumerate(is_speech):
        if active and start_index is None:
            start_index = index
        elif not active and start_index is not None:
            runs.append((start_index, index))
            start_index = None
    if start_index is not None:
        runs.append((start_index, len(is_speech)))
    runs = [run for run in runs if run[1] - run[0] >= min_run]

    if not runs:
        # No speech found. Reporting the whole sample as speech here would hide
        # silence from the quality gate, so report an empty speech region.
        return 0, 0, 0.0

    first = runs[0][0] * hop
    last = min(runs[-1][1] * hop, samples.size)

    speech_energy = float(np.mean([energies[s:e].mean() for s, e in runs]))
    noise_mask = np.ones(energies.size, dtype=bool)
    for s, e in runs:
        noise_mask[s:e] = False
    if noise_mask.any():
        noise_energy = float(energies[noise_mask].mean())
    else:
        # Continuous speech with no pauses: fall back to the low percentile as
        # the noise estimate. Using a floor constant here would report a
        # perfect SNR for a noisy recording and defeat the noise gate.
        noise_energy = max(noise_floor, 1e-6)

    snr_db = 20.0 * np.log10(max(speech_energy, 1e-6) / max(noise_energy, 1e-6))
    return first, last, float(snr_db)


def analyse(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, QualityReport]:
    """Trim silence and measure quality.

    Returns the trimmed samples and a `QualityReport`. Trimming uses a short
    padding so the encoder still sees natural onsets and offsets.
    """
    start, end, snr_db = detect_speech(samples, sample_rate)

    padding = int(sample_rate * PADDING_MS / 1000)
    trimmed = samples[max(start - padding, 0) : min(end + padding, samples.size)]
    if trimmed.size == 0:
        trimmed = samples

    speech_ms = int(round((end - start) / sample_rate * 1000))
    duration_ms = int(round(samples.size / sample_rate * 1000))
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    clipping_ratio = float(np.mean(np.abs(samples) >= 0.99)) if samples.size else 0.0

    report = QualityReport(
        duration_ms=duration_ms,
        speech_ms=max(speech_ms, 0),
        speech_ratio=min(speech_ms / duration_ms, 1.0) if duration_ms else 0.0,
        snr_db=round(snr_db, 2),
        clipping_ratio=round(clipping_ratio, 5),
        peak=round(peak, 4),
    )
    return trimmed, report


def prepare(data: bytes) -> DecodedAudio:
    """Decode, resample, trim and measure in one step."""
    samples, source_rate = decode_audio(data)
    samples = resample(samples, source_rate)
    trimmed, report = analyse(samples, TARGET_SAMPLE_RATE)
    return DecodedAudio(samples=trimmed, sample_rate=TARGET_SAMPLE_RATE, quality=report)


def fingerprint(samples: np.ndarray, sample_rate: int) -> str:
    """Stable hash of the decoded audio content.

    Used to check that the five enrollment phrases are five distinct
    recordings. The digest covers decoded samples rather than uploaded bytes,
    so re-encoding the same recording does not produce a different value. It is
    not reversible and no audio is retained.
    """
    import hashlib

    resampled = resample(samples, sample_rate, TARGET_SAMPLE_RATE)
    # Quantise to 16-bit so tiny decoder differences do not change the digest.
    # The scale matches the decoder (32768) so an int16 sample maps back to
    # itself through a decode/encode round trip.
    quantised = np.clip(np.round(resampled * 32768.0), -32768, 32767).astype("<i2")
    return hashlib.sha256(quantised.tobytes()).hexdigest()
