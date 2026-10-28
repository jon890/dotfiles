"""sync-agent-rules.py 를 임시 폴더의 가짜 지침 파일로 검증한다."""

import importlib.util
import io
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "sync-agent-rules.py"
spec = importlib.util.spec_from_file_location("sync_agent_rules", SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

OMX_BLOCK = (
    "<!-- OMX:AGENTS:START -->\n"
    "한글 블록\t탭과  공백 보존\n"
    "<!-- OMX:AGENTS:END -->"
)
CLAUDE_OK = "@~/.agents/personal-rules.md\n\n## Claude 전용\n\n<!-- OMC:IMPORT:START -->\n\n@CLAUDE-omc.md\n"


class SyncAgentRulesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="sync-agent-rules-")
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)
        for name in (".agents", ".claude", ".codex"):
            (self.root / name).mkdir()
        self.write(".agents/personal-rules.md", "공통 규칙 한 줄\n\n## 절\n\n내용\n")
        self.write(".claude/CLAUDE.md", CLAUDE_OK)
        self.write(".codex/AGENTS.md", "옛 개인 지침\n\n" + OMX_BLOCK + "\n\n뒤에 붙은 것\n")

    def write(self, relative, text):
        (self.root / relative).write_text(text, encoding="utf-8")

    def read(self, relative):
        return (self.root / relative).read_bytes()

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sync.main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_check_fails_before_sync_and_does_not_write(self):
        before = self.read(".codex/AGENTS.md")
        code, _, err = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("공통 규칙 한 줄", err)
        self.assertEqual(self.read(".codex/AGENTS.md"), before)

    def test_sync_embeds_source_verbatim_and_keeps_omx_block_bytes(self):
        code, _, _ = self.run_main()
        self.assertEqual(code, 0)
        result = self.read(".codex/AGENTS.md")
        self.assertIn(self.read(".agents/personal-rules.md").rstrip(b"\n"), result)
        self.assertIn(OMX_BLOCK.encode(), result)
        self.assertNotIn("옛 개인 지침".encode(), result)
        self.assertNotIn("뒤에 붙은 것".encode(), result)

    def test_sync_is_idempotent_and_check_passes_afterwards(self):
        self.run_main()
        first = self.read(".codex/AGENTS.md")
        self.run_main()
        self.assertEqual(self.read(".codex/AGENTS.md"), first)
        self.assertEqual(self.run_main("--check")[0], 0)

    def test_source_change_makes_check_fail(self):
        self.run_main()
        self.write(".agents/personal-rules.md", "바뀐 규칙\n")
        self.assertEqual(self.run_main("--check")[0], 1)

    def test_hand_edit_of_codex_personal_part_makes_check_fail(self):
        self.run_main()
        text = self.read(".codex/AGENTS.md").decode().replace("공통 규칙 한 줄", "손으로 고친 줄")
        self.write(".codex/AGENTS.md", text)
        self.assertEqual(self.run_main("--check")[0], 1)

    def test_missing_omx_markers_fail_without_writing(self):
        self.write(".codex/AGENTS.md", "표지 없는 파일\n")
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("표지", err)
        self.assertEqual(self.read(".codex/AGENTS.md"), "표지 없는 파일\n".encode())

    def test_missing_end_marker_fails(self):
        self.write(".codex/AGENTS.md", "<!-- OMX:AGENTS:START -->\n끝 표지 없음\n")
        self.assertEqual(self.run_main("--check")[0], 2)

    def test_check_fails_when_claude_does_not_import_source(self):
        self.run_main()
        self.write(".claude/CLAUDE.md", "@CLAUDE-omc.md\n")
        code, _, err = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("personal-rules.md", err)

    def test_check_fails_when_import_comes_after_omc_block(self):
        self.run_main()
        self.write(".claude/CLAUDE.md", "@CLAUDE-omc.md\n\n@~/.agents/personal-rules.md\n")
        self.assertEqual(self.run_main("--check")[0], 1)


if __name__ == "__main__":
    unittest.main()
