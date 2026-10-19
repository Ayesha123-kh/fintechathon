"""Checks on voice notes before they reach the speech-to-text model."""

from dataclasses import dataclass


@dataclass
class WavInfo:
    sample_rate: int
    channels: int
    bits: int
    seconds: float


class BadAudio(ValueError):
    pass


def wav_info(data: bytes) -> WavInfo:
    """Read a PCM WAV file's format and length from its chunks (not by assuming a 44-byte header)."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise BadAudio("not a WAV file")
    fmt: tuple[int, int, int, int, int] | None = None
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], int.from_bytes(data[pos + 4:pos + 8], "little")
        body = pos + 8
        if cid == b"fmt " and size >= 16:
            f = data[body:body + 16]
            fmt = (int.from_bytes(f[0:2], "little"), int.from_bytes(f[2:4], "little"),
                   int.from_bytes(f[4:8], "little"), int.from_bytes(f[8:12], "little"),
                   int.from_bytes(f[14:16], "little"))
        elif cid == b"data":
            if not fmt:
                raise BadAudio("data before format")
            audio_format, channels, rate, byte_rate, bits = fmt
            if audio_format != 1 or not 1 <= channels <= 2 or not 8_000 <= rate <= 48_000 or bits != 16 or not byte_rate:
                raise BadAudio("only 16-bit PCM WAV")
            present = min(size, len(data) - body)  # a header may claim more than was sent
            return WavInfo(rate, channels, bits, present / byte_rate)
        pos = body + size + (size & 1)  # chunks are word aligned
    raise BadAudio("no audio data")
