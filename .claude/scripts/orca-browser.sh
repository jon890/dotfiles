#!/usr/bin/env bash
# Orca 내장 브라우저 자동화 공용 헬퍼.
#
# 왜 필요한가:
#   1. orca CLI 는 실패해도 종료 코드가 0 이다 (JSON 의 "ok" 필드만 실패를 알린다).
#      그대로 쓰면 오류가 조용히 묻힌다. 이 헬퍼는 ok:false 를 종료 코드 1 로 바꾼다.
#   2. 매 스킬마다 "탭 열고 page id 뽑기" JSON 파싱을 반복하지 않게 한다.
#   3. orca wait --load 는 이미 로드된 페이지에서 항상 timeout 이므로 (실측),
#      대신 --fn 으로 document.readyState 를 확인한다.
#
# 사용법:
#   PAGE=$(orca-browser.sh open "https://example.com")
#   orca-browser.sh js   "$PAGE" "document.title"
#   orca-browser.sh nav  "$PAGE" "https://example.com/other"
#   orca-browser.sh url  "$PAGE"
#   orca-browser.sh snap "$PAGE"
#   orca-browser.sh ready "$PAGE" 30000
#   orca-browser.sh waitjs "$PAGE" "document.querySelector('#toastUuid').value !== ''"
#   orca-browser.sh shot  "$PAGE" /tmp/debug.png
#   orca-browser.sh close "$PAGE"
#
# waitjs 를 쓰는 이유: UI 안정화를 sleep 으로 기다리면 느리고 불안정한데다,
# 이 환경은 foreground sleep 을 차단한다. 조건이 참이 될 때까지 기다리는 편이 옳다.
set -euo pipefail

READY_TIMEOUT_DEFAULT=30000

# orca 를 호출하고 JSON 에서 값을 뽑는다. ok:false 면 stderr 로 오류를 내고 종료 코드 1.
#   $1 = result 하위 경로 (점 표기, 빈 문자열이면 result 전체를 JSON 으로)
#   나머지 = orca 인자
_call() {
  local path="$1"; shift
  local out
  out=$(orca "$@" --json 2>&1)
  ORCA_PATH="$path" python3 -c '
import json, os, sys
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except json.JSONDecodeError:
    sys.stderr.write("orca 응답이 JSON 이 아니다:\n" + raw + "\n")
    sys.exit(1)
if not d.get("ok"):
    err = d.get("error", {})
    sys.stderr.write("orca 실패 [%s] %s\n" % (err.get("code", "unknown"), err.get("message", raw)))
    sys.exit(1)
node = d.get("result", {})
path = os.environ["ORCA_PATH"]
if not path:
    print(json.dumps(node, ensure_ascii=False))
    sys.exit(0)
for key in path.split("."):
    if not isinstance(node, dict) or key not in node:
        sys.stderr.write("응답에 %s 가 없다: %s\n" % (path, json.dumps(node, ensure_ascii=False)))
        sys.exit(1)
    node = node[key]
print(node if isinstance(node, str) else json.dumps(node, ensure_ascii=False))
' <<<"$out"
}

# document.readyState 가 complete 가 될 때까지 기다린다.
_ready() {
  local page="$1" timeout="${2:-$READY_TIMEOUT_DEFAULT}"
  _call "" wait --fn "document.readyState==='complete'" \
    --timeout "$timeout" --page "$page" >/dev/null
}

cmd="${1:-}"; shift || true
case "$cmd" in
  open)
    page=$(_call browserPageId tab create --url "$1")
    _ready "$page" "${2:-$READY_TIMEOUT_DEFAULT}"
    echo "$page"
    ;;
  nav)
    _call "" goto --url "$2" --page "$1" >/dev/null
    _ready "$1" "${3:-$READY_TIMEOUT_DEFAULT}"
    ;;
  js)    _call result eval --expression "$2" --page "$1" ;;
  url)   _call url get --what url --page "$1" ;;
  snap)  orca snapshot --page "$1" ;;
  ready) _ready "$1" "${2:-$READY_TIMEOUT_DEFAULT}" ;;
  waitjs)
    _call "" wait --fn "$2" --timeout "${3:-10000}" --page "$1" >/dev/null
    ;;
  shot)
    # orca screenshot 은 파일이 아니라 base64 를 JSON 으로 돌려주므로 직접 디코딩한다.
    out="${2:-/tmp/orca-shot.png}"
    fmt="png"; [[ "$out" == *.jpg || "$out" == *.jpeg ]] && fmt="jpeg"
    ORCA_OUT="$out" python3 -c '
import base64, json, os, sys
d = json.load(sys.stdin)
if not d.get("ok"):
    err = d.get("error", {})
    sys.stderr.write("orca 실패 [%s] %s\n" % (err.get("code","unknown"), err.get("message","")))
    sys.exit(1)
data = d.get("result", {}).get("data")
if not data:
    sys.stderr.write("응답에 이미지 데이터가 없다\n")
    sys.exit(1)
path = os.environ["ORCA_OUT"]
with open(path, "wb") as f:
    f.write(base64.b64decode(data))
print(path)
' <<<"$(orca screenshot --format "$fmt" --page "$1" --json 2>&1)"
    ;;
  console) _call "" exec --command console --page "$1" ;;
  errors)  _call "" exec --command errors  --page "$1" ;;
  close) _call "" tab close --page "$1" >/dev/null ;;
  *)
    sed -n '2,20p' "$0" >&2
    exit 2
    ;;
esac
