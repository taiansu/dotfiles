"""CLI destination selection and live ownership guard, without model requests."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

COMMAND = Path(__file__).resolve().parents[1] / "home/dot-local/bin/hop"
OMP = shutil.which("omp")


class DestinationSelectionTest(unittest.TestCase):
    def test_explicit_host_overrides_environment_and_missing_target_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="hop-host-") as directory:
            missing_session = Path(directory) / "absent.jsonl"
            cases = [
                ("missing target", None, [], 2),
                ("environment target", "workbox", [], 1),
                ("explicit overrides invalid environment", "-invalid-env", ["--host", "devbox"], 1),
                ("invalid explicit overrides environment", "workbox", ["--host=-invalid-cli"], 2),
                ("empty environment", "", [], 2),
                ("blank environment", "   ", [], 2),
            ]
            for label, host_env, flags, expected_exit in cases:
                with self.subTest(label=label):
                    env = dict(os.environ)
                    env.pop("HOP_HOST", None)
                    if host_env is not None:
                        env["HOP_HOST"] = host_env
                    result = subprocess.run(
                        [sys.executable, str(COMMAND), str(missing_session), *flags],
                        capture_output=True, text=True, env=env, timeout=10,
                    )
                    # Configured destinations reach the missing input (exit 1).
                    # Invalid/missing destinations fail argument validation (exit 2).
                    # No case can read a session or initiate SSH.
                    self.assertEqual(result.returncode, expected_exit, result.stderr)


@unittest.skipUnless(OMP, "OMP executable is required for the ownership integration test")
class SourceOwnershipTest(unittest.TestCase):
    def test_live_source_is_refused_before_contacting_destination(self):
        with tempfile.TemporaryDirectory(prefix="hop-ownership-") as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            session = root / "session.jsonl"
            session_id = str(uuid.uuid4())
            session.write_text(json.dumps({
                "type": "session", "version": 3, "id": session_id,
                "timestamp": "2026-01-01T00:00:00.000Z", "cwd": str(project),
            }) + "\n")
            env = {**os.environ, "PI_CODING_AGENT_DIR": str(root / "agent")}
            env.pop("OMP_PROFILE", None)
            with (root / "agent.log").open("wb") as log:
                process = subprocess.Popen([
                    OMP, "--mode", "rpc", "--no-ui", "--resume", str(session),
                    "--no-context-files", "--no-skills", "--no-extensions", "--no-rules",
                ], stdin=subprocess.PIPE, stdout=log, stderr=log, env=env, cwd=project)
                try:
                    deadline = time.monotonic() + 20
                    while True:
                        lease = subprocess.run([
                            OMP, "session", "lease", "--json", "--", session_id,
                        ], capture_output=True, text=True, env=env, timeout=10, check=True)
                        if session_id in json.loads(lease.stdout)["held"]:
                            break
                        if process.poll() is not None or time.monotonic() >= deadline:
                            self.fail("Fixture OMP did not acquire the session: " + (root / "agent.log").read_text())
                        time.sleep(0.1)
                    before = hashlib.sha256(session.read_bytes()).hexdigest()
                    result = subprocess.run([
                        sys.executable, str(COMMAND), str(session), "--host", "must-not-contact.invalid",
                    ], capture_output=True, text=True, env=env, timeout=15)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Source session is live", result.stderr)
                    self.assertNotIn("Checking must-not-contact", result.stderr)
                    self.assertEqual(hashlib.sha256(session.read_bytes()).hexdigest(), before)
                    self.assertIsNone(process.poll())
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    if process.stdin:
                        process.stdin.close()


if __name__ == "__main__":
    unittest.main()
