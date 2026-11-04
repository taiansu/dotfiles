#!/usr/bin/env python3
"""Git repository snapshot and safe restoration for OMP session handoff."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from typing import Any
import unicodedata

METADATA_FILENAME = "project.json"
BUNDLE_FILENAME = "repo.bundle"
STAGED_PATCH_FILENAME = "staged.patch"
UNSTAGED_PATCH_FILENAME = "unstaged.patch"
UNTRACKED_ARCHIVE_FILENAME = "untracked.tar"

_HEX_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$")
_SCRUBBED_GIT_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_NAMESPACE",
    "GIT_SUPER_PREFIX",
    "GIT_EXTERNAL_DIFF",
    "GIT_DIFF_OPTS",
)
_IN_PROGRESS_SENTINELS = (
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "BISECT_LOG",
    "rebase-merge",
    "rebase-apply",
    "sequencer",
)


class HandoffProjectError(ValueError, RuntimeError):
    """Raised when a project cannot be safely packed or unpacked."""


def _git_env(*, read_only: bool) -> dict[str, str]:
    env = os.environ.copy()
    for key in _SCRUBBED_GIT_ENV_VARS:
        env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if read_only:
        env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def _run_git(
    cwd: Path,
    args: list[str],
    *,
    read_only: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    cmd = [
        "git",
        *(["--no-optional-locks"] if read_only else []),
        "-C",
        str(cwd),
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.autocrlf=false",
        "-c",
        "core.safecrlf=false",
        "-c",
        "core.fileMode=true",
        "-c",
        "core.symlinks=true",
        "-c",
        "core.quotePath=true",
        "-c",
        "diff.noprefix=false",
        "-c",
        "diff.mnemonicPrefix=false",
        "-c",
        "diff.external=",
        "-c",
        "color.ui=false",
        "-c",
        "filter.lfs.smudge=",
        "-c",
        "filter.lfs.clean=",
        "-c",
        "filter.lfs.process=",
        "-c",
        "filter.lfs.required=false",
        *args,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        env=_git_env(read_only=read_only),
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise HandoffProjectError(
            f"Git command failed ({' '.join(args)}): {stderr or f'exit {result.returncode}'}"
        )
    return result


def _validate_relative_repo_path(rel_path: str) -> PurePosixPath:
    if not isinstance(rel_path, str) or not rel_path or "\x00" in rel_path:
        raise HandoffProjectError(f"Invalid repository relative path: {rel_path!r}")
    if rel_path.startswith(("/", "\\")) or "\\" in rel_path:
        raise HandoffProjectError(f"Unsafe non-relative repository path: {rel_path!r}")
    if len(rel_path) >= 2 and rel_path[1] == ":":
        raise HandoffProjectError(f"Unsafe drive-prefixed repository path: {rel_path!r}")
    raw_parts = rel_path.split("/")
    if any(part in ("", ".", "..") for part in raw_parts):
        raise HandoffProjectError(f"Unsafe path component in repository path: {rel_path!r}")
    if ".git" in raw_parts:
        raise HandoffProjectError(f"Refusing reserved .git path component: {rel_path!r}")
    return PurePosixPath(*raw_parts)


def _validate_symlink_target(link_rel_path: str, target: str) -> None:
    link_posix = _validate_relative_repo_path(link_rel_path)
    if not isinstance(target, str) or not target or "\x00" in target:
        raise HandoffProjectError(f"Invalid symlink target for {link_rel_path!r}: {target!r}")
    if target.startswith(("/", "\\")) or "\\" in target:
        raise HandoffProjectError(
            f"Symlink {link_rel_path!r} uses unsafe absolute or backslash target: {target!r}"
        )
    if len(target) >= 2 and target[1] == ":":
        raise HandoffProjectError(
            f"Symlink {link_rel_path!r} uses drive-prefixed target: {target!r}"
        )

    parent_parts = [] if str(link_posix.parent) == "." else list(link_posix.parent.parts)
    stack = list(parent_parts)
    for part in target.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not stack:
                raise HandoffProjectError(
                    f"Symlink {link_rel_path!r} traverses outside repository root: {target!r}"
                )
            stack.pop()
        elif part == ".git":
            raise HandoffProjectError(
                f"Symlink {link_rel_path!r} targets reserved .git entry: {target!r}"
            )
        else:
            stack.append(part)


def _validate_realpath_within_root(root_real: Path, candidate: Path, description: str) -> None:
    resolved = Path(os.path.realpath(candidate))
    if not resolved.is_relative_to(root_real):
        raise HandoffProjectError(
            f"{description} resolves outside repository root ({resolved} not under {root_real})"
        )


def _validate_no_symlink_parents(root: Path, rel_posix: PurePosixPath) -> None:
    current = root
    for part in rel_posix.parts[:-1]:
        current = current / part
        if os.path.lexists(current):
            st = os.lstat(current)
            if stat.S_ISLNK(st.st_mode):
                raise HandoffProjectError(
                    f"Refusing path {str(rel_posix)!r} traversing through symlink directory {part!r}"
                )
            if not stat.S_ISDIR(st.st_mode):
                raise HandoffProjectError(
                    f"Parent component {part!r} of {str(rel_posix)!r} is not a directory"
                )


def _decode_git_z_paths(payload: bytes) -> list[str]:
    if not payload:
        return []
    entries = payload.split(b"\x00")
    if entries and entries[-1] == b"":
        entries.pop()
    result: list[str] = []
    for raw in entries:
        try:
            result.append(raw.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise HandoffProjectError(f"Non-UTF-8 path in repository is not supported: {raw!r}") from exc
    return result


def _check_no_in_progress_operations(source_root: Path) -> None:
    git_dir_raw = _run_git(source_root, ["rev-parse", "--git-dir"]).stdout.decode("utf-8").strip()
    common_dir_raw = (
        _run_git(source_root, ["rev-parse", "--git-common-dir"]).stdout.decode("utf-8").strip()
    )
    git_dirs = {
        (source_root / git_dir_raw).resolve(strict=False),
        (source_root / common_dir_raw).resolve(strict=False),
    }
    for gdir in git_dirs:
        for sentinel in _IN_PROGRESS_SENTINELS:
            if os.path.lexists(gdir / sentinel):
                raise HandoffProjectError(
                    f"Repository has an in-progress Git operation ({sentinel}); complete or abort it before handoff."
                )

    unmerged = _run_git(source_root, ["ls-files", "-u", "-z"]).stdout
    if unmerged:
        raise HandoffProjectError(
            "Repository has unmerged index entries; resolve merge conflicts before handoff."
        )


def _check_tree_and_index_entries(source_root: Path) -> tuple[list[str], dict[str, tuple[str, str]]]:
    if os.path.lexists(source_root / ".gitmodules"):
        raise HandoffProjectError("Submodules (.gitmodules) are not supported for handoff.")

    head_tree = _run_git(source_root, ["ls-tree", "-r", "-z", "HEAD"]).stdout
    for record in head_tree.split(b"\x00"):
        if not record:
            continue
        meta_bytes, sep, path_bytes = record.partition(b"\t")
        if not sep:
            continue
        path_str = path_bytes.decode("utf-8", errors="strict")
        _validate_relative_repo_path(path_str)
        parts = meta_bytes.decode("ascii").split()
        mode, _obj_type, obj_sha = parts[0], parts[1], parts[2]
        if mode == "160000":
            raise HandoffProjectError(
                f"Submodules/gitlinks are not supported for handoff: {path_str}"
            )
        if mode == "120000":
            target = _run_git(source_root, ["cat-file", "blob", obj_sha]).stdout.decode(
                "utf-8", errors="strict"
            )
            _validate_symlink_target(path_str, target)

    staged_raw = _run_git(source_root, ["ls-files", "--stage", "-z"]).stdout
    tracked_paths: list[str] = []
    index_entries: dict[str, tuple[str, str]] = {}
    for record in staged_raw.split(b"\x00"):
        if not record:
            continue
        meta_bytes, sep, path_bytes = record.partition(b"\t")
        if not sep:
            continue
        path_str = path_bytes.decode("utf-8", errors="strict")
        _validate_relative_repo_path(path_str)
        tracked_paths.append(path_str)
        parts = meta_bytes.decode("ascii").split()
        mode, obj_sha = parts[0], parts[1]
        index_entries[path_str] = (mode, obj_sha)
        if mode == "160000":
            raise HandoffProjectError(
                f"Submodules/gitlinks in index are not supported for handoff: {path_str}"
            )
        if mode == "120000":
            target = _run_git(source_root, ["cat-file", "blob", obj_sha]).stdout.decode(
                "utf-8", errors="strict"
            )
            _validate_symlink_target(path_str, target)

    return tracked_paths, index_entries


def _check_attributes_and_worktree_fidelity(
    source_root: Path,
    index_entries: dict[str, tuple[str, str]],
    untracked_paths: list[str],
) -> None:
    all_paths = sorted(set(index_entries) | set(untracked_paths))
    if all_paths:
        stdin_payload = b"\x00".join(p.encode("utf-8") for p in all_paths) + b"\x00"
        attr_proc = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-C",
                str(source_root),
                "check-attr",
                "--stdin",
                "-z",
                "filter",
                "working-tree-encoding",
                "ident",
            ],
            input=stdin_payload,
            capture_output=True,
            env=_git_env(read_only=True),
            check=False,
        )
        if attr_proc.returncode != 0:
            stderr = attr_proc.stderr.decode("utf-8", errors="replace").strip()
            raise HandoffProjectError(f"Failed to inspect Git attributes: {stderr}")
        tokens = attr_proc.stdout.split(b"\x00")
        if tokens and tokens[-1] == b"":
            tokens.pop()
        for idx in range(0, len(tokens) - 2, 3):
            p_str = tokens[idx].decode("utf-8", errors="replace")
            attr_name = tokens[idx + 1].decode("utf-8", errors="replace")
            attr_val = tokens[idx + 2].decode("utf-8", errors="replace")
            if attr_val not in ("unspecified", "unset"):
                raise HandoffProjectError(
                    f"Unsupported Git attribute {attr_name}={attr_val!r} on {p_str!r}; "
                    "external filters/LFS/encodings are refused to prevent lossy handoff."
                )

    unstaged_changed = set(
        _decode_git_z_paths(
            _run_git(
                source_root,
                ["diff", "--name-only", "--no-renames", "--no-ext-diff", "-z"],
            ).stdout
        )
    )
    clean_regular_paths: list[str] = []
    for rel_path, (mode, _sha) in index_entries.items():
        if mode not in ("100644", "100755") or rel_path in unstaged_changed:
            continue
        full_path = source_root / rel_path
        if os.path.lexists(full_path):
            clean_regular_paths.append(rel_path)

    if clean_regular_paths:
        for rel_path in clean_regular_paths:
            if "\n" in rel_path:
                data = (source_root / rel_path).read_bytes()
                actual_sha = hashlib.sha1(
                    f"blob {len(data)}\x00".encode("ascii") + data
                ).hexdigest()
                expected_sha = index_entries[rel_path][1]
                if actual_sha.lower() != expected_sha.lower():
                    raise HandoffProjectError(
                        f"Tracked file {rel_path!r} on disk differs from its index blob "
                        "(filter/LFS/line-ending smudge active); refusing lossy handoff."
                    )
        batch_paths = [p for p in clean_regular_paths if "\n" not in p]
        if batch_paths:
            hash_proc = subprocess.run(
                [
                    "git",
                    "--no-optional-locks",
                    "-C",
                    str(source_root),
                    "hash-object",
                    "--no-filters",
                    "--stdin-paths",
                ],
                input=("\n".join(batch_paths) + "\n").encode("utf-8"),
                capture_output=True,
                env=_git_env(read_only=True),
                check=False,
            )
            if hash_proc.returncode != 0:
                stderr = hash_proc.stderr.decode("utf-8", errors="replace").strip()
                raise HandoffProjectError(f"Failed to verify worktree object hashes: {stderr}")
            actual_hashes = hash_proc.stdout.decode("ascii").splitlines()
            if len(actual_hashes) != len(batch_paths):
                raise HandoffProjectError("Unexpected output count from git hash-object.")
            for rel_path, actual_sha in zip(batch_paths, actual_hashes):
                expected_sha = index_entries[rel_path][1]
                if actual_sha.strip().lower() != expected_sha.lower():
                    raise HandoffProjectError(
                        f"Tracked file {rel_path!r} on disk differs from its index blob "
                        "(filter/LFS/line-ending smudge active); refusing lossy handoff."
                    )


def _check_worktree_and_nested_repos(
    source_root: Path,
    tracked_paths: list[str],
    untracked_paths: list[str],
) -> None:
    for untracked in untracked_paths:
        if untracked.endswith("/"):
            raise HandoffProjectError(
                f"Nested Git repository is not supported for handoff: {untracked.rstrip('/')}"
            )
        _validate_relative_repo_path(untracked)

    ignored_raw = _run_git(
        source_root,
        ["ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z"],
    ).stdout
    ignored_dirs = {
        unicodedata.normalize("NFC", entry.rstrip("/"))
        for entry in _decode_git_z_paths(ignored_raw)
        if entry.rstrip("/")
    }

    for current_root, dirnames, filenames in os.walk(source_root, topdown=True, followlinks=False):
        curr_path = Path(current_root)
        rel_dir = "." if curr_path == source_root else curr_path.relative_to(source_root).as_posix()

        if rel_dir == ".":
            if ".git" in dirnames:
                dirnames.remove(".git")
        else:
            if ".git" in dirnames or ".git" in filenames or os.path.lexists(curr_path / ".git"):
                ign = _run_git(
                    source_root, ["check-ignore", "-q", "--", rel_dir], check=False
                )
                if ign.returncode == 0:
                    dirnames[:] = []
                    continue
                raise HandoffProjectError(
                    f"Nested Git repository is not supported for handoff: {rel_dir}"
                )

        pruned: list[str] = []
        for dname in dirnames:
            child_rel = dname if rel_dir == "." else f"{rel_dir}/{dname}"
            if unicodedata.normalize("NFC", child_rel) in ignored_dirs:
                continue
            child_full = curr_path / dname
            try:
                st = os.lstat(child_full)
            except OSError as exc:
                raise HandoffProjectError(f"Unable to stat {child_rel}: {exc}") from exc
            if stat.S_ISLNK(st.st_mode):
                target = os.readlink(child_full)
                _validate_symlink_target(child_rel, target)
                _validate_realpath_within_root(source_root, child_full, f"Symlink {child_rel!r}")
                continue
            pruned.append(dname)
        dirnames[:] = pruned

    untracked_set = {unicodedata.normalize("NFC", u) for u in untracked_paths}
    for rel_path in tracked_paths:
        rel_posix = _validate_relative_repo_path(rel_path)
        _validate_no_symlink_parents(source_root, rel_posix)
        full_path = source_root / rel_path
        if not os.path.lexists(full_path):
            continue
        st = os.lstat(full_path)
        if stat.S_ISDIR(st.st_mode):
            prefix = f"{rel_path}/"
            if not any(u.startswith(prefix) for u in untracked_set):
                raise HandoffProjectError(
                    f"Tracked file {rel_path!r} was replaced by an empty directory, which Git cannot represent."
                )
        elif stat.S_ISLNK(st.st_mode):
            target = os.readlink(full_path)
            _validate_symlink_target(rel_path, target)
            _validate_realpath_within_root(source_root, full_path, f"Symlink {rel_path!r}")
        elif not stat.S_ISREG(st.st_mode):
            raise HandoffProjectError(
                f"Unsupported special file at tracked path {rel_path!r} (mode { oct(st.st_mode) })."
            )

    for rel_path in untracked_paths:
        rel_posix = _validate_relative_repo_path(rel_path)
        _validate_no_symlink_parents(source_root, rel_posix)
        full_path = source_root / rel_path
        if not os.path.lexists(full_path):
            raise HandoffProjectError(
                f"Untracked path disappeared during inspection: {rel_path!r}"
            )
        st = os.lstat(full_path)
        if stat.S_ISLNK(st.st_mode):
            target = os.readlink(full_path)
            _validate_symlink_target(rel_path, target)
            _validate_realpath_within_root(source_root, full_path, f"Symlink {rel_path!r}")
        elif not stat.S_ISREG(st.st_mode):
            raise HandoffProjectError(
                f"Unsupported untracked non-regular file {rel_path!r} (mode {oct(st.st_mode)})."
            )


def _detect_intent_to_add(source_root: Path) -> list[str]:
    raw = _run_git(
        source_root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=no"],
    ).stdout
    intent_paths: list[str] = []
    entries = raw.split(b"\x00")
    i = 0
    while i < len(entries):
        entry = entries[i]
        if not entry:
            i += 1
            continue
        xy = entry[:2]
        path_bytes = entry[3:]
        if xy == b" A":
            path_str = path_bytes.decode("utf-8", errors="strict")
            _validate_relative_repo_path(path_str)
            intent_paths.append(path_str)
        if xy[:1] in (b"R", b"C") or xy[1:2] in (b"R", b"C"):
            i += 2
        else:
            i += 1
    return sorted(intent_paths)


def _capture_repo_fingerprint(source_root: Path) -> bytes:
    hasher = hashlib.sha256()
    head_commit = _run_git(source_root, ["rev-parse", "--verify", "HEAD^{commit}"]).stdout
    symref = _run_git(source_root, ["symbolic-ref", "-q", "HEAD"], check=False).stdout
    ls_stage = _run_git(source_root, ["ls-files", "--stage", "-z"]).stdout
    diff_cached = _run_git(
        source_root,
        ["diff", "--cached", "--raw", "--no-renames", "--no-ext-diff", "--abbrev=40", "-z", "HEAD"],
    ).stdout
    diff_worktree = _run_git(
        source_root,
        ["diff", "--raw", "--no-renames", "--no-ext-diff", "--abbrev=40", "-z"],
    ).stdout
    untracked_raw = _run_git(
        source_root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ).stdout

    for chunk in (head_commit, symref, ls_stage, diff_cached, diff_worktree, untracked_raw):
        hasher.update(len(chunk).to_bytes(8, "big"))
        hasher.update(chunk)

    tracked_paths = _decode_git_z_paths(_run_git(source_root, ["ls-files", "-z"]).stdout)
    untracked_paths = _decode_git_z_paths(untracked_raw)
    for rel_path in sorted(set(tracked_paths) | set(untracked_paths)):
        full_path = source_root / rel_path
        hasher.update(rel_path.encode("utf-8") + b"\x00")
        try:
            st = os.lstat(full_path)
        except FileNotFoundError:
            hasher.update(b"MISSING\x00")
            continue
        stat_record = f"{st.st_mode}:{st.st_size}:{st.st_mtime_ns}:{st.st_ino}\x00".encode("ascii")
        hasher.update(stat_record)
        if stat.S_ISLNK(st.st_mode):
            hasher.update(os.readlink(full_path).encode("utf-8") + b"\x00")

    return hasher.digest()


def _write_untracked_archive(
    source_root: Path,
    untracked_paths: list[str],
    archive_path: Path,
) -> None:
    open_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with tarfile.open(archive_path, "w", format=tarfile.PAX_FORMAT) as tf:
        for rel_path in sorted(untracked_paths):
            rel_posix = _validate_relative_repo_path(rel_path)
            _validate_no_symlink_parents(source_root, rel_posix)
            full_path = source_root / rel_path
            try:
                st = os.lstat(full_path)
            except OSError as exc:
                raise HandoffProjectError(
                    f"Untracked file changed or vanished while packing: {rel_path}"
                ) from exc

            info = tarfile.TarInfo(name=rel_posix.as_posix())
            info.mtime = int(st.st_mtime)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""

            if stat.S_ISLNK(st.st_mode):
                target = os.readlink(full_path)
                _validate_symlink_target(rel_path, target)
                _validate_realpath_within_root(source_root, full_path, f"Symlink {rel_path!r}")
                info.type = tarfile.SYMTYPE
                info.linkname = target
                info.mode = 0o777
                info.size = 0
                tf.addfile(info)
            elif stat.S_ISREG(st.st_mode):
                info.type = tarfile.REGTYPE
                info.mode = 0o755 if (st.st_mode & 0o111) else 0o644
                info.size = st.st_size
                try:
                    fd = os.open(full_path, open_flags)
                except OSError as exc:
                    raise HandoffProjectError(
                        f"Failed to open untracked file {rel_path!r}: {exc}"
                    ) from exc
                with os.fdopen(fd, "rb") as fobj:
                    fd_st = os.fstat(fobj.fileno())
                    if (
                        not stat.S_ISREG(fd_st.st_mode)
                        or fd_st.st_ino != st.st_ino
                        or fd_st.st_size != st.st_size
                        or fd_st.st_mtime_ns != st.st_mtime_ns
                    ):
                        raise HandoffProjectError(
                            f"Untracked file {rel_path!r} changed while packing snapshot."
                        )
                    tf.addfile(info, fileobj=fobj)
                    fd_st_after = os.fstat(fobj.fileno())
                    if (
                        fd_st_after.st_size != st.st_size
                        or fd_st_after.st_mtime_ns != st.st_mtime_ns
                    ):
                        raise HandoffProjectError(
                            f"Untracked file {rel_path!r} was modified while packing snapshot."
                        )
            else:
                raise HandoffProjectError(
                    f"Unsupported untracked file type at {rel_path!r}: {oct(st.st_mode)}"
                )


def pack_project(project: Path, staging: Path) -> dict[str, Any]:
    """Create a non-mutating snapshot of the Git repository containing `project`."""
    try:
        project_path = Path(project).expanduser().resolve(strict=True)
    except OSError as exc:
        raise HandoffProjectError(f"Project path does not exist: {project}") from exc
    if not project_path.is_dir():
        raise HandoffProjectError(f"Project path is not a directory: {project_path}")

    try:
        staging_path = Path(staging).expanduser().resolve(strict=True)
    except OSError as exc:
        raise HandoffProjectError(f"Staging directory does not exist: {staging}") from exc
    if not staging_path.is_dir():
        raise HandoffProjectError(f"Staging path is not a directory: {staging_path}")
    staging_path.chmod(0o700)

    is_bare_proc = _run_git(project_path, ["rev-parse", "--is-bare-repository"], check=False)
    if is_bare_proc.returncode != 0:
        raise HandoffProjectError(f"Project path is not inside a Git repository: {project_path}")
    if is_bare_proc.stdout.decode("utf-8", errors="replace").strip() == "true":
        raise HandoffProjectError(f"Bare Git repositories are not supported: {project_path}")

    toplevel_proc = _run_git(project_path, ["rev-parse", "--show-toplevel"], check=False)
    if toplevel_proc.returncode != 0:
        raise HandoffProjectError(f"Project path is not inside a Git working tree: {project_path}")
    source_root = Path(toplevel_proc.stdout.decode("utf-8", errors="strict").strip()).resolve(
        strict=True
    )

    if not project_path.is_relative_to(source_root):
        raise HandoffProjectError(
            f"Resolved project directory {project_path} is outside repository root {source_root}"
        )
    rel_cwd_path = project_path.relative_to(source_root)
    relative_cwd = "." if rel_cwd_path == Path(".") else rel_cwd_path.as_posix()
    if relative_cwd != ".":
        rel_posix = _validate_relative_repo_path(relative_cwd)
        _validate_no_symlink_parents(source_root, rel_posix)

    commit_proc = _run_git(source_root, ["rev-parse", "--verify", "HEAD^{commit}"], check=False)
    if commit_proc.returncode != 0:
        raise HandoffProjectError(
            "Repository has an unborn HEAD (no commits exist yet); create an initial commit before handoff."
        )
    commit = commit_proc.stdout.decode("ascii").strip()
    if not _HEX_COMMIT_RE.fullmatch(commit):
        raise HandoffProjectError(f"Invalid HEAD commit hash: {commit!r}")

    symref_proc = _run_git(source_root, ["symbolic-ref", "-q", "HEAD"], check=False)
    branch: str | None = None
    if symref_proc.returncode == 0:
        symref = symref_proc.stdout.decode("utf-8", errors="strict").strip()
        if not symref.startswith("refs/heads/"):
            raise HandoffProjectError(f"Unsupported symbolic HEAD reference: {symref!r}")
        branch = symref[len("refs/heads/") :]
        if not branch:
            raise HandoffProjectError("Empty branch name in symbolic HEAD reference.")

    _check_no_in_progress_operations(source_root)
    tracked_paths, index_entries = _check_tree_and_index_entries(source_root)
    untracked_paths = _decode_git_z_paths(
        _run_git(
            source_root, ["ls-files", "--others", "--exclude-standard", "-z"]
        ).stdout
    )
    _check_worktree_and_nested_repos(source_root, tracked_paths, untracked_paths)
    _check_attributes_and_worktree_fidelity(source_root, index_entries, untracked_paths)
    intent_to_add = _detect_intent_to_add(source_root)

    before_fp = _capture_repo_fingerprint(source_root)

    bundle_path = staging_path / BUNDLE_FILENAME
    staged_patch_path = staging_path / STAGED_PATCH_FILENAME
    unstaged_patch_path = staging_path / UNSTAGED_PATCH_FILENAME
    untracked_archive_path = staging_path / UNTRACKED_ARCHIVE_FILENAME
    metadata_path = staging_path / METADATA_FILENAME
    created_files = (
        bundle_path,
        staged_patch_path,
        unstaged_patch_path,
        untracked_archive_path,
        metadata_path,
    )

    try:
        bundle_refs = ["HEAD", f"refs/heads/{branch}"] if branch is not None else ["HEAD"]
        _run_git(source_root, ["bundle", "create", str(bundle_path), *bundle_refs])

        staged_patch = _run_git(
            source_root,
            [
                "diff",
                "--cached",
                "--binary",
                "--full-index",
                "--no-renames",
                "--no-ext-diff",
                "--no-textconv",
                "--no-color",
                "--src-prefix=a/",
                "--dst-prefix=b/",
                "HEAD",
            ],
        ).stdout
        staged_patch_path.write_bytes(staged_patch)

        unstaged_patch = _run_git(
            source_root,
            [
                "diff",
                "--binary",
                "--full-index",
                "--no-renames",
                "--no-ext-diff",
                "--no-textconv",
                "--no-color",
                "--src-prefix=a/",
                "--dst-prefix=b/",
            ],
        ).stdout
        unstaged_patch_path.write_bytes(unstaged_patch)

        _write_untracked_archive(source_root, untracked_paths, untracked_archive_path)

        after_fp = _capture_repo_fingerprint(source_root)
        if before_fp != after_fp:
            raise HandoffProjectError(
                "Source repository changed while packing snapshot; aborting handoff."
            )

        metadata: dict[str, Any] = {
            "version": 1,
            "source_root": str(source_root),
            "relative_cwd": relative_cwd,
            "commit": commit,
            "branch": branch,
            "files": {
                "bundle": BUNDLE_FILENAME,
                "staged_patch": STAGED_PATCH_FILENAME,
                "unstaged_patch": UNSTAGED_PATCH_FILENAME,
                "untracked_archive": UNTRACKED_ARCHIVE_FILENAME,
            },
            "intent_to_add": intent_to_add,
        }
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        for file_path in created_files:
            file_path.chmod(0o600)
        return metadata
    except Exception:
        for file_path in created_files:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _unquote_git_c_path(raw: str) -> str:
    text = raw.strip()
    if not text:
        raise HandoffProjectError("Empty path in Git patch header")
    if text.startswith('"'):
        if not text.endswith('"') or len(text) < 2:
            raise HandoffProjectError(f"Malformed quoted path in Git patch: {raw!r}")
        inner = text[1:-1]
        out = bytearray()
        i = 0
        n = len(inner)
        while i < n:
            ch = inner[i]
            if ch != "\\":
                out.extend(ch.encode("utf-8"))
                i += 1
                continue
            i += 1
            if i >= n:
                raise HandoffProjectError(f"Trailing backslash in quoted path: {raw!r}")
            esc = inner[i]
            if esc in "01234567":
                oct_digits = esc
                i += 1
                for _ in range(2):
                    if i < n and inner[i] in "01234567":
                        oct_digits += inner[i]
                        i += 1
                    else:
                        break
                out.append(int(oct_digits, 8))
            else:
                mapping = {
                    "a": 0x07,
                    "b": 0x08,
                    "f": 0x0C,
                    "n": 0x0A,
                    "r": 0x0D,
                    "t": 0x09,
                    "v": 0x0B,
                    "\\": 0x5C,
                    '"': 0x22,
                }
                if esc not in mapping:
                    raise HandoffProjectError(f"Unsupported escape \\{esc} in patch path: {raw!r}")
                out.append(mapping[esc])
                i += 1
        try:
            return out.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HandoffProjectError(f"Invalid UTF-8 path in patch header: {raw!r}") from exc
    return text


def _split_diff_git_header_paths(rest: str) -> tuple[str, str]:
    rest = rest.strip()
    if not rest:
        raise HandoffProjectError("Empty diff --git header")
    if rest.startswith('"'):
        tokens: list[str] = []
        i = 0
        n = len(rest)
        while i < n:
            while i < n and rest[i] == " ":
                i += 1
            if i >= n:
                break
            if rest[i] == '"':
                start = i
                i += 1
                while i < n:
                    if rest[i] == "\\":
                        i += 2
                        continue
                    if rest[i] == '"':
                        i += 1
                        break
                    i += 1
                tokens.append(_unquote_git_c_path(rest[start:i]))
            else:
                start = i
                while i < n and rest[i] != " ":
                    i += 1
                tokens.append(rest[start:i])
        if len(tokens) != 2:
            raise HandoffProjectError(f"Malformed diff --git header: {rest!r}")
        return tokens[0], tokens[1]

    # Check symmetric unquoted "a/<path> b/<path>" first (handles spaces in filenames).
    if rest.startswith("a/") and len(rest) >= 5 and (len(rest) - 5) % 2 == 0:
        half = (len(rest) - 5) // 2
        candidate = rest[2 : 2 + half]
        if rest == f"a/{candidate} b/{candidate}":
            return f"a/{candidate}", f"b/{candidate}"

    marker = " b/"
    idx = rest.find(marker)
    if idx == -1:
        raise HandoffProjectError(f"Malformed diff --git header (missing b/ prefix): {rest!r}")
    return _unquote_git_c_path(rest[:idx]), _unquote_git_c_path(rest[idx + 1 :])


def _strip_patch_prefix(path_str: str, expected_prefix: str) -> str:
    if not path_str.startswith(expected_prefix):
        raise HandoffProjectError(
            f"Patch path {path_str!r} does not start with expected prefix {expected_prefix!r}"
        )
    rel = path_str[len(expected_prefix) :]
    _validate_relative_repo_path(rel)
    return rel


def _validate_patch_safety(patch_bytes: bytes, label: str) -> None:
    if not patch_bytes:
        return
    try:
        patch_text = patch_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HandoffProjectError(f"Patch {label} is not valid UTF-8") from exc

    in_hunk = False
    in_binary = False
    current_path: str | None = None
    current_is_symlink = False
    symlink_target_chunks: list[str] = []

    def _flush_symlink_check() -> None:
        nonlocal symlink_target_chunks
        if current_is_symlink and current_path is not None and symlink_target_chunks:
            target = "".join(symlink_target_chunks)
            _validate_symlink_target(current_path, target)
        symlink_target_chunks = []

    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            _flush_symlink_check()
            in_hunk = False
            in_binary = False
            current_is_symlink = False
            old_p, new_p = _split_diff_git_header_paths(line[len("diff --git ") :])
            _strip_patch_prefix(old_p, "a/")
            current_path = _strip_patch_prefix(new_p, "b/")
            continue

        if in_binary:
            if line == "":
                in_binary = False
            continue

        if in_hunk:
            if line.startswith("@@ "):
                _flush_symlink_check()
                continue
            if line.startswith(("+", "-", " ", "\\")):
                if current_is_symlink and line.startswith("+"):
                    symlink_target_chunks.append(line[1:])
                continue
            in_hunk = False

        if line.startswith(("new file mode ", "new mode ", "old mode ", "deleted file mode ")):
            mode = line.rsplit(" ", 1)[-1].strip()
            if mode == "160000":
                raise HandoffProjectError(f"Submodule mode 160000 refused in {label}")
            if line.startswith(("new file mode ", "new mode ")) and mode == "120000":
                current_is_symlink = True
        elif line.startswith("index "):
            parts = line.split()
            if len(parts) >= 3 and parts[2] == "120000":
                current_is_symlink = True
            if len(parts) >= 3 and parts[2] == "160000":
                raise HandoffProjectError(f"Submodule mode 160000 refused in {label}")
        elif line.startswith("rename from "):
            rel = _unquote_git_c_path(line[len("rename from ") :])
            _validate_relative_repo_path(rel)
        elif line.startswith("rename to "):
            rel = _unquote_git_c_path(line[len("rename to ") :])
            _validate_relative_repo_path(rel)
            current_path = rel
        elif line.startswith("copy from "):
            rel = _unquote_git_c_path(line[len("copy from ") :])
            _validate_relative_repo_path(rel)
        elif line.startswith("copy to "):
            rel = _unquote_git_c_path(line[len("copy to ") :])
            _validate_relative_repo_path(rel)
            current_path = rel
        elif line.startswith("--- "):
            raw_old = line[4:].split("\t", 1)[0]
            old_unquoted = _unquote_git_c_path(raw_old)
            if old_unquoted != "/dev/null":
                _strip_patch_prefix(old_unquoted, "a/")
        elif line.startswith("+++ "):
            raw_new = line[4:].split("\t", 1)[0]
            new_unquoted = _unquote_git_c_path(raw_new)
            if new_unquoted != "/dev/null":
                current_path = _strip_patch_prefix(new_unquoted, "b/")
        elif line.startswith("@@ "):
            in_hunk = True
        elif line == "GIT binary patch":
            if current_is_symlink:
                raise HandoffProjectError(f"Binary symlink patch is not supported in {label}")
            in_binary = True

    _flush_symlink_check()


def _validate_staging_file(staging_path: Path, filename: Any, role: str) -> Path:
    if not isinstance(filename, str) or not filename or "\x00" in filename:
        raise HandoffProjectError(f"Invalid filename for {role}: {filename!r}")
    if "/" in filename or "\\" in filename or filename in (".", ".."):
        raise HandoffProjectError(f"Unsafe staging filename for {role}: {filename!r}")
    candidate = staging_path / filename
    if not os.path.lexists(candidate):
        raise HandoffProjectError(f"Missing staging artifact for {role}: {candidate}")
    st = os.lstat(candidate)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise HandoffProjectError(f"Staging artifact for {role} must be a regular file: {candidate}")
    return candidate


def _validate_tar_safety(archive_path: Path) -> None:
    try:
        with tarfile.open(archive_path, "r:*") as tf:
            seen_paths: set[str] = set()
            seen_symlinks: set[str] = set()
            for member in tf.getmembers():
                rel_posix = _validate_relative_repo_path(member.name)
                norm_name = rel_posix.as_posix()
                if norm_name in seen_paths:
                    raise HandoffProjectError(
                        f"Duplicate entry in untracked archive: {norm_name!r}"
                    )

                parts = rel_posix.parts
                for depth in range(1, len(parts)):
                    ancestor = "/".join(parts[:depth])
                    if ancestor in seen_symlinks:
                        raise HandoffProjectError(
                            f"Archive entry {norm_name!r} traverses through archived symlink {ancestor!r}"
                        )

                if member.issym():
                    _validate_symlink_target(norm_name, member.linkname)
                    seen_symlinks.add(norm_name)
                    seen_paths.add(norm_name)
                elif member.isreg():
                    if member.size < 0:
                        raise HandoffProjectError(
                            f"Negative file size in archive for {norm_name!r}"
                        )
                    seen_paths.add(norm_name)
                elif member.isdir():
                    seen_paths.add(norm_name)
                else:
                    raise HandoffProjectError(
                        f"Unsupported tar member type for {norm_name!r} (only regular files and symlinks allowed)"
                    )
    except tarfile.TarError as exc:
        raise HandoffProjectError(f"Invalid untracked tar archive: {exc}") from exc


def _ensure_safe_directory(root: Path, rel_posix: PurePosixPath) -> Path:
    current = root
    for part in rel_posix.parts:
        if part in ("", ".", "..", ".git"):
            raise HandoffProjectError(f"Unsafe directory component: {part!r}")
        current = current / part
        if os.path.lexists(current):
            st = os.lstat(current)
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                raise HandoffProjectError(
                    f"Refusing to traverse non-directory or symlink component: {current}"
                )
        else:
            current.mkdir(mode=0o755, exist_ok=False)
    return current


def _extract_untracked_tar_safely(archive_path: Path, dest_root: Path) -> None:
    dest_real = Path(os.path.realpath(dest_root))
    open_flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
    )
    with tarfile.open(archive_path, "r:*") as tf:
        for member in tf.getmembers():
            rel_posix = _validate_relative_repo_path(member.name)
            norm_name = rel_posix.as_posix()
            if member.isdir():
                _ensure_safe_directory(dest_root, rel_posix)
                continue

            parent_posix = rel_posix.parent
            parent_dir = (
                dest_root
                if str(parent_posix) == "."
                else _ensure_safe_directory(dest_root, parent_posix)
            )
            target_path = parent_dir / rel_posix.name
            if os.path.lexists(target_path):
                raise HandoffProjectError(
                    f"Refusing to overwrite existing destination path during untracked extraction: {norm_name!r}"
                )

            if member.issym():
                _validate_symlink_target(norm_name, member.linkname)
                os.symlink(member.linkname, target_path)
                _validate_realpath_within_root(dest_real, target_path, f"Extracted symlink {norm_name!r}")
            elif member.isreg():
                mode = 0o755 if (member.mode & 0o111) else 0o644
                src_stream = tf.extractfile(member)
                if src_stream is None:
                    raise HandoffProjectError(f"Missing payload for regular file {norm_name!r}")
                with src_stream:
                    fd = os.open(target_path, open_flags, mode)
                    written = 0
                    with os.fdopen(fd, "wb") as out_file:
                        while True:
                            chunk = src_stream.read(65536)
                            if not chunk:
                                break
                            out_file.write(chunk)
                            written += len(chunk)
                    if written != member.size:
                        raise HandoffProjectError(
                            f"Size mismatch extracting {norm_name!r}: expected {member.size}, wrote {written}"
                        )
                    os.chmod(target_path, mode)
            else:
                raise HandoffProjectError(f"Unsupported archive entry: {norm_name!r}")


def _verify_worktree_safety(dest_root: Path) -> None:
    dest_real = Path(os.path.realpath(dest_root))
    for current_root, dirnames, filenames in os.walk(dest_root, topdown=True, followlinks=False):
        curr_path = Path(current_root)
        if curr_path == dest_root and ".git" in dirnames:
            dirnames.remove(".git")
        for name in [*dirnames, *filenames]:
            full_path = curr_path / name
            rel_str = full_path.relative_to(dest_root).as_posix()
            st = os.lstat(full_path)
            if stat.S_ISLNK(st.st_mode):
                target = os.readlink(full_path)
                _validate_symlink_target(rel_str, target)
                _validate_realpath_within_root(dest_real, full_path, f"Restored symlink {rel_str!r}")


def unpack_project(
    staging: Path,
    destination: Path,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Restore a packed Git snapshot into a brand-new `destination` directory."""
    try:
        staging_path = Path(staging).expanduser().resolve(strict=True)
    except OSError as exc:
        raise HandoffProjectError(f"Staging directory does not exist: {staging}") from exc
    if not staging_path.is_dir():
        raise HandoffProjectError(f"Staging path is not a directory: {staging_path}")

    dest_raw = Path(destination).expanduser()
    if os.path.lexists(dest_raw):
        raise HandoffProjectError(f"Destination already exists; refusing to overwrite: {dest_raw}")
    try:
        dest_parent = dest_raw.parent.resolve(strict=True)
    except OSError as exc:
        raise HandoffProjectError(
            f"Destination parent directory does not exist: {dest_raw.parent}"
        ) from exc
    dest_path = dest_parent / dest_raw.name
    if os.path.lexists(dest_path):
        raise HandoffProjectError(f"Destination already exists; refusing to overwrite: {dest_path}")

    if metadata is None:
        meta_file = _validate_staging_file(staging_path, METADATA_FILENAME, "metadata")
        try:
            metadata = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise HandoffProjectError(f"Invalid metadata in {meta_file}: {exc}") from exc

    if not isinstance(metadata, dict):
        raise HandoffProjectError("Project metadata must be a JSON object.")

    relative_cwd = metadata.get("relative_cwd")
    if not isinstance(relative_cwd, str) or not relative_cwd:
        raise HandoffProjectError(f"Invalid relative_cwd in metadata: {relative_cwd!r}")
    if relative_cwd != ".":
        _validate_relative_repo_path(relative_cwd)

    commit = metadata.get("commit")
    if not isinstance(commit, str) or not _HEX_COMMIT_RE.fullmatch(commit):
        raise HandoffProjectError(f"Invalid commit in metadata: {commit!r}")

    branch = metadata.get("branch")
    if branch is not None:
        if not isinstance(branch, str) or not branch or branch.startswith("-"):
            raise HandoffProjectError(f"Invalid branch in metadata: {branch!r}")
        ref_check = _run_git(
            staging_path, ["check-ref-format", "--branch", branch], check=False
        )
        if ref_check.returncode != 0:
            raise HandoffProjectError(f"Invalid Git branch name in metadata: {branch!r}")

    intent_to_add = metadata.get("intent_to_add") or []
    if not isinstance(intent_to_add, list):
        raise HandoffProjectError("Invalid intent_to_add in metadata.")
    for item in intent_to_add:
        if not isinstance(item, str):
            raise HandoffProjectError("Non-string entry in intent_to_add.")
        _validate_relative_repo_path(item)

    files_meta = metadata.get("files")
    if not isinstance(files_meta, dict):
        raise HandoffProjectError("Metadata missing 'files' mapping.")

    bundle_path = _validate_staging_file(
        staging_path, files_meta.get("bundle", BUNDLE_FILENAME), "bundle"
    )
    staged_patch_path = _validate_staging_file(
        staging_path, files_meta.get("staged_patch", STAGED_PATCH_FILENAME), "staged_patch"
    )
    unstaged_patch_path = _validate_staging_file(
        staging_path, files_meta.get("unstaged_patch", UNSTAGED_PATCH_FILENAME), "unstaged_patch"
    )
    untracked_archive_path = _validate_staging_file(
        staging_path,
        files_meta.get("untracked_archive", UNTRACKED_ARCHIVE_FILENAME),
        "untracked_archive",
    )

    staged_bytes = staged_patch_path.read_bytes()
    unstaged_bytes = unstaged_patch_path.read_bytes()
    _validate_patch_safety(staged_bytes, "staged.patch")
    _validate_patch_safety(unstaged_bytes, "unstaged.patch")
    _validate_tar_safety(untracked_archive_path)

    dest_path.mkdir(mode=0o700, exist_ok=False)
    try:
        _run_git(dest_path, ["init", "-q"], read_only=False)
        _run_git(dest_path, ["bundle", "unbundle", str(bundle_path)], read_only=False)

        resolved_commit = (
            _run_git(dest_path, ["rev-parse", "--verify", f"{commit}^{{commit}}"])
            .stdout.decode("ascii")
            .strip()
        )
        if resolved_commit.lower() != commit.lower():
            raise HandoffProjectError(
                f"Unbundled commit mismatch: expected {commit}, got {resolved_commit}"
            )

        if branch is not None:
            _run_git(
                dest_path,
                ["checkout", "-f", "-B", branch, commit, "--"],
                read_only=False,
            )
        else:
            _run_git(
                dest_path,
                ["checkout", "-f", "--detach", commit, "--"],
                read_only=False,
            )

        _verify_worktree_safety(dest_path)

        if staged_bytes:
            _run_git(
                dest_path,
                ["apply", "--index", "--binary", "--whitespace=nowarn", str(staged_patch_path)],
                read_only=False,
            )
            _verify_worktree_safety(dest_path)

        if unstaged_bytes:
            _run_git(
                dest_path,
                ["apply", "--binary", "--whitespace=nowarn", str(unstaged_patch_path)],
                read_only=False,
            )
            _verify_worktree_safety(dest_path)

        if intent_to_add:
            _run_git(
                dest_path,
                ["add", "-N", "--", *intent_to_add],
                read_only=False,
            )

        _extract_untracked_tar_safely(untracked_archive_path, dest_path)
        _verify_worktree_safety(dest_path)

        if relative_cwd == ".":
            target_cwd = dest_path
        else:
            target_cwd = _ensure_safe_directory(dest_path, _validate_relative_repo_path(relative_cwd))

        dest_real = Path(os.path.realpath(dest_path))
        _validate_realpath_within_root(dest_real, target_cwd, "Target working directory")
        if not target_cwd.is_dir():
            raise HandoffProjectError(f"Restored working directory does not exist: {target_cwd}")
        return target_cwd
    except Exception as exc:
        shutil.rmtree(dest_path, ignore_errors=True)
        if isinstance(exc, HandoffProjectError):
            raise
        raise HandoffProjectError(f"Failed to unpack project: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    pack_parser = subparsers.add_parser("pack", help="Pack a Git repository snapshot into staging")
    pack_parser.add_argument("project", type=Path, help="Source project directory inside Git repo")
    pack_parser.add_argument("staging", type=Path, help="Existing private staging directory")

    restore_parser = subparsers.add_parser(
        "restore", help="Restore a staged snapshot into a new destination directory"
    )
    restore_parser.add_argument("staging", type=Path, help="Staging directory containing project.json")
    restore_parser.add_argument("destination", type=Path, help="New destination directory to create")

    args = parser.parse_args(argv)
    if args.command == "pack":
        metadata = pack_project(args.project, args.staging)
        print(json.dumps(metadata))
        return 0
    if args.command == "restore":
        cwd = unpack_project(args.staging, args.destination)
        print(cwd)
        return 0
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HandoffProjectError as err:
        print(f"hop_project: {err}", file=sys.stderr)
        raise SystemExit(1)
