"""Unit and contract tests for hop_remote edge cases."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

LIBEXEC_DIR = Path(__file__).resolve().parents[1] / "home" / "dot-local" / "libexec" / "dotfiles"
if str(LIBEXEC_DIR) not in sys.path:
    sys.path.insert(0, str(LIBEXEC_DIR))

import hop_remote  # noqa: E402


class SessionHeaderAndNameTests(unittest.TestCase):
    def test_extract_session_id_handles_unpacked_leading_title_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "2026-11-03T00-00-00-000Z_abc12345.jsonl"
            session_file.write_text(
                json.dumps({"type": "title", "v": 1, "title": "", "updatedAt": "2026-11-03T00:00:00.000Z"})
                + "\n"
                + json.dumps(
                    {
                        "type": "session",
                        "id": "abc12345",
                        "timestamp": "2026-11-03T00:00:00.000Z",
                        "cwd": tmp,
                        "version": 3,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(hop_remote.extract_session_id(session_file), "abc12345")

    def test_extract_session_id_rejects_missing_session_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_file = Path(tmp) / "invalid.jsonl"
            bad_file.write_text(json.dumps({"type": "title", "v": 1, "title": "only-title"}) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                hop_remote.extract_session_id(bad_file)

    def test_validate_session_name_rejects_default_and_unsafe_names(self) -> None:
        for invalid in ("", "   ", "default", "DEFAULT", ".", "..", "bad/name", "bad name", "bad;name"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    hop_remote.validate_session_name(invalid)

        self.assertEqual(hop_remote.validate_session_name("omp-handoff-1a2b3c4d5e6f"), "omp-handoff-1a2b3c4d5e6f")


if __name__ == "__main__":
    unittest.main()
