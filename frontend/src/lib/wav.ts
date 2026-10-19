/** Voice messages recorded straight to 16 kHz mono 16-bit WAV. MediaRecorder only makes WebM or MP4,
 *  which llama.cpp's speech-to-text server cannot decode (it reads WAV, MP3 and FLAC by itself). */
const RATE = 16000;

export type WavRecorder = { stop: () => Promise<Blob>; cancel: () => void };

/** Call straight from the click handler: the AudioContext is created before the first await, while the
 *  click still counts as a user gesture (Safari will not start audio otherwise). */
export async function recordWav(): Promise<WavRecorder> {
  const ctx = new AudioContext();
  let stream: MediaStream | undefined;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    await ctx.audioWorklet.addModule("/pcm-recorder.js");
    if (ctx.state === "suspended") await ctx.resume();
  } catch (e) {
    stream?.getTracks().forEach((t) => t.stop());
    void ctx.close();
    throw e;
  }
  const source = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, "pcm-recorder");
  const chunks: Float32Array[] = [];
  let flushed: (() => void) | undefined;
  node.port.onmessage = (e: MessageEvent<Float32Array | { final: Float32Array }>) => {
    if (e.data instanceof Float32Array) chunks.push(e.data);
    else {
      chunks.push(e.data.final);
      flushed?.();
    }
  };
  source.connect(node);
  node.connect(ctx.destination); // outputs silence; keeps the node in the rendered graph in every browser

  const rate = ctx.sampleRate;
  const release = () => {
    source.disconnect();
    node.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    void ctx.close();
  };
  return {
    stop: async () => {
      await new Promise<void>((resolve) => {
        flushed = resolve;
        node.port.postMessage("flush");
      });
      release();
      const pcm = join(chunks);
      return rate > RATE ? encodeWav(downsample(pcm, rate), RATE) : encodeWav(pcm, rate);
    },
    cancel: release,
  };
}

function join(chunks: Float32Array[]): Float32Array {
  const out = new Float32Array(chunks.reduce((n, c) => n + c.length, 0));
  let at = 0;
  for (const c of chunks) {
    out.set(c, at);
    at += c.length;
  }
  return out;
}

/** Averages the input samples each output sample covers: a cheap low-pass, then decimation. */
function downsample(pcm: Float32Array, rate: number): Float32Array {
  const ratio = rate / RATE;
  const out = new Float32Array(Math.floor(pcm.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const from = Math.floor(i * ratio);
    const to = Math.min(pcm.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = from; j < to; j++) sum += pcm[j];
    out[i] = sum / Math.max(1, to - from);
  }
  return out;
}

function encodeWav(pcm: Float32Array, rate: number): Blob {
  const out = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const ascii = (at: number, s: string) => [...s].forEach((c, i) => out.setUint8(at + i, c.charCodeAt(0)));
  ascii(0, "RIFF");
  out.setUint32(4, 36 + pcm.length * 2, true);
  ascii(8, "WAVE");
  ascii(12, "fmt ");
  out.setUint32(16, 16, true); // fmt chunk size
  out.setUint16(20, 1, true); // PCM
  out.setUint16(22, 1, true); // mono
  out.setUint32(24, rate, true);
  out.setUint32(28, rate * 2, true); // byte rate
  out.setUint16(32, 2, true); // block align
  out.setUint16(34, 16, true); // bits per sample
  ascii(36, "data");
  out.setUint32(40, pcm.length * 2, true);
  pcm.forEach((v, i) => out.setInt16(44 + i * 2, Math.max(-1, Math.min(1, v)) * 0x7fff, true));
  return new Blob([out], { type: "audio/wav" });
}
