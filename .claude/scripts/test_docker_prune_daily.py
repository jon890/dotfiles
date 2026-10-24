"""docker-prune-daily 를 가짜 Docker 와 plist 도구로 검증한다."""

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


CLAUDE_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = CLAUDE_DIR / "bin" / "docker-prune-daily"
PLIST = CLAUDE_DIR / "launchd" / "com.jon890.docker-prune-daily.plist"
EXPECTED_PRUNES = [
    "docker builder prune -f --filter until=72h",
    "docker image prune -f",
    "docker volume prune -f",
]


class DockerPruneDailyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="docker-prune-daily-")
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name)
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.calls = self.directory / "calls.txt"
        fake_docker = self.bin / "docker"
        fake_docker.write_text(
            "#!/usr/bin/env python3\n"
            "import os, pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "with pathlib.Path(os.environ['FAKE_DOCKER_CALLS']).open('a') as f:\n"
            "    f.write('docker ' + ' '.join(args) + '\\n')\n"
            "mode = os.environ.get('FAKE_DOCKER_MODE', '')\n"
            "if args == ['info'] and mode == 'info-fails': sys.exit(8)\n"
            "if args[:3] == ['builder', 'prune', '-f'] and mode == 'prune-fails': sys.exit(9)\n"
            "print('fake docker output')\n",
            encoding="utf-8",
        )
        fake_docker.chmod(0o755)
        self.env = {
            **os.environ,
            "HOME": str(self.directory),
            "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
            "FAKE_DOCKER_CALLS": str(self.calls),
        }

    def run_script(self, *args, mode=""):
        env = {**self.env, "FAKE_DOCKER_MODE": mode}
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True, capture_output=True, env=env, check=False,
        )

    def recorded_calls(self):
        return self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []

    def log_contents(self):
        log_file = self.directory / "Library" / "Logs" / "docker-prune-daily.log"
        return log_file.read_text(encoding="utf-8") if log_file.exists() else ""

    def test_dry_run_prints_only_safe_prune_commands_without_calling_docker(self):
        result = self.run_script("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = result.stdout.splitlines()
        self.assertEqual(commands, EXPECTED_PRUNES)
        self.assertFalse(any("-a" in command.split() for command in commands))
        self.assertEqual(self.recorded_calls(), [])

    def test_docker_info_failure_skips_pruning_and_succeeds(self):
        result = self.run_script(mode="info-fails")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded_calls(), ["docker info"])
        log_lines = self.log_contents().splitlines()
        self.assertEqual(len(log_lines), 1)
        self.assertIn("정리를 건너뜁니다", log_lines[0])

    def test_prune_failure_returns_one(self):
        result = self.run_script(mode="prune-fails")
        self.assertEqual(result.returncode, 1, result.stderr)
        calls = self.recorded_calls()
        self.assertIn("docker builder prune -f --filter until=72h", calls)
        self.assertNotIn("docker image prune -f", calls)
        self.assertNotIn("docker volume prune -f", calls)

    def test_plist_is_valid(self):
        result = subprocess.run(["plutil", "-lint", str(PLIST)], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
