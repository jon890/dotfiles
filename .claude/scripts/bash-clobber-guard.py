#!/usr/bin/env python3
"""Bash 도구의 noclobber 실패를 명령이 돌기 전에 막는다.

Claude Code 의 Bash 도구는 자기 영속 셸에 `noclobber` 를 켠다.
사용자 dotfile 이 아니라 도구가 켜는 것이라 설정으로 끌 수 없고,
셸 상태가 호출 사이에 남지 않아 `setopt clobber` 를 한 번 돌려 둘 수도 없다.

그래서 두 경우가 실패한다.

    echo x > 있는파일     # file exists. 파일은 옛 내용을 유지한다
    echo x >> 없는파일    # no such file or directory. 파일이 만들어지지 않는다

둘 다 종료 코드 1 과 한 줄만 낸다. 쓰기와 검증을 한 명령에 묶으면
검증이 옛 파일을 읽고 통과를 찍는다. 실측으로 그렇게 통과한 검사가 있다.

이 훅은 그 명령을 실행 전에 거절하고 고칠 형태를 알려 준다.

PreToolUse 훅으로 쓴다. stdin 으로 JSON 을 받고 stdout 으로 결정을 낸다.
막지 못한 것은 통과시킨다. 판정하지 못하면 통과시킨다.
"""

from __future__ import annotations

import json
import os
import re
import sys

# heredoc 본문을 지우기 위한 시작 표식이다.
# `<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"` 를 모두 잡는다.
HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# 덮어쓰기 redirect 다. 앞에 fd 번호나 다른 redirect 문자가 없어야 한다.
# `>>`, `>|`, `>&` 는 제외한다. `2>` 와 `&>` 도 제외한다.
OVERWRITE = re.compile(r"(?<![0-9&<>])>(?![>|&(])\s*([^\s;|&<>()]+)")

# 이어쓰기 redirect 다. `>>|` 는 제외한다.
APPEND = re.compile(r"(?<![0-9&<>])>>(?![|&(])\s*([^\s;|&<>()]+)")

# 파일이 아니라 장치이거나 셸이 만들어 내는 이름이다. 검사하지 않는다.
SKIP_PREFIXES = ("/dev/", "/proc/", "$", "`", "&")


def strip_heredocs(command: str) -> str:
    """heredoc 본문을 지운다.

    본문에 `> 인용문` 같은 마크다운이 들어 있으면 redirect 로 오인한다.
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
        # 종료 표식을 만날 때까지 본문을 버린다.
        while index < len(lines) and lines[index].strip() != terminator:
            index += 1
        if index < len(lines):
            index += 1
    return "\n".join(kept)


def strip_quoted(text: str) -> str:
    """작은따옴표로 감싼 구간을 지운다.

    `grep '> foo'` 처럼 인용 안의 부등호를 redirect 로 세지 않기 위해서다.
    큰따옴표는 변수 확장이 있어 건드리지 않는다.
    """
    return re.sub(r"'[^']*'", "''", text)


def resolve(path: str, cwd: str) -> str | None:
    if path.startswith(SKIP_PREFIXES):
        return None
    expanded = os.path.expanduser(path)
    if not os.path.isabs(expanded):
        expanded = os.path.join(cwd, expanded)
    return expanded


def looks_like_path(token: str) -> bool:
    """파일 경로처럼 보이는지 본다.

    덮어쓰기는 대상이 실재할 때만 막으므로 이 검사가 필요 없다.
    이어쓰기는 대상이 없을 때 막기 때문에, 산문 낱말이 그대로 걸린다.
    실측으로 메시지 본문의 ``>> 없는파일`` 이 걸렸다.
    그래서 이어쓰기에서만 경로 모양을 함께 본다.
    """
    return "/" in token or bool(re.search(r"\.[A-Za-z0-9]{1,8}$", token))


def find_problems(command: str, cwd: str) -> list[str]:
    text = strip_quoted(strip_heredocs(command))
    problems: list[str] = []

    for match in OVERWRITE.finditer(text):
        target = resolve(match.group(1), cwd)
        if target and os.path.exists(target):
            problems.append(
                f"`> {match.group(1)}` 는 이미 있는 파일을 가리킨다. "
                f"덮어쓰려면 `>| {match.group(1)}` 를 쓴다."
            )

    for match in APPEND.finditer(text):
        if not looks_like_path(match.group(1)):
            continue
        target = resolve(match.group(1), cwd)
        if target and not os.path.exists(target):
            problems.append(
                f"`>> {match.group(1)}` 는 없는 파일을 가리킨다. "
                f"새로 만들려면 `>>| {match.group(1)}` 를 쓴다."
            )

    return problems


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = payload.get("tool_input", {}).get("command")
    if not isinstance(command, str):
        return 0

    cwd = payload.get("cwd") or os.getcwd()

    try:
        problems = find_problems(command, cwd)
    except Exception:
        return 0

    if not problems:
        return 0

    reason = (
        "이 셸은 `noclobber` 가 켜져 있어 이 명령이 파일을 바꾸지 못하고 "
        "종료 코드 1 과 한 줄만 낸다.\n"
        + "\n".join(f"- {problem}" for problem in problems)
        + "\n\n덮어쓸 의도가 아니면 다른 경로를 쓴다. "
        "검증 명령을 같은 호출에 붙이지 않는다. 붙이면 옛 파일을 읽고 통과한다."
    )

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
