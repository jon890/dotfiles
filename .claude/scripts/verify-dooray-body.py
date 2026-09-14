#!/usr/bin/env python3
"""Dooray 업무 본문 자가 점검 — 기계로 잡히는 항목만 검사한다.

규칙 단일 소스는 `dooray-task` 스킬과 각 레포의 오버레이다.
이 스크립트는 그중 형식으로 판정 가능한 항목만 본다. 의미 판단(표로 나눌 때인가,
phase 가 동사로 서술됐나)은 사람이 해야 하므로 여기서 다루지 않는다.

사용:
    python3 ~/.claude/scripts/verify-dooray-body.py <본문.md> [...]

출력이 0 줄이면 통과. 위반이 있으면 `파일:줄  [코드] 설명` 형식으로 찍고 exit 1.
경고(약신호)는 exit code 에 반영하지 않는다. 판단 재료일 뿐이라 통과를 막지 않는다.
인자나 대상 파일이 없을 때, 공용 검사기를 돌리지 못했을 때는 exit 2 다.
검사가 돌지 못한 것은 위반이 없는 것과 다르므로 통과로 세지 않는다.

**왜 스크립트가 필요한가**: Dooray 본문은 저장소 밖(스크래치패드)에서 작성돼
저장소 파일에 걸린 표기 훅이 닿지 않는다. 그 사각지대를 메운다.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

KOREAN_STYLE = Path.home() / ".claude" / "scripts" / "korean-style-check.py"


class CheckerUnavailable(RuntimeError):
    """공용 검사기를 돌리지 못했다. 위반 없음과 구분해 종료 코드 2 로 끝낸다."""


def run_korean_style(path: Path) -> list[str]:
    """외래어와 인라인 `+` 연결 검사를 공용 검사기에 위임한다.

    검사기를 찾지 못하거나 실행에 실패하면 소리내어 실패한다.
    조용히 건너뛰면 검사가 도는 것처럼 보이면서 금지어를 하나도 잡지 못한다.
    실측으로 이 경로가 옛 `.sh` 를 가리키던 동안 심어둔 금지어 3건이 모두 통과했다.
    """
    if not KOREAN_STYLE.is_file():
        raise CheckerUnavailable(f"공용 검사기를 찾을 수 없다: {KOREAN_STYLE}")
    try:
        out = subprocess.run(
            [sys.executable, str(KOREAN_STYLE), str(path)],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise CheckerUnavailable(f"공용 검사기를 돌리지 못했다: {exc}") from exc
    # 공용 검사기는 "경로:줄: 메시지" 로 낸다. 이 스크립트의 표기에 맞춰 다시 적는다.
    found = []
    for raw in out.splitlines():
        parts = raw.split(":", 2)
        if len(parts) == 3:
            found.append(f"{path.name}:{parts[1]}  [STYLE]{parts[2]}")
    return found

# 명사형 종결로 자주 쓰이는 어간. paragraph 평문에서만 문제이고 목록·표·헤더는 허용된다.
NOUN_ENDINGS = ("필요", "확보", "불변", "미확정", "완료", "가능", "예정", "무관")

WIDE = 200  # 화면 폭 기준 (한글 2폭 환산)


def display_width(s: str) -> int:
    """한글·전각을 2폭으로 세어 실제 화면 폭을 낸다. len() 은 한글을 1로 세어 과소평가한다."""
    return sum(2 if ord(ch) > 0x1100 else 1 for ch in s)


def scan(path: Path) -> tuple[list[str], list[str]]:
    """(위반, 경고) 를 돌려준다. 경고는 exit code 에 반영하지 않는다."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 코드 펜스 안은 대부분의 규칙이 적용되지 않는다.
    # 이걸 빼먹으면 Python 주석 `# ...` 을 마크다운 H1 으로 오탐한다 (실측).
    in_fence = False
    in_code: list[bool] = []
    for line in lines:
        if line.lstrip().startswith("```"):
            in_code.append(True)
            in_fence = not in_fence
            continue
        in_code.append(in_fence)

    bad: list[str] = []
    warn: list[str] = []

    def hit(no: int, code: str, msg: str) -> None:
        bad.append(f"{path.name}:{no}  [{code}] {msg}")

    # --- 줄 단위 ---
    for i, (line, code) in enumerate(zip(lines, in_code), start=1):
        if code:
            continue

        if line.startswith("# "):
            hit(i, "H1", "H1 을 쓰지 않는다. Dooray UI 가 제목을 별도 노출하므로 H2 부터 시작한다")

        if display_width(line) > WIDE:
            hit(i, "WIDTH", f"한 줄이 {display_width(line)}폭이다. 의미 단위로 나눈다 (기준 {WIDE})")

        if line.startswith("- ") and line.count(",") >= 3:
            hit(i, "COMMA", "bullet 한 줄에 콤마 3개 이상 나열이다. sub-bullet 으로 나눈다")

        # 명사형 종결은 평문 문장에서만 문제다. 목록·표·헤더 항목은 명사구가 자연스럽다.
        if not line.startswith(("-", "|", "#", " ", ">")) and line.strip():
            if re.search(rf"(?:{'|'.join(NOUN_ENDINGS)})\.\s*$", line):
                hit(i, "NOUN", "평문 문장이 명사형으로 끝난다. 동사로 끝맺는다")

    # 외래어와 인라인 `+` 연결은 공용 검사기가 소유한다.
    # 여기에 사본을 두면 매핑 표가 늘 때마다 갈라진다 (실측: 사본 11항, 원본 26항).
    bad.extend(run_korean_style(path))

    # --- 문서 단위 ---
    body_wo_code = "\n".join(l for l, c in zip(lines, in_code) if not c)

    # 참고 절의 위치는 원본 파일 기준으로 잡는다. 코드 블록을 뺀 텍스트에서 세면
    # 앞에 코드 블록이 있는 만큼 줄 번호가 당겨져 엉뚱한 줄을 가리킨다.
    ref_start = next(
        (
            i
            for i, (line, code) in enumerate(zip(lines, in_code), start=1)
            if not code and line.startswith("## 참고")
        ),
        None,
    )

    if ref_start is not None:
        ref = body_wo_code.split("## 참고", 1)[1]

        if re.search(r"^- (상위|하위|형제) 업무", ref, re.M) or re.search(
            r"nhnent\.dooray\.com/task/", ref
        ):
            hit(ref_start, "REF-FAMILY",
                "참고에 상위·하위·형제 업무 링크를 넣었다. Dooray UI 가 관계를 제공하므로 지운다")

        if not re.search(r"^- ", ref, re.M):
            hit(ref_start, "REF-EMPTY", "참고 절이 비었다. 넣을 것이 없으면 절 자체를 지운다")

    # 구체성은 의미 판단이라 단정할 수 없다. 재료가 없다는 신호만 준다.
    if "```" not in text and "| ---" not in text:
        warn.append(
            f"{path.name}  [ABSTRACT?] 코드 블록도 표도 없다. "
            "바뀌는 값·before/after·로그 원문 중 필요한 것이 빠지지 않았는지 본다"
        )

    if "### 용어" not in body_wo_code:
        warn.append(
            f"{path.name}  [TERM?] `### 용어` 절이 없다. "
            "처음 등장하는 전문 용어가 있으면 풀이를 넣는다"
        )

    return bad, warn


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip())
        return 2

    all_bad: list[str] = []
    all_warn: list[str] = []
    for arg in argv:
        p = Path(arg)
        if not p.is_file():
            print(f"파일을 찾을 수 없다: {arg}", file=sys.stderr)
            return 2
        try:
            bad, warn = scan(p)
        except CheckerUnavailable as exc:
            print(f"{exc}", file=sys.stderr)
            return 2
        all_bad += bad
        all_warn += warn

    for line in all_bad:
        print(line)
    for line in all_warn:
        print(line)

    return 1 if all_bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
