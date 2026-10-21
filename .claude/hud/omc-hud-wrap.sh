#!/bin/sh
# Claude Code 는 상태줄을 터미널 폭보다 좁게 그려 끝을 … 로 자른다.
# OMC HUD 가 COLUMNS 를 줄바꿈 폭으로 쓰므로 여백만큼 줄여 넘긴다.
if [ "${COLUMNS:-0}" -gt 0 ]; then
  COLUMNS=$((COLUMNS - ${OMC_HUD_MARGIN:-10}))
  export COLUMNS
fi
exec /Users/nhn/.local/share/mise/installs/node/24.15.0/bin/node /Users/nhn/.claude/hud/omc-hud.mjs
