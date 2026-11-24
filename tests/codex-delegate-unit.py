#!/usr/bin/env python3
"""Unit tests with a fake CLI, an in-memory archive, and no network."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import tomllib
import unittest
from unittest.mock import patch


sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1] / "tools/codex-delegate.py"
SPEC = importlib.util.spec_from_file_location("codex_delegate", SOURCE)
delegate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delegate)

FAKE_CODEX = r"""#!/bin/sh
set -eu
while [ "${1:-}" = "-c" ]; do shift 2; done
case "$1" in
    --version) printf 'codex-cli %s\n' "${FAKE_CODEX_VERSION:-0.172.0}" ;;
    login)
        [ "$2" = "status" ]
        printf '%s\n' "${FAKE_LOGIN:-Logged in using ChatGPT}" >&2
        ;;
    sandbox)
        shift
        [ "$1" = "-P" ] && [ "$2" = "delegate" ] && [ "$3" = "--" ]
        shift 3
        if [ "$#" -eq 5 ] && [ "$3" = "-c" ] && [ "$2" = "-I" ]; then
            result=true
            if [ "${FAKE_CASE:-}" = "blocked" ]; then result=false; fi
            outside=false
            case "${FAKE_CASE:-}" in
                sandbox-only) outside=true ;;
                host-job|host-repo|watch-content|watch-mtime|watch-atime)
                    "$1" -I -c '
import json, os, sys
from pathlib import Path
job, repo, _, _, name, *_ = json.loads(sys.argv[1])
case = sys.argv[2]
watch = Path(job) / "watch"
before = watch.stat()
if case == "host-job":
    (Path(job) / name).touch()
elif case == "host-repo":
    (Path(repo) / name).touch()
elif case == "watch-content":
    watch.write_bytes(b"changed")
    os.utime(watch, ns=(before.st_atime_ns, before.st_mtime_ns))
elif case == "watch-mtime":
    os.utime(watch, ns=(before.st_atime_ns, before.st_mtime_ns + 10**9))
elif case == "watch-atime":
    os.utime(watch, ns=(before.st_atime_ns + 10**9, before.st_mtime_ns))
' "$5" "$FAKE_CASE"
                    ;;
            esac
            printf '{"work_readable":true,"work_write_policy":true,"outside_hidden":true,"outside_writable":%s,"auth_hidden":true,"network_blocked":%s,"secret_env_names_zero":true}\n' "$outside" "$result"
        else
            exec "$@"
        fi
        ;;
    exec)
        shift
        [ "$1" = "--ephemeral" ] && [ "$2" = "--ignore-user-config" ]
        [ "$3" = "--skip-git-repo-check" ] && [ "$4" = "-C" ]
        [ "$5" = "$PWD" ] && [ "$6" = "--json" ] && [ "$7" = "-o" ]
        [ "$9" = "-m" ] && [ "${10}" = "gpt-6.2-sol" ] && [ "${11}" = "-" ]
        answer="$8"
        input=$(cat)
        [ -z "${DEMO_TOKEN+x}" ] && [ "${AWS_CA_BUNDLE:-}" = "/cert.pem" ]
        [ -f "$answer" ] && [ ! -L "$answer" ]
        sleep 0.15
        case "${FAKE_CASE:-}" in
            stdin)
                printf 'mode=%s dir=%s stdin=%s\n' "$(stat -c %a "$answer")" \
                    "$(stat -c %a "$(dirname "$answer")")" \
                    "$(printf '%s\n' "$input" | grep -c 'STDIN-MARKER-OK')" > "$answer"
                printf '%s\n' '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}'
                exit 0
                ;;
            symlink)
                rm -f "$answer"
                ln -s "$FAKE_TARGET" "$answer"
                printf '%s\n' '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}'
                exit 0
                ;;
            fail-after)
                printf '%s\n' 'partial answer ghp_demo' > "$answer"
                exit 3
                ;;
            changes)
                printf 'new\n' > added.txt
                rm deleted.txt
                printf 'changed\n' > modified.txt
                ;;
            leak)
                printf '%s\n' 'CODEX_DELEGATE_WATCH_2020' > "$answer"
                printf '%s\n' 'sk-fake-secret' >&2
                ;;
        esac
        if [ "${FAKE_CASE:-}" != leak ]; then printf '%s\n' Done > "$answer"; fi
        printf '%s\n' '{"type":"turn.completed","usage":{"input_tokens":31,"cached_input_tokens":4,"output_tokens":7}}'
        ;;
    *) exit 99 ;;
esac
"""


class NoNetworkListener:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def bind(self, _):
        pass

    def listen(self):
        pass

    def getsockname(self):
        return ("127.0.0.1", 12345)


class DelegateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.repo = root / "source"
        self.repo.mkdir()
        self.job = root / "job"
        self.auth = root / "private-home" / ".codex"
        denial = patch.object(delegate, "DENIED", {self.auth})
        denial.start()
        self.addCleanup(denial.stop)
        self.bin = root / "bin"
        self.bin.mkdir()
        self.codex = self.bin / "fake-codex"
        self.codex.write_text(FAKE_CODEX)
        self.codex.chmod(0o700)
        self.prompt = root / "prompt.txt"
        self.prompt.write_text("作業してください\n")
        self.root = root

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = delegate.main(["--codex-bin", str(self.codex), *map(str, args)])
        return status, stdout.getvalue(), stderr.getvalue()

    def prepare(self, job=None):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w") as stream:
            for name in ("modified.txt", "deleted.txt"):
                data = b"before\n"
                item = tarfile.TarInfo(name)
                item.size = len(data)
                item.mode = 0o644
                stream.addfile(item, io.BytesIO(data))
        responses = [
            (0, os.fsencode(self.repo) + b"\n", b""),
            (0, b"a" * 40 + b"\n", b""),
            (0, archive.getvalue(), b""),
        ]
        with patch.object(delegate, "invoke", side_effect=responses) as git:
            result = self.cli("prepare", "--repo", self.repo, "--ref", "topic", "--job", job or self.job)
        self.assertEqual(git.call_args_list[0].args[0][3:], ["rev-parse", "--show-toplevel"])
        if result[0] == 0:
            self.assertEqual(git.call_count, 3)
            self.assertEqual(git.call_args.args[0][3:], ["archive", "a" * 40])
        return result

    def run_fake(self, situation="", limit=2):
        with patch.dict(os.environ, {
            "DEMO_TOKEN": "a-value-without-a-key-prefix", "AWS_CA_BUNDLE": "/cert.pem",
            "FAKE_CASE": situation,
        }), patch.object(delegate.socket, "socket", NoNetworkListener):
            return self.cli("run", "--job", self.job, "--mode", "rw",
                            "--prompt", self.prompt, "--max-runs", limit)

    def result(self, number=1):
        return json.loads((self.job / "runs" / str(number) / "report.json").read_text())

    def test_permissions_realpath_and_access_mode(self):
        external = self.root / "external"
        external.mkdir()
        link = self.root / "link"
        link.symlink_to(external, target_is_directory=True)
        for mode, access in (("ro", "read"), ("rw", "write")):
            args = delegate.permissions(self.codex, self.job, self.repo, mode, [link], ["NODE_PATH=a=b"])
            rendered = tomllib.loads("\n".join(args[1::2]))
            fs = rendered["permissions"]["delegate"]["filesystem"]
            self.assertEqual(fs[str(self.job / "work")], access)
            self.assertEqual(fs[str(self.auth)], "deny")
            self.assertEqual(fs[":minimal"], "read")
            self.assertEqual(fs[str(external)], "read")
            self.assertNotIn(str(link), fs)
            self.assertEqual(rendered["shell_environment_policy"]["set"]["NODE_PATH"], "a=b")
            self.assertEqual(rendered["default_permissions"], "delegate")
            self.assertEqual(rendered["approval_policy"], "never")
            self.assertEqual(rendered["shell_environment_policy"]["inherit"], "core")

    def test_protected_reads(self):
        alias = self.root / "alias"
        alias.symlink_to(self.auth)
        for target in (Path("/"), self.auth, self.auth.parent, self.auth / "auth.json", alias, self.repo, self.job):
            with self.subTest(target=target), self.assertRaises(delegate.DelegateError):
                delegate.permissions(self.codex, self.job, self.repo, "rw", [target], [])

    def test_npm_vendor_resolution(self):
        package = self.root / "node_modules/@openai/codex"
        vendor = package / "node_modules/@openai/codex-linux-x64/vendor"
        vendor.mkdir(parents=True)
        self.assertEqual(delegate.codex_vendor(package / "bin/codex.js"), vendor)

    def test_environment_filters_by_name_without_reading_secret(self):
        class NamesOnlyForSecrets(dict):
            def __getitem__(self, key):
                if delegate.secret_name(key):
                    raise AssertionError("secret value was accessed")
                return super().__getitem__(key)

        allowed = dict.fromkeys(delegate.ALLOWED_NAMES | {"NODE_PATH"}, "allowed")
        with patch.object(delegate.os, "environ", NamesOnlyForSecrets(
            allowed, MY_CLOUDSDK_AUTH="hidden", GiThUb_ToKeN="hidden", AWS_REGION="hidden"
        )):
            self.assertEqual(delegate.clean_env(), allowed)

    def test_rejects_secret_assignments(self):
        for assignment in ("API_KEY=mock", "V=sk-", "V=ghp_demo", "V=github_pat_mock",
                           "V=eyJmock", "V=AKIAmock", "INVALID NAME=x", "NOVALUE"):
            with self.subTest(assignment=assignment), self.assertRaises(delegate.DelegateError):
                delegate.permissions(self.codex, self.job, self.repo, "ro", [], [assignment])

    def test_prepare_rejects_repository_and_existing_job(self):
        self.assertEqual(self.prepare(self.repo / "nested")[0], 1)
        self.job.mkdir()
        marker = self.job / "keep"
        marker.write_text("keep")
        self.assertEqual(self.prepare()[0], 1)
        self.assertEqual(marker.read_text(), "keep")

    def test_prepare_exports_identical_snapshots(self):
        self.assertEqual(self.prepare()[0], 0)
        meta = delegate.read_json(self.job / "job.json")
        self.assertEqual((meta["ref"], meta["file_count"], meta["runs"]), ("topic", 2, 0))
        files = delegate.read_json(self.job / "files.json")
        self.assertEqual(files, delegate.snapshot(self.job / "base"))
        self.assertEqual(files, delegate.snapshot(self.job / "work"))
        self.assertEqual((self.job / "watch").stat().st_atime_ns, delegate.WATCH_NS)

    def test_run_changes_usage_and_limit(self):
        self.assertEqual(self.prepare()[0], 0)
        self.assertEqual(self.run_fake("changes", limit=1)[0], 0)
        report = self.result()
        self.assertEqual(report["changes"], {
            "added": ["added.txt"], "deleted": ["deleted.txt"], "modified": ["modified.txt"],
        })
        self.assertEqual(report["usage"]["input_tokens"], 31)
        self.assertEqual(report["max_secret_env_names"], 0)
        self.assertTrue(report["watch_atime_unchanged"])
        self.assertEqual(self.run_fake(limit=1)[0], 1)
        self.assertEqual(delegate.read_json(self.job / "job.json")["runs"], 1)
        run = self.job / "runs/1"
        self.assertLessEqual(len((run / "report.md").read_text().splitlines()), 30)
        self.assertEqual((run / "answer.txt").read_text().strip(), "Done")
        for path in run.iterdir():
            self.assertNotIn("a-value-without-a-key-prefix", path.read_text())
        status, diff, _ = self.cli("diff", "--job", self.job, "--file", "modified.txt")
        self.assertEqual(status, 0)
        self.assertIn("-before\n+changed\n", diff)
        self.assertNotIn("added.txt", diff)

    def test_preflight_blocks_exec_and_consumes_attempt(self):
        self.assertEqual(self.prepare()[0], 0)
        self.assertEqual(self.run_fake("blocked")[0], 1)
        self.assertFalse(self.result()["sandbox_check"]["checks"]["network_blocked"])
        self.assertFalse((self.job / "runs/1/exec.jsonl").exists())
        self.assertEqual(delegate.read_json(self.job / "job.json")["runs"], 1)
        self.assertIn("FAIL", self.cli("report", "--job", self.job)[1])

    def test_preflight_allows_sandbox_only_writes(self):
        self.assertEqual(self.prepare()[0], 0)
        self.assertEqual(self.run_fake("sandbox-only")[0], 0)
        result = self.result()["sandbox_check"]
        self.assertTrue(result["checks"]["outside_read_only"])
        self.assertTrue(result["sandbox_only_writes"])
        self.assertEqual((self.job / "watch").stat().st_atime_ns, delegate.WATCH_NS)

    def test_sandbox_check_blocks_host_writes_and_watch_changes(self):
        self.assertEqual(self.prepare()[0], 0)
        for situation in ("host-job", "host-repo", "watch-content", "watch-mtime", "watch-atime"):
            with self.subTest(situation=situation):
                watch = self.job / "watch"
                watch.write_text(delegate.WATCH, encoding="ascii")
                os.utime(watch, ns=(delegate.WATCH_NS, delegate.WATCH_NS))
                with patch.dict(os.environ, {"FAKE_CASE": situation}), patch.object(
                    delegate.socket, "socket", NoNetworkListener,
                ):
                    status, _, error = self.cli("sandbox-check", "--job", self.job)
                self.assertEqual(status, 1, error)
                result = delegate.read_json(self.job / "sandbox-check.json")
                self.assertFalse(result["checks"]["outside_read_only"])
                self.assertFalse(result["sandbox_only_writes"])
                for folder in (self.job, self.repo, self.job / "work"):
                    self.assertEqual(list(folder.glob(".delegate-probe-*")), [])

    def test_detects_and_redacts_leaks(self):
        self.assertEqual(self.prepare()[0], 0)
        self.assertEqual(self.run_fake("leak")[0], 1)
        self.assertEqual(self.result()["watch_strings"], 1)
        self.assertEqual(self.result()["secret_like_strings"], 1)
        self.assertFalse(self.result()["ok"])
        for path in (self.job / "runs/1").iterdir():
            self.assertNotIn(delegate.WATCH, path.read_text())
            self.assertNotIn("sk-fake-secret", path.read_text())

    def test_answer_goes_through_private_regular_file_and_stdin(self):
        self.assertEqual(self.prepare()[0], 0)
        self.prompt.write_text("STDIN-MARKER-OK を読んでください\n")
        self.assertEqual(self.run_fake("stdin")[0], 0)
        run = self.job / "runs/1"
        self.assertEqual((run / "answer.txt").read_text().strip(), "mode=600 dir=700 stdin=1")
        self.assertFalse(os.path.lexists(run / ".answer.raw"))
        self.assertEqual(os.stat(self.job / "runs").st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(run).st_mode & 0o777, 0o700)
        for path in run.iterdir():
            with self.subTest(path=path.name):
                self.assertEqual(os.lstat(path).st_mode & 0o777, 0o600)

    def test_answer_symlink_substitution_is_rejected(self):
        self.assertEqual(self.prepare()[0], 0)
        target = self.root / "outside-secret.txt"
        target.write_text("TARGET-CONTENT-7781\n")
        with patch.dict(os.environ, {"FAKE_TARGET": str(target)}):
            status, _, error = self.run_fake("symlink")
        self.assertEqual(status, 1)
        self.assertIn("シンボリックリンク", error)
        run = self.job / "runs/1"
        self.assertFalse(os.path.lexists(run / ".answer.raw"))
        self.assertEqual(target.read_text(), "TARGET-CONTENT-7781\n")
        for path in run.iterdir():
            self.assertNotIn("TARGET-CONTENT-7781", path.read_text())
        self.assertFalse(self.result()["ok"])

    def test_raw_answer_removed_and_redacted_on_failure(self):
        self.assertEqual(self.prepare()[0], 0)
        self.assertEqual(self.run_fake("fail-after")[0], 1)
        run = self.job / "runs/1"
        self.assertFalse(os.path.lexists(run / ".answer.raw"))
        self.assertNotIn("ghp_demo", (run / "answer.txt").read_text())
        report = self.result()
        self.assertEqual(report["exit_code"], 3)
        self.assertEqual(report["secret_like_strings"], 1)
        self.assertFalse(report["ok"])

    def test_escaped_json_markers_are_redacted(self):
        raw = r'{"type":"message","content":"\u0073k-test CODEX_DELEGATE_WATCH_2020"}' + "\n"
        safe_log, scan = delegate.sanitize_events(raw)
        self.assertEqual(json.loads(safe_log)["content"], "[redacted] [watch redacted]")
        self.assertEqual(delegate.count_markers([scan]), {"watch_strings": 1, "secret_like_strings": 1})

    def test_three_revision_assigned_through_minified_constant(self):
        path = self.root / "three.min.js"
        path.write_text('const e="128",n=9;t.REVISION=e,t.VERSION=n;')
        self.assertTrue(delegate.is_three_r128(path))
        path.write_text('const e="129";t.REVISION=e;')
        self.assertFalse(delegate.is_three_r128(path))

    def test_sandbox_test_and_summary(self):
        self.assertEqual(self.prepare()[0], 0)
        command = [sys.executable, "-I", "-c", "import os; print('noise'); print('PASS'); assert 'DEMO_TOKEN' not in os.environ"]
        with patch.dict(os.environ, {"DEMO_TOKEN": "hidden"}):
            status, _, stderr = self.cli("test", "--job", self.job, "--name", "demo", "--sandbox", "--", *command)
            self.assertEqual((status, stderr), (0, ""))
            summary = delegate.read_json(self.job / "tests/demo.json")
            self.assertEqual(summary["summary"], ["PASS"])
            self.assertEqual((self.job / "tests/demo.log").read_text(), "noise\nPASS\n")
            status, _, stderr = self.cli("test", "--job", self.job, "--name", "host", "--", *command)
            self.assertEqual(status, 0)
            self.assertIn("レビュー済み", stderr)

    def test_report_line_limit(self):
        self.assertEqual(self.prepare()[0], 0)
        for number in range(50):
            delegate.write_json(self.job / "tests" / f"{number:02}.json", {"name": str(number), "exit_code": 0})
        status, output, _ = self.cli("report", "--job", self.job)
        self.assertEqual(status, 0)
        self.assertEqual(len(output.splitlines()), 40)
        self.assertIn("Test 合格 50", output)
        self.assertEqual((self.job / "report.md").read_text(), output)

    def test_check_only_discloses_expected_login_status(self):
        # Fake even the version probes so the test never invokes Git.
        invoke = delegate.invoke
        def local_cli(command, **kwargs):
            if command[0] == str(self.codex):
                return invoke(command, **kwargs)
            return 0, b"1.2.3\n", b""
        with patch.object(delegate, "invoke", side_effect=local_cli):
            self.assertIn("Logged in using ChatGPT", self.cli("check")[1])
            with patch.dict(os.environ, {"FAKE_LOGIN": "private account detail"}):
                _, output, error = self.cli("check")
            self.assertNotIn("private account detail", output + error)
            self.assertIn("codex login --device-auth", output)

    def test_check_parses_prefixed_and_plain_versions(self):
        invoke = delegate.invoke
        versions = {"node": b"v22.23.5", "python3": b"Python 3.12.0", "git": b"git version v2.51.1"}

        def local_cli(command, **kwargs):
            if command[0] == str(self.codex):
                return invoke(command, **kwargs)
            if command[1:] == ["--version"]:
                return 0, versions[command[0]], b""
            return 1, b"", b""

        with patch.object(delegate, "invoke", side_effect=local_cli), patch.dict(
            os.environ, {"FAKE_CODEX_VERSION": "v0.172.0"},
        ):
            _, output, _ = self.cli("check")
        for program, version in (("Codex", "0.172.0"), ("node", "22.23.5"),
                                 ("python3", "3.12.0"), ("git", "2.51.1")):
            self.assertIn(f"| {program} | {version} |", output)

    def test_check_uses_node_playwright_and_requests_environment_setup(self):
        invoke = delegate.invoke
        path_is_dir = Path.is_dir

        for playwright, browsers in ((True, True), (False, True), (True, False), (False, False)):
            with self.subTest(playwright=playwright, browsers=browsers):
                def local_cli(command, **kwargs):
                    if command[0] == str(self.codex):
                        return invoke(command, **kwargs)
                    if command[1:] == ["--version"]:
                        return 0, b"1.2.3", b""
                    self.assertEqual(command[:2], ["node", "-e"])
                    self.assertIn("require.resolve('playwright'", command[2])
                    self.assertIn("/opt/node-tools", command[2])
                    return int(not playwright), b"", b""

                def is_dir(path):
                    return browsers if path == Path("/opt/pw-browsers") else path_is_dir(path)

                with patch.object(delegate, "invoke", side_effect=local_cli) as mocked, patch.object(
                    Path, "is_dir", is_dir,
                ):
                    _, output, _ = self.cli("check")
                self.assertTrue(any(call.args[0][:2] == ["node", "-e"] for call in mocked.call_args_list))
                self.assertIn(f"| Playwright | {'あり' if playwright else 'なし'} |", output)
                self.assertIn(f"| /opt/pw-browsers | {'あり' if browsers else 'なし'} |", output)
                human, machine = output.split("人が行うこと\n")[1].split("コマンドで入れられること\n")
                setup = "環境の Playwright（/opt/node-tools・/opt/pw-browsers）を用意してもらう（入れ直さない）"
                self.assertEqual(setup in human, not (playwright and browsers))
                self.assertNotIn("playwright", machine.lower())


if __name__ == "__main__":
    unittest.main()
