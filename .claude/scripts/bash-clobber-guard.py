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

`2>&1` 같은 fd 복제와 `/dev/null` 로 가는 리다이렉트만 있으면 바꾸지 않는다.
noclobber 와 상관이 없는데, 입력을 바꾸면 auto mode 분류기가 판정하지 못해 호출이 한 번 거부된다.

zsh 는 따옴표 없는 `=` 로 시작하는 낱말을 명령 경로로 바꾼다(EQUALS).
`echo =====` 가 `==== not found` 로 실패하므로, 그런 낱말이 보이면 `setopt no_equals;` 를 붙인다.
명령이 이미 접두어로 시작하면 다시 붙이지 않는다. 처음부터 접두어를 붙여 보내면 입력이 바뀌지 않는다.

PreToolUse 훅으로 쓴다. `updatedInput` 만 내고 `permissionDecision` 은 내지 않는다.
권한 판정은 원래 흐름에 맡긴다. 판정하지 못하면 아무것도 내지 않는다.
"""

from __future__ import annotations

import json
import re
import sys

PREFIX = "set +o noclobber; "
EQUALS_PREFIX = "setopt no_equals; "

# heredoc 본문을 지우기 위한 시작 표식이다.
# `<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"` 를 모두 잡는다.
HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# 출력 리다이렉트다. `=>` 와 `->` 는 산문과 코드의 화살표라 제외한다.
REDIRECT = re.compile(r"(?<![=-])>")

# 파일에 쓰지 않는 리다이렉트다. noclobber 와 상관이 없어 판정 전에 지운다.
# `2>&1`, `>&2`, `2>&-`, `&>/dev/null`, `2>/dev/null`, `>>/dev/null` 이 해당한다.
NON_FILE_REDIRECT = re.compile(r"\d*>&(?:\d+|-)|&>>?\s*/dev/null|\d*>>?\s*/dev/null")

# 따옴표 밖에서 `=` 로 시작하고 뒤에 글자가 더 있는 낱말이다. 낱말 하나뿐인 `=`(`[ a = b ]`)와
# 낱말 가운데의 `=`(`a=b`, `--opt=v`)는 걸리지 않는다.
EQUALS_WORD = re.compile(r"(?:^|(?<=[\s;|&(]))=\S")


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


def strip_double_quoted(text: str) -> str:
    """큰따옴표 구간을 지운다. 그 안의 `=` 는 EQUALS 로 바뀌지 않는다."""
    return re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)


def peel_prefixes(command: str) -> tuple[set[str], str]:
    """명령 앞에 이미 붙은 접두어를 떼어 낸다."""
    found: set[str] = set()
    rest = command
    while True:
        for prefix in (PREFIX, EQUALS_PREFIX):
            if rest.startswith(prefix):
                found.add(prefix)
                rest = rest[len(prefix):]
                break
        else:
            return found, rest


def needed_prefixes(command: str) -> list[str]:
    """붙여야 할 접두어를 붙일 차례대로 돌려준다. 없으면 빈 목록이다."""
    present, rest = peel_prefixes(command)
    body = strip_quoted(strip_heredocs(rest))
    needed: list[str] = []
    if EQUALS_PREFIX not in present and EQUALS_WORD.search(strip_double_quoted(body)):
        needed.append(EQUALS_PREFIX)
    if PREFIX not in present and REDIRECT.search(NON_FILE_REDIRECT.sub("", body)):
        needed.append(PREFIX)
    return needed


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
        prefixes = needed_prefixes(command)
    except Exception:
        return 0
    if not prefixes:
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": {**tool_input, "command": "".join(prefixes) + command},
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
