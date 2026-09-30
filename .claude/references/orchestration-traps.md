# worker 를 띄울 때 실측한 것

`orchestration` 으로 worker 를 띄우기 전에 읽는다.
오류 없이 잘못된 결과가 완료로 보고되는 자리와, 멈춘 원인이 바로 보이지 않는 자리만 적는다.
CLI 가 인자 오류로 거절하는 것은 적지 않는다. 거절 메시지가 이유를 알려준다.

## 띄우기

**worker 는 `--agent claude` 로 띄운다.** 사용자가 정한 기본값이다.
사용자가 다른 에이전트를 지정한 경우에만 바꾼다. 아래 codex 항목은 그때만 적용한다.

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

**`--worktree new-top-level` 은 대상 저장소 안에 워크트리를 만든다.**
Orca 1.4.215 에서 `worker-start --worktree new-top-level --name <name>` 이 `<repo>/worktrees/<repo>/<name>` 에 워크트리를 만들었다(2026-09-29 실측).
그 경로가 `.gitignore` 에 없어 main checkout 의 `git status` 에 `?? worktrees/` 로 나타났다.
이 상태에서 main 에서 `git add -A` 를 하면 워크트리가 저장소에 커밋될 수 있다.
워크트리를 지운 뒤에도 Orca 가 `worktrees/<repo>/.orca-worktree-trash` 를 남겼다.

띄운 직후 `git -C <repo> status --short` 로 확인한다.
`worktrees/` 가 보이면 공유되는 `.gitignore` 대신 로컬 전용인 `.git/info/exclude` 에 `/worktrees/` 를 추가한다.
`.orca-worktree-trash` 는 Orca 가 관리하므로 지우지 않는다.

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

**코디네이터 터미널은 run 하나에만 묶인다. 여러 worker 를 동시에 두면 한 run 에 띄운다.**
worker 가 살아 있는 run A 를 두고 `run-create` 로 run B 를 만들었다(2026-09-30 실측).
코디네이터가 B 에 묶이면서 A 의 `check` 와 `worker-start --run A` 가 `consumer_fenced` 로 거절됐다.
A 에 걸어 둔 백그라운드 `check --wait` 는 A 의 완료 메시지를 받아 오지 못했다.

새 worker 는 지금 묶인 run 에 띄운다. 어느 run 에 묶였는지는 `run-current` 로 확인한다.
이미 run 이 둘로 나뉘었으면 `orca orchestration run-use --id <run_id>` 로 옮겨 붙은 뒤 메시지를 읽는다.
`run-use` 는 `--run` 이 아니라 `--id` 를 받는다.
worker 상태만 볼 때는 fenced 상태여도 `worker-list --run <run_id>` 가 동작한다.

## 지시를 보낼 때

**긴 지시는 앞부분도 중간도 잘려 도착한다.**
잘렸다는 것은 worker 가 되물어야만 드러나고, 되묻지 않으면 받은 만큼만 하고 완료로 보고한다.

지시 본문은 scratchpad 파일로 쓰고, `--spec` 에는 그 경로와 「끝까지 읽고, 못 읽으면 escalation」 만 적는다.
후속 지시도 짧게 보내거나 새 파일로 준다.

**지시서의 Ownership 에 docs 수정 조건을 처음부터 넣는다.**
2026-09-30 fos-agents plan136 에서 지시서가 `docs/` 를 수정 범위에서 뺐다.
코디네이터가 구현 중에 계약을 바꾸자(PUT 응답에서 본문 제외) 그 계약이 docs 에 없게 됐다.
worker 의 docs-verifier 가 `UPDATE_NEEDED` 로 판정했고, worker 는 docs 를 고칠 때마다 `ask` 로 멈췄다.

Ownership 에 「구현이 docs 계약과 달라지면 같은 커밋에서 그 절을 고친다. 고치기 전에 ask 로 알린다」 를 넣는다.

**worker 가 critic 을 돌리는 절차면 계획서 결함에 대한 질문이 구현 전에 온다.**
2026-09-30 plan136 과 plan137 에서 두 번 모두 critic 이 `REVISE` 로 판정했다.
worker 는 지시대로 계획서를 고치지 않고 「구현에서 처리할 권장안」 을 `ask` 로 보냈다.

이 질문이 오면 권장안이 검사를 무력화하는지 먼저 본다.
실측한 권장안에 「금지 문자열 검사를 피하려고 문자열을 쪼개 붙인다」 가 있었다.
그런 안은 받지 않고 검사 범위를 고치게 한다.

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
