#!/bin/sh
# Claude Code 는 상태줄을 터미널 폭보다 좁게 그려 끝을 … 로 자른다.
# OMC HUD 가 COLUMNS 를 줄바꿈 폭으로 쓰므로 여백만큼 줄여 넘긴다.
# 사용자 이름과 node 경로를 박지 않는다. 회사 맥과 맥북이 같은 파일을 쓴다.
if [ "${COLUMNS:-0}" -gt 0 ]; then
  COLUMNS=$((COLUMNS - ${OMC_HUD_MARGIN:-10}))
  export COLUMNS
fi
NODE_BIN="$(command -v node || echo "$HOME/.local/share/mise/shims/node")"
exec "$NODE_BIN" "$(dirname "$0")/omc-hud.mjs"
