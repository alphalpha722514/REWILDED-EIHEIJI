#!/usr/bin/env python3
"""Run Codex in a disposable git archive and retain a review report."""

import argparse
import contextlib
import datetime
import difflib
import errno
import fcntl
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tarfile
import threading
import time
import uuid


SECRET_NAME = r"token|key|secret|pass|askpass|aws_|cloudsdk_auth|_auth"
ALLOWED_NAMES = {
    "MAX_THINKING_TOKENS", "BUN_TLS_EXTRA_DISTRUSTED_KEYS",
    "CCR_AUTO_MODE_USER_ENV_KEYS_FACT", "AWS_CA_BUNDLE",
}
SECRET_VALUE = re.compile(
    r"(?:sk-|ghp_|github_pat_|gho_|eyJ|AKIA|Bearer )[A-Za-z0-9_.-]+"
)
SECRET_PREFIX = re.compile(r"sk-|ghp_|github_pat_|gho_|eyJ|AKIA|Bearer ")
WATCH = "CODEX_DELEGATE_WATCH_2020"
WATCH_NS = 1577836800 * 10**9
PROFILE = "delegate"
DENIED = {Path("/root/.codex"), Path.home() / ".codex"}
DOC_VERSION = "0.172.0"
VERSION_NUMBER = re.compile(r"\bv?(\d+\.\d+\.\d+)\b")


class DelegateError(Exception):
    pass


def secret_name(name):
    return name not in ALLOWED_NAMES and re.search(SECRET_NAME, name, re.I) is not None


def clean_env():
    return {name: os.environ[name] for name in os.environ if not secret_name(name)}


def redact(value):
    return SECRET_VALUE.sub("[redacted]", value).replace(WATCH, "[watch redacted]")


def decode(value):
    return value.decode("utf-8", errors="replace")


def write_private(path, data):
    # Owner-only, never through a symlink: records may hold redacted logs from a run.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as target:
        os.fchmod(target.fileno(), 0o600)
        target.write(data)


def write_json(path, value):
    write_private(path, (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8"))


ANSWER_LIMIT = 4 * 1024 * 1024


def private_run_folder(job, folder):
    runs = job / "runs"
    if runs.is_symlink() or not runs.is_dir():
        raise DelegateError("JOB/runs が不正です")
    os.chmod(runs, 0o700)
    folder.mkdir(mode=0o700)
    os.chmod(folder, 0o700)
    real = Path(os.path.realpath(folder))
    if folder.is_symlink() or not real.is_dir() or not real.is_relative_to(Path(os.path.realpath(job))):
        raise DelegateError("実行の記録の場所が JOB の外を指しています")


def read_answer(path):
    # Codex writes the answer here; accept only a regular, single-link file of bounded size.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise DelegateError("回答ファイルがシンボリックリンクに置き換えられていました") from None
        raise
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise DelegateError("回答ファイルが通常のファイルではありません")
        data = source.read(ANSWER_LIMIT + 1)
    if len(data) > ANSWER_LIMIT:
        raise DelegateError("回答ファイルが大きすぎます")
    return data


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def quote(value):
    return json.dumps(str(value), ensure_ascii=False).replace("\x7f", "\\u007f")


def toml_table(values):
    return "{" + ",".join(f"{quote(key)}={quote(value)}" for key, value in values.items()) + "}"


def overlap(left, right):
    return left.is_relative_to(right) or right.is_relative_to(left)


def codex_vendor(binary):
    candidates = [
        binary.parent / "vendor",
        *(parent / "@openai/codex-linux-x64/vendor" for parent in binary.parents),
        *(parent / "node_modules/@openai/codex-linux-x64/vendor" for parent in binary.parents),
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    # A standalone executable or test double can live outside the npm package.
    return binary.parent


def permissions(binary, job, repo, mode, reads, assignments):
    denied = DENIED | {path.resolve() for path in DENIED}
    protected = denied | {job, repo}
    filesystem = {":minimal": "read"}
    system_interfaces = {Path(name) for name in ("/proc", "/sys", "/dev")}
    for path in [codex_vendor(binary), Path("/opt/node22").resolve(),
                 *(Path(os.path.realpath(p)) for p in reads)]:
        if any(overlap(path, protected_path) for protected_path in protected | system_interfaces):
            raise DelegateError("読み取り許可が保護対象と重なっています")
        filesystem[str(path)] = "read"
    filesystem[str(job / "work")] = "write" if mode == "rw" else "read"
    filesystem.update({str(path): "deny" for path in sorted(denied)})
    env = {}
    for assignment in assignments:
        key, sep, value = assignment.partition("=")
        if (not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
                or secret_name(key) or SECRET_PREFIX.match(value.lstrip())
                or WATCH in value or "\x00" in value):
            raise DelegateError("--env に渡せない指定があります")
        env[key] = value
    config = {
        f"permissions.{PROFILE}.filesystem": toml_table(filesystem),
        "default_permissions": quote(PROFILE),
        "approval_policy": quote("never"),
        "shell_environment_policy.inherit": quote("core"),
    }
    if env:
        config["shell_environment_policy.set"] = toml_table(env)
    return [arg for key, value in config.items() for arg in ("-c", f"{key}={value}")]


def invoke(command, *, cwd=None, timeout=None, input_data=None, monitor=None, merge_output=False):
    env = clean_env()
    if Path(command[0]).name == "git":
        env = {key: value for key, value in env.items() if not key.startswith("GIT_")}
        env["GIT_TERMINAL_PROMPT"] = "0"
    with subprocess.Popen(
        command, cwd=cwd, env=env, stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT if merge_output else subprocess.PIPE,
        start_new_session=True,
    ) as child:
        stop = threading.Event()
        observer = None
        if monitor is not None:
            observer = threading.Thread(target=watch_processes, args=(child.pid, stop, monitor))
            observer.start()
        try:
            out, err = child.communicate(input_data, timeout=timeout)
            status = child.returncode
        except subprocess.TimeoutExpired:
            kill_group(child.pid)
            out, err = child.communicate()
            status = 124
        finally:
            kill_group(child.pid)
            stop.set()
            if observer:
                observer.join()
    return status, out, err


def kill_group(pid):
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pid, signal.SIGKILL)


def process_sample(pid, host_namespace):
    path = Path("/proc") / str(pid)
    namespace = os.readlink(path / "ns/mnt")
    environ = (path / "environ").read_bytes()
    names = re.findall(rb"(?:^|\x00)([^=\x00]+)=", environ)
    return {
        "comm": decode((path / "comm").read_bytes()).strip(),
        "cmdline": decode((path / "cmdline").read_bytes().replace(b"\0", b" ")).strip(),
        "sandboxed_mnt_ns": namespace != host_namespace,
        "secret_env_names": sum(secret_name(decode(name)) for name in names),
    }


def watch_processes(root, stop, samples):
    host_namespace = os.readlink("/proc/self/ns/mnt")
    seen = set()
    while True:
        children = {}
        for path in Path("/proc").iterdir():
            if path.name.isdecimal():
                try:
                    parent = int((path / "stat").read_text().rsplit(")", 1)[1].split()[1])
                    children.setdefault(parent, []).append(int(path.name))
                except (OSError, ValueError, IndexError):
                    continue
        pending = [root]
        while pending:
            pid = pending.pop()
            pending.extend(children.get(pid, ()))
            try:
                sample = process_sample(pid, host_namespace)
            except OSError:
                continue
            identity = (pid, *sample.values())
            if identity not in seen:
                seen.add(identity)
                samples.append({"pid": pid, **sample})
        if stop.wait(0.02):
            break


def repository(path):
    status, out, _ = invoke(["git", "-C", str(path), "rev-parse", "--show-toplevel"], timeout=15)
    if status:
        raise DelegateError("--repo に Git の作業ツリーを指定してください")
    return Path(os.fsdecode(out.rstrip(b"\n"))).resolve()


def reject_repo_job(job, repo):
    if overlap(job, repo):
        raise DelegateError("JOB はリポジトリの外に置いてください")
    for parent in job.parents:
        if os.path.lexists(parent / ".git"):
            raise DelegateError("JOB はリポジトリの外に置いてください")


def snapshot(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in dirs + sorted(files):
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                continue
            if stat.S_ISLNK(mode):
                digest = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
                kind = "symlink"
            elif stat.S_ISREG(mode):
                with path.open("rb") as source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
                kind = "file"
            else:
                raise DelegateError("作業ツリーに未対応のファイル形式があります")
            result[path.relative_to(root).as_posix()] = {
                "sha256": digest, "type": kind, "executable": bool(mode & stat.S_IXUSR),
            }
    return result


def changes(before, after):
    return {
        "added": sorted(after.keys() - before.keys()),
        "deleted": sorted(before.keys() - after.keys()),
        "modified": sorted(name for name in before.keys() & after.keys() if before[name] != after[name]),
    }


def extract_archive(data, dest):
    def archive_filter(member, target):
        if ".git" in Path(member.name).parts or member.islnk():
            raise DelegateError("アーカイブに許可されないパスまたはハードリンクがあります")
        return tarfile.data_filter(member, target)

    dest.mkdir()
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(dest, filter=archive_filter)


def prepare(args):
    repo = repository(Path(args.repo))
    supplied = Path(args.job)
    if os.path.lexists(supplied):
        raise DelegateError("指定の JOB は既にあります")
    job = supplied.resolve()
    reject_repo_job(Path(os.path.abspath(supplied)), repo)
    reject_repo_job(job, repo)
    if redact(str(repo)) != str(repo):
        raise DelegateError("リポジトリのパスに秘密らしい文字列があります")
    status, out, _ = invoke(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--end-of-options", args.ref + "^{commit}"],
        timeout=15,
    )
    if status:
        raise DelegateError("ref をコミットに解決できません")
    commit = decode(out).strip()
    status, archive, _ = invoke(["git", "-C", str(repo), "archive", commit], timeout=120)
    if status:
        raise DelegateError("git archive に失敗しました")
    job.mkdir(mode=0o700)
    try:
        for name in ("work", "base"):
            extract_archive(archive, job / name)
        (job / "runs").mkdir(mode=0o700)
        (job / "tests").mkdir(mode=0o700)
        (job / "watch").write_text(WATCH, encoding="utf-8")
        os.utime(job / "watch", ns=(WATCH_NS, WATCH_NS))
        files = snapshot(job / "work")
        safe_json(job / "files.json", files)
        write_json(job / "job.json", {
            "repo": str(repo), "ref": redact(args.ref), "commit": commit,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "file_count": len(files), "runs": 0,
        })
        (job / "report.md").write_text(f"# Codex JOB\n\n準備済み（{len(files)} ファイル）\n")
    except BaseException:
        shutil.rmtree(job)
        raise
    print(redact(str(job)))


# The probe runs under the same permissions as the model's shell commands.
PROBE = r"""
import errno, json, os, re, socket, sys
from pathlib import Path
job, repo, mode, port, name, pattern, allowed, auth_paths = json.loads(sys.argv[1])
job, repo = Path(job), Path(repo)

def denied(exc):
    return exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS, errno.ENOENT}

def visible(path):
    try:
        path.lstat()
        return True
    except OSError as exc:
        if denied(exc):
            return False
        raise

def writable(path, *, keep=False):
    try:
        with path.open("xb"):
            pass
    except OSError as exc:
        if denied(exc):
            return False
        raise
    if not keep:
        path.unlink()
    return True

work = job / "work"
with (work / name).open("rb") as source:
    readable = source.read() == b"probe"
write_path = work / (name + "-write")
work_writable = writable(write_path)
outside = [job / "watch", repo]
outside_hidden = all([not visible(path) for path in outside])
outside_readable = False
try:
    with (job / "watch").open("rb"):
        outside_readable = True
except OSError as exc:
    if not denied(exc):
        raise
outside_writable = any([writable(path / name, keep=True) for path in (job, repo)])
try:
    with socket.create_connection(("127.0.0.1", int(port)), timeout=1):
        offline = False
except OSError:
    offline = True
print(json.dumps({
    "work_readable": readable,
    "work_write_policy": work_writable == (mode == "rw"),
    "outside_hidden": outside_hidden and not outside_readable,
    "outside_writable": outside_writable,
    "auth_hidden": all(not visible(Path(path)) for path in auth_paths),
    "network_blocked": offline,
    "secret_env_names_zero": not any(
        key not in allowed and re.search(pattern, key, re.I) for key in os.environ
    ),
}))
"""
PROBE_KEYS = {
    "work_readable", "work_write_policy", "outside_hidden",
    "auth_hidden", "network_blocked", "secret_env_names_zero",
}


def sandbox_command(binary, config, command):
    return [str(binary), *config, "sandbox", "-P", PROFILE, "--", *command]


def watch_unchanged(path, before):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOATIME | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        if exc.errno in {errno.ENOENT, errno.EACCES, errno.EPERM, errno.ELOOP}:
            return False
        raise
    with os.fdopen(fd, "rb") as watch:
        after = os.fstat(watch.fileno())
        return (
            stat.S_ISREG(after.st_mode)
            and (after.st_mtime_ns, after.st_atime_ns) == (before.st_mtime_ns, before.st_atime_ns)
            and watch.read(len(WATCH) + 1) == WATCH.encode("ascii")
        )


def sandbox_check(binary, config, job, repo, mode):
    work = job / "work"
    watch = job / "watch"
    watch_before = watch.stat()
    name = ".delegate-probe-" + uuid.uuid4().hex
    host_write = False
    with (work / name).open("xb") as seed:
        seed.write(b"probe")
    try:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            arguments = json.dumps([
                str(job), str(repo), mode, listener.getsockname()[1], name,
                SECRET_NAME, sorted(ALLOWED_NAMES), [str(path / "auth.json") for path in DENIED],
            ])
            try:
                status, out, _ = invoke(
                    sandbox_command(binary, config, [sys.executable, "-I", "-c", PROBE, arguments]),
                    cwd=work, timeout=30,
                )
            finally:
                # A sandbox-local write disappears before the host can unlink it.
                for directory in (job, repo):
                    try:
                        (directory / name).unlink()
                    except FileNotFoundError:
                        continue
                    host_write = True
        try:
            result = json.loads(out)
        except (ValueError, UnicodeError):
            result = {}
        checks = {key: isinstance(result, dict) and result.get(key) is True for key in sorted(PROBE_KEYS)}
        watch_ok = watch_unchanged(watch, watch_before)
        checks["outside_read_only"] = not host_write and watch_ok
        checks["probe_outside_write_reported"] = (
            isinstance(result, dict) and type(result.get("outside_writable")) is bool
        )
        checks["probe_exit_zero"] = status == 0
        return {
            "ok": all(checks.values()),
            "checks": checks,
            "sandbox_only_writes": (
                checks["outside_read_only"] and checks["probe_outside_write_reported"]
                and result["outside_writable"]
            ),
        }
    finally:
        (work / name).unlink(missing_ok=True)
        (work / (name + "-write")).unlink(missing_ok=True)


def file_lines(root, name, entry):
    if entry is None:
        return []
    path = root / name
    if entry["type"] == "symlink":
        return ["symlink -> " + os.readlink(path) + "\n"]
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    try:
        return io.StringIO(data.decode("utf-8"), newline="").readlines()
    except UnicodeDecodeError:
        return None


def make_diff(base, work, selected=None):
    before, after = snapshot(base), snapshot(work)
    changed = changes(before, after)
    lines = []
    for name in sorted(sum(changed.values(), [])):
        if selected is not None and name != selected:
            continue
        old, new = before.get(name), after.get(name)
        left = quote("a/" + name) if old else "/dev/null"
        right = quote("b/" + name) if new else "/dev/null"
        if old is None or new is None or (old["type"], old["executable"]) != (new["type"], new["executable"]):
            lines.append(f"File metadata {left} -> {right}: {old and old['type']}, executable={old and old['executable']} -> {new and new['type']}, executable={new and new['executable']}\n")
        old_lines, new_lines = file_lines(base, name, old), file_lines(work, name, new)
        if old_lines is None or new_lines is None:
            lines.append(f"Binary files {left} and {right} differ\n")
            continue
        for line in difflib.unified_diff(old_lines, new_lines, left, right):
            lines.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    return "".join(lines)


def usage_from_events(log):
    usage = {}
    for line in log.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "turn.completed":
            counts = event.get("usage")
            if isinstance(counts, dict):
                for key, value in counts.items():
                    if re.fullmatch(r"[a-z_]+_tokens", key) and type(value) is int and value >= 0:
                        usage[key] = usage.get(key, 0) + value
    return usage


def safe_json(path, value):
    write_json(path, safe_value(value))


def safe_value(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [safe_value(item) for item in value]
    if isinstance(value, dict):
        return {redact(key): safe_value(item) for key, item in value.items()}
    return value


def store_text(path, value):
    write_private(path, redact(value).encode("utf-8"))


def sanitize_events(log):
    lines, scan = [], []
    for line in log.splitlines(keepends=True):
        try:
            event = json.loads(line)
        except ValueError:
            scan.append(line)
            lines.append(redact(line))
            continue
        scan.append(json.dumps(event, ensure_ascii=False))
        safe = safe_value(event)
        lines.append(line if safe == event else json.dumps(safe, ensure_ascii=True) + "\n")
    return "".join(lines), "\n".join(scan)


def count_markers(records):
    return {
        "watch_strings": sum(value.count(WATCH) for value in records),
        "secret_like_strings": sum(len(SECRET_VALUE.findall(value)) for value in records),
    }


def run(args, binary, job, meta, config):
    if meta["runs"] >= args.max_runs:
        raise DelegateError("実行回数の上限に達しました")
    work = job / "work"
    if args.max_runs < 1:
        raise DelegateError("--max-runs は1以上を指定してください")
    prompt = Path(args.prompt).read_bytes()
    if WATCH.encode() in prompt or SECRET_VALUE.search(decode(prompt)):
        raise DelegateError("プロンプトに見張り文字列または秘密らしい文字列があります")
    prompt = "GitHub を操作しないこと。作業は指定された作業フォルダ内に限定すること。\n\n".encode() + prompt
    before = snapshot(work)
    number = meta["runs"] + 1
    folder = job / "runs" / str(number)
    meta["runs"] = number
    metadata = job / "job.json.tmp"
    try:
        write_json(metadata, meta)
        metadata.replace(job / "job.json")
    finally:
        metadata.unlink(missing_ok=True)
    private_run_folder(job, folder)
    result = {"run": number, "ok": False, "exit_code": None, "usage": {}, "changes": changes(before, before)}
    try:
        result["sandbox_check"] = sandbox_check(
            binary, config, job, Path(meta["repo"]), args.mode,
        )
        if not result["sandbox_check"]["ok"]:
            result["unresolved"] = "sandbox-check に失敗したためモデル実行を中止"
            return 1

        samples = []
        # The CLI writes its raw answer to an owner-only regular file inside this run's folder.
        # It is read back without following links, redacted into answer.txt, and always removed.
        raw_answer = folder / ".answer.raw"
        os.close(os.open(raw_answer, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600))
        try:
            command = [
                str(binary), *config, "exec", "--ephemeral", "--ignore-user-config",
                "--skip-git-repo-check", "-C", str(work), "--json",
                "-o", str(raw_answer), "-m", args.model, "-",
            ]
            status, out, err = invoke(
                command, cwd=work, timeout=args.timeout, input_data=prompt,
                monitor=samples,
            )
            reply = decode(read_answer(raw_answer))
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(raw_answer)  # removes a substituted link itself, never its target
        log, stderr = decode(out), decode(err)
        proc = {"exit_code": status, "processes": samples}
        result.update(
            exit_code=status, usage=usage_from_events(log),
            max_secret_env_names=max((sample["secret_env_names"] for sample in samples), default=None),
            host_processes=sorted({sample["comm"] for sample in samples if not sample["sandboxed_mnt_ns"]}),
            watch_atime_unchanged=(job / "watch").stat().st_atime_ns == WATCH_NS,
        )
        safe_log, event_text = sanitize_events(log)
        store_text(folder / "exec.jsonl", safe_log)
        store_text(folder / "stderr", stderr)
        store_text(folder / "answer.txt", reply)
        safe_json(folder / "proc.json", proc)
        diff = make_diff(job / "base", work)
        store_text(folder / "changes.diff", diff)
        result["changes"] = changes(before, snapshot(work))
        result["diff_lines"] = len(diff.splitlines())
        result.update(count_markers([event_text, stderr, reply, json.dumps(proc, ensure_ascii=False), diff]))
        result["ok"] = (
            status == 0 and bool(reply.strip()) and result["watch_atime_unchanged"]
            and result["max_secret_env_names"] == 0 and not result["watch_strings"]
            and not result["secret_like_strings"] and (args.mode == "rw" or not any(result["changes"].values()))
        )
        if not result["ok"]:
            result["unresolved"] = "終了コード、回答、変更、安全確認の要レビュー項目あり"
        return 0 if result["ok"] else 1
    except (DelegateError, OSError, ValueError):
        result["unresolved"] = "実行または記録の途中でエラー"
        raise
    finally:
        marker_counts = result.get("watch_strings", "?"), result.get("secret_like_strings", "?")
        atime = result.get("watch_atime_unchanged", "?")
        max_secret = result.get("max_secret_env_names", "?")
        lines = run_summary(result) + [
            f"- atime 維持 {atime} / ダミー検出 {marker_counts[0]} / 秘密形式検出 {marker_counts[1]}",
            f"- プロセス内の秘密名の最大数 {max_secret}",
            "- 砂場外の観測プロセス " + compact(result.get("host_processes", [])),
        ]
        safe_json(folder / "report.json", result)
        store_text(folder / "report.md", "\n".join(lines[:30]) + "\n")
        print(redact(str(folder / "report.md")))


def compact(names, limit=300):
    text = ", ".join(json.dumps(name, ensure_ascii=False) for name in names) or "なし"
    return text if len(text) <= limit else text[:limit] + f"…（全{len(names)}件）"


def run_summary(result):
    verdict = "PASS" if result["ok"] else "FAIL"
    checks = result.get("sandbox_check", {})
    failed = [key for key, ok in checks.get("checks", {}).items() if not ok]
    safety = "PASS" if checks.get("ok") else ("FAIL " + ", ".join(failed) if failed else "未確認")
    observed = result.get("watch_atime_unchanged")
    if observed is not None:
        safety += f" / atime {observed}"
        safety += f" / 秘密環境変数の最大数 {result.get('max_secret_env_names', '?')}"
    usage = ", ".join(f"{key}={value}" for key, value in sorted(result["usage"].items()))
    lines = [
        f"## Run {result['run']} {verdict}（終了 {result['exit_code']}）",
        f"- 安全確認 {safety}",
        f"- 差分 {result.get('diff_lines', '未計測')} 行 / トークン {usage or '未計測'}",
    ]
    for key, label in (("added", "追加"), ("deleted", "削除"), ("modified", "変更")):
        lines.append(f"- {label} {compact(result['changes'][key])}")
    if result.get("unresolved"):
        lines.append("- 未解決 " + result["unresolved"])
    return lines


def test_command(args, binary, job, meta):
    name = args.name
    if redact(name) != name:
        raise DelegateError("--name に秘密らしい文字列があります")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", name):
        raise DelegateError("--name は英数字で始まる100文字以内の英数字・._- を指定してください")
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise DelegateError("-- の後にテストコマンドを指定してください")
    if args.sandbox:
        config = permissions(binary, job, Path(meta["repo"]), "rw", [], [])
        command = sandbox_command(binary, config, command)
    else:
        print("警告：レビュー済みのコードだけを動かすこと", file=sys.stderr)
    start = time.monotonic()
    status, log, _ = invoke(
        command, cwd=job / "work", timeout=args.timeout, merge_output=True,
    )
    log = decode(log)
    store_text(job / "tests" / (name + ".log"), log)
    summary = [line for line in log.splitlines() if re.match(r"^(?:ok|PASS|FAIL|Error)", line)][:20]
    safe_json(job / "tests" / (name + ".json"), {
        "name": name, "exit_code": status, "elapsed_seconds": round(time.monotonic() - start, 3),
        "sandbox": args.sandbox, "summary": summary,
    })
    return 0 if status == 0 else 1


def report(job, meta):
    runs = [read_json(path) for path in sorted(
        (job / "runs").glob("*/report.json"), key=lambda item: int(item.parent.name),
    )]
    tests = [read_json(path) for path in sorted((job / "tests").glob("*.json"))]
    blocked = sum(not item["ok"] for item in runs)
    incomplete = meta["runs"] - len(runs)
    failed = sum(item["exit_code"] != 0 for item in tests)
    changed = changes(snapshot(job / "base"), snapshot(job / "work"))
    diff_lines = len(make_diff(job / "base", job / "work").splitlines())
    total_usage = {}
    for item in runs:
        for key, count in item["usage"].items():
            total_usage[key] = total_usage.get(key, 0) + count
    usage = ", ".join(f"{key}={value}" for key, value in sorted(total_usage.items()))
    preflight = job / "sandbox-check.json"
    safety = "未実施"
    if preflight.exists():
        safety = "PASS" if read_json(preflight)["ok"] else "FAIL"
    run_safety = sum(
        item.get("sandbox_check", {}).get("ok") is True and item.get("watch_atime_unchanged") is True
        and item.get("max_secret_env_names") == 0 and not item.get("watch_strings")
        and not item.get("secret_like_strings")
        for item in runs
    )
    lines = [
        "# Codex JOB",
        f"- Run 成功 {len(runs) - blocked} / 失敗 {blocked} / 記録未完了 {incomplete}",
        f"- Test 合格 {len(tests) - failed} / 不合格 {failed}",
        f"- 安全確認 sandbox-check {safety} / Run 合格 {run_safety}/{len(runs)}",
        f"- 現在の差分 {diff_lines} 行 / トークン合計 {usage or '未計測'}",
        f"- 追加 {compact(changed['added'])}",
        f"- 削除 {compact(changed['deleted'])}",
        f"- 変更 {compact(changed['modified'])}",
    ]
    pending = []
    if not runs or incomplete or blocked:
        pending.append("Run の実施または失敗・未完了の確認")
    if not tests or failed:
        pending.append("テストの実施または失敗の確認")
    if safety == "FAIL" or run_safety < len(runs):
        pending.append("安全確認の失敗の調査")
    pending.append("Claude Code のレビューと最終判定")
    lines.append("- 未解決 " + "、".join(pending))
    for item in runs:
        checks = item.get("sandbox_check", {})
        verdict = "PASS" if item["ok"] else "FAIL"
        usage = ", ".join(f"{key}={value}" for key, value in sorted(item["usage"].items()))
        lines.append(
            f"- Run {item['run']} {verdict} / sandbox-check {'PASS' if checks.get('ok') else 'FAIL'}"
            f" / 差分 {item.get('diff_lines', '未計測')} 行 / {usage or 'トークン未計測'}"
        )
    for item in tests:
        verdict = "PASS" if item["exit_code"] == 0 else "FAIL"
        lines.append(f"- Test {item['name']} {verdict}（終了 {item['exit_code']}）")
    if len(lines) > 40:
        lines = lines[:39] + ["- 残りの結果は runs/ と tests/ の各記録を参照"]
    text = "\n".join(lines) + "\n"
    safe_json(job / "report.json", {
        "runs": runs, "tests": tests, "incomplete_runs": incomplete,
        "changes": changed, "diff_lines": diff_lines, "usage": total_usage,
        "sandbox_check": safety, "runs_passing_safety_checks": run_safety, "unresolved": pending,
    })
    store_text(job / "report.md", text)
    print(redact(text), end="")
    return 0


def is_three_r128(path):
    if path.name != "three.min.js" or not path.is_file():
        return False
    contents = path.read_bytes()
    if re.search(rb"""\bREVISION\s*=\s*["']128["']""", contents):
        return True
    exported = re.search(rb"\bREVISION\s*=\s*([a-zA-Z_$][\w$]*)\b", contents)
    return bool(exported and re.search(
        rb"""(?<![\w$])""" + re.escape(exported[1]) + rb"""\s*=\s*["']128["']""", contents,
    ))


def check(args):
    def query(command, cwd=None):
        try:
            status, out, _ = invoke(command, cwd=cwd, timeout=20)
        except FileNotFoundError:
            return False, ""
        return status == 0, decode(out).strip()

    def version_number(program):
        ok, version = query([program, "--version"])
        match = VERSION_NUMBER.search(version) if ok else None
        return match.group(1) if match else None

    rows = []
    machine, human = [], []
    binary = args.codex_bin
    version = version_number(binary)
    rows.append(("Codex", version or "未確認"))
    if version != DOC_VERSION:
        machine.append(f"npm install -g @openai/codex@{DOC_VERSION}")
    logged_in = False
    if version:
        status, out, err = invoke([binary, "login", "status"], timeout=20)
        logged_in = status == 0 and any(
            stream.strip() == b"Logged in using ChatGPT" for stream in (out, err)
        )
    rows.append(("ChatGPT 認証", "Logged in using ChatGPT" if logged_in else "未確認"))
    if not logged_in:
        human.append("codex login --device-auth でデバイス認証")
    for program in ("node", "python3", "git"):
        version = version_number(program)
        rows.append((program, version or "未確認"))
        if not version:
            human.append(f"環境の管理者に {program} の準備を依頼")
    playwright, _ = query([
        "node", "-e", "require.resolve('playwright', {paths: ['/opt/node-tools', process.cwd()]})",
    ])
    rows.append(("Playwright", "あり" if playwright else "なし"))
    browsers = Path("/opt/pw-browsers").is_dir()
    rows.append(("/opt/pw-browsers", "あり" if browsers else "なし"))
    if not playwright or not browsers:
        human.append("環境の Playwright（/opt/node-tools・/opt/pw-browsers）を用意してもらう（入れ直さない）")
    three = args.three or os.environ.get("THREE_JS")
    r128 = bool(three and is_three_r128(Path(three)))
    rows.append(("three.js r128", "あり" if r128 else "未確認"))
    if not r128:
        machine.append("npm pack three@0.128.0 で取得し THREE_JS を設定")
    if args.branch:
        repo = repository(Path(args.repo))
        remote, _ = query(["git", "ls-remote", "--exit-code", "--heads", "origin", "refs/heads/" + args.branch], repo)
        rows.append(("git ls-remote (origin)", "利用可" if remote else "未確認"))
        if not remote:
            human.append("origin・アクセス権・ブランチ名を確認")
    print("| 項目 | 結果 |\n| --- | --- |")
    for label, value in rows:
        print(f"| {label} | {value} |")
    for title, items in (("人が行うこと", human), ("コマンドで入れられること", machine)):
        print(f"\n{title}")
        for item in items or ["なし"]:
            print("- " + item)
    return 1 if human or machine else 0


def positive_seconds(value):
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("正の秒数を指定してください")
    return seconds


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-bin", default="codex")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("check", "prepare", "sandbox-check", "run", "test", "report", "diff"):
        command = sub.add_parser(action)
        command.add_argument("--codex-bin", default=argparse.SUPPRESS)
        if action != "check":
            command.add_argument("--job", required=True)
        if action in ("check", "prepare"):
            command.add_argument("--repo", required=action == "prepare", default=".")
        if action == "check":
            command.add_argument("--branch")
            command.add_argument("--three")
        if action == "prepare":
            command.add_argument("--ref", required=True)
        if action in ("sandbox-check", "run"):
            command.add_argument("--mode", choices=("ro", "rw"), required=action == "run", default="ro")
            command.add_argument("--read", action="append", default=[])
            command.add_argument("--env", action="append", default=[])
        if action in ("run", "test"):
            command.add_argument("--timeout", type=positive_seconds, default=600)
        if action == "run":
            command.add_argument("--model", default="gpt-6.2-sol")
            command.add_argument("--prompt", required=True)
            command.add_argument("--max-runs", type=int, default=4)
        if action == "test":
            command.add_argument("--name", required=True)
            command.add_argument("--sandbox", action="store_true")
            command.add_argument("command", nargs=argparse.REMAINDER)
        if action == "diff":
            command.add_argument("--file")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.action == "check":
            return check(args)
        if args.action == "prepare":
            return prepare(args) or 0
        job = Path(args.job).resolve(strict=True)
        # Lock the directory inode, so updating job.json does not release the lock.
        descriptor = os.open(job, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            return dispatch(args, job)
        finally:
            os.close(descriptor)
    except (DelegateError, OSError, ValueError, tarfile.TarError) as exc:
        print(redact(str(exc)), file=sys.stderr)
        return 1


def dispatch(args, job):
    meta = read_json(job / "job.json")
    repo = Path(meta["repo"]).resolve()
    reject_repo_job(job, repo)
    for name in ("work", "base", "runs", "tests"):
        if (job / name).is_symlink() or not (job / name).is_dir():
            raise DelegateError("JOB のディレクトリ構成が不正です")
    if args.action == "report":
        return report(job, meta)
    if args.action == "diff":
        selected = args.file
        if selected is not None:
            relative = Path(selected)
            if relative.is_absolute() or ".." in relative.parts:
                raise DelegateError("--file は JOB/work 内の相対パスを指定してください")
            selected = relative.as_posix()
        print(redact(make_diff(job / "base", job / "work", selected)), end="")
        return 0
    binary = None
    if args.action in ("sandbox-check", "run") or args.sandbox:
        executable = shutil.which(args.codex_bin)
        if not executable:
            raise DelegateError("Codex 実行ファイルが見つかりません")
        binary = Path(executable).resolve()
    if args.action == "test":
        return test_command(args, binary, job, meta)
    config = permissions(binary, job, repo, args.mode, args.read, args.env)
    if args.action == "run":
        return run(args, binary, job, meta, config)
    result = sandbox_check(binary, config, job, repo, args.mode)
    write_json(job / "sandbox-check.json", result)
    lines = ["# Sandbox check", *(f"- {key} {'PASS' if ok else 'FAIL'}" for key, ok in result["checks"].items())]
    (job / "sandbox-check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
