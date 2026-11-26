"""Extract deterministic descriptors from an authorized, checksummed PCM WAV."""
import argparse
from datetime import date
import hashlib
from io import BytesIO
import json
from pathlib import Path
import wave

import numpy as np


def authorize(manifest, cutoff, processing):
    if not manifest["approval_ref"] or processing not in manifest["allowed_processing"]:
        raise ValueError(f"Audio processing is not authorized for {processing}")
    if not date.fromisoformat(manifest["available_on"]) <= cutoff:
        raise ValueError("Audio was unavailable at the cutoff")
    expires = manifest.get("rights_expire_on")
    if expires and date.today() >= date.fromisoformat(expires):
        raise ValueError("Audio processing rights have expired")
    if not manifest["recording_id"]:
        raise ValueError("Audio recording ID is required")


def extract(audio, manifest, cutoff, processing="local"):
    authorize(manifest, cutoff, processing)
    digest = hashlib.sha256(audio).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError("Audio checksum does not match manifest")

    with wave.open(BytesIO(audio), "rb") as recording:
        channels = recording.getnchannels()
        rate = recording.getframerate()
        frames = recording.getnframes()
        if recording.getsampwidth() != 2 or not 0 < frames <= rate * 900:
            raise ValueError("Expected nonempty 16-bit PCM WAV of at most 15 minutes")
        samples = np.frombuffer(recording.readframes(frames), dtype="<i2")
        if samples.size != frames * channels:
            raise ValueError("Truncated WAV")
        samples = samples.reshape(-1, channels).astype(np.float64) / 32768

    # Calculate signal energy over channels before mixing to avoid phase cancellation.
    rms = np.sqrt(np.mean(np.square(samples)))
    peak = np.max(np.abs(samples))
    block = max(1, rate // 10)
    window_count = frames // block
    if window_count:
        windows = samples[:window_count * block].reshape(window_count, block, channels)
        energies = np.sqrt(np.mean(np.square(windows), axis=(1, 2)))
        dynamics = np.quantile(energies, 0.95) - np.quantile(energies, 0.05)
    else:
        dynamics = 0.0
    return {
        "recording_id": manifest["recording_id"],
        "audio_sha256": digest,
        "extractor": "pcm-amplitude-v1",
        "duration_seconds": frames / rate,
        "rms_amplitude": float(rms),
        "peak_amplitude": float(peak),
        "amplitude_range_p95_p05": float(dynamics),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    authorize(manifest, args.as_of, "local")
    print(json.dumps(extract(args.wav.read_bytes(), manifest, args.as_of), indent=2))
