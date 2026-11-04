from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBEXEC_DIR = REPO_ROOT / "home" / "dot-local" / "libexec" / "dotfiles"
if str(LIBEXEC_DIR) not in sys.path:
    sys.path.insert(0, str(LIBEXEC_DIR))

from hop_project import (  # noqa: E402
    HandoffProjectError,
    main as hop_project_main,
    pack_project,
    unpack_project,
)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
    ):
        env.pop(key, None)
    env["GIT_AUTHOR_NAME"] = "Test User"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test User"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        [
            "git",
            "-C",
            str(cwd),
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.fileMode=true",
            "-c",
            "core.symlinks=true",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        capture_output=True,
        env=env,
        check=True,
    )


def _tree_state(root: Path) -> dict[str, tuple[str, object, bool]]:
    """Capture normalized relative paths -> (kind, payload, is_executable) excluding .git."""
    state: dict[str, tuple[str, object, bool]] = {}
    for current_root, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        curr = Path(current_root)
        if curr == root and ".git" in dirnames:
            dirnames.remove(".git")
        for name in [*dirnames, *filenames]:
            full = curr / name
            rel = unicodedata.normalize("NFC", full.relative_to(root).as_posix())
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                state[rel] = ("symlink", os.readlink(full), False)
            elif stat.S_ISREG(st.st_mode):
                state[rel] = ("file", full.read_bytes(), bool(st.st_mode & 0o111))
    return state


class HandoffProjectTests(unittest.TestCase):
    def _init_repo(self, path: Path, branch: str = "main") -> None:
        path.mkdir(parents=True, exist_ok=True)
        _git(path, "init", "-q")
        _git(path, "checkout", "-q", "-B", branch)

    def test_pack_and_unpack_preserves_staged_unstaged_binary_deletions_unicode_symlinks_and_excludes_ignored(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "source repo with spaces"
            staging = tmp_path / "staging"
            staging.mkdir(mode=0o700)
            dest = tmp_path / "dest-workspace"

            self._init_repo(repo, branch="feat/handoff-snapshot")

            # Initial commit (HEAD~1)
            (repo / ".gitignore").write_text(
                ".env\n.env.*\nsecrets/\nnode_modules/\nbuild/\n", encoding="utf-8"
            )
            (repo / "README.md").write_text("# Demo Project\n", encoding="utf-8")
            (repo / "src" / "app" / "nested").mkdir(parents=True)
            (repo / "src" / "app" / "shared.txt").write_text(
                "v1: base line\n", encoding="utf-8"
            )
            (repo / "deleted_staged.txt").write_text("remove in index\n", encoding="utf-8")
            (repo / "deleted_unstaged.txt").write_text("remove in worktree\n", encoding="utf-8")
            (repo / "cached_removed.txt").write_text("keep on disk only\n", encoding="utf-8")

            (repo / "assets").mkdir()
            (repo / "assets" / "both.bin").write_bytes(b"\x00\x01\x02base\xff\xfe")
            (repo / "assets" / "staged.bin").write_bytes(b"\x00staged-v1\x80")
            (repo / "assets" / "unstaged.bin").write_bytes(b"\x00unstaged-v1\x81")

            (repo / "bin").mkdir()
            run_sh = repo / "bin" / "run.sh"
            run_sh.write_text("#!/bin/sh\necho v1\n", encoding="utf-8")
            run_sh.chmod(0o755)

            (repo / "links").mkdir()
            os.symlink("../README.md", repo / "links" / "tracked_link")

            _git(repo, "add", ".")
            _git(repo, "commit", "-q", "-m", "Initial commit")
            first_commit = _git(repo, "rev-parse", "HEAD").stdout.decode("ascii").strip()

            # Second commit (HEAD)
            (repo / "README.md").write_text("# Demo Project\nSecond commit\n", encoding="utf-8")
            _git(repo, "add", "README.md")
            _git(repo, "commit", "-q", "-m", "Second commit")
            head_commit = _git(repo, "rev-parse", "HEAD").stdout.decode("ascii").strip()

            # 1. Staged + unstaged changes on the SAME text file
            (repo / "src" / "app" / "shared.txt").write_text(
                "v1: base line\nv2: staged line\n", encoding="utf-8"
            )
            _git(repo, "add", "src/app/shared.txt")
            (repo / "src" / "app" / "shared.txt").write_text(
                "v1: base line\nv2: staged line\nv3: unstaged line\n", encoding="utf-8"
            )

            # 2. Staged + unstaged binary changes
            (repo / "assets" / "both.bin").write_bytes(b"\x00\x01\x02staged\x00\xff\xaa")
            _git(repo, "add", "assets/both.bin")
            (repo / "assets" / "both.bin").write_bytes(
                b"\x00\x01\x02staged\x00\xff\xaa\x00unstaged\xfe"
            )

            (repo / "assets" / "staged.bin").write_bytes(b"\x00\xff\x00staged-v2\xfe\x01")
            _git(repo, "add", "assets/staged.bin")

            (repo / "assets" / "unstaged.bin").write_bytes(b"\x00\xfe\x00unstaged-v2\xff\x02")

            # 3. Staged and unstaged deletions + git rm --cached
            _git(repo, "rm", "-q", "deleted_staged.txt")
            (repo / "deleted_unstaged.txt").unlink()
            _git(repo, "rm", "-q", "--cached", "cached_removed.txt")

            # 4. Untracked file with Unicode and spaces + untracked executable + untracked symlink
            unicode_rel = "src/app/nested/untracked file café 🚀 日本語.txt"
            (repo / unicode_rel).write_text("unicode untracked payload\n", encoding="utf-8")

            untracked_exec = repo / "bin" / "untracked_tool.sh"
            untracked_exec.write_text("#!/bin/sh\necho tool\n", encoding="utf-8")
            untracked_exec.chmod(0o755)

            os.symlink("../src/app/shared.txt", repo / "links" / "untracked_link")

            # 5. Ignored secrets and build/dependency directories (including a .git inside ignored dir)
            (repo / ".env").write_text("SECRET_TOKEN=super-secret-value\n", encoding="utf-8")
            (repo / ".env.local").write_text("LOCAL_SECRET=do-not-copy\n", encoding="utf-8")
            (repo / "secrets").mkdir()
            (repo / "secrets" / "key.pem").write_text("PRIVATE KEY\n", encoding="utf-8")
            (repo / "node_modules" / "pkg" / ".git").mkdir(parents=True)
            (repo / "node_modules" / "pkg" / "index.js").write_text(
                "module.exports = 1;\n", encoding="utf-8"
            )
            (repo / "build").mkdir()
            (repo / "build" / "artifact.bin").write_bytes(b"\xde\xad\xbe\xef")

            # Record full source state before pack_project to verify non-mutation
            index_path = repo / ".git" / "index"
            index_bytes_before = index_path.read_bytes()
            index_mtime_before = os.lstat(index_path).st_mtime_ns
            status_before = _git(
                repo, "--no-optional-locks", "status", "--porcelain=v2", "-z", "--untracked-files=all"
            ).stdout
            tree_before = _tree_state(repo)

            subdir_project = repo / "src" / "app" / "nested"
            metadata = pack_project(subdir_project, staging)

            # Verify source repository was not mutated
            self.assertEqual(index_path.read_bytes(), index_bytes_before)
            self.assertEqual(os.lstat(index_path).st_mtime_ns, index_mtime_before)
            status_after = _git(
                repo, "--no-optional-locks", "status", "--porcelain=v2", "-z", "--untracked-files=all"
            ).stdout
            self.assertEqual(status_after, status_before)
            self.assertEqual(_tree_state(repo), tree_before)

            # Verify metadata and flat top-level staging files
            self.assertEqual(Path(metadata["source_root"]), repo.resolve())
            self.assertEqual(metadata["relative_cwd"], "src/app/nested")
            self.assertEqual(metadata["commit"], head_commit)
            self.assertEqual(metadata["branch"], "feat/handoff-snapshot")
            self.assertTrue((staging / "project.json").is_file())
            for entry in staging.iterdir():
                self.assertTrue(entry.is_file(), f"Non-regular file in staging: {entry}")

            # Unpack into destination
            restored_cwd = unpack_project(staging, dest, metadata)
            self.assertEqual(restored_cwd, dest.resolve() / "src" / "app" / "nested")
            self.assertTrue(restored_cwd.is_dir())

            # Verify commit history and branch
            self.assertEqual(
                _git(dest, "rev-parse", "HEAD").stdout.decode("ascii").strip(),
                head_commit,
            )
            self.assertEqual(
                _git(dest, "rev-parse", "HEAD~1").stdout.decode("ascii").strip(),
                first_commit,
            )
            self.assertEqual(
                _git(dest, "symbolic-ref", "--short", "HEAD").stdout.decode("utf-8").strip(),
                "feat/handoff-snapshot",
            )

            # Verify staged and unstaged diffs match source exactly
            self.assertEqual(
                _git(dest, "diff", "--cached", "--binary", "HEAD").stdout,
                _git(repo, "diff", "--cached", "--binary", "HEAD").stdout,
            )
            self.assertEqual(
                _git(dest, "diff", "--binary").stdout,
                _git(repo, "diff", "--binary").stdout,
            )
            self.assertEqual(
                _git(dest, "status", "--porcelain=v2", "-z", "--untracked-files=all").stdout,
                status_before,
            )

            # Verify ignored files were excluded and all non-ignored files match exactly
            expected_dest_tree = {
                k: v
                for k, v in tree_before.items()
                if not k.startswith((".env", "secrets/", "node_modules/", "build/"))
            }
            self.assertEqual(_tree_state(dest), expected_dest_tree)
            self.assertFalse((dest / ".env").exists())
            self.assertFalse((dest / ".env.local").exists())
            self.assertFalse((dest / "secrets").exists())
            self.assertFalse((dest / "node_modules").exists())
            self.assertFalse((dest / "build").exists())

    def test_detached_head_and_cli_restore_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "repo"
            staging = tmp_path / "staging"
            staging.mkdir(mode=0o700)
            dest = tmp_path / "dest"

            self._init_repo(repo)
            (repo / "file.txt").write_text("one\n", encoding="utf-8")
            _git(repo, "add", "file.txt")
            _git(repo, "commit", "-q", "-m", "c1")
            c1 = _git(repo, "rev-parse", "HEAD").stdout.decode("ascii").strip()

            (repo / "file.txt").write_text("two\n", encoding="utf-8")
            _git(repo, "add", "file.txt")
            _git(repo, "commit", "-q", "-m", "c2")

            _git(repo, "checkout", "-q", "--detach", c1)
            meta = pack_project(repo, staging)
            self.assertIsNone(meta["branch"])
            self.assertEqual(meta["commit"], c1)

            proc = subprocess.run(
                [
                    sys.executable,
                    str(LIBEXEC_DIR / "hop_project.py"),
                    "restore",
                    str(staging),
                    str(dest),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(Path(proc.stdout.strip()), dest.resolve())
            self.assertEqual(
                _git(dest, "rev-parse", "HEAD").stdout.decode("ascii").strip(),
                c1,
            )
            sym = subprocess.run(
                ["git", "-C", str(dest), "symbolic-ref", "-q", "HEAD"],
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(sym.returncode, 0)

    def test_existing_destination_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "repo"
            staging = tmp_path / "staging"
            staging.mkdir(mode=0o700)

            self._init_repo(repo)
            (repo / "a.txt").write_text("hello\n", encoding="utf-8")
            _git(repo, "add", "a.txt")
            _git(repo, "commit", "-q", "-m", "init")
            meta = pack_project(repo, staging)

            existing_dir = tmp_path / "already-exists"
            existing_dir.mkdir()
            sentinel = existing_dir / "keep.txt"
            sentinel.write_text("do not touch\n", encoding="utf-8")

            with self.assertRaises(HandoffProjectError):
                unpack_project(staging, existing_dir, meta)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not touch\n")

            existing_file = tmp_path / "existing-file"
            existing_file.write_text("file\n", encoding="utf-8")
            with self.assertRaises(HandoffProjectError):
                unpack_project(staging, existing_file, meta)
            self.assertTrue(existing_file.is_file())

    def test_unsafe_extraction_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "repo"
            staging = tmp_path / "staging"
            staging.mkdir(mode=0o700)

            self._init_repo(repo)
            (repo / "ok.txt").write_text("safe\n", encoding="utf-8")
            _git(repo, "add", "ok.txt")
            _git(repo, "commit", "-q", "-m", "init")
            base_meta = pack_project(repo, staging)

            # 1. Path traversal "../escape.txt" in untracked.tar
            tar_path = staging / "untracked.tar"
            with tarfile.open(tar_path, "w", format=tarfile.PAX_FORMAT) as tf:
                payload = b"pwned\n"
                info = tarfile.TarInfo(name="../escape.txt")
                info.size = len(payload)
                tf.addfile(info, io.BytesIO(payload))

            dest1 = tmp_path / "dest-traversal"
            with self.assertRaises(HandoffProjectError):
                unpack_project(staging, dest1, base_meta)
            self.assertFalse(dest1.exists())
            self.assertFalse((tmp_path / "escape.txt").exists())

            # 2. Absolute path in untracked.tar
            with tarfile.open(tar_path, "w", format=tarfile.PAX_FORMAT) as tf:
                payload = b"pwned\n"
                info = tarfile.TarInfo(name="/tmp/omp-handoff-abs-escape.txt")
                info.size = len(payload)
                tf.addfile(info, io.BytesIO(payload))

            dest2 = tmp_path / "dest-abs"
            with self.assertRaises(HandoffProjectError):
                unpack_project(staging, dest2, base_meta)
            self.assertFalse(dest2.exists())

            # 3. Symlink escaping root in untracked.tar
            with tarfile.open(tar_path, "w", format=tarfile.PAX_FORMAT) as tf:
                info = tarfile.TarInfo(name="sub/escape_link")
                info.type = tarfile.SYMTYPE
                info.linkname = "../../outside.txt"
                tf.addfile(info)

            dest3 = tmp_path / "dest-symlink-escape"
            with self.assertRaises(HandoffProjectError):
                unpack_project(staging, dest3, base_meta)
            self.assertFalse(dest3.exists())

            # 4. Archive writing through an archived symlink directory
            with tarfile.open(tar_path, "w", format=tarfile.PAX_FORMAT) as tf:
                sym = tarfile.TarInfo(name="redir")
                sym.type = tarfile.SYMTYPE
                sym.linkname = "."
                tf.addfile(sym)
                reg = tarfile.TarInfo(name="redir/inside.txt")
                reg.size = 3
                tf.addfile(reg, io.BytesIO(b"abc"))

            dest4 = tmp_path / "dest-symlink-parent"
            with self.assertRaises(HandoffProjectError):
                unpack_project(staging, dest4, base_meta)
            self.assertFalse(dest4.exists())

            # Reset untracked.tar to valid empty tar, test unsafe relative_cwd & patch traversal
            with tarfile.open(tar_path, "w", format=tarfile.PAX_FORMAT):
                pass

            bad_cwd_meta = dict(base_meta, relative_cwd="../outside")
            dest5 = tmp_path / "dest-bad-cwd"
            with self.assertRaises(HandoffProjectError):
                unpack_project(staging, dest5, bad_cwd_meta)
            self.assertFalse(dest5.exists())

            # 5. Malicious patch attempting path traversal
            (staging / "unstaged.patch").write_text(
                "diff --git a/../evil.txt b/../evil.txt\n"
                "new file mode 100644\n"
                "--- /dev/null\n"
                "+++ b/../evil.txt\n"
                "@@ -0,0 +1 @@\n"
                "+evil\n",
                encoding="utf-8",
            )
            dest6 = tmp_path / "dest-bad-patch"
            with self.assertRaises(HandoffProjectError):
                unpack_project(staging, dest6, base_meta)
            self.assertFalse(dest6.exists())
            self.assertFalse((tmp_path / "evil.txt").exists())

    def test_unsupported_source_states_refused_before_transfer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            staging = tmp_path / "staging"
            staging.mkdir(mode=0o700)

            # 1. Empty / unborn repository
            unborn = tmp_path / "unborn"
            self._init_repo(unborn)
            with self.assertRaises(HandoffProjectError):
                pack_project(unborn, staging)

            # 2. Nested non-ignored Git repository
            nested_outer = tmp_path / "nested-outer"
            self._init_repo(nested_outer)
            (nested_outer / "root.txt").write_text("ok\n", encoding="utf-8")
            _git(nested_outer, "add", "root.txt")
            _git(nested_outer, "commit", "-q", "-m", "init")
            self._init_repo(nested_outer / "subrepo")
            (nested_outer / "subrepo" / "inner.txt").write_text("inner\n", encoding="utf-8")
            with self.assertRaises(HandoffProjectError):
                pack_project(nested_outer, staging)

            # 3. Source symlink escaping repository root
            bad_link_repo = tmp_path / "bad-link-repo"
            self._init_repo(bad_link_repo)
            (bad_link_repo / "a.txt").write_text("a\n", encoding="utf-8")
            _git(bad_link_repo, "add", "a.txt")
            _git(bad_link_repo, "commit", "-q", "-m", "init")
            os.symlink("../../outside", bad_link_repo / "escape_link")
            with self.assertRaises(HandoffProjectError):
                pack_project(bad_link_repo, staging)

            # 4. External Git filter / LFS attribute refused
            lfs_repo = tmp_path / "lfs-repo"
            self._init_repo(lfs_repo)
            (lfs_repo / ".gitattributes").write_text("*.bin filter=lfs\n", encoding="utf-8")
            (lfs_repo / "model.bin").write_bytes(b"\x00\x01\x02")
            _git(lfs_repo, "add", ".gitattributes", "model.bin")
            _git(lfs_repo, "commit", "-q", "-m", "lfs")
            with self.assertRaises(HandoffProjectError):
                pack_project(lfs_repo, staging)


if __name__ == "__main__":
    unittest.main()
