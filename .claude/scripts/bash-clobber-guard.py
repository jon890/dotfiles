#!/usr/bin/env python3
"""Bash 도구의 noclobber 를 리다이렉트가 있는 명령에서만 끈다.

Claude Code 의 Bash 도구는 자기 셸에 `noclobber` 를 켠다.
사용자 dotfile 이 아니라 도구가 켜는 것이라 설정으로 끌 수 없고,
셸 상태가 호출 사이에 남지 않아 한 번 꺼 둘 수도 없다.

그래서 두 경우가 실패한다.

    echo x > 있는파일     # file exists. 파일은 옛 내용을 유지한다
    echo x >> 없는파일    # no such file or directory. 파일이 만들어지지 않는다

둘 다 종료 코드 1 과 한 줄만 낸다. 쓰기와 검증을 한 명령에 묶으면
검증이 옛 파일을 읽고 통과를 찍는다.

이 훅은 리다이렉트가 보이는 명령 앞에 `set +o noclobber;` 를 붙여 보통 셸처럼 돌게 한다.
대상 경로는 판정하지 않는다. `cd` 뒤의 상대경로나 따옴표로 감싼 대상을
실행 전에 정확히 풀 수 없어서, 경로를 판정하던 거절 방식은 오탐을 냈다.

PreToolUse 훅으로 쓴다. `updatedInput` 만 내고 `permissionDecision` 은 내지 않는다.
권한 판정은 원래 흐름에 맡긴다. 판정하지 못하면 아무것도 내지 않는다.
"""

from __future__ import annotations

import json
import re
import sys

PREFIX = "set +o noclobber; "

# heredoc 본문을 지우기 위한 시작 표식이다.
# `<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"` 를 모두 잡는다.
HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# 출력 리다이렉트다. `=>` 와 `->` 는 산문과 코드의 화살표라 제외한다.
# `2>&1` 처럼 파일이 아닌 것도 걸리지만, 접두어는 해가 없으므로 가르지 않는다.
REDIRECT = re.compile(r"(?<![=-])>")


def strip_heredocs(command: str) -> str:
    """heredoc 본문을 지운다.

    본문에 `> 인용문` 같은 마크다운이 들어 있으면 리다이렉트로 오인한다.
    """
    lines = command.split("\n")
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        match = HEREDOC_START.search(line)
        index += 1
        if not match:
            continue
        terminator = match.group(2)
        while index < len(lines) and lines[index].strip() != terminator:
            index += 1
        if index < len(lines):
            index += 1
    return "\n".join(kept)


def strip_quoted(text: str) -> str:
    """작은따옴표 구간을 지운다. `grep '> foo'` 의 부등호를 세지 않기 위해서다."""
    return re.sub(r"'[^']*'", "''", text)


def needs_prefix(command: str) -> bool:
    if command.startswith(PREFIX):
        return False
    return bool(REDIRECT.search(strip_quoted(strip_heredocs(command))))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str):
        return 0

    try:
        if not needs_prefix(command):
            return 0
    except Exception:
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": {**tool_input, "command": PREFIX + command},
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
