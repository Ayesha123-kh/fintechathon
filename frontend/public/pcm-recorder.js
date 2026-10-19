// AudioWorklet for voice messages (see src/lib/wav.ts): hands the page the microphone's raw samples
// (first channel) in blocks of 4096, so the main thread is not woken for every 128-sample quantum.
class PcmRecorder extends AudioWorkletProcessor {
  constructor() {
    super();
    this.block = new Float32Array(4096);
    this.filled = 0;
    // "flush": the recording is over, send what is left.
    this.port.onmessage = () => {
      this.port.postMessage({ final: this.block.slice(0, this.filled) });
      this.filled = 0;
    };
  }

  process(inputs) {
    const input = inputs[0][0];
    if (input) {
      for (let i = 0; i < input.length; i++) {
        this.block[this.filled++] = input[i];
        if (this.filled === this.block.length) {
          this.port.postMessage(this.block.slice());
          this.filled = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor("pcm-recorder", PcmRecorder);
