---
name: content-preview
description: 외부에 게시·등록되는 본문(Dooray 댓글·업무, GitHub 이슈·PR, 메일·슬랙 메시지, 위키 등)을 사용자에게 등록 전 미리보기로 보여줄 때 사용한다. 렌더링 HTML 을 띄우는 절차, 미리보기 직전 자가 점검 체크리스트, Dooray(TOAST UI)·GitHub(marked.js) HTML 생성기 사용법을 담는다. 사용자가 "미리보기"라고 명시하지 않아도, 외부에 나갈 텍스트를 작성해 등록·게시하려는 순간이면 반드시 이 skill 을 연다. 로컬 파일 작성·코드 커밋처럼 외부에 게시되지 않는 산출물은 대상이 아니다.
---

# content-preview — 외부 게시 본문 미리보기

Dooray·GitHub·메일·슬랙 등 외부로 나가는 본문을, 사용자가 등록 전에 검토·수정할 수 있도록 미리보기로 보여주는 절차다.

핵심 이유: `Write`/`Edit` 로 임시 파일에만 저장하면 사용자 화면에는 도구 호출만 보이고 내용이 숨겨져, 검토·수정 지시를 할 수 없다. 그래서 본문을 **실제 렌더링 HTML** 로 띄워 눈으로 볼 수 있게 한다.

## 순서 (고정)

```
수신자 확인 → 문체 결정 → 본문 작성 → 자가 점검 → 미리보기(턴 종료) → 사용자가 읽고 응답 → 등록
```

- **본인 명의로 나가는 글이면 본문을 쓰기 전에 [`references/work-writing-persona.md`](references/work-writing-persona.md) 를 읽는다.** 다 쓴 뒤 점검 항목으로 확인하면 늦다. 헤더와 표로 짜놓은 본문은 문체를 고치는 게 아니라 처음부터 다시 쓰는 일이 된다.
- **HTML 미리보기를 띄운다.** 사용자가 따로 요청하지 않아도 생략하지 않는다.
- **본문 전문을 채팅에 다시 쓰지 않는다.** 무엇을 띄웠는지와 제목만 한 줄로 알린다.
    * 본문은 이미 파일과 브라우저에 있다. 채팅에 옮겨 적으면 같은 내용이 두 번 쌓여 토큰만 쓴다.
    * 사용자는 렌더링된 쪽을 읽는다. 인라인 사본은 읽히지 않는다.
    * 예외는 사용자가 채팅에서 보자고 명시할 때뿐이다.

**이 확인 방식은 본 skill 이 소유한다.** `create-pr`, `dooray-task` 같은 게시 skill 과
레포 오버레이는 여기를 가리키고 자기 쪽에 확인 절차를 다시 적지 않는다.
두 곳에 적으면 한쪽만 고쳐져 서로 다른 지시가 남는다.

부분 수정은 예외다. 바뀐 블록만 AS-IS / TO-BE 로 채팅에 보인다.
렌더링된 전문은 무엇이 바뀌었는지 보여주지 못하고, 바뀐 블록은 전문이 아니라 diff 다.
- **미리보기와 구조화된 질문을 같은 턴에 묶지 않는다.** 선택창이 본문을 가려 사용자가 읽기 전에 결정을 강요당한다. 미리보기 턴은 미리보기로 끝내고, 등록 확인은 사용자가 본문을 읽고 응답한 다음 턴에서 받는다.

## 자가 점검 (미리보기 직전, 의무)

미리보기로 넘어가기 전에 아래를 통과한다. 건너뛰면 사용자가 같은 규칙 위반을 반복 지적하게 된다. 컨텍스트 누적으로 규칙이 밀려도 이 단계만은 강제한다.

- 본인 명의 업무 글이면 페르소나 자가 점검 8항목을 통과했는지 — 댓글에 `##` 헤더나 표를 넣지 않았는지가 가장 자주 걸린다
- 마크다운 가독성 규칙 적용 여부 — `~/.claude/rules/markdown-readability.md`
- 같은 규칙의 자가 점검: 인라인 항목 연결, 명사형 종결, 긴 나열, 압축된 표 셀
- 작성 함정: `~` 짝수개(취소선 오작동), `§` 기호, heredoc escape 잔존
- 한국어 표현 정책 — `~/.claude/rules/korean-style.md`
- 본문 파일이 실제로 갱신됐는지 — 아래 "본문 파일 덮어쓰기" 참조

## HTML 미리보기 생성 (Dooray · GitHub)

Dooray 업무·댓글, GitHub issue·PR 본문은 실제 렌더링과 비슷한 HTML 을 만들어 브라우저로 띄운다.

생성기·템플릿은 `~/.claude/templates/` 에 둔다 (brain-add skill 도 공유하므로 이 위치를 유지한다).

| 대상 | 렌더링 원리 | 생성기 |
| --- | --- | --- |
| Dooray | NHN TOAST UI Editor viewer CSS/JS (`uicdn.toast.com/editor/latest`) → 실제 등록 화면과 거의 동일 | `~/.claude/templates/dooray-preview/` |
| GitHub | github-markdown-css(공식 스타일)와 marked.js(GitHub Flavored Markdown) → 실제 화면과 비슷 | `~/.claude/templates/github-preview/` |

공통 주의:

- 본문에 `` `</script>` `` 문자열 금지 (생성기가 검출·거부).
- CDN 로드라 오프라인이면 스타일이 빠진다.

### 본문 파일 덮어쓰기

수정본을 같은 경로에 다시 쓸 때 zsh 의 `noclobber` 로 `cat > 기존파일` 이 거부된다. 오류는 `file exists` 한 줄로만 나오고 뒤이은 생성기는 그대로 성공하므로, **이전 본문으로 만든 미리보기를 새 본문이라고 착각한다.**

수정본을 쓸 때는 기존 파일을 먼저 지우고, 쓴 뒤 첫 줄을 확인한다.

```bash
rm -f "$SP/body.md" "$SP/preview.html"
cat > "$SP/body.md" <<'EOF'
...
EOF
head -3 "$SP/body.md"
```

Dooray 사용법:

```bash
python3 ~/.claude/templates/dooray-preview/generate.py \
  --title "[VectorSearch] [DocParser] ..." \
  --tag "Document Parser" --tag "개선" --tag "REAL" \
  --meta "담당자:김병태" --meta "참조:개발 그룹" \
  --md-file /tmp/body.md --out /tmp/dooray-preview.html
orca tab create --url "file:///tmp/dooray-preview.html"
```

GitHub 사용법 (`--type` 은 `issue` 또는 `pr`, 헤더 배지 색 구분):

```bash
python3 ~/.claude/templates/github-preview/generate.py \
  --type issue \
  --repo "toast-lab/ai-playground-docu-parser" \
  --title "..." \
  --md-file /tmp/gh-body.md --out /tmp/gh-preview.html
orca tab create --url "file:///tmp/gh-preview.html"
```

- GitHub 고유 자동링크(`#번호`)와 `:emoji:` 코드는 marked.js 가 변환하지 않는다. 정확한 GFM 은 등록 후 GitHub 에서 확인한다.

## 승격 메모

`~/.claude/templates/` 는 Claude Code 자동 인식 경로가 아니라 절대경로로 참조하는 관례 폴더다. 미리보기 유틸이 더 늘면 이 skill 번들 안(`templates/` 와 `scripts/`)으로 옮겨 자체 완결 구조로 승격한다. 단 현재 템플릿은 brain-add skill 과 공유 중이라, 옮길 때 참조처를 함께 갱신해야 한다.
