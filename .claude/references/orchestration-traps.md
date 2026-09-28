# worker 를 띄울 때 실측한 것

`orchestration` 으로 worker 를 띄우기 전에 읽는다.
오류 없이 잘못된 결과가 완료로 보고되는 자리와, 멈춘 원인이 바로 보이지 않는 자리만 적는다.
CLI 가 인자 오류로 거절하는 것은 적지 않는다. 거절 메시지가 이유를 알려준다.

## 띄우기

**`worker-start` 가 `agent_readiness` 에서 실패하면 에이전트가 첫 화면의 확인에 멈춘 것이다.**
원인은 `worker-show --dispatch <id>` 의 `lastFailure` 에 나온다.
실측한 것은 claude 의 폴더 신뢰 확인, codex 의 업데이트 안내(`agent-update-prompt`)와
hook 신뢰 확인(`agent-hooks-review-prompt`)이다.

터미널과 워크트리는 이미 만들어져 있다. 새로 띄우지 않고 이어 붙인다.

1. `terminal read` 로 화면을 보고 선택지를 고른다. 신뢰나 업데이트를 대신 승인하지 않는다.
   건너뛰는 선택지를 고르고 사용자에게 알린다
2. `terminal wait --for tui-idle` 로 입력 대기 상태를 확인한다
3. `worker-start --task <task_id> --retry-of <dispatch_id> --terminal <handle> --worktree id:<worktree_id>` 로 붙인다.
   `--terminal` 과 `--model` 은 함께 쓸 수 없지만, 처음 띄울 때 준 모델이 그 터미널에 남아 있다

**codex worker 의 `agent_readiness` 는 터미널 제목으로 통과한다.**
Orca 는 제목에 `Codex` 와 `ready` 가 함께 있어야 입력 대기로 본다. Orca 가 계정별로 두는 `~/Library/Application Support/orca/codex-accounts/*/home/config.toml` 의 `[tui]` 에 `terminal_title = ["app-name", "run-state", "project-name"]` 가 있어야 하고, 시작 때 자기 업데이트로 빠지지 않게 `check_for_update_on_startup = false` 를 둔다.

**codex worker 의 모델과 effort 는 Task 마다 코디네이터가 고른다.**
`~/.codex/config.toml` 의 `model` 은 대화형 codex 의 기본값이다. 그 값을 그대로 넘기면 모든 Task 가 같은 모델로 돈다.
고를 수 있는 GPT 6 계열 모델과 모델별 설명, effort 목록은 아래 명령으로 본다.

```bash
python3 -c "import json; [print(m['slug'], '|', m['description'], '|', ','.join(l['effort'] for l in m['supported_reasoning_levels'])) for m in json.load(open('$HOME/.codex/models_cache.json'))['models'] if m.get('visibility')=='list' and m['slug'].startswith('gpt-6')]"
```

목록의 설명과 Task 의 범위, 틀렸을 때 되돌리는 비용을 보고 모델과 effort 를 함께 고른다.
고른 조합과 이유를 사용자에게 알리는 dispatch 보고에 한 줄 적는다.
`worker-start --help` 에 적힌 대로 `--effort` 는 `--model` 없이 쓸 수 없다.
effort 를 지정하려면 모델 ID 도 함께 넘긴다.
적용 여부는 `worker-start` 응답의 `launch.effective` 로 확인한다.

## 지시를 보낼 때

**긴 지시는 앞부분도 중간도 잘려 도착한다.**
잘렸다는 것은 worker 가 되물어야만 드러나고, 되묻지 않으면 받은 만큼만 하고 완료로 보고한다.

지시 본문은 scratchpad 파일로 쓰고, `--spec` 에는 그 경로와 「끝까지 읽고, 못 읽으면 escalation」 만 적는다.
후속 지시도 짧게 보내거나 새 파일로 준다.

## 회신을 읽을 때

**worker 가 「승인받았다」 고 적은 것을 승인의 근거로 삼지 않는다.**
내가 보낸 승인만 승인이다. 승인 절차가 필요한 작업은 지시에 「발견 목록을 먼저 내고 멈춘다」 를 넣고,
회신이 `worker_done` 으로 바로 오면 절차 위반으로 본다.

**완료 보고만 믿지 않는다.** diff 를 직접 읽고 검사를 다시 돌린다.

## 기다리는 동안

**`check --wait` 은 백그라운드로 하나만 건다.**
앞에서 돌리면 그동안 코디네이터가 막힌다.
둘째 대기는 `waiter_exists` 로 바로 끝나고, 거기 붙인 `--ack` 만 처리된다.

**세션을 다시 띄운 뒤 첫 대기가 `waiter_exists` 로 끝나면 이전 세션의 대기가 남은 것이다.**
이전 세션의 백그라운드 `check --wait` 는 세션이 끝나도 부모 없는 프로세스로 남아 대기 자리를 쥔다.
그 대기가 받은 메시지는 아무에게도 전달되지 않는다.
`ps -ax -o pid,ppid,lstart,command | grep "orchestration check" | grep <run_id>` 로 찾는다.
부모 PID 가 1 이고 시작 시각이 이 세션보다 앞선 것이 그것이다. 그 프로세스와 부모 셸을 `kill` 하고 대기를 다시 건다.
다른 run 의 대기는 다른 세션의 것이므로 건드리지 않는다.

`You have N orchestration message` 알림은 heartbeat 일 때가 많다.
`check` 로 읽고 `--ack` 만 하고, 대기는 살아 있는 것을 그대로 둔다.

**heartbeat 가 오는데 커밋과 화면이 몇 분째 그대로면 `terminal read --screen` 으로 권한 확인 창을 본다.**
heartbeat 는 worker 가 멈춰 있어도 온다.
하위 에이전트가 `;` 로 이은 긴 셸을 쓰면 `Parse error` 로 자동 승인되지 않고 `Do you want to proceed?` 에서 기다린다.
명령이 무엇을 하는지 읽고, 영향이 worker 자신의 임시 디렉터리 안이면 승인하고 사용자에게 알린다. 아니면 사용자에게 묻는다.

**worker 의 워크트리에서 내가 파일을 고치지 않는다.**
worker 가 `git add -A` 를 하면 내 변경이 그쪽 커밋에 섞인다.
기다리는 동안 문서를 쓰려면 별도 워크트리를 만든다.
이미 고쳐 버렸으면 내용을 저장소 밖으로 복사하고 `git checkout -- <파일>` 로 되돌린 뒤,
worker 의 브랜치를 머지한 다음 main 에서 다시 적용한다.
