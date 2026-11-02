#!/usr/bin/env python3
"""GitHub 저장소들의 Claude 리뷰 토큰 secret 을 새 값으로 한 번에 바꾼다.

언제 쓰나: CI 의 claude-review 가 비용 0, 1초 안에 is_error 로 끝날 때(토큰 계정의 사용 한도, 만료).
새 토큰은 다른 계정으로 로그인한 터미널에서 `claude setup-token` 으로 만든다.

사용법:
  python3 rotate-claude-review-token.py --dry-run             # 바꿀 저장소와 secret 종류만 보인다
  python3 rotate-claude-review-token.py --from-clipboard      # 클립보드의 토큰으로 바꾸고 클립보드를 비운다
  printf '%s' "$TOKEN" | python3 rotate-claude-review-token.py --stdin
  옵션: --owner jon890(기본), --name CLAUDE_CODE_OAUTH_TOKEN(기본), --repo <이름> 을 여러 번(지정하면 그 저장소만)

대상: --repo 를 주지 않으면 owner 의 저장소 가운데 이 이름의 secret 이 이미 있는 곳이다.
Actions secret 과 Dependabot secret 을 각각 보고, 이미 있는 쪽만 바꾼다(없는 곳에 새로 만들지 않는다).

토큰 값은 출력하지 않는다. gh 에는 표준 입력으로만 넘긴다.
종료 코드: 0 모두 바꿨다(또는 --dry-run), 1 일부 실패, 2 사용법 오류나 토큰 없음.
"""
import argparse
import json
import subprocess
import sys


def gh(args, stdin=None):
    return subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)


def repos(owner):
    r = gh(["repo", "list", owner, "--limit", "200", "--json", "name", "--no-archived"])
    if r.returncode != 0:
        sys.exit(f"저장소 목록을 읽지 못했다: {r.stderr.strip()}")
    return [x["name"] for x in json.loads(r.stdout)]


def has_secret(owner, repo, name, app):
    args = ["secret", "list", "-R", f"{owner}/{repo}"]
    if app:
        args += ["--app", app]
    r = gh(args)
    if r.returncode != 0:
        return False
    return any(line.split("\t")[0] == name for line in r.stdout.splitlines())


def read_token(a):
    if a.from_clipboard:
        token = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
    elif a.stdin:
        token = sys.stdin.read().strip()
    else:
        print("토큰 입력 방식이 없다: --from-clipboard 나 --stdin 을 준다", file=sys.stderr)
        sys.exit(2)
    # 터미널이 긴 토큰을 줄바꿈해 복사되는 일이 있어 공백과 줄바꿈을 모두 뺀다. 토큰에는 공백이 없다
    token = "".join(token.split())
    if not token:
        print("토큰이 비었다. claude setup-token 이 낸 토큰을 복사했는지 본다", file=sys.stderr)
        sys.exit(2)
    return token


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--owner", default="jon890")
    p.add_argument("--name", default="CLAUDE_CODE_OAUTH_TOKEN")
    p.add_argument("--repo", action="append")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--from-clipboard", action="store_true")
    p.add_argument("--stdin", action="store_true")
    try:
        a = p.parse_args()
    except SystemExit:
        sys.exit(2)

    # 저장소마다 gh 를 두 번 부르므로 동시에 묻는다. 순서는 이름순으로 맞춘다
    from concurrent.futures import ThreadPoolExecutor
    pairs = [(repo, app) for repo in (a.repo or repos(a.owner)) for app in (None, "dependabot")]
    with ThreadPoolExecutor(max_workers=12) as pool:
        found = list(pool.map(lambda x: has_secret(a.owner, x[0], a.name, x[1]), pairs))
    targets = sorted((pair for pair, ok in zip(pairs, found) if ok), key=lambda x: (x[0], x[1] or ""))
    if not targets:
        print(f"{a.name} secret 이 있는 저장소가 없다")
        return 0
    for repo, app in targets:
        print(f"대상 {a.owner}/{repo} {app or 'actions'}")
    if a.dry_run:
        return 0

    token = read_token(a)
    failed = 0
    for repo, app in targets:
        args = ["secret", "set", a.name, "-R", f"{a.owner}/{repo}"]
        if app:
            args += ["--app", app]
        r = gh(args, stdin=token)
        ok = r.returncode == 0
        failed += not ok
        print(f"{'바꿈' if ok else '실패'} {a.owner}/{repo} {app or 'actions'}" + ("" if ok else f": {r.stderr.strip()}"))
    if a.from_clipboard:
        subprocess.run(["pbcopy"], input="", text=True)
        print("클립보드를 비웠다")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
