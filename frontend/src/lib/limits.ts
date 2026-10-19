/** Size limits, mirroring backend/app/core/limits.py (keep the two in step). The server enforces them; checking
 *  here too gives a clear message before anything is uploaded. */
export const VOICE_MAX_SECONDS = 30;
export const VOICE_MIN_SECONDS = 0.3;
export const VOICE_MAX_BYTES = 16_000 * 2 * VOICE_MAX_SECONDS + 4096;

export const AVATAR_MAX_BYTES = 512 * 1024;
/** Largest original photo the browser will try to crop (only the small square it makes is uploaded). */
export const AVATAR_MAX_INPUT_BYTES = 20 * 1024 * 1024;

export const CHAT_TEXT_MAX = 4000;
