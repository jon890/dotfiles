#!/usr/bin/env python3
"""두레이 본문을 등록·수정하기 전에 두레이 링크 형식을 검사한다.

`dooray post create`, `dooray post edit`, `dooray post comment add|edit` 를 `--body-file <파일>` 과 함께
부르면, dooray-task 스킬의 `check_dooray_links.py` 로 그 파일을 검사한다. 위반이 있으면 실행을 막고
고칠 줄과 `--fix` 명령을 알려 준다. 스킬을 거치지 않고 CLI 를 바로 불러 `https://` 업무 주소가
그대로 나간 일이 되풀이됐다(사용자 결정 2026-11-16).

PreToolUse 훅으로 쓴다. 판정하지 못하면(검사기 없음, 파일 없음, 본문을 stdin·`--body` 로 넘김)
아무것도 내지 않고 원래 흐름에 맡긴다.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shlex
import subprocess
import sys

TARGET = re.compile(r"\bdooray\s+post\s+(?:create|edit|comment\s+(?:add|edit))\b")
CHECKER_GLOBS = (
    "~/Library/Application Support/orca/claude-profiles/*/home/plugins/cache/ai-sdt-skills/ai-sdt/*/skills/dooray-task/scripts/check_dooray_links.py",
    "~/.claude/plugins/cache/ai-sdt-skills/ai-sdt/*/skills/dooray-task/scripts/check_dooray_links.py",
)


def find_checker() -> str | None:
    found: list[str] = []
    for pattern in CHECKER_GLOBS:
        found.extend(glob.glob(os.path.expanduser(pattern)))
    if not found:
        return None
    return max(found, key=os.path.getmtime)


def body_files(command: str) -> list[str]:
    files: list[str] = []
    for part in re.split(r"&&|\|\||;|\n", command):
        if not TARGET.search(part):
            continue
        try:
            words = shlex.split(part)
        except ValueError:
            continue
        for i, word in enumerate(words):
            if word == "--body-file" and i + 1 < len(words):
                files.append(words[i + 1])
            elif word.startswith("--body-file="):
                files.append(word.split("=", 1)[1])
    return [os.path.expandvars(os.path.expanduser(f)) for f in files if f != "-"]


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not TARGET.search(command):
        return
    files = [f for f in body_files(command) if os.path.isfile(f)]
    checker = find_checker()
    if not files or not checker:
        return
    problems: list[str] = []
    for path in files:
        result = subprocess.run([sys.executable, checker, path], capture_output=True, text=True)
        if result.returncode == 1:
            problems.append(f"{path}\n{(result.stdout + result.stderr).strip()}")
    if not problems:
        return
    reason = (
        "두레이 링크 형식 위반이 있어 등록을 막았다. 아래 명령으로 고친 뒤 다시 등록한다.\n"
        + "\n".join(f'python3 "{checker}" --fix "{p.splitlines()[0]}"' for p in problems)
        + "\n\n"
        + "\n\n".join(problems)
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
