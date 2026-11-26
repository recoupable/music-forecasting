from datetime import date
import hashlib
from io import BytesIO
import struct
import unittest
import wave

from forecasting.audio import extract


class AudioTests(unittest.TestCase):
    def setUp(self):
        wav = BytesIO()
        with wave.open(wav, "wb") as recording:
            recording.setparams((2, 2, 8000, 0, "NONE", "not compressed"))
            recording.writeframes(struct.pack("<hh", 16384, -16384) * 800)
        self.wav = wav.getvalue()
        self.manifest = {
            "recording_id": "synthetic",
            "approval_ref": "generated WAV",
            "available_on": "2021-01-01",
            "allowed_processing": ["local"],
            "sha256": hashlib.sha256(self.wav).hexdigest(),
        }
        self.cutoff = date(2021, 1, 2)

    def test_extracts_deterministic_amplitude(self):
        result = extract(self.wav, self.manifest, self.cutoff)
        self.assertEqual(result["duration_seconds"], 0.1)
        self.assertEqual(result["rms_amplitude"], 0.5)
        self.assertEqual(result["peak_amplitude"], 0.5)

    def test_rejects_unapproved_cloud_processing(self):
        with self.assertRaisesRegex(ValueError, "not authorized"):
            extract(self.wav, self.manifest, self.cutoff, "modal")

    def test_checks_source_hash(self):
        with self.assertRaisesRegex(ValueError, "checksum"):
            extract(self.wav + b"suffix", self.manifest, self.cutoff)

    def test_rejects_audio_available_after_cutoff(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            extract(self.wav, self.manifest, date(2020, 12, 31))
