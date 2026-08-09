#!/bin/sh
# stale TMUX 소켓 복구 — Claude Code SessionStart 훅에서 실행한다.
#
# 왜 unset 이 아니라 복구인가:
# 훅은 자식 프로세스라 이미 떠 있는 Claude Code 의 환경변수를 지울 수 없다.
# 그래서 반대로, TMUX 가 가리키는 죽은 소켓 자리에 tmux 서버를 다시 띄우고
# TMUX_PANE 이 가리키는 pane 번호까지 window 를 채워 조회가 성공하게 만든다.
# 예방(값 자체를 지우는 쪽)은 ~/.zshenv.d/20-stale-tmux.sh 가 담당한다.
#
# 어떤 경우에도 세션 시작을 막지 않는다 — 실패하면 조용히 넘어간다.

[ -n "$TMUX" ] || exit 0

SOCK="${TMUX%%,*}"
[ -n "$SOCK" ] || exit 0

# 소켓이 살아 있으면 정상 상태다.
if [ -S "$SOCK" ] && tmux -S "$SOCK" has-session 2>/dev/null; then
  exit 0
fi

command -v tmux >/dev/null 2>&1 || exit 0

# TMUX_PANE 은 "%N" 형식. N 번 pane 까지 있어야 조회가 성공한다.
PANE_NUM=0
case "$TMUX_PANE" in
  %[0-9]*) PANE_NUM="${TMUX_PANE#%}" ;;
esac

# 비정상적으로 큰 값은 무시한다 (window 를 무한히 만들지 않기 위한 상한).
case "$PANE_NUM" in
  *[!0-9]*) PANE_NUM=0 ;;
esac
[ "$PANE_NUM" -le 64 ] 2>/dev/null || PANE_NUM=0

mkdir -p "$(dirname "$SOCK")" 2>/dev/null || exit 0
tmux -S "$SOCK" new-session -d -s stale-tmux-revive 2>/dev/null || exit 0

# 새 서버의 pane 은 %0 부터 붙는다. %N 을 확보하려면 window 를 N+1 개 만든다.
i=0
while [ "$i" -lt "$PANE_NUM" ]; do
  tmux -S "$SOCK" new-window -t stale-tmux-revive 2>/dev/null || break
  i=$((i + 1))
done

echo "[fix-stale-tmux] 죽은 tmux 소켓을 복구했습니다: $SOCK (pane ${TMUX_PANE:-%0})" >&2
exit 0
