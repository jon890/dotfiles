#!/usr/bin/env python3
"""마크다운 가독성 규칙 중 기계로 판정 가능한 축을 검사한다.

규칙의 단일 소스는 `~/.claude/rules/` 의 세 파일이다.
# korean-style.md(언어), writing-structure.md(구조), markdown-readability.md(매체).

사용법:
    check-readability.py <파일.md> [<파일.md>...]
    check-readability.py --hook          # PostToolUse 훅 모드 (stdin 으로 JSON)

위반 줄을 stdout 으로 출력한다. 출력이 0 줄이면 통과다.
위반이 있으면 종료 코드 1, 사용법 오류면 2 로 끝난다.

여기서 검사하는 것은 `markdown-readability.md` 가 소유한 매체·렌더 축이다.

    NEST   괄호 2겹 중첩
    SECT   `§` 사용
    TILDE  한 단락에 이스케이프하지 않은 물결표 2개 이상 (취소선 오작동)
    DASH   제목과 평문의 엠대시 (목록과 표의 이름-설명 구분은 허용)

나머지 축은 다른 곳이 맡는다.

- 외래어와 인라인 `+` 연결은 `korean-style-check.sh` 가 강제한다
- fos-blog 렌더러 고유 함정(bold 안 따옴표, heading 숫자 prefix 등)은
  fos-study 의 `blog_score.py` 가 강제한다
- 명사형 종결은 Dooray 본문에 한해 각 레포의 `verify-dooray-body.py` 가 잡는다
- 한 문장 한 줄, `=` 와 `→` 압축, bullet 다중 속성은 의미 판단이 필요해 사람이 본다

**코드 블록과 표와 링크와 frontmatter 는 검사에서 제외한다.**
규칙이 이들을 미적용 대상으로 정했는데, 예전에 쓰던 맨 grep 은 그것을 거르지 않아
검출 결과가 전부 오탐이었다 (규칙 자신을 잡는 자기참조 포함).
"""

import json
import re
import sys

# 여는 괄호 안에서 다시 괄호가 열리고 닫히는 형태만 잡는다.
NESTED_PAREN = re.compile(r"\([^()]*\([^()]*\)")

# 목록 항목. 이름과 설명을 엠대시로 가르는 용도가 규칙상 허용이라 DASH 검사에서 뺀다.
LIST_ITEM = re.compile(r"^([-*+]|\d+\.)\s")

# 홈 경로의 물결표는 범위 표기가 아니다.
HOME_PATH = re.compile(r"~/[\w./-]+")

# 검사 전에 줄에서 지울 것. 남기면 이들 안의 문자가 위반으로 잡힌다.
CODE_SPAN = re.compile(r"`[^`]*`")
MD_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")


def strip_noise(line):
    """코드 스팬과 마크다운 링크를 지운다.

    링크를 먼저 지운다. `[텍스트](경로)` 는 괄호를 품고 있어
    코드 스팬만 지우면 중첩 괄호로 오인된다.
    """
    return CODE_SPAN.sub("", MD_LINK.sub("", line))


def check(path):
    """한 파일을 검사해 (경로, 줄번호, 코드, 메시지) 목록을 반환한다."""
    found = []
    in_fence = False
    in_front = False
    para = []  # 물결표는 단락 단위로 세야 한다. 취소선이 단락 안에서 짝지어지기 때문이다.

    def flush(para):
        if not para:
            return
        first = para[0][0]
        text = " ".join(t for _, t in para).replace("\\~", "")
        if HOME_PATH.sub("", text).count("~") >= 2:
            found.append((path, first, "TILDE",
                          "한 단락에 물결표가 2개 이상이다: 취소선으로 렌더될 수 있어 이스케이프하거나 표현을 바꾼다"))

    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        print(f"{path}: 읽기 실패, {e}", file=sys.stderr)
        return found

    for n, raw in enumerate(lines, 1):
        stripped = raw.strip()

        # YAML frontmatter 는 건너뛴다.
        # skill 과 agent 의 description 은 트리거 예시를 괄호로 감싸는 형식이라 규칙이 과적용된다.
        if stripped == "---" and (n == 1 or in_front):
            in_front = n == 1
            continue
        if in_front:
            continue

        # 코드 블록 안은 통째로 건너뛴다.
        if stripped.startswith("```"):
            in_fence = not in_fence
            flush(para)
            para = []
            continue
        if in_fence:
            continue

        # 표 행도 건너뛴다. 이미 구조화돼 있어 규칙이 과적용된다.
        if stripped.startswith("|"):
            continue

        line = strip_noise(raw)
        body = line.lstrip("> ").strip()

        if not body:
            flush(para)
            para = []
            continue

        para.append((n, body))

        if NESTED_PAREN.search(line):
            found.append((path, n, "NEST", "괄호 2겹 중첩: 별도 문장으로 나눈다"))

        if "§" in line:
            found.append((path, n, "SECT", "§ 대신 섹션이나 장, 또는 번호를 쓴다"))

        # 엠대시. 목록 항목과 표 행에서 이름과 설명을 가르는 용도는 규칙이 허용한다.
        if "\u2014" in body and not LIST_ITEM.match(body):
            if body.startswith("#"):
                found.append((path, n, "DASH",
                              "제목의 엠대시: 부제를 떼고 한 문장으로 쓴다"))
            else:
                found.append((path, n, "DASH",
                              "평문의 엠대시: 콜론이나 접속사로 바꾼다"))

    flush(para)
    return found


def run_hook():
    """PostToolUse 훅 모드.

    stdin 의 tool 입력 JSON 에서 편집된 파일 하나를 뽑아 검사하고,
    위반이 있을 때만 모델 컨텍스트로 되돌릴 JSON 을 낸다. 작업을 막지 않는다.
    """
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    target = payload.get("tool_input", {}).get("file_path") or payload.get(
        "tool_response", {}
    ).get("filePath")

    if not target or not target.endswith(".md"):
        return 0

    found = check(target)
    if not found:
        return 0

    lines = "\n".join(f"{p}:{n}  [{c}] {m}" for p, n, c, m in found)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        "마크다운 가독성 위반 — 방금 편집한 파일에서 발견했다. 지금 고쳐라.\n"
                        + lines
                    ),
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    if sys.argv[1] == "--hook":
        return run_hook()

    found = []
    for path in sys.argv[1:]:
        found.extend(check(path))

    for path, n, code, msg in found:
        print(f"{path}:{n}  [{code}] {msg}")

    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
