# cmux 터미널 환경 — AI 에이전트 규칙

이 환경은 **cmux** (https://www.cmux.dev) 위에서 실행되고 있습니다.
tmux 대신 cmux CLI를 사용하세요.

## 핵심 원칙

- **tmux 명령 대신 cmux 명령 사용**
- cmux가 없거나 CMUX_WORKSPACE_ID가 없으면 tmux로 폴백
- OMC `/team` 및 `/omc-teams`는 내부적으로 `execFile('tmux', ...)` 호출 → tmux 바이너리 필요 (별도 설치 유지)
- 에이전트가 터미널을 수동 조작할 때는 cmux CLI 사용

## 환경 변수 (자동 설정)

```bash
CMUX_WORKSPACE_ID   # 현재 워크스페이스 ID
CMUX_SURFACE_ID     # 현재 서페이스(창/패널) ID
```

## 핵심 cmux 명령어

| 목적 | cmux | tmux 대응 |
|------|------|-----------|
| 화면 읽기 | `cmux read-screen` | `tmux capture-pane -p` |
| 패널 캡처 | `cmux capture-pane [--surface ID]` | `tmux capture-pane -t` |
| 브라우저 조작 | `cmux browser [action]` | — |
| 대기 | `cmux wait-for [condition]` | — |
| 새 분할 | `cmux new-split right\|left\|up\|down` | `tmux split-window` |
| 명령 전송 | `cmux send --surface ID "command\n"` | `tmux send-keys -t` |
| 포커스 이동 | `cmux focus --surface ID` | `tmux select-pane -t` |

## cmux 감지 + tmux 폴백 패턴

```bash
if command -v cmux &>/dev/null && [ -n "$CMUX_WORKSPACE_ID" ]; then
  # cmux 환경
  cmux new-split right
  cmux send --surface surface:2 "npm run dev\n"
else
  # tmux 폴백
  tmux split-window -h
  tmux send-keys "npm run dev" C-m
fi
```

## cmux claude-teams

Agent Teams 모드로 Claude를 실행하는 내장 명령:

```bash
# CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 자동 설정 + tmux 심(shim) 주입
cmux claude-teams '<task description>'
cmux claude-teams --dangerously-skip-permissions -p '<task>'
```

## 주의사항

- OMC `omc team` / `/team` / `/omc-teams`는 tmux 바이너리를 직접 호출 → 별도 설치 필요
- `cmux claude-teams`는 OMC team과 별개로 동작하는 독립 명령
- 에이전트가 직접 터미널을 열거나 pane을 조작해야 할 때만 cmux CLI 사용
