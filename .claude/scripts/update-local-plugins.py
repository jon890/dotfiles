#!/usr/bin/env python3
"""로컬 폴더를 마켓플레이스로 쓰는 플러그인을 그 저장소의 main 이 바뀔 때 다시 설치한다.

git post-merge hook 이 부른다. 인자는 플러그인 이름(`fos-skills@fos-skills` 꼴)이다.
그 저장소의 원본 체크아웃이 main 일 때만 돈다. worker 워크트리의 merge 는 건너뛴다.
모든 Orca 프로필의 plugins 폴더가 ~/.claude/plugins 를 가리키므로 한 번 갱신하면 모든 프로필이 받는다.
새 버전은 다음에 여는 세션부터 실린다. orch 스크립트는 부를 때마다 설치 기록을 읽어 바로 새 번들을 쓴다.
"""
import datetime
import os
import subprocess
import sys

LOG = os.path.expanduser("~/.claude/logs/update-local-plugins.log")


def log(line: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{stamp} {line}\n")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: update-local-plugins.py <플러그인@마켓플레이스> ...", file=sys.stderr)
        return 2
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    common = os.path.realpath(git("rev-parse", "--git-common-dir"))
    toplevel = os.path.realpath(git("rev-parse", "--show-toplevel"))
    if branch != "main" or os.path.dirname(common) != toplevel:
        return 0
    for plugin in sys.argv[1:]:
        market = plugin.split("@", 1)[1]
        for cmd in (["claude", "plugin", "marketplace", "update", market], ["claude", "plugin", "update", plugin]):
            done = subprocess.run(cmd, capture_output=True, text=True)
            out = (done.stdout + done.stderr).strip().splitlines()
            log(f"{toplevel} {' '.join(cmd[2:])} exit={done.returncode} {out[-1] if out else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
