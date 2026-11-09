#!/bin/sh
# Claude Code 는 상태줄을 터미널 폭보다 좁게 그려 끝을 … 로 자른다.
# OMC HUD 가 COLUMNS 를 줄바꿈 폭으로 쓰므로 여백만큼 줄여 넘긴다.
if [ "${COLUMNS:-0}" -gt 0 ]; then
  COLUMNS=$((COLUMNS - ${OMC_HUD_MARGIN:-10}))
  export COLUMNS
fi
# node 는 버전 경로 대신 mise shim 으로 찾는다. 버전을 박으면 mise 정리로 그 버전이 지워질 때 HUD 가 사라진다.
exec /Users/nhn/.local/share/mise/shims/node /Users/nhn/.claude/hud/omc-hud.mjs
