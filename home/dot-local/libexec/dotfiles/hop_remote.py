#!/usr/bin/env python3
"""Destination runtime launcher and readiness verifier for OMP session handoff."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any

SESSION_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

HERDR_CALLER_ENV_VARS = (
    "HERDR_ENV",
    "HERDR_SOCKET_PATH",
    "HERDR_CLIENT_SOCKET_PATH",
    "HERDR_SESSION",
    "HERDR_WORKSPACE_ID",
    "HERDR_TAB_ID",
    "HERDR_PANE_ID",
    "HERDR_ACTIVE_WORKSPACE_ID",
    "HERDR_ACTIVE_TAB_ID",
    "HERDR_ACTIVE_PANE_ID",
    "HERDR_ACTIVE_PANE_CWD",
    "OMPCODE",
)

PRIVATE_HERDR_CONFIG = """\
onboarding = false

[terminal]
new_cwd = "current"

[update]
version_check = false
manifest_check = false

[ui.sound]
enabled = false
"""

OMP_LEASE_HOOK_TS = """\
export default function (pi: any) {
  pi.on("session_start", async () => {
    // A public extension entry claims the restored session without submitting work.
    await pi.appendEntry("dotfiles.omp-handoff", { kind: "destination-claimed" });
  });
}
"""


class HandoffRuntimeError(RuntimeError):
    """Raised when the destination runtime cannot be started or verified."""


class HandoffTimeoutError(HandoffRuntimeError, TimeoutError):
    """Raised when the destination runtime does not claim the OMP lease within timeout."""


def validate_session_name(name: str) -> str:
    """Validate an isolated Herdr session name, rejecting empty, default, or unsafe names."""
    if not isinstance(name, str):
        raise ValueError("Herdr session name must be a string")
    cleaned = name.strip()
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(f"Invalid Herdr session name: {name!r}")
    if cleaned.lower() == "default":
        raise ValueError("Refusing to use the 'default' Herdr session for isolated handoff")
    if not SESSION_NAME_RE.match(cleaned):
        raise ValueError(
            f"Invalid Herdr session name {name!r}: only ASCII letters, digits, '.', '_', and '-' are allowed"
        )
    return cleaned


def extract_session_id(session_file: Path) -> str:
    """Extract the session ID from an OMP .jsonl session file (supporting leading title records)."""
    path = Path(session_file).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"OMP session file not found: {path}")
    with path.open("rb") as handle:
        for _ in range(50):
            line = handle.readline(1024 * 1024)
            if not line:
                break
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(record, dict) and record.get("type") == "session":
                session_id = record.get("id")
                if isinstance(session_id, str) and session_id.strip():
                    return session_id.strip()
                break
    raise ValueError(f"No valid OMP session header in {path}")


def _resolve_executable(name: str, env: dict[str, str]) -> Path:
    found = shutil.which(name, path=env.get("PATH"))
    if found:
        return Path(found).resolve()
    candidate = Path.home() / ".local" / "bin" / name
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate.resolve()
    raise FileNotFoundError(f"Required destination executable not found: {name}")


def _build_runtime_env(herdr_bin: Path, omp_bin: Path, herdr_config_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in HERDR_CALLER_ENV_VARS:
        env.pop(key, None)
    path_entries = [str(omp_bin.parent), str(herdr_bin.parent)]
    local_bin = str(Path.home() / ".local" / "bin")
    if local_bin not in path_entries:
        path_entries.append(local_bin)
    existing_path = env.get("PATH", "")
    if existing_path:
        path_entries.append(existing_path)
    env["PATH"] = os.pathsep.join(path_entries)
    env["HERDR_CONFIG_PATH"] = str(herdr_config_path)
    env["OMP_SKIP_SETUP"] = "1"
    return env


def _append_log(log_path: Path, message: str) -> None:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message.rstrip()}\n")


def _write_private_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _write_state(state_path: Path, payload: dict[str, Any]) -> None:
    tmp_path = state_path.with_suffix(".json.tmp")
    _write_private_text(tmp_path, json.dumps(payload, indent=2) + "\n")
    tmp_path.replace(state_path)


def _run_cmd(
    argv: list[str],
    *,
    env: dict[str, str],
    cwd: Path | None = None,
    timeout: float = 10.0,
    log_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd_Timeout = max(1.0, min(timeout, 30.0))
    result = subprocess.run(
        argv,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        capture_output=True,
        text=True,
        timeout=cmd_Timeout,
    )
    if log_path is not None:
        _append_log(
            log_path,
            f"cmd={shlex.join(argv)} rc={result.returncode} "
            f"stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}",
        )
    return result


def _pid_is_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        try:
            stat_text = proc_stat.read_text(encoding="utf-8", errors="replace")
            rparen = stat_text.rfind(")")
            if rparen != -1:
                state_fields = stat_text[rparen + 2 :].split()
                if state_fields and state_fields[0] == "Z":
                    return False
        except OSError:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _query_omp_lease(
    omp_bin: Path,
    session_id: str,
    *,
    env: dict[str, str],
    timeout: float = 5.0,
    log_path: Path | None = None,
) -> dict[str, list[str]]:
    res = _run_cmd(
        [str(omp_bin), "session", "lease", "--json", "--", session_id],
        env=env,
        timeout=timeout,
        log_path=log_path,
    )
    if res.returncode != 0:
        detail = res.stderr.strip() or res.stdout.strip() or f"exit {res.returncode}"
        raise HandoffRuntimeError(f"omp session lease failed: {detail}")
    try:
        data = json.loads(res.stdout)
    except ValueError as exc:
        raise HandoffRuntimeError(f"Invalid JSON from omp session lease: {res.stdout!r}") from exc
    if not isinstance(data, dict):
        raise HandoffRuntimeError(f"Unexpected omp session lease payload: {data!r}")
    held = [str(item) for item in data.get("held", []) if isinstance(item, str)]
    unknown = [str(item) for item in data.get("unknown", []) if isinstance(item, str)]
    return {"held": held, "unknown": unknown}


def _query_herdr_server_status(
    herdr_bin: Path,
    session_name: str,
    *,
    env: dict[str, str],
    timeout: float = 5.0,
    log_path: Path | None = None,
) -> dict[str, Any]:
    res = _run_cmd(
        [str(herdr_bin), "--session", session_name, "status", "server", "--json"],
        env=env,
        timeout=timeout,
        log_path=log_path,
    )
    stdout = res.stdout.strip()
    if stdout:
        try:
            data = json.loads(stdout)
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
    if res.returncode != 0:
        detail = res.stderr.strip() or stdout or f"exit {res.returncode}"
        raise HandoffRuntimeError(f"herdr status server failed for {session_name!r}: {detail}")
    raise HandoffRuntimeError(f"Unparseable herdr status server output: {stdout!r}")


def _herdr_json(
    herdr_bin: Path,
    session_name: str,
    args: list[str],
    *,
    env: dict[str, str],
    timeout: float = 10.0,
    log_path: Path | None = None,
) -> dict[str, Any]:
    res = _run_cmd(
        [str(herdr_bin), "--session", session_name, *args],
        env=env,
        timeout=timeout,
        log_path=log_path,
    )
    if res.returncode != 0:
        detail = res.stderr.strip() or res.stdout.strip() or f"exit {res.returncode}"
        raise HandoffRuntimeError(f"herdr {' '.join(args)} failed: {detail}")
    try:
        payload = json.loads(res.stdout)
    except ValueError as exc:
        raise HandoffRuntimeError(
            f"Invalid JSON from herdr {' '.join(args)}: {res.stdout!r}"
        ) from exc
    if not isinstance(payload, dict) or "result" not in payload:
        raise HandoffRuntimeError(
            f"Unexpected response from herdr {' '.join(args)}: {payload!r}"
        )
    return payload


def _same_path(first: str | Path | None, second: Path) -> bool:
    if not first:
        return False
    try:
        return Path(first).expanduser().resolve() == second.resolve()
    except OSError:
        return False


def _ensure_workspace_pane(
    herdr_bin: Path,
    session_name: str,
    cwd: Path,
    *,
    env: dict[str, str],
    timeout: float,
    log_path: Path,
) -> dict[str, str]:
    pane_list = _herdr_json(
        herdr_bin,
        session_name,
        ["pane", "list"],
        env=env,
        timeout=timeout,
        log_path=log_path,
    )
    panes = pane_list.get("result", {}).get("panes", [])
    if isinstance(panes, list):
        for pane in panes:
            if isinstance(pane, dict) and _same_path(pane.get("cwd"), cwd):
                return {
                    "workspace_id": str(pane["workspace_id"]),
                    "tab_id": str(pane["tab_id"]),
                    "pane_id": str(pane["pane_id"]),
                    "terminal_id": str(pane.get("terminal_id") or ""),
                }

    initial_workspaces = [
         str(p["workspace_id"])
        for p in (panes if isinstance(panes, list) else [])
        if isinstance(p, dict) and p.get("workspace_id")
    ]
    created = _herdr_json(
        herdr_bin,
        session_name,
        ["workspace", "create", "--cwd", str(cwd), "--label", cwd.name or "handoff", "--focus"],
        env=env,
        timeout=timeout,
        log_path=log_path,
    )["result"]
    workspace_id = str(created["workspace"]["workspace_id"])
    tab_id = str(created["tab"]["tab_id"])
    root_pane = created["root_pane"]
    pane_id = str(root_pane["pane_id"])
    terminal_id = str(root_pane.get("terminal_id") or "")

    for old_ws_id in set(initial_workspaces):
        if old_ws_id != workspace_id:
            try:
                _run_cmd(
                    [str(herdr_bin), "--session", session_name, "workspace", "close", old_ws_id],
                    env=env,
                    timeout=5.0,
                    log_path=log_path,
                )
            except Exception:
                pass

    return {
        "workspace_id": workspace_id,
        "tab_id": tab_id,
        "pane_id": pane_id,
        "terminal_id": terminal_id,
    }


def _find_child_omp_pid(
    process_info: dict[str, Any],
    *,
    env: dict[str, str],
) -> tuple[int | None, int | None]:
    shell_pid_raw = process_info.get("shell_pid")
    shell_pid = shell_pid_raw if isinstance(shell_pid_raw, int) and shell_pid_raw > 0 else None

    fg_procs = process_info.get("foreground_processes")
    candidates: list[int] = []
    fallback_candidates: list[int] = []
    if isinstance(fg_procs, list):
        for entry in fg_procs:
            if not isinstance(entry, dict):
                continue
            pid = entry.get("pid")
            if not isinstance(pid, int) or pid <= 0 or not _pid_is_alive(pid):
                continue
            name = str(entry.get("name") or "").lower()
            cmdline = str(entry.get("cmdline") or "").lower()
            argv = [str(a).lower() for a in (entry.get("argv") or []) if isinstance(a, str)]
            if "omp" in name or "omp" in cmdline or any("omp" in arg for arg in argv):
                candidates.append(pid)
            elif pid != shell_pid:
                fallback_candidates.append(pid)

    if candidates:
        return shell_pid, candidates[0]

    if shell_pid is not None and _pid_is_alive(shell_pid):
        try:
            ps_res = subprocess.run(
                ["ps", "-o", "pid=,comm=,args=", "--ppid", str(shell_pid)],
                env=env,
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if ps_res.returncode == 0:
                for line in ps_res.stdout.splitlines():
                    parts = line.strip().split(None, 2)
                    if not parts:
                        continue
                    try:
                        child_pid = int(parts[0])
                    except ValueError:
                        continue
                    if not _pid_is_alive(child_pid):
                        continue
                    rest = " ".join(parts[1:]).lower()
                    if "omp" in rest:
                        return shell_pid, child_pid
                    fallback_candidates.append(child_pid)
        except Exception:
            pass

    if fallback_candidates:
        return shell_pid, fallback_candidates[0]
    return shell_pid, None


def _read_pane_tail(
    herdr_bin: Path,
    session_name: str,
    pane_id: str,
    *,
    env: dict[str, str],
    log_path: Path,
) -> str:
    try:
        res = _run_cmd(
            [
                str(herdr_bin),
                "--session",
                session_name,
                "pane",
                "read",
                pane_id,
                "--source",
                "recent-unwrapped",
                "--lines",
                "60",
            ],
            env=env,
            timeout=5.0,
            log_path=log_path,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def _read_file_tail(path: Path, max_bytes: int = 4096) -> str:
    try:
        if not path.is_file():
            return ""
        data = path.read_bytes()
        return data[-max_bytes:].decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _wait_for_readiness(
    *,
    herdr_bin: Path,
    omp_bin: Path,
    session_name: str,
    session_id: str,
    session_file: Path,
    cwd: Path,
    transfer_dir: Path,
    pane_meta: dict[str, str],
    herdr_config_path: Path,
    omp_hook_path: Path,
    runtime_log_path: Path,
    server_log_path: Path,
    state_path: Path,
    env: dict[str, str],
    deadline: float,
    server_proc: subprocess.Popen[bytes] | None = None,
) -> dict[str, Any]:
    pane_id = pane_meta["pane_id"]
    last_lease: dict[str, list[str]] = {"held": [], "unknown": []}
    last_shell_pid: int | None = None
    last_omp_pid: int | None = None
    socket_path: str = ""

    while True:
        now = time.monotonic()
        remaining = max(1.0, deadline - now)

        if server_proc is not None and server_proc.poll() is not None:
            server_tail = _read_file_tail(server_log_path)
            raise HandoffRuntimeError(
                f"Herdr server for session {session_name!r} exited early with code {server_proc.returncode}. "
                f"Inspect {server_log_path} and {runtime_log_path}. "
                f"Server log tail: {server_tail or '<empty>'}"
            )

        status = _query_herdr_server_status(
            herdr_bin,
            session_name,
            env=env,
            timeout=min(5.0, remaining),
            log_path=runtime_log_path,
        )
        if not status.get("running"):
            server_tail = _read_file_tail(server_log_path)
            raise HandoffRuntimeError(
                f"Herdr session {session_name!r} is no longer running while waiting for OMP lease. "
                f"Inspect {server_log_path} and {runtime_log_path}. "
                f"Server log tail: {server_tail or '<empty>'}"
            )
        socket_path = str(status.get("socket") or socket_path)

        proc_payload = _herdr_json(
            herdr_bin,
            session_name,
            ["pane", "process-info", "--pane", pane_id],
            env=env,
            timeout=min(5.0, remaining),
            log_path=runtime_log_path,
        )
        pinfo = proc_payload.get("result", {}).get("process_info", {})
        if not isinstance(pinfo, dict):
            pinfo = {}
        last_shell_pid, last_omp_pid = _find_child_omp_pid(pinfo, env=env)

        last_lease = _query_omp_lease(
            omp_bin,
            session_id,
            env=env,
            timeout=min(5.0, remaining),
            log_path=runtime_log_path,
        )
        lease_held = (
            session_id in last_lease["held"]
            and session_id not in last_lease["unknown"]
        )

        if (
            lease_held
            and _pid_is_alive(last_shell_pid)
            and _pid_is_alive(last_omp_pid)
        ):
            # Re-verify lease and child liveness to guard against a crash right after lease acquisition.
            confirm_lease = _query_omp_lease(
                omp_bin,
                session_id,
                env=env,
                timeout=min(5.0, max(1.0, deadline - time.monotonic())),
                log_path=runtime_log_path,
            )
            if (
                session_id in confirm_lease["held"]
                and session_id not in confirm_lease["unknown"]
                and _pid_is_alive(last_shell_pid)
                and _pid_is_alive(last_omp_pid)
            ):
                ready_payload: dict[str, Any] = {
                    "ready": True,
                    "status": "ready",
                    "session_name": session_name,
                    "name": session_name,
                    "session_id": session_id,
                    "session_file": str(session_file),
                    "cwd": str(cwd),
                    "transfer_dir": str(transfer_dir),
                    "workspace_id": pane_meta["workspace_id"],
                    "tab_id": pane_meta["tab_id"],
                    "pane_id": pane_id,
                    "terminal_id": pane_meta["terminal_id"],
                    "shell_pid": last_shell_pid,
                    "omp_pid": last_omp_pid,
                    "server_pid": server_proc.pid if server_proc is not None else None,
                    "socket_path": socket_path,
                    "lease": confirm_lease,
                    "attach_command": f"herdr --session {shlex.quote(session_name)}",
                    "attach_hint": f"herdr --session {shlex.quote(session_name)}",
                    "config_path": str(herdr_config_path),
                    "herdr_config_path": str(herdr_config_path),
                    "hook_path": str(omp_hook_path),
                    "log_path": str(runtime_log_path),
                    "server_log_path": str(server_log_path),
                    "state_path": str(state_path),
                }
                _write_state(state_path, ready_payload)
                _append_log(
                    runtime_log_path,
                    f"READY session_name={session_name} session_id={session_id} "
                    f"pane_id={pane_id} omp_pid={last_omp_pid}",
                )
                return ready_payload

        if time.monotonic() >= deadline:
            pane_tail = _read_pane_tail(
                herdr_bin,
                session_name,
                pane_id,
                env=env,
                log_path=runtime_log_path,
            )
            server_tail = _read_file_tail(server_log_path)
            failure_state: dict[str, Any] = {
                "ready": False,
                "status": "timeout",
                "session_name": session_name,
                "name": session_name,
                "session_id": session_id,
                "session_file": str(session_file),
                "cwd": str(cwd),
                "transfer_dir": str(transfer_dir),
                "workspace_id": pane_meta["workspace_id"],
                "tab_id": pane_meta["tab_id"],
                "pane_id": pane_id,
                "terminal_id": pane_meta["terminal_id"],
                "shell_pid": last_shell_pid,
                "omp_pid": last_omp_pid,
                "server_pid": server_proc.pid if server_proc is not None else None,
                "socket_path": socket_path,
                "lease": last_lease,
                "herdr_bin": str(herdr_bin),
                "omp_bin": str(omp_bin),
                "attach_command": f"herdr --session {shlex.quote(session_name)}",
                "attach_hint": f"herdr --session {shlex.quote(session_name)}",
                "config_path": str(herdr_config_path),
                "herdr_config_path": str(herdr_config_path),
                "hook_path": str(omp_hook_path),
                "log_path": str(runtime_log_path),
                "server_log_path": str(server_log_path),
                "state_path": str(state_path),
                "pane_tail": pane_tail,
            }
            _write_state(state_path, failure_state)
            _append_log(
                runtime_log_path,
                f"TIMEOUT session_name={session_name} session_id={session_id} "
                f"lease={last_lease} shell_pid={last_shell_pid} omp_pid={last_omp_pid} "
                f"pane_tail={pane_tail!r}",
            )
            raise HandoffTimeoutError(
                f"Timed out waiting for destination OMP to hold lease for session {session_id} "
                f"in Herdr session {session_name!r} (lease={last_lease}, shell_pid={last_shell_pid}, "
                f"omp_pid={last_omp_pid}). Agent was NOT killed. "
                f"Inspect logs at {runtime_log_path} and {server_log_path} "
                f"(config: {herdr_config_path})."
                + (f" Pane output: {pane_tail}" if pane_tail else "")
                + (f" Server log: {server_tail}" if server_tail and not pane_tail else "")
            )

        time.sleep(0.15)


def start_runtime(
    cwd: Path,
    session_file: Path,
    transfer_dir: Path,
    name: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Start a new isolated named Herdr session running `omp --resume` and wait for lease ownership."""
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    session_name = validate_session_name(name)
    resolved_transfer_dir = Path(transfer_dir).expanduser().resolve()
    resolved_transfer_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        resolved_transfer_dir.chmod(0o700)
    except OSError:
        pass

    runtime_log_path = resolved_transfer_dir / "runtime.log"
    server_log_path = resolved_transfer_dir / "herdr-server.log"
    herdr_config_path = resolved_transfer_dir / "herdr-config.toml"
    omp_hook_path = resolved_transfer_dir / "hop_omp_hook.ts"
    state_path = resolved_transfer_dir / "runtime-state.json"

    resolved_cwd = Path(cwd).expanduser().resolve()
    if not resolved_cwd.is_dir():
        raise FileNotFoundError(f"Destination project directory not found: {resolved_cwd}")

    resolved_session_file = Path(session_file).expanduser().resolve()
    session_id = extract_session_id(resolved_session_file)

    _write_private_text(herdr_config_path, PRIVATE_HERDR_CONFIG)
    _write_private_text(omp_hook_path, OMP_LEASE_HOOK_TS)

    herdr_bin = _resolve_executable("herdr", os.environ)
    omp_bin = _resolve_executable("omp", os.environ)
    env = _build_runtime_env(herdr_bin, omp_bin, herdr_config_path)

    deadline = time.monotonic() + float(timeout)
    _append_log(
        runtime_log_path,
        f"START session_name={session_name} session_id={session_id} "
        f"cwd={resolved_cwd} session_file={resolved_session_file}",
    )

    initial_lease = _query_omp_lease(
        omp_bin,
        session_id,
        env=env,
        timeout=min(5.0, max(1.0, deadline - time.monotonic())),
        log_path=runtime_log_path,
    )
    if session_id in initial_lease["held"] or session_id in initial_lease["unknown"]:
        raise HandoffRuntimeError(
            f"Destination session {session_id} is already held or unknown before launch: {initial_lease}"
        )

    initial_status = _query_herdr_server_status(
        herdr_bin,
        session_name,
        env=env,
        timeout=min(5.0, max(1.0, deadline - time.monotonic())),
        log_path=runtime_log_path,
    )
    if initial_status.get("running"):
        raise HandoffRuntimeError(
            f"Herdr session {session_name!r} is already running; refusing to touch an existing session"
        )

    with server_log_path.open("ab") as server_log_file:
        try:
            server_log_path.chmod(0o600)
        except OSError:
            pass
        server_proc = subprocess.Popen(
            [str(herdr_bin), "--session", session_name, "server"],
            cwd=str(resolved_cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=server_log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )

    _append_log(runtime_log_path, f"Spawned herdr server pid={server_proc.pid}")

    # Wait for the new isolated Herdr server socket to accept API requests.
    socket_path = str(initial_status.get("socket") or "")
    while True:
        if server_proc.poll() is not None:
            server_tail = _read_file_tail(server_log_path)
            raise HandoffRuntimeError(
                f"Herdr server for session {session_name!r} exited during startup "
                f"(exit {server_proc.returncode}). Inspect {server_log_path}. "
                f"Server log: {server_tail or '<empty>'}"
            )
        status = _query_herdr_server_status(
            herdr_bin,
            session_name,
            env=env,
            timeout=min(5.0, max(1.0, deadline - time.monotonic())),
            log_path=runtime_log_path,
        )
        if status.get("running"):
            socket_path = str(status.get("socket") or socket_path)
            break
        if time.monotonic() >= deadline:
            server_tail = _read_file_tail(server_log_path)
            raise HandoffTimeoutError(
                f"Timed out waiting for Herdr server {session_name!r} to start. "
                f"Inspect {server_log_path} and {runtime_log_path}. "
                f"Server log: {server_tail or '<empty>'}"
            )
        time.sleep(0.1)

    pane_meta = _ensure_workspace_pane(
        herdr_bin,
        session_name,
        resolved_cwd,
        env=env,
        timeout=min(10.0, max(1.0, deadline - time.monotonic())),
        log_path=runtime_log_path,
    )
    pane_id = pane_meta["pane_id"]

    # Wait briefly for the pane's shell process to exist before sending the launch command.
    while time.monotonic() < deadline:
        proc_payload = _herdr_json(
            herdr_bin,
            session_name,
            ["pane", "process-info", "--pane", pane_id],
            env=env,
            timeout=min(5.0, max(1.0, deadline - time.monotonic())),
            log_path=runtime_log_path,
        )
        pinfo = proc_payload.get("result", {}).get("process_info", {})
        shell_pid = pinfo.get("shell_pid") if isinstance(pinfo, dict) else None
        if isinstance(shell_pid, int) and _pid_is_alive(shell_pid):
            break
        time.sleep(0.05)

    omp_command = (
        f"cd -- {shlex.quote(str(resolved_cwd))} && "
        f"{shlex.quote(str(omp_bin))} --resume {shlex.quote(str(resolved_session_file))} "
        f"--hook {shlex.quote(str(omp_hook_path))}"
    )

    _write_state(
        state_path,
        {
            "ready": False,
            "status": "starting",
            "session_name": session_name,
            "name": session_name,
            "session_id": session_id,
            "session_file": str(resolved_session_file),
            "cwd": str(resolved_cwd),
            "transfer_dir": str(resolved_transfer_dir),
            "workspace_id": pane_meta["workspace_id"],
            "tab_id": pane_meta["tab_id"],
            "pane_id": pane_id,
            "terminal_id": pane_meta["terminal_id"],
            "server_pid": server_proc.pid,
            "socket_path": socket_path,
            "herdr_bin": str(herdr_bin),
            "omp_bin": str(omp_bin),
            "attach_command": f"herdr --session {shlex.quote(session_name)}",
            "attach_hint": f"herdr --session {shlex.quote(session_name)}",
            "config_path": str(herdr_config_path),
            "herdr_config_path": str(herdr_config_path),
            "hook_path": str(omp_hook_path),
            "log_path": str(runtime_log_path),
            "server_log_path": str(server_log_path),
            "state_path": str(state_path),
        },
    )

    launch = _run_cmd(
        [str(herdr_bin), "--session", session_name, "pane", "run", pane_id, omp_command],
        env=env,
        timeout=min(10.0, max(1.0, deadline - time.monotonic())),
        log_path=runtime_log_path,
    )
    if launch.returncode:
        raise HandoffRuntimeError(
            f"Failed to launch destination OMP: {launch.stderr.strip() or launch.stdout.strip()}"
        )

    return _wait_for_readiness(
        herdr_bin=herdr_bin,
        omp_bin=omp_bin,
        session_name=session_name,
        session_id=session_id,
        session_file=resolved_session_file,
        cwd=resolved_cwd,
        transfer_dir=resolved_transfer_dir,
        pane_meta=pane_meta,
        herdr_config_path=herdr_config_path,
        omp_hook_path=omp_hook_path,
        runtime_log_path=runtime_log_path,
        server_log_path=server_log_path,
        state_path=state_path,
        env=env,
        deadline=deadline,
        server_proc=server_proc,
    )


def check_runtime(transfer_dir: Path, timeout: float = 5.0) -> dict[str, Any]:
    """Re-check whether a previously started runtime in transfer_dir now owns the OMP lease."""
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    resolved_transfer_dir = Path(transfer_dir).expanduser().resolve()
    state_path = resolved_transfer_dir / "runtime-state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"Runtime state file not found in transfer_dir: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError(f"Invalid runtime state in {state_path}")

    session_name = validate_session_name(str(state["session_name"]))
    session_file = Path(str(state["session_file"])).expanduser().resolve()
    session_id = str(state.get("session_id") or extract_session_id(session_file))
    cwd = Path(str(state["cwd"])).expanduser().resolve()
    herdr_config_path = Path(str(state.get("herdr_config_path") or (resolved_transfer_dir / "herdr-config.toml")))
    omp_hook_path = Path(str(state.get("hook_path") or (resolved_transfer_dir / "hop_omp_hook.ts")))
    runtime_log_path = Path(str(state.get("log_path") or (resolved_transfer_dir / "runtime.log")))
    server_log_path = Path(str(state.get("server_log_path") or (resolved_transfer_dir / "herdr-server.log")))

    herdr_bin = (
        Path(state["herdr_bin"])
        if state.get("herdr_bin") and Path(str(state["herdr_bin"])).is_file()
        else _resolve_executable("herdr", os.environ)
    )
    omp_bin = (
        Path(state["omp_bin"])
        if state.get("omp_bin") and Path(str(state["omp_bin"])).is_file()
        else _resolve_executable("omp", os.environ)
    )
    env = _build_runtime_env(herdr_bin, omp_bin, herdr_config_path)

    pane_meta = {
        "workspace_id": str(state.get("workspace_id") or "w1"),
        "tab_id": str(state.get("tab_id") or "w1:t1"),
        "pane_id": str(state.get("pane_id") or "w1:p1"),
        "terminal_id": str(state.get("terminal_id") or ""),
    }

    return _wait_for_readiness(
        herdr_bin=herdr_bin,
        omp_bin=omp_bin,
        session_name=session_name,
        session_id=session_id,
        session_file=session_file,
        cwd=cwd,
        transfer_dir=resolved_transfer_dir,
        pane_meta=pane_meta,
        herdr_config_path=herdr_config_path,
        omp_hook_path=omp_hook_path,
        runtime_log_path=runtime_log_path,
        server_log_path=server_log_path,
        state_path=state_path,
        env=env,
        deadline=time.monotonic() + float(timeout),
        server_proc=None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    start_parser = subparsers.add_parser("start", help="Start isolated Herdr runtime and wait for OMP lease")
    start_parser.add_argument("cwd", type=Path)
    start_parser.add_argument("session_file", type=Path)
    start_parser.add_argument("transfer_dir", type=Path)
    start_parser.add_argument("name", type=str)
    start_parser.add_argument("--timeout", type=float, default=30.0)

    check_parser = subparsers.add_parser("check", help="Check whether a staged runtime holds the OMP lease")
    check_parser.add_argument("transfer_dir", type=Path)
    check_parser.add_argument("--timeout", type=float, default=5.0)

    args = parser.parse_args(argv)
    if args.action == "start":
        result = start_runtime(
            args.cwd,
            args.session_file,
            args.transfer_dir,
            args.name,
            timeout=args.timeout,
        )
    else:
        result = check_runtime(args.transfer_dir, timeout=args.timeout)

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    os.umask(0o077)
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"hop_remote: {exc}", file=sys.stderr)
        raise SystemExit(1)
