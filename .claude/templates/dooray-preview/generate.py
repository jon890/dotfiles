#!/usr/bin/env python3
"""Dooray 본문 미리보기 HTML 생성기.

Dooray 는 본문을 TOAST UI Editor 로 렌더링하므로, 같은 viewer CSS/JS (uicdn.toast.com)
를 쓰는 템플릿에 markdown 을 흘려 넣으면 실제 등록 화면과 거의 동일한 미리보기가 된다.

사용 예:
    python3 ~/.claude/templates/dooray-preview/generate.py \
        --title "[VectorSearch] [DocParser] ..." \
        --tag "Document Parser" --tag "개선" --tag "REAL" \
        --meta "담당자:김병태" --meta "참조:개발 그룹" \
        --md-file /tmp/body.md \
        --out /tmp/dooray-preview.html
    cmux browser open "file:///tmp/dooray-preview.html"

주의:
- markdown 본문에 '</script>' 문자열이 있으면 안 된다 (text/plain 블록이 깨짐).
- CDN 로드라 오프라인에서는 스타일이 빠진 채 보인다.
"""

import argparse
import html
import sys
from pathlib import Path

TEMPLATE = Path(__file__).parent / "template.html"


def main() -> int:
    ap = argparse.ArgumentParser(description="Dooray 본문 미리보기 HTML 생성")
    ap.add_argument("--title", required=True, help="업무 제목")
    ap.add_argument("--project", default="AI-TF-VectorSearch", help="프로젝트명 (헤더 표시용)")
    ap.add_argument("--tag", action="append", default=[], help="태그 (반복 지정)")
    ap.add_argument("--meta", action="append", default=[],
                    help="메타 정보 '라벨:값' (반복 지정, 예: 담당자:김병태)")
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

    tags_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in args.tag)
    meta_parts = []
    for m in args.meta:
        label, _, value = m.partition(":")
        meta_parts.append(f"<span>{html.escape(label)} <b>{html.escape(value)}</b></span>")

    out = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("{{TITLE}}", html.escape(args.title))
        .replace("{{PROJECT}}", html.escape(args.project))
        .replace("{{TAGS_HTML}}", tags_html)
        .replace("{{META_HTML}}", "".join(meta_parts))
        .replace("{{MD_BODY}}", md)
    )
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"생성 완료: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
