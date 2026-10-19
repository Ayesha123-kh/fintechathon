import pytest

from app.services.voice import BadAudio, wav_info


def wav(seconds: float, rate: int = 16_000, channels: int = 1, bits: int = 16, fmt: int = 1, extra: bytes = b"") -> bytes:
    data = b"\0" * int(rate * channels * bits // 8 * seconds)
    block = channels * bits // 8
    fmt_chunk = (b"fmt " + (16).to_bytes(4, "little") + fmt.to_bytes(2, "little") + channels.to_bytes(2, "little")
                 + rate.to_bytes(4, "little") + (rate * block).to_bytes(4, "little") + block.to_bytes(2, "little")
                 + bits.to_bytes(2, "little"))
    body = b"WAVE" + fmt_chunk + extra + b"data" + len(data).to_bytes(4, "little") + data
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def test_length_comes_from_the_format_chunk():
    assert wav_info(wav(30)).seconds == pytest.approx(30)
    assert wav_info(wav(2.5, rate=48_000, channels=2)).seconds == pytest.approx(2.5)


def test_extra_chunks_before_the_audio_are_skipped():
    extra = b"LIST" + (5).to_bytes(4, "little") + b"hello\0"  # odd size: padded to a word
    assert wav_info(wav(1, extra=extra)).seconds == pytest.approx(1)


def test_a_header_claiming_more_audio_than_was_sent_counts_only_what_arrived():
    data = wav(10)
    assert wav_info(data[: 44 + 16_000 * 2 * 3]).seconds == pytest.approx(3)


@pytest.mark.parametrize("data", [
    b"", b"ID3\x04 not a wav", b"RIFF\0\0\0\0WAVE",
    wav(1, fmt=3, bits=32),  # float samples
    wav(1, bits=8),
])
def test_anything_but_16_bit_pcm_wav_is_refused(data):
    with pytest.raises(BadAudio):
        wav_info(data)
