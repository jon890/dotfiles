# Orca orchestration 운영 절차

**목표: worker 가 보고한 완료가 실제로 끝난 작업이고, 끝난 뒤 워크트리와 대기 프로세스가 남지 않는다.**

명령 문법과 lifecycle 은 `orca skills get orchestration` 가이드가 소유한다.
이 문서는 그 가이드에 없는 우리 쪽 판단과, 각 단계에서 같은 실패를 피하는 규칙만 담는다.

## 언제 쓰나

| 상황 | 방식 |
| --- | --- |
| 현재 세션이 연 저장소가 아닌 곳의 파일을 고치고 커밋, 푸시해야 한다 | orchestration 으로 worker 를 띄운다 |
| 다른 저장소를 조회하거나 로그를 보거나 이미 있는 스크립트를 실행한다 | 현재 세션에서 직접 한다 |
| 현재 저장소 안의 독립적이고 큰 작업이다 | 하위 에이전트(`Agent`)를 쓴다 |
| 사용자가 감독 없이 작업을 통째로 넘기라고 했다 | `orca-cli` 로 handoff 한다 |

저장소마다 변경이 독립된 검토 단위로 남아야 한다.
한 세션이 여러 저장소의 브랜치를 쥐면 어느 변경이 어디에 얹혔는지 추적하기 어렵다.

**일을 여러 worker 로 나누면 worker 는 모두 코디네이터가 띄운다.** worker 는 다시 worker 를 띄우지 못한다.
worker 가 띄우면 `nested_worker_depth_exceeded` 로 거절되고, 새 run 을 만들어도 깊이는 초기화되지 않는다.
일을 나눠야 하면 worker 에게는 계획서 작성과 검토, worktree 준비까지만 맡긴다.
worker 는 소계획마다 `ready: <plan> <worktree 절대경로> <지시서 절대경로>` 를 status 메시지로 보내고, 코디네이터가 그 worktree 에 띄운다.

**PR 생성은 사용자가 미리 허락한 경우에만 worker 에게 맡긴다.**
허락받았으면 2단계 지시서에 「PR 생성은 승인돼 있다」 를 적는다. 허락받지 않았으면 worker 는 브랜치 push 까지만 하고, 코디네이터가 사용자에게 확인받은 뒤 PR 을 연다.
머지는 worker 에게 맡기지 않는다. 사용자가 머지까지 맡겼으면 코디네이터가 6단계 검증 뒤 7단계의 상태 확인을 거쳐 머지한다.
맡기지 않았으면 6단계 검증 뒤 사용자에게 확인받고 같은 상태 확인을 거쳐 머지한다.

## 단계

| 단계 | 이름 | 통과 조건 |
| --- | --- | --- |
| 1 | 에이전트 고르기 | 에이전트, 모델, effort 와 고른 이유가 dispatch 보고에 한 줄로 있다 |
| 2 | 지시서 쓰기 | 지시 본문이 파일에 있고 `--spec` 에는 그 경로만 있다 |
| 3 | 띄우기 | `worker-start` 가 종료 코드 0 으로 끝났고, `launch.effective` 가 고른 값과 같고, 대상 저장소 `git status` 에 `worktrees/` 가 없다 |
| 4 | 기다리기 | 이 세션의 백그라운드 `check --wait` 가 하나만 돌고, 앞 대기가 돌려준 `deliveryId` 를 `--ack` 로 넘겼다 |
| 5 | 답하고 지시 보내기 | 답과 지시를 worker 의 마지막 메시지에 `reply` 로 보냈고, 그 답이 검사를 무력화하지 않는다 |
| 6 | 완료 검증 | diff 를 직접 읽었고 검사를 다시 돌려 통과했다. 앞 PR 이 머지된 뒤라면 최신 base 와 합친 사본에서 통과했다 |
| 7 | 정리 | 머지와 삭제 직전에 `gh pr view --json state` 를 봤고, 끝난 dispatch 와 워크트리, 머지된 로컬 브랜치가 없다 |

각 단계에서 생기는 오류와 대응은 그 단계 절에 있다.

## 1. 에이전트 고르기

**모델과 effort 는 Task 마다 성능과 가격을 비교해 고르고, 고른 이유를 dispatch 보고에 한 줄로 남긴다.**
기본값을 두지 않는다. 사용자가 지정하면 그것을 따른다.

### 모델

계획서의 구체성과 필요한 탐색에 따라 고른다.
인증과 권한 작업도 계획서에 수정 위치와 검증 명령이 있으면 첫 행을 따른다.

| Task 성격 | 모델 | effort |
| --- | --- | --- |
| 계획서가 있고 수정 위치와 검증 명령이 정해진 구현 | `gpt-6.1-sol`, Claude Sonnet 5.5 | sol `low`, Sonnet `medium` |
| 단순 반영(리뷰 지적, 문구, 설정 한 줄) | `gpt-6-luna` | `high`(공식 시작점) |
| 계획은 있지만 저장소를 탐색해야 하는 여러 파일 구현 | `gpt-6.1-sol`, Claude Sonnet 5.5 | `medium`, 같은 Task 가 실패하면 `high` |
| 어려운 디버깅, 계약 설계, 데이터 마이그레이션 | Claude Opus 5.5, `gpt-6.1-sol` | Opus `medium` 시작, sol `high` |
| 리뷰와 검증 | 구현한 쪽과 다른 제공자의 모델 | `medium` |

비교 근거다(2026-10-01 공식 자료 조사. 값이 바뀌면 아래 출처에서 다시 확인한다).

| 모델 | 공식 권장 용도 | 공식 effort 시작점 | 입력 / 출력 ($/1M 토큰) | 상대 속도 |
| --- | --- | --- | --- | --- |
| `gpt-6.1-sol` | 복잡한 리팩터링, 코드베이스 조사, 장기 에이전트 | `medium`(기본) | 2 / 10 | Fast 2배(사용량 증가) |
| `gpt-6-luna` | 집중된 대량 작업, focused coding | `high` | 0.10 / 0.50 | Fast 1.5배 |
| `gpt-6-astra` | 가장 강한 능력이 필요할 때 | 확인 못 함 | 10 / 50 | Fast 2배 |
| Claude Sonnet 5.5 | 일상 코딩과 에이전트 | 잘 정의된 Task 는 `medium`, 어렵거나 긴 Task 는 `high`(기본) | 2 / 10 | Fast |
| Claude Opus 5.5 | 장시간 에이전트 코딩, 대규모 리팩터링 | `medium`(기본) | 4 / 20 | Moderate |
| Claude Fable 5.1 | Opus 5.5 의 `xhigh`, `max` 로도 부족한 추론 | `high` | 10 / 50 | Slower |
| Claude Haiku 4.5 | 실시간, 대량 처리, 서브에이전트 | 미지원 | 1 / 5 | Fastest |

- worker 가 시작 직후 출력 없이 실패하면 3단계의 [시작 직후 실패](#시작-직후-실패) 대로 다른 모델로 다시 띄운다
- `gpt-6-astra` 와 Claude Fable 5.1 은 다른 후보가 같은 Task 에서 실패했을 때만 검토한다
- 확인하지 못한 effort 별 코딩 점수는 선택 근거에서 뺐다. 제공자 사이의 점수도 직접 비교하지 않는다
- 공식 effort 별 지연과 비용 배수는 양쪽 모두 확인 못 함
- 출처: [sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [astra](https://developers.openai.com/api/docs/models/gpt-6-astra), [Codex 모델](https://learn.chatgpt.com/docs/models)
- 출처: [Claude effort](https://platform.claude.com/docs/en/build-with-claude/effort), [Claude 가격](https://platform.claude.com/docs/en/about-claude/pricing), [Claude 모델 선택](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)

### effort

**모델마다 공식 시작점이 다르다. 계획서가 있으면 위 표의 낮은 쪽에서 시작한다.**

| 단계 | 올리거나 내리는 조건 |
| --- | --- |
| `low` | 계획서에 수정 위치와 검증 명령이 정해진 sol 구현. Claude 에서는 속도와 가격이 중요한 단순 Task 와 서브에이전트 |
| `medium` | 지연, 성능, 비용의 균형점. 모델과 Task 에 따라 위 선택 표를 따른다 |
| `high` | 어려운 디버깅이나 깊은 계획. 같은 Task 가 `medium` 에서 실패했을 때 올린다 |
| `xhigh`, `max` | 기본으로 쓰지 않는다. 같은 Task 에서 `high` 보다 낫다는 결과가 있을 때만 |
| `ultra` | worker 에 쓰지 않는다. 스스로 subagent 를 띄워 코디네이터가 모르는 작업자가 생긴다 |

높은 effort 는 추가 작업과 비용을 늘릴 수 있다.

- Claude 의 `xhigh`, `max` 는 스스로 리뷰 라운드를 돌리고 reviewer subagent 를 띄워 비용이 커진다
- `high` 이상은 요청하지 않은 변경과 저장소 관례에 맞지 않는 커밋 제목을 낼 수 있다. 계획서가 충분하면 낮은 effort 로 빠르게 끝낸다
- 출처: [OpenAI reasoning](https://developers.openai.com/api/docs/guides/reasoning), [Claude effort](https://platform.claude.com/docs/en/build-with-claude/effort)

### Codex 에 넘기는 방법

`~/.codex/config.toml` 의 `model` 은 대화형 codex 의 기본값이라, 그대로 넘기면 모든 Task 가 같은 모델로 돈다.
`--model` 과 `--effort` 를 함께 넘긴다.
고를 수 있는 모델과 effort 목록은 아래 명령으로 본다.

```bash
codex debug models | python3 -c "import json,sys; d=json.load(sys.stdin); [print(m['slug'], '|', m['description'], '|', ','.join(l['effort'] for l in m['supported_reasoning_levels'])) for m in d['models'] if m.get('visibility')=='list']"
```

`~/.codex/models_cache.json` 은 읽지 않는다. 대화형 codex 를 띄울 때만 갱신돼 새 모델이 빠진다.
기본 service tier 가 `priority`(Fast)일 수 있고, Fast 는 사용량이 늘어난다. 실제 적용 값은 `worker-start` 응답의 `launch.effective` 로 확인한다.

## 2. 지시서 쓰기

**지시 본문은 scratchpad 파일에 쓰고, `--spec` 에는 그 경로와 「끝까지 읽고, 못 읽으면 escalation」 만 적는다.**
긴 지시는 앞부분도 중간도 잘려 도착한다.
worker 는 되묻지 않으면 받은 만큼만 하고 완료로 보고한다. 후속 지시도 짧게 보내거나 새 파일로 준다.

지시서에 넣을 것이다.

- 담당 범위, 기대하는 이득, 선행 결과, 결정하지 못한 사항
- effort 가 `low` 나 `medium` 이면 「끝까지 진행하고 판단만 ask 로 묻는다. 검증 명령을 실행한다」 를 넣는다. 낮은 effort 는 중간에 멈추거나 검증을 건너뛸 수 있다
- Ownership 에 「구현이 docs 계약과 달라지면 같은 커밋에서 그 절을 고친다. 고치기 전에 ask 로 알린다」.
  docs 를 범위에서 빼면 구현 중 계약이 바뀔 때마다 worker 가 docs-verifier 판정에 걸려 `ask` 로 멈춘다
- 승인이 필요한 작업이면 「발견 목록을 먼저 내고 멈춘다」.
  그 회신이 `worker_done` 으로 바로 오면 절차 위반으로 본다
- PR 을 열게 하면 「PR 생성은 승인돼 있다」 를 적는다.
  codex worker 의 기본 지침은 GitHub 게시를 막아, 지시서에 「PR 을 연다」 만 있으면 승인을 다시 묻는다
- PR 을 열게 하면 「PR 은 기준 브랜치를 base 로 따로 연다. 다른 PR 브랜치를 base 로 두지 않는다」 도 적는다.
  앞 PR 브랜치를 base 로 연 PR 은 앞 PR 을 `--delete-branch` 로 머지하면 자동으로 닫히거나 앞 브랜치로 머지된다
- 소계획으로 나누는 일을 맡기면 「worker 를 띄우지 않는다. 소계획마다 `ready:` status 메시지를 보낸다」 와 그 형식을 적는다.
  이유는 [언제 쓰나](#언제-쓰나)에 있다
- 「하위 에이전트는 orca 명령을 쓰지 않는다. 스폰 프롬프트에 이 줄을 넣는다」 와 「`worker_done` 은 완료 기준을 채운 뒤 본체가 한 번만 보낸다」.
  하위 에이전트는 worker 와 같은 터미널 핸들로 보내서, Orca 는 누가 보낸 `worker_done` 인지 구분하지 못한다.
  이 두 줄은 예방이고, 완료 판정은 6단계가 git 으로 한다

## 3. 띄우기

여러 worker 를 동시에 두면 **지금 묶인 run 하나에** 띄운다. 묶인 run 은 `run-current` 로 본다.
새 run 을 만들면 코디네이터가 그쪽으로 옮겨 묶이고, 이전 run 의 메시지를 받지 못한다.
`check` 나 `worker-start --run` 이 `consumer_fenced` 로 거절되면 코디네이터가 다른 run 에 묶인 것이다.
`orca orchestration run-use --id <run_id>` 로 옮겨 붙은 뒤 메시지를 읽는다.
상태만 볼 때는 fenced 상태에서도 `worker-list --run <run_id>` 가 동작한다.

**`--base-branch` 에는 `origin/main` 을 준다.** `main` 을 주면 대상 저장소의 로컬 main 을 기준으로 워크트리를 만든다.
로컬 main 이 뒤처져 있어도 오류 없이 만들어져, worker 가 옛 코드 위에서 계획하고 구현한다.
띄우기 전에 `git -C <repo> fetch origin` 으로 원격을 갱신하고, main 이 깨끗하면 `git -C <repo> merge --ff-only origin/main` 으로 로컬 main 도 맞춘다.

codex 를 띄우기 전에 [codex 준비 판정](#codex-준비-판정)의 설정이 있는지 본다.

**`--spec` 에는 지시서 경로를 담은 한 줄만 준다.** 새 worktree 를 만들 때는 `--name` 이 필수다.
`$SPEC_FILE` 은 2단계의 지시서 경로, `$NAME` 은 새 worktree 이름, `$REPO` 는 대상 저장소 경로다.

```bash
SPEC_LINE="지시서 $SPEC_FILE 를 끝까지 읽고 수행한다. 못 읽으면 escalation 으로 알린다."
orca orchestration worker-start --run "$RUN_ID" --spec "$SPEC_LINE" \
  --worktree new-top-level --name "$NAME" --repo "path:$REPO" --base-branch origin/main \
  --agent codex --model gpt-6.1-sol --effort low --json
```

이미 있는 worktree 에 띄울 때는 `--worktree path:` 만 준다. 5단계의 후속 일과 worker 가 보낸 `ready:` 가 여기 해당한다.
`--name`, `--repo`, `--base-branch` 는 이때 주지 않는다.

```bash
orca orchestration worker-start --run "$RUN_ID" --spec "$SPEC_LINE" --worktree "path:$WORKTREE" \
  --agent claude --model claude-sonnet-5-5 --effort medium --json
```

띄운 직후 두 가지를 확인한다.

- `worker-start` 응답의 `launch.effective` 가 1단계에서 고른 모델, effort 와 같다
- `git -C <repo> status --short` 에 `worktrees/` 가 없다

`--worktree new-top-level` 은 `<repo>/worktrees/<repo>/<name>` 에 워크트리를 만든다.
그 경로가 ignore 되지 않아, main 에서 `git add -A` 를 하면 워크트리가 커밋될 수 있다.
`worktrees/` 가 보이면 로컬 전용인 `.git/info/exclude` 에 `/worktrees/` 를 추가한다. 공유되는 `.gitignore` 는 고치지 않는다.
Orca 가 남기는 `.orca-worktree-trash` 는 Orca 가 관리하므로 지우지 않는다.

`worker-start` 가 0 이 아닌 코드로 끝나면 새로 띄우지 않고 아래 절에서 원인을 찾는다.

### codex 준비 판정

Orca 가 계정별로 두는 `~/Library/Application Support/orca/codex-accounts/*/home/config.toml` 에 아래 두 키를 둔다.
`check_for_update_on_startup` 은 첫 절 머리 앞의 최상위 키이고, `terminal_title` 은 `[tui]` 절의 키다.

```toml
check_for_update_on_startup = false

[tui]
terminal_title = ["app-name", "run-state", "project-name"]
```

이 설정이 없으면 codex 가 떠 있어도 터미널 제목에 `Codex` 와 `ready` 가 함께 나오지 않아 `agent_readiness` 에서 실패한다.
둘째 줄은 시작할 때 업데이트 안내로 빠지지 않게 한다.

### 첫 화면에서 멈춤

원인은 `worker-show --dispatch <id>` 의 `lastFailure` 에 나온다.
알려진 원인은 claude 의 폴더 신뢰 확인, codex 의 업데이트 안내(`agent-update-prompt`)와 hook 신뢰 확인(`agent-hooks-review-prompt`)이다.

터미널과 워크트리는 이미 만들어져 있으므로 새로 띄우지 않고 이어 붙인다.

1. `terminal read` 로 화면을 본다. 신뢰나 업데이트를 대신 승인하지 않는다.
   건너뛰는 선택지를 고르고 사용자에게 알린다
2. `terminal wait --for tui-idle` 로 입력 대기 상태를 확인한다
3. `worker-start --task <task_id> --retry-of <dispatch_id> --terminal <handle> --worktree id:<worktree_id>` 로 붙인다.
   `--model` 은 줄 수 없지만 처음 띄울 때 준 모델이 그 터미널에 남아 있다

### 시작 직후 실패

worker 가 `stage.detail: agent_readiness`, `outcome: failed` 로 아무 출력 없이 끝나면, codex 는 먼저 [codex 준비 판정](#codex-준비-판정)의 설정을 본다.
설정이 있는데도 실패하면 그 모델이 이 환경에서 뜨지 않는 것이므로 같은 Task 를 다른 모델로 다시 띄운다. `--retry-of` 는 `--spec` 이 아니라 `--task` 와 함께 쓴다.

```bash
orca orchestration worker-start --task "$TASK_ID" --retry-of "$DISPATCH_ID" --agent codex --model gpt-6.1-sol --effort low --worktree "path:$WORKTREE"
```

`$WORKTREE` 는 처음 띄운 워크트리 경로다.

## 4. 기다리기

**`check --wait` 는 하네스의 백그라운드 실행 기능으로 하나만 건다.**
앞에서 돌리면 그동안 코디네이터가 막힌다.
셸의 `&` 로 띄우면 끝나도 완료 알림이 오지 않고 고아 프로세스가 남는다.
둘째 대기는 `waiter_exists` 로 바로 끝나고 거기 붙인 `--ack` 만 처리된다.

**대기 시간은 하네스의 명령 한도보다 짧게 준다.**
Claude Code 의 백그라운드 Bash 는 따로 정하지 않으면 30분 뒤 멈춘다.
Bash 도구의 `timeout` 을 최대인 7200000 으로 주고 `--timeout-ms` 는 그보다 작은 7000000 으로 준다.

**처리한 delivery 는 다음 대기의 `--ack` 로 넘긴다.**
묶인 run 은 ack 하기 전까지 같은 delivery 를 다시 준다.
앞 대기가 돌려준 `result.deliveryId` 를 `$DELIVERY_ID` 에 넣는다. 첫 대기처럼 넘길 delivery 가 없으면 `--ack "$DELIVERY_ID"` 를 통째로 뺀다.

keepalive 줄은 15초마다 stderr 로 나와 출력 파일에 섞인다. 그 줄을 빼고 받는다. 이때 파이프의 종료 코드는 `grep` 의 것이라, 대기 결과는 JSON 의 `timedOut` 과 `messages` 로 판단한다.
worker 가 `ready:` 같은 status 메시지를 보내기로 했으면 `--types` 에 `status` 를 더한다. `--types` 는 깨어나는 조건이다.

```bash
orca orchestration check --run "$RUN_ID" --ack "$DELIVERY_ID" --wait --types "worker_done,escalation,question" --timeout-ms 7000000 --json 2>&1 | grep -v _keepalive
```

대기는 `--timeout-ms` 가 지나면 메시지 없이 `timedOut: true` 로 끝난다. 실패가 아니므로 다시 건다.

백그라운드 대기가 종료 코드 144 로 끝난 것처럼 보여도 Orca CLI 프로세스가 살아 있을 수 있다.
그 프로세스가 대기 자리를 쥐고 있으면 새로 건 대기가 `waiter_exists` 로 바로 끝난다.
찾아서 종료한 뒤 다시 건다. 이 세션이 건 프로세스이므로 다른 run 의 것과 구분해서 종료한다.
세션을 다시 띄운 뒤 첫 대기가 `waiter_exists` 면 [이전 세션의 대기](#이전-세션의-대기)를 따른다.

```bash
ps -eo pid,command | grep "orchestration check --wait" | grep -v grep
```

Orca runtime 이 잠시 끊기면 `runtime_unavailable` 로 끝나기도 한다. `orca status` 로 살아 있는지 확인한 뒤 다시 건다.

`You have N orchestration message` 알림은 대개 heartbeat 다.
살아 있는 대기는 그대로 두고, 그 대기가 heartbeat 만 든 delivery 를 돌려주면 다음 대기의 `--ack` 로 넘긴다.
heartbeat 는 worker 가 멈춰 있어도 오므로, 진행은 커밋과 화면으로 판단한다.
heartbeat 는 오는데 커밋과 화면이 몇 분째 그대로면 `terminal read --screen` 으로 화면을 보고 아래를 따른다.

- 하위 에이전트가 `Do you want to proceed?` 에서 기다린다: [권한 확인 창](#권한-확인-창)
- codex 화면에 `Usage limit reached` 가 떠 있다: [사용량 한도로 멈춤](#사용량-한도로-멈춤)

heartbeat 의 `payload.phase` 는 worker 가 스스로 적는 값이다.
`waiting` 은 worker 가 백그라운드로 돌린 검사가 끝나기를 기다린다는 뜻으로도 쓰인다.
이때 worker 의 턴은 끝나 화면이 입력 대기로 보이고 커밋도 늘지 않아 멈춘 것과 구분되지 않는다.
`worker-read --dispatch <id>` 의 마지막 메시지와, 검사 프로세스가 `ps` 에 살아 있는지로 판단한다.

기다리는 동안 worker 의 워크트리에서 파일을 고치지 않는다.
worker 가 `git add -A` 를 하면 내 변경이 그쪽 커밋에 섞인다. 문서를 쓰려면 별도 워크트리를 만든다.
이미 고쳤으면 [worker 워크트리를 고침](#worker-워크트리를-고침)을 따른다.

### 이전 세션의 대기

이전 세션의 백그라운드 `check --wait` 는 세션이 끝나도 부모 없는 프로세스로 남는다.
그 대기가 받은 메시지는 아무에게도 전달되지 않는다.

```bash
ps -ax -o pid,ppid,lstart,command | grep "orchestration check" | grep "$RUN_ID"
```

부모 PID 가 1 이고 시작 시각이 이 세션보다 앞선 것이 그것이다.
그 프로세스와 부모 셸을 `kill` 하고 대기를 다시 건다.
다른 run 의 대기는 다른 세션의 것이므로 건드리지 않는다.

### worker 워크트리를 고침

1. 고친 내용을 저장소 밖으로 복사한다
2. `git checkout -- <파일>` 로 되돌린다
3. worker 의 브랜치를 머지한 다음 main 에서 다시 적용한다

### 권한 확인 창

`terminal read --screen` 으로 화면을 본다.
하위 에이전트가 `;` 로 이은 긴 셸을 쓰면 `Parse error` 로 자동 승인되지 않고 `Do you want to proceed?` 에서 기다린다.
명령이 무엇을 하는지 읽고, 영향이 worker 자신의 임시 디렉터리 안이면 승인하고 사용자에게 알린다. 아니면 사용자에게 묻는다.

### 사용량 한도로 멈춤

heartbeat 와 liveness 는 `live` 로 남아 대기만으로는 알 수 없다. `terminal read --screen` 으로 화면을 본다.
한도 안내가 떠 있으면 그 worker 는 더 진행하지 않는다는 근거다.

`worker-stop` 은 터미널이 `user_owned` 이면 `stop_unknown` 으로 끝나고, 이 상태의 Task 에 `--retry-of` 를 주면 `task_not_startable` 로 거절된다.
`worker-abandon` 으로 dispatch 를 닫은 뒤 다른 제공자로 다시 띄운다. 워크트리는 그대로 이어 쓴다.

```bash
orca orchestration worker-abandon --dispatch "$DISPATCH_ID" --json
orca orchestration worker-start --task "$TASK_ID" --retry-of "$DISPATCH_ID" --worktree "id:$WORKTREE_ID" --agent claude --model claude-sonnet-5-5 --effort medium --json
```

## 5. 답하고 지시 보내기

**worker 에게 보내는 답과 후속 지시는 그 worker 가 보낸 마지막 메시지에 `reply` 로 단다.**

```bash
orca orchestration reply --id "$MSG_ID" --body "$BODY" --json
```

`send --to dispatch:<id>` 는 worker 가 하위 run 을 만든 뒤에는 `recipient_run_mismatch`, 끝난 dispatch 에는 `dispatch_inactive` 로 거절된다.
같은 worker 의 마지막 메시지에 단 `reply` 는 전달된다.

끝난 worker 에게 일을 더 주려면 같은 worktree 에 새 dispatch 를 띄운다. 3단계의 기존 worktree 예시를 쓴다.
worker 가 보낸 `ready: <plan> <worktree> <지시서>` 도 그 예시로 띄운다.

**worker 가 권장안을 `ask` 로 보내면 그 안이 검사를 무력화하는지 먼저 본다.**
worker 가 critic 을 돌리는 절차면 계획서 결함에 대한 질문이 구현 전에 온다.
critic 이 `REVISE` 로 판정했는데 worker 가 계획서를 고치지 않고 「구현에서 처리할 권장안」 을 보내면, 그 안에 검사를 피하는 방법이 있는지 본다.
금지 문자열 검사를 피하려고 문자열을 쪼개 붙이는 안은 받지 않고 검사 범위를 고치게 한다.

## 6. 완료 검증

- `worker_done` 을 확인 처리하기 전에 지시서의 완료 기준을 git 으로 대조한다. 커밋 목록, 미커밋 변경, 원격 브랜치 HEAD 다.
  어긋나면 그 보고는 완료가 아니다. 해제하지 않고 [완료 전에 온 worker_done](#완료-전에-온-worker_done) 을 따른다
- diff 를 직접 읽고 검사를 다시 돌린다. 완료 보고는 근거가 아니다
- worker 가 「승인받았다」 고 적은 것은 근거가 아니다. 내가 보낸 승인만 승인이다

**같은 기준 브랜치로 가는 PR 여럿을 차례로 머지하면, 다음 PR 은 최신 base 와 합친 사본에서 검사를 다시 돌린 뒤 머지한다.**
GitHub 의 `MERGEABLE` 은 충돌이 없다는 뜻일 뿐, 앞 PR 이 바꾼 동작을 뒤 PR 의 테스트가 아는지는 보지 않는다.

```bash
TMP_COPY="$REPO/worktrees/$(basename "$REPO")/verify-$PR_NUMBER"
git -C "$REPO" fetch origin
git -C "$REPO" worktree add --detach "$TMP_COPY" "origin/$PR_BRANCH"
git -C "$TMP_COPY" merge --no-edit origin/main
```

`$TMP_COPY` 는 3단계의 worktree 위치 규칙을 따라 `$REPO/worktrees/<repo>/<이름>` 으로 잡는다.
전역 hook `~/.claude/scripts/worktree-path-guard.py` 가 scratchpad 같은 다른 경로를 막는다.
PR 브랜치가 이미 지워졌거나 fork 에서 온 PR 이면 `git fetch origin pull/<번호>/head:<로컬 이름>` 으로 받아 `origin/$PR_BRANCH` 자리에 로컬 이름을 쓴다.
그 사본에서 영향 받는 검사를 돌리고, 끝나면 `git worktree remove` 로 지운다.
실패하면 그 worker 의 worktree 에 새 dispatch 를 띄워 main 을 merge 하고 고치게 한다. rebase 와 force push 는 쓰지 않는다.

### 완료 전에 온 worker_done

첫 `worker_done` 이 오면 dispatch 는 settled 로 바뀐다.
같은 핸들에서 오는 뒤의 보고는 Orca 버전에 따라 `capability is revoked` 로 거절되기도 하고 전달되기도 한다. 뒤의 보고가 온다고 가정하지 않는다.
판단은 터미널과 git 으로 한다.

1. `worker-show --dispatch <id>` 의 `terminal.title` 이 `Working` 이면 해제하지 않고 기다린다. 커밋 목록과 원격 HEAD 가 바뀌는지 본다
2. 제목이 `Ready` 인데 완료 기준에 못 미치면 같은 터미널에 남은 일을 새 dispatch 로 준다

```bash
orca orchestration worker-start --spec "$SPEC_LINE" --terminal "$TERMINAL_HANDLE" --worktree "path:$WORKTREE"
```

`$SPEC_LINE` 은 남은 일만 적은 지시서의 경로를 담은 한 줄이다. 형식은 3단계 예시와 같다.

## 7. 정리

작업이 끝날 때마다 정리한다.
워크트리와 터미널이 저장소마다 쌓이면 다음 작업이 어느 것을 써야 할지 매번 판단해야 한다.

**PR 을 머지한 직후 같은 흐름에서, 사용자 지시를 기다리지 않고 정리한다.**
그 PR 의 dispatch 반납, 워커 터미널 닫기, 워크트리 제거, 로컬과 원격 브랜치 삭제까지가 머지의 마지막 단계다.
같은 워크트리에서 후속 작업을 하는 워커가 있으면 그 워커가 끝날 때까지 남긴다.

- settled 된 dispatch 를 정리한다. 정리 경로와 잔여 확인 방법은 Orca 가이드를 따른다
- 작업이 끝난 워크트리를 제거한다. `orca worktree rm` 뒤에 `git -C <repo> worktree prune` 을 돌린다.
  디렉터리만 지우고 git 의 워크트리 기록이 남아, 그대로면 브랜치 삭제가 `used by worktree` 로 거절된다
- base 에 머지된 로컬 브랜치를 지운다

**머지 직전과 지우기 직전에 `gh pr view --json state` 를 본다.** 머지는 `OPEN` 일 때만 하고, 브랜치와 워크트리는 `MERGED` 일 때만 지운다.
`gh pr merge` 는 미해결 리뷰 스레드 때문에 거절될 수 있고, 결과를 보지 않고 브랜치를 지우면 PR 이 닫힌다.
다른 세션이나 사용자가 같은 PR 을 먼저 머지하기도 한다.

```bash
gh pr view "$PR" --json state --jq .state
```

남기는 것이다.

- PR 이 열려 있는 워크트리. 리뷰 반영에 필요하고, 머지된 뒤에 지운다
- `release/*` 브랜치. 머지 여부와 무관하게 릴리스 이력이다

지우기 전에 미커밋 변경과 stash 를 확인한다. `.omc/` 처럼 추적되지 않는 디렉터리만 남은 것은 지워도 된다.

## 이 문서에 더할 때

- 규칙으로 일반화해 그 일이 일어나는 단계 절에 넣는다. 사례를 쌓지 않는다
- 규칙에는 이유를 한 줄 붙인다. 처음 따라 하는 세션이 그 단계에서 같은 실패를 피하게 쓴다
- 사례가 이유를 이해하는 데 꼭 필요하면 저장소 이름과 날짜 없이 한 줄만 둔다
- CLI 가 인자 오류로 거절하는 것은 적지 않는다. 거절 메시지가 이유를 알려준다
- 회복 절차가 길면 그 단계 절 아래 `###` 절로 둔다
