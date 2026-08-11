#!/usr/bin/env bash
# 한국어 표기 정책 검사 — 금지어와 인라인 `+` 연결을 찾는다.
#
# 금지어 목록의 단일 소스는 ~/.claude/rules/korean-style.md 의 "외래어 매핑 표" 다.
# 별도 데이터 파일을 두지 않는다 — 검사기가 쓰는 정보는 그 표의 부분집합이라,
# 사본을 만들면 원본과 갈라지는 문제만 되돌아온다.
#
# 사용법: korean-style-check.sh <파일> [<파일>...]
# 위반 줄을 stdout 으로 출력한다. 출력이 0 줄이면 통과.
# 코드 블록(```)과 코드 스팬(`...`)은 렌더·표기 대상이 아니라 검사에서 제외한다.
#
# 편집 직후 자동 검사 (settings.json 은 머신 로컬이라 추적하지 않으므로 여기 남긴다).
# ~/.claude/settings.json 의 hooks 에 아래를 넣으면 .md 를 쓸 때마다 검사한다:
#
#   "PostToolUse": [{
#     "matcher": "Edit|Write|MultiEdit",
#     "hooks": [{
#       "type": "command",
#       "command": "~/.claude/scripts/korean-style-check.sh --hook",
#       "timeout": 15,
#       "statusMessage": "한국어 표기 점검"
#     }]
#   }]
set -u

RULES="${KOREAN_STYLE_RULES:-$HOME/.claude/rules/korean-style.md}"
[ -f "$RULES" ] || exit 0   # 규칙 파일이 없는 환경(팀원 등)에서는 조용히 건너뛴다

# --hook: PostToolUse 에서 호출되는 모드.
#   stdin 의 tool 입력 JSON 에서 편집된 파일 하나를 뽑아 검사하고,
#   위반이 있을 때만 모델 컨텍스트로 되돌릴 JSON 을 낸다. 작업을 막지 않는다.
if [ "${1:-}" = "--hook" ]; then
  command -v jq >/dev/null || exit 0
  target=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty' 2>/dev/null)
  case "$target" in *.md) ;; *) exit 0 ;; esac
  [ -f "$target" ] || exit 0
  found=$("$0" "$target")
  [ -n "$found" ] || exit 0
  jq -n --arg c "한국어 표기 정책 위반 — 방금 편집한 파일에서 발견했다. 지금 고쳐라.
$found" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $c}}'
  exit 0
fi

[ $# -gt 0 ] || exit 0

# 금지어를 부분 문자열로 품고 있지만 그 자체로는 정당한 합성어.
# 한국어 금지어는 조사가 붙어 "게이트를" 처럼 쓰이므로 부분 문자열로 찾아야 한다.
# 그래서 "게이트웨이"(gateway) 처럼 다른 낱말인 경우도 같이 걸린다.
# 뒤 글자가 한글인지로는 조사와 합성어를 가를 수 없어, 예외는 여기에 명시한다.
# 검사 전에 이 낱말들을 줄에서 지우므로, 같은 줄에 맨 "게이트" 가 따로 있으면 그건 여전히 잡힌다.
COMPOUND_ALLOW='게이트웨이'

# 매핑 표 첫 열에서 금지어를 뽑는다.
#   "클램프 / clamp"     → 클램프, clamp   (슬래시는 동의어 구분)
#   "게이트 (gate)"      → 게이트, gate    (괄호 안 영어 원어도 금지어)
#   "폭주 (CPU 폭주 등)" → 폭주            (괄호 안이 한국어면 용례 설명이라 제외)
#   "ephemeral (instance / runner)" → ephemeral  (괄호 안 슬래시는 한정 설명이라 제외)
# 괄호 안 영어를 등록하지 않으면 "외부 상태 gate" 처럼 원어를 그대로 쓴 문장이 통과한다.
TERMS=$(awk '
  function emit(s) {
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", s)
    if (s != "") print s
  }
  /^## 외래어 매핑 표/ { t = 1; next }
  t && /^## / { exit }
  t && /^\| / && !/^\|[[:space:]]*-/ && !/^\| 금지 / {
    split($0, cell, "|")
    col = cell[2]
    while (match(col, /\([^)]*\)/)) {
      inner = substr(col, RSTART + 1, RLENGTH - 2)
      col = substr(col, 1, RSTART - 1) " " substr(col, RSTART + RLENGTH)
      if (inner ~ /^[A-Za-z][A-Za-z -]*$/) emit(inner)
    }
    n = split(col, parts, "/")
    for (i = 1; i <= n; i++) emit(parts[i])
  }
' "$RULES" | sort -u)

# 표 형태가 바뀌어 추출이 비면 조용히 통과시키지 않고 시끄럽게 실패한다.
# (검사기가 안 도는데 통과로 보이는 상황이 가장 위험하다)
if [ -z "$TERMS" ]; then
  echo "korean-style-check: $RULES 에서 금지어를 추출하지 못했다 — 매핑 표 형식 확인 필요" >&2
  exit 2
fi

for f in "$@"; do
  case "$f" in *.md) ;; *) continue ;; esac
  [ -f "$f" ] || continue
  # 규칙 파일 자신은 건너뛴다 — 매핑 표가 곧 금지어 목록이라 전부 위반으로 잡힌다.
  [ "$f" -ef "$RULES" ] && continue

  printf '%s\n' "$TERMS" | awk -v F="$f" -v ALLOW="$COMPOUND_ALLOW" '
    NR == FNR { terms[FNR] = $0; cnt = FNR; next }
    /^```/ { code = !code; next }
    code { next }
    {
      line = $0
      gsub(/`[^`]*`/, "", line)                       # 코드 스팬 제외
      if (ALLOW != "") gsub(ALLOW, "", line)          # 정당한 합성어 제외
      for (i = 1; i <= cnt; i++) {
        t = terms[i]
        if (t ~ /^[A-Za-z-]+$/) {                     # 영문 용어는 단어 경계로
          if (line ~ ("(^|[^A-Za-z-])" t "([^A-Za-z-]|$)"))
            print F ":" FNR ": 금지어 \"" t "\" — korean-style 매핑 표의 권장 표현으로"
        } else if (index(line, t) > 0) {
          print F ":" FNR ": 금지어 \"" t "\" — korean-style 매핑 표의 권장 표현으로"
        }
      }
      # 제목은 제외한다. 이 검사는 본문의 인라인 항목 연결만 다룬다.
      if (line ~ / \+ / && line !~ /^#+ /)
        print F ":" FNR ": 인라인 + 연결 — 쉼표·와/과 또는 목록으로"
    }
  ' - "$f"
done
