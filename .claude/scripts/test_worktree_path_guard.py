"""Replay hook payloads without creating worktrees or changing repositories."""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


GUARD = pathlib.Path(__file__).with_name("worktree-path-guard.py")


class HookPayloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="hook-guard-")
        self.addCleanup(self.directory.cleanup)
        self.repo = pathlib.Path(self.directory.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
        self.allowed = self.repo / "worktrees" / self.repo.name / "probe"

    def run_hook(self, payload):
        result = subprocess.run(
            [sys.executable, str(GUARD)],
            input=json.dumps(payload), text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout) if result.stdout else None

    def test_unrelated_serialized_command_does_not_crash(self):
        self.assertIsNone(self.run_hook({"tool_input": json.dumps({"cmd": "pwd"})}))

    def test_allowed_and_denied_paths_for_each_input_format(self):
        for key in ("command", "cmd"):
            for serialized in (False, True):
                for allowed in (False, True):
                    target = self.allowed if allowed else ".claude/worktrees/probe"
                    tool_input = {key: f"git worktree add {target}"}
                    if serialized:
                        tool_input = json.dumps(tool_input)
                    with self.subTest(key=key, serialized=serialized, allowed=allowed):
                        output = self.run_hook({"cwd": str(self.repo), "tool_input": tool_input})
                        if allowed:
                            self.assertIsNone(output)
                        else:
                            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_plain_shell_string_is_checked(self):
        output = self.run_hook({"cwd": str(self.repo), "tool_input": "git worktree add .claude/worktrees/probe"})
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_unsupported_payloads_are_ignored(self):
        for payload in (None, [], 42, "text", {}, {"tool_input": []},
                        {"tool_input": 42}, {"tool_input": "[]"},
                        {"tool_input": {"command": 42}},
                        {"tool_input": {"command": "git worktree add x"}, "cwd": []}):
            with self.subTest(payload=payload):
                self.assertIsNone(self.run_hook(payload))

    def test_existing_variable_expansion_is_preserved(self):
        self.assertIsNone(self.run_hook({
            "cwd": str(self.repo),
            "tool_input": {"command": f"D={self.allowed.parent}; git worktree add $D/probe"},
        }))

    def test_move_target_is_checked(self):
        for target, denied in ((self.allowed, False), (self.repo / "outside", True)):
            with self.subTest(target=target):
                output = self.run_hook({
                    "cwd": str(self.repo),
                    "tool_input": json.dumps({"command": f"git worktree move old {target}"}),
                })
                self.assertEqual(output is not None, denied)

    def test_quoted_text_is_not_split_into_commands(self):
        for command in (
            'git commit -q -m "feat: 설명\n\ngit worktree add 로 만든 워크트리는 숨는다"',
            "git commit -m 'a; git worktree add outside'",
            'echo "x | git worktree add outside"',
        ):
            with self.subTest(command=command):
                self.assertIsNone(self.run_hook({"cwd": str(self.repo), "tool_input": {"command": command}}))

    def test_unquoted_separators_still_split(self):
        for command in ("pwd\ngit worktree add outside", "pwd && git worktree add outside",
                        'echo "a;b"; git worktree add outside'):
            with self.subTest(command=command):
                output = self.run_hook({"cwd": str(self.repo), "tool_input": {"command": command}})
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_malformed_json_is_ignored(self):
        result = subprocess.run([sys.executable, str(GUARD)], input="{", text=True, capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_claude_and_codex_contract_payloads(self):
        common = {
            "session_id": "test-session", "transcript_path": "/tmp/test-transcript",
            "cwd": str(self.repo), "hook_event_name": "PreToolUse",
            "tool_name": "Bash", "tool_use_id": "test-call",
        }
        for runtime_fields in ({"permission_mode": "default"}, {"turn_id": "test-turn"}):
            for target, denied in ((self.allowed, False), (self.repo / "outside", True)):
                with self.subTest(runtime_fields=runtime_fields, denied=denied):
                    output = self.run_hook({
                        **common, **runtime_fields,
                        "tool_input": {"command": f"git worktree add {target}", "description": "test"},
                    })
                    if denied:
                        self.assertEqual(set(output), {"hookSpecificOutput"})
                        specific = output["hookSpecificOutput"]
                        self.assertEqual(set(specific), {"hookEventName", "permissionDecision", "permissionDecisionReason"})
                        self.assertEqual(specific["hookEventName"], "PreToolUse")
                        self.assertEqual(specific["permissionDecision"], "deny")
                        self.assertIsInstance(specific["permissionDecisionReason"], str)
                    else:
                        self.assertIsNone(output)

    def test_other_tools_and_events_do_not_interpret_content_as_shell(self):
        for fields in ({"tool_name": "apply_patch"}, {"tool_name": "Write"},
                       {"hook_event_name": "PostToolUse"}):
            with self.subTest(fields=fields):
                self.assertIsNone(self.run_hook({
                    "cwd": str(self.repo), **fields,
                    "tool_input": {"command": "git worktree add outside"},
                }))


if __name__ == "__main__":
    unittest.main()
