#!/usr/bin/env python3
"""Claude 와 Codex 가 같은 개인 지침을 읽도록 `.codex/AGENTS.md` 를 만든다.

원본은 `.agents/personal-rules.md` 하나다.
Claude 는 `.claude/CLAUDE.md` 의 `@~/.agents/personal-rules.md` 로 원본을 가져온다.
Codex 의 AGENTS.md 는 가져오기를 지원하지 않아 이 스크립트가 원본을 그대로 넣어 만든다.

    sync-agent-rules.py           .codex/AGENTS.md 를 다시 쓴다
    sync-agent-rules.py --check   쓰지 않고, 어긋나면 차이를 내고 종료 코드 1 이다
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

SOURCE = Path(".agents/personal-rules.md")
CLAUDE = Path(".claude/CLAUDE.md")
CODEX = Path(".codex/AGENTS.md")

CLAUDE_IMPORT = "@~/.agents/personal-rules.md"
CLAUDE_OMC_IMPORT = "@CLAUDE-omc.md"

OMX_START = b"<!-- OMX:AGENTS:START -->"
OMX_END = b"<!-- OMX:AGENTS:END -->"

CODEX_HEADER = """\
# Codex 개인 지침

이 아래 개인 지침은 `.agents/personal-rules.md` 에서 `scripts/sync-agent-rules.py` 가 만든다. 이 파일을 직접 고치지 않고 원본을 고친 뒤 스크립트를 돌린다.
OMX 관리 영역은 설치 도구가 갱신하므로 직접 수정하지 않는다.

"""

CODEX_SECTION = """
## Codex 전용

- Codex CLI 를 기본으로 안내한다.
- Codex 관리 스킬은 플러그인으로 설치한다. 기존 개별 복사와 원본 폴더 연결은 플러그인이 제공하는 스킬을 확인한 뒤 단계적으로 정리한다.
- 다른 저장소를 바꾸는 위임은 `orchestration` 스킬로 한다.

"""

OMX_WRAP_HEAD = "<details>\n<summary>OMX 관리 지침</summary>\n\n"
OMX_WRAP_TAIL = "\n\n</details>\n"


class SyncError(Exception):
    pass


def extract_omx_block(existing: bytes) -> bytes:
    """기존 AGENTS.md 에서 OMX 관리 블록을 표지 포함 바이트 그대로 잘라 낸다."""
    start = existing.find(OMX_START)
    if start < 0:
        raise SyncError(f"{OMX_START.decode()} 표지를 찾지 못했다")
    end = existing.find(OMX_END, start)
    if end < 0:
        raise SyncError(f"{OMX_END.decode()} 표지를 찾지 못했다")
    return existing[start : end + len(OMX_END)]


def build_codex(root: Path) -> bytes:
    source = (root / SOURCE).read_bytes()
    existing = (root / CODEX).read_bytes()
    block = extract_omx_block(existing)
    return (
        CODEX_HEADER.encode()
        + source.rstrip(b"\n")
        + b"\n"
        + CODEX_SECTION.encode()
        + OMX_WRAP_HEAD.encode()
        + block
        + OMX_WRAP_TAIL.encode()
    )


def check_claude(root: Path) -> list[str]:
    """CLAUDE.md 가 공통 원본을 가져오는지 본다. 어긋난 곳을 문장으로 돌려준다."""
    problems = []
    claude = root / CLAUDE
    if not claude.exists():
        return [f"{CLAUDE} 가 없다"]
    lines = claude.read_text(encoding="utf-8").splitlines()
    if CLAUDE_IMPORT not in lines:
        problems.append(f"{CLAUDE} 에 `{CLAUDE_IMPORT}` 줄이 없다")
    elif CLAUDE_OMC_IMPORT in lines and lines.index(CLAUDE_IMPORT) > lines.index(CLAUDE_OMC_IMPORT):
        problems.append(f"{CLAUDE} 에서 `{CLAUDE_IMPORT}` 가 `{CLAUDE_OMC_IMPORT}` 보다 뒤에 있다")
    if not (root / SOURCE).exists():
        problems.append(f"{SOURCE} 가 없다. Claude 가 가져올 원본이 없다")
    return problems


def run(root: Path, check: bool) -> int:
    try:
        expected = build_codex(root)
    except (SyncError, OSError) as error:
        print(f"실패: {error}", file=sys.stderr)
        return 2

    problems = check_claude(root)
    current = (root / CODEX).read_bytes()
    drift = current != expected

    if check:
        if drift:
            diff = difflib.unified_diff(
                current.decode("utf-8", "replace").splitlines(keepends=True),
                expected.decode("utf-8", "replace").splitlines(keepends=True),
                fromfile=f"{CODEX} (지금)",
                tofile=f"{CODEX} (원본에서 만든 것)",
            )
            sys.stderr.writelines(diff)
            problems.append(f"{CODEX} 가 {SOURCE} 와 어긋났다. scripts/sync-agent-rules.py 를 돌린다")
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    if drift:
        (root / CODEX).write_bytes(expected)
        print(f"{CODEX} 를 다시 썼다")
    else:
        print(f"{CODEX} 는 이미 최신이다")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="쓰지 않고 어긋남만 검사한다")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="지침 파일이 있는 저장소 루트(기본: 스크립트의 상위 폴더)",
    )
    args = parser.parse_args(argv)
    return run(args.root, args.check)


if __name__ == "__main__":
    sys.exit(main())
