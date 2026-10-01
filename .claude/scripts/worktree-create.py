#!/usr/bin/env python3
"""Claude Code 의 워크트리를 `.claude/worktrees/` 대신 Orca 자리에 만든다.

Claude Code 는 `--worktree`, 하위 에이전트의 `isolation: "worktree"` 로 워크트리를 만들 때
기본으로 `<저장소>/.claude/worktrees/<이름>` 을 쓰고, 이 자리를 바꾸는 설정 키는 없다.
`WorktreeCreate` 훅만 그 동작을 대신할 수 있다(https://code.claude.com/docs/en/worktrees.md).

이 훅은 Orca 규칙인 `<저장소>/worktrees/<저장소 이름>/<이름>` 에 `worktree-<이름>` 브랜치로 만들고,
만든 절대경로를 stdout 에 한 줄로 낸다. 기준은 원격 기본 브랜치이고, 없으면 HEAD 다.
같은 자리에 이미 워크트리가 있으면 그 경로를 그대로 낸다.
git 출력은 stderr 로 보낸다. stdout 에 경로 외의 것이 섞이면 Claude Code 가 경로를 읽지 못한다.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys


def git(*args: str, cwd: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, text=True,
        stdout=subprocess.PIPE, stderr=sys.stderr,
    ).stdout.strip()


def main() -> int:
    payload = json.load(sys.stdin)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", str(payload.get("name") or "")).strip("-.")
    if not name:
        print("worktree-create: name 이 비어 있다", file=sys.stderr)
        return 1
    cwd = payload.get("cwd") or os.getcwd()
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)
    root = os.path.dirname(common) if common.endswith("/.git") else git("rev-parse", "--show-toplevel", cwd=cwd)
    target = os.path.join(root, "worktrees", os.path.basename(root), name)

    if os.path.isdir(target):
        print(target)
        return 0

    try:
        base = git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", cwd=root)
    except subprocess.CalledProcessError:
        base = "HEAD"
    branch = f"worktree-{name}"
    os.makedirs(os.path.dirname(target), exist_ok=True)
    exists = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=root
    ).returncode == 0
    if exists:
        git("worktree", "add", target, branch, cwd=root)
    else:
        git("worktree", "add", "-b", branch, target, base, cwd=root)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
