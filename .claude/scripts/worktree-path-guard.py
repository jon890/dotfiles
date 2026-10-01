#!/usr/bin/env python3
"""`git worktree add`, `git worktree move` 가 정해진 자리 밖에 워크트리를 만들지 못하게 한다.

워크트리 자리는 Orca 규칙인 `<저장소>/worktrees/<저장소 이름>/<이름>` 하나다.
`orca worktree create`, `orca orchestration worker-start --worktree new-top-level` 이 이 자리에 만든다.
손으로 `git worktree add worktrees/<이름>` 처럼 한 단을 빼거나 `.claude/worktrees/` 에 만들면
Orca 화면과 정리 도구가 그 워크트리를 놓치고, 끝난 뒤에도 남는다(2026-10-01 실측).

PreToolUse 훅으로 쓴다. 자리 밖이면 `permissionDecision: deny` 와 바른 경로를 낸다.
판정하지 못하면(저장소가 아님, 경로를 못 읽음) 아무것도 내지 않고 원래 흐름에 맡긴다.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\n|\|")
# `add` 와 `move` 에서 값을 하나 받는 옵션이다. 이 값은 경로가 아니다.
OPTIONS_WITH_VALUE = {"-b", "-B", "--reason"}


def main_repo_root(directory: str) -> str | None:
    try:
        common = subprocess.run(
            ["git", "-C", directory, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    if not common.endswith("/.git"):
        return None
    return os.path.dirname(common)


def worktree_target(tokens: list[str]) -> tuple[str, str | None, str] | None:
    """`git [-C dir] worktree add|move ...` 에서 (하위 명령, -C 값, 대상 경로) 를 꺼낸다."""
    if "git" not in tokens:
        return None
    rest = tokens[tokens.index("git") + 1:]
    git_dir = None
    while rest and rest[0].startswith("-"):
        if rest[0] == "-C" and len(rest) > 1:
            git_dir = rest[1]
            rest = rest[2:]
        elif rest[0] in ("-c",) and len(rest) > 1:
            rest = rest[2:]
        else:
            rest = rest[1:]
    if len(rest) < 2 or rest[0] != "worktree" or rest[1] not in ("add", "move"):
        return None
    sub = rest[1]
    args = rest[2:]
    positional: list[str] = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in OPTIONS_WITH_VALUE:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        positional.append(arg)
    if sub == "add" and positional:
        return sub, git_dir, positional[0]
    if sub == "move" and len(positional) >= 2:
        return sub, git_dir, positional[1]
    return None


def judge(command: str, cwd: str) -> str | None:
    """자리 밖이면 거절 사유를, 아니면 None 을 낸다."""
    base = cwd
    for segment in SEGMENT_SPLIT.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        if not tokens:
            continue
        if tokens[0] == "cd" and len(tokens) > 1:
            base = os.path.normpath(os.path.join(base, os.path.expanduser(tokens[1])))
            continue
        found = worktree_target(tokens)
        if not found:
            continue
        sub, git_dir, target = found
        run_dir = os.path.normpath(os.path.join(base, os.path.expanduser(git_dir))) if git_dir else base
        root = main_repo_root(run_dir)
        if not root:
            continue
        name = os.path.basename(root)
        allowed = os.path.join(root, "worktrees", name) + os.sep
        target_abs = os.path.normpath(os.path.join(run_dir, os.path.expanduser(target)))
        if (target_abs + os.sep).startswith(allowed):
            continue
        leaf = os.path.basename(target_abs.rstrip(os.sep)) or "<이름>"
        return (
            f"워크트리 자리 밖입니다: {target_abs}\n"
            f"워크트리는 {allowed}<이름> 에만 둡니다. "
            f"`orca worktree create --repo path:{root} --name {leaf}` 로 만들거나 "
            f"`git worktree {sub} ... {allowed}{leaf}` 로 경로를 고쳐 다시 실행하세요."
        )
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    if "worktree" not in command:
        return
    reason = judge(command, payload.get("cwd") or os.getcwd())
    if not reason:
        return
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
