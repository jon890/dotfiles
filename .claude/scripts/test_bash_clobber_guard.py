"""bash-clobber-guard.py 에 hook 입력을 넣어 바뀐 명령을 확인한다."""

import json
import pathlib
import subprocess
import sys
import unittest


GUARD = pathlib.Path(__file__).with_name("bash-clobber-guard.py")
CLOBBER = "set +o noclobber; "
EQUALS = "setopt no_equals; "


def run_hook(command):
    payload = {"tool_name": "Bash", "tool_input": {"command": command, "description": "x"}}
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload), text=True, capture_output=True, check=False,
    )
    if result.returncode != 0 or result.stderr:
        raise AssertionError(result.stderr)
    if not result.stdout:
        return None
    output = json.loads(result.stdout)["hookSpecificOutput"]["updatedInput"]
    if output["description"] != "x":
        raise AssertionError("다른 입력 칸이 바뀌었다")
    return output["command"]


class RedirectTests(unittest.TestCase):
    def test_file_redirect_gets_prefix(self):
        self.assertEqual(run_hook("echo x > out.txt"), CLOBBER + "echo x > out.txt")

    def test_append_redirect_gets_prefix(self):
        self.assertEqual(run_hook("echo x >> out.txt 2>&1"), CLOBBER + "echo x >> out.txt 2>&1")

    def test_fd_duplication_only_is_left_alone(self):
        self.assertIsNone(run_hook("claude plugin list 2>&1 | head -5"))
        self.assertIsNone(run_hook("echo warn >&2; ls 2>&-"))

    def test_dev_null_only_is_left_alone(self):
        self.assertIsNone(run_hook("command -v orch >/dev/null || echo none"))
        self.assertIsNone(run_hook("ls nope 2>/dev/null; ls &>/dev/null; ls >> /dev/null"))

    def test_quoted_and_heredoc_brackets_are_ignored(self):
        self.assertIsNone(run_hook("grep -n '> 인용' README.md"))
        self.assertIsNone(run_hook("cat <<'EOF'\n> 인용문\nEOF"))

    def test_existing_prefix_is_not_repeated(self):
        self.assertIsNone(run_hook(CLOBBER + "echo x > out.txt"))

    def test_arrows_are_not_redirects(self):
        self.assertIsNone(run_hook("echo a=>b c->d"))


class EqualsWordTests(unittest.TestCase):
    def test_bare_equals_word_gets_prefix(self):
        self.assertEqual(run_hook("echo ======"), EQUALS + "echo ======")

    def test_equals_word_after_separator(self):
        self.assertEqual(run_hook("ls; echo =====; pwd"), EQUALS + "ls; echo =====; pwd")

    def test_quoted_equals_word_is_left_alone(self):
        self.assertIsNone(run_hook("echo '=====' \"=====\""))

    def test_assignment_and_single_equals_are_left_alone(self):
        self.assertIsNone(run_hook('a=b; [ "$a" = b ] && ls --sort=size'))

    def test_both_prefixes_in_order(self):
        self.assertEqual(run_hook("echo ===== > out.txt"), EQUALS + CLOBBER + "echo ===== > out.txt")

    def test_clobber_prefix_present_adds_only_equals(self):
        command = CLOBBER + "echo ===== > out.txt"
        self.assertEqual(run_hook(command), EQUALS + command)

    def test_both_prefixes_present_is_left_alone(self):
        self.assertIsNone(run_hook(EQUALS + CLOBBER + "echo ===== > out.txt"))


class ZshBehaviourTests(unittest.TestCase):
    def test_prefix_makes_equals_word_literal_in_zsh(self):
        result = subprocess.run(
            ["zsh", "-c", run_hook("echo =====")], text=True, capture_output=True, check=False,
        )
        self.assertEqual((result.returncode, result.stdout), (0, "=====\n"), result.stderr)


if __name__ == "__main__":
    unittest.main()
