"""Size limits for what people send. The frontend mirrors these in src/lib/limits.ts (keep the two in step)."""

# Voice notes: 16 kHz mono 16-bit WAV, as the app records them (src/lib/wav.ts).
VOICE_MAX_SECONDS = 30
VOICE_MIN_SECONDS = 0.3
VOICE_MAX_BYTES = 16_000 * 2 * VOICE_MAX_SECONDS + 4096  # 30 s of audio plus room for the WAV header

# Profile photos: the app uploads a 256 px square of a few tens of KB.
AVATAR_MAX_BYTES = 512 * 1024

CHAT_TEXT_MAX = 4000
