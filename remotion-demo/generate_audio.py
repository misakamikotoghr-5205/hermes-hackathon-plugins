"""Generate a 75-second stereo WAV soundtrack (ambient synth pad + scene chimes + terminal UI cues)
for the Remotion Hermes Hackathon showcase video.
"""

from __future__ import annotations

import math
from pathlib import Path
import wave
import numpy as np

SAMPLE_RATE = 44100
DURATION = 75.0


def main() -> None:
    out_path = Path(__file__).resolve().parent / "public" / "soundtrack.wav"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = int(SAMPLE_RATE * DURATION)
    t = np.linspace(0.0, DURATION, n, endpoint=False, dtype=np.float32)

    # Warm futuristic ambient chord pad (C9 / Am9 progression shifting softly across chapters)
    pad_l = (
        0.045 * np.sin(2 * math.pi * 130.81 * t)
        + 0.035 * np.sin(2 * math.pi * 196.00 * t + 0.3 * np.sin(0.25 * t))
        + 0.028 * np.sin(2 * math.pi * 246.94 * t)
        + 0.022 * np.sin(2 * math.pi * 293.66 * t)
    )
    pad_r = (
        0.045 * np.sin(2 * math.pi * 130.81 * t)
        + 0.035 * np.sin(2 * math.pi * 196.50 * t)
        + 0.028 * np.sin(2 * math.pi * 246.94 * t + 0.4 * np.cos(0.25 * t))
        + 0.022 * np.sin(2 * math.pi * 329.63 * t)
    )

    # Scene transition chimes at 0s, 8s, 30s, 52s, 69s
    chime_times = [0.05, 8.0, 30.0, 52.0, 69.0]
    chime_freqs = [(523.25, 659.25, 783.99), (587.33, 739.99, 880.0), (523.25, 659.25, 987.77), (440.0, 659.25, 880.0), (523.25, 783.99, 1046.50)]

    for ct, (f1, f2, f3) in zip(chime_times, chime_freqs):
        idx0 = int(ct * SAMPLE_RATE)
        length = int(1.6 * SAMPLE_RATE)
        idx1 = min(n, idx0 + length)
        dt = np.arange(idx1 - idx0, dtype=np.float32) / SAMPLE_RATE
        env = np.exp(-3.2 * dt) * (1.0 - np.exp(-60.0 * dt))
        tone = (
            0.09 * np.sin(2 * math.pi * f1 * dt)
            + 0.07 * np.sin(2 * math.pi * f2 * dt)
            + 0.05 * np.sin(2 * math.pi * f3 * dt)
        ) * env
        pad_l[idx0:idx1] += tone
        pad_r[idx0:idx1] += tone

    # Subtle confirmation / alert UI pings on key terminal events
    event_pings = [
        (1.1, 880.0), (2.0, 987.77), (2.9, 1046.50), (6.1, 1318.51),
        (10.2, 880.0), (15.2, 1046.50), (19.6, 440.0), (25.2, 987.77),
        (36.8, 880.0), (42.8, 1046.50), (47.5, 392.0),
        (54.1, 392.0), (58.2, 440.0), (65.5, 1046.50),
        (72.3, 1318.51),
    ]
    for et, freq in event_pings:
        idx0 = int(et * SAMPLE_RATE)
        length = int(0.35 * SAMPLE_RATE)
        idx1 = min(n, idx0 + length)
        dt = np.arange(idx1 - idx0, dtype=np.float32) / SAMPLE_RATE
        env = np.exp(-10.0 * dt)
        ping = 0.075 * np.sin(2 * math.pi * freq * dt) * env
        pad_l[idx0:idx1] += ping
        pad_r[idx0:idx1] += ping

    # Smooth fade-in and fade-out
    fade_samples = int(1.2 * SAMPLE_RATE)
    pad_l[:fade_samples] *= np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    pad_r[:fade_samples] *= np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    pad_l[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
    pad_r[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)

    stereo = np.stack([np.clip(pad_l, -0.95, 0.95), np.clip(pad_r, -0.95, 0.95)], axis=-1)
    pcm16 = (stereo * 32767.0).astype(np.int16)

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm16.tobytes())

    print("Generated soundtrack:", out_path, "size=", out_path.stat().st_size)


if __name__ == "__main__":
    main()
