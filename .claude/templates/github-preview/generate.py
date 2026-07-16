#!/usr/bin/env python3
"""GitHub issue/PR 본문 미리보기 HTML 생성기.

GitHub 은 본문을 GitHub Flavored Markdown 으로 렌더링한다. 같은 모양을 재현하기 위해
github-markdown-css (GitHub 공식 마크다운 스타일) + marked.js (클라이언트 GFM 렌더) 를
쓰는 템플릿에 markdown 을 흘려 넣어 등록 전 본문을 실제 화면과 비슷하게 검토한다.

Dooray 미리보기(~/.claude/templates/dooray-preview/) 와 같은 구조 — viewer 엔진만 다르다.

사용 예:
    python3 ~/.claude/templates/github-preview/generate.py \
        --type issue \
        --repo "toast-lab/ai-playground-docu-parser" \
        --title "markdown 표: th+td 혼합 첫 행 헤더 중복 잔존" \
        --md-file /tmp/gh-body.md \
        --out /tmp/gh-preview.html
    cmux browser open "file:///tmp/gh-preview.html"

주의:
- markdown 본문에 '</script>' 문자열이 있으면 안 된다 (text/markdown 블록이 깨진다).
- CDN 로드라 오프라인에서는 스타일이 빠진 채 보인다.
- GitHub 고유 자동링크(#번호)·@mention·:emoji: 코드는 marked.js 가 GitHub 처럼 변환하지
  않는다 (유니코드 emoji 는 그대로 표시됨). 정확한 GFM 은 등록 후 GitHub 에서 확인.
"""

import argparse
import html
import sys
from pathlib import Path

TEMPLATE = Path(__file__).parent / "template.html"

TYPE_MAP = {
    "issue": ("issue", "Issue"),
    "pr": ("pr", "Pull Request"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="GitHub issue/PR 본문 미리보기 HTML 생성")
    ap.add_argument("--type", choices=["issue", "pr"], default="issue", help="본문 종류")
    ap.add_argument("--repo", default="", help="저장소 (예: toast-lab/ai-playground-docu-parser)")
    ap.add_argument("--title", required=True, help="issue/PR 제목")
    ap.add_argument("--md-file", required=True, help="본문 markdown 파일 경로 ('-' 는 stdin)")
    ap.add_argument("--out", required=True, help="출력 HTML 경로")
    args = ap.parse_args()

    if args.md_file == "-":
        md = sys.stdin.read()
    else:
        md = Path(args.md_file).read_text(encoding="utf-8")

    if "</script>" in md:
        print("오류: 본문에 '</script>' 가 포함되어 미리보기가 깨진다. 본문을 수정하라.", file=sys.stderr)
        return 1

    type_class, type_label = TYPE_MAP[args.type]

    out = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("{{TITLE}}", html.escape(args.title))
        .replace("{{REPO}}", html.escape(args.repo))
        .replace("{{TYPE_CLASS}}", type_class)
        .replace("{{TYPE_LABEL}}", type_label)
        .replace("{{MD_BODY}}", md)
    )
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"생성 완료: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
