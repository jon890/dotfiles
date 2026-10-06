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
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")


def expand(text: str, assigned: dict[str, str]) -> tuple[str, set[str]]:
    """`$이름`, `${이름}` 을 같은 명령의 대입값과 환경 변수로 푼다. 못 푼 이름을 함께 낸다."""
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        if name in assigned:
            return assigned[name]
        if name in os.environ:
            return os.environ[name]
        missing.add(name)
        return match.group(0)

    return VARIABLE.sub(replace, text), missing


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
    # 같은 명령 안에서 `D=/경로; git worktree add $D/이름` 처럼 대입한 변수를 풀어 본다.
    # 풀지 않으면 `$D/이름` 을 글자 그대로 경로로 읽어 올바른 자리도 거절한다(2026-10-02 실측).
    assigned: dict[str, str] = {}
    for segment in SEGMENT_SPLIT.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        while tokens and ASSIGNMENT.match(tokens[0]):
            key, _, value = tokens.pop(0).partition("=")
            assigned[key] = expand(value, assigned)[0]
        unresolved: set[str] = set()
        expanded = []
        for token in tokens:
            text, missing = expand(token, assigned)
            expanded.append(text)
            unresolved |= missing
        tokens = expanded
        if not tokens:
            continue
        if tokens[0] == "cd" and len(tokens) > 1:
            base = os.path.normpath(os.path.join(base, os.path.expanduser(tokens[1])))
            continue
        found = worktree_target(tokens)
        if not found:
            continue
        sub, git_dir, target = found
        if unresolved and "$" in target:
            # 값을 알 수 없는 변수가 경로에 남았다. 어디를 가리키는지 판정할 수 없어 경로를 그대로 쓰게 한다.
            names = ", ".join(sorted(f"${n}" for n in unresolved))
            return (
                f"워크트리 경로에 값을 알 수 없는 변수가 있습니다: {target} ({names})\n"
                "이 점검은 같은 명령 안에서 대입한 변수와 환경 변수만 풉니다. "
                "변수 대신 경로를 그대로 적어 다시 실행하세요."
            )
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
    if not isinstance(payload, dict):
        return
    # 두 런타임의 표준 셸 훅 이름은 Bash 이다. 다른 도구의 본문은 명령이 아니다.
    if payload.get("hook_event_name", "PreToolUse") != "PreToolUse":
        return
    if payload.get("tool_name", "Bash") not in ("Bash", "exec_command", "shell_command"):
        return
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, ValueError):
            # JSON 으로 감싸지 않은 셸 명령도 경로 점검을 거친다.
            tool_input = {"command": tool_input}
    if not isinstance(tool_input, dict):
        return
    command = tool_input.get("command") or tool_input.get("cmd") or ""
    if not isinstance(command, str) or "worktree" not in command:
        return
    cwd = payload.get("cwd")
    if cwd is None or cwd == "":
        cwd = os.getcwd()
    if not isinstance(cwd, str):
        return
    reason = judge(command, cwd)
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
