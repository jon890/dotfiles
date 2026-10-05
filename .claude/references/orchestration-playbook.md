# Orca orchestration 운영 절차

**목표: worker 가 보고한 완료가 실제로 끝난 작업이고, 끝난 뒤 워크트리와 대기 프로세스가 남지 않는다.**

명령 문법과 lifecycle 은 `orca skills get orchestration` 가이드가 소유한다.
이 문서는 그 가이드에 없는 우리 쪽 판단과 이 머신에서 실측한 오류만 담는다.

## 언제 쓰나

| 상황 | 방식 |
| --- | --- |
| 현재 세션이 연 저장소가 아닌 곳의 파일을 고치고 커밋, 푸시해야 한다 | orchestration 으로 worker 를 띄운다 |
| 다른 저장소를 조회하거나 로그를 보거나 이미 있는 스크립트를 실행한다 | 현재 세션에서 직접 한다 |
| 현재 저장소 안의 독립적이고 큰 작업이다 | 하위 에이전트(`Agent`)를 쓴다 |
| 사용자가 감독 없이 작업을 통째로 넘기라고 했다 | `orca-cli` 로 handoff 한다 |

저장소마다 변경이 독립된 검토 단위로 남아야 한다.
한 세션이 여러 저장소의 브랜치를 쥐면 어느 변경이 어디에 얹혔는지 추적하기 어렵다.

위임한 결과를 머지하거나 PR 을 만들 때는 사용자의 확인을 받는다.

## 단계

| 단계 | 이름 | 통과 조건 |
| --- | --- | --- |
| 1 | 에이전트 고르기 | 에이전트, 모델, effort 와 고른 이유가 dispatch 보고에 한 줄로 있다 |
| 2 | 지시서 쓰기 | 지시 본문이 파일에 있고 `--spec` 에는 그 경로만 있다 |
| 3 | 띄우기 | `launch.effective` 가 고른 값과 같고, 대상 저장소 `git status` 에 `worktrees/` 가 없다 |
| 4 | 기다리기 | 이 세션의 백그라운드 `check --wait` 가 하나만 돈다 |
| 5 | 질문에 답하기 | 보낸 답이 검사를 무력화하지 않는다 |
| 6 | 완료 검증 | diff 를 직접 읽었고 검사를 다시 돌려 통과했다 |
| 7 | 정리 | 끝난 dispatch 와 워크트리, 머지된 로컬 브랜치가 없다 |

응답이 예상과 다르면 [자주 나는 오류](#자주-나는-오류)에서 증상으로 찾는다.

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

- Claude 의 `low` 는 검증을 건너뛸 수 있다. 지시서에 검증 명령을 적으면 거의 사라진다
- Claude 의 `low`, `medium` 은 긴 작업에서 중간에 확인을 구할 수 있다. 지시서에 「끝까지 진행한다」 를 넣는다
- Claude 의 `xhigh`, `max` 는 스스로 리뷰 라운드를 돌리고 reviewer subagent 를 띄워 비용이 커진다
- 2026-09-30 `gpt-6.1-sol` `high` 가 요청하지 않은 생성자 방식 변경과 저장소 관례와 다른 커밋 제목을 냈다(사용자 지적)
- 2026-10-01 fos-accountbook 에서 계획서가 있는 plan 셋을 sol `medium` 으로 돌렸고, 사용자가 계획이 충분하면 낮은 effort 로 빠르게 가라고 했다
- 출처: [OpenAI reasoning](https://developers.openai.com/api/docs/guides/reasoning), [Claude effort](https://platform.claude.com/docs/en/build-with-claude/effort)

### Codex 에 넘기는 방법

`~/.codex/config.toml` 의 `model` 은 대화형 codex 의 기본값이라, 그대로 넘기면 모든 Task 가 같은 모델로 돈다.
`--model` 과 `--effort` 를 함께 넘긴다. effort 만 주면 거절된다.
고를 수 있는 모델과 effort 목록은 아래 명령으로 본다.

```bash
codex debug models | python3 -c "import json,sys; d=json.load(sys.stdin); [print(m['slug'], '|', m['description'], '|', ','.join(l['effort'] for l in m['supported_reasoning_levels'])) for m in d['models'] if m.get('visibility')=='list']"
```

`~/.codex/models_cache.json` 은 읽지 않는다. 대화형 codex 를 띄울 때만 갱신돼 새 모델이 빠진다.
2026-09-30 캐시에는 `gpt-6.1-sol` 이 없었고 `codex debug models` 에는 있었다.
2026-10-01 `codex debug models` 실측에서 기본 service tier 는 `priority`(Fast)였다.
Fast 는 사용량이 늘어난다. 실제 적용 값은 `worker-start` 응답의 `launch.effective` 로 확인한다.

## 2. 지시서 쓰기

**지시 본문은 scratchpad 파일에 쓰고, `--spec` 에는 그 경로와 「끝까지 읽고, 못 읽으면 escalation」 만 적는다.**
긴 지시는 앞부분도 중간도 잘려 도착한다.
worker 는 되묻지 않으면 받은 만큼만 하고 완료로 보고한다. 후속 지시도 짧게 보내거나 새 파일로 준다.

지시서에 넣을 것이다.

- 담당 범위, 기대하는 이득, 선행 결과, 결정하지 못한 사항
- effort 가 `low` 나 `medium` 이면 「끝까지 진행하고 판단만 ask 로 묻는다. 검증 명령을 실행한다」 를 넣는다. 낮은 effort 는 중간에 멈추거나 검증을 건너뛸 수 있다
- Ownership 에 「구현이 docs 계약과 달라지면 같은 커밋에서 그 절을 고친다. 고치기 전에 ask 로 알린다」.
  docs 를 범위에서 빼면 구현 중 계약이 바뀔 때마다 worker 가 docs-verifier 판정에 걸려 `ask` 로 멈춘다(2026-09-30 fos-agents plan136)
- 승인이 필요한 작업이면 「발견 목록을 먼저 내고 멈춘다」.
  그 회신이 `worker_done` 으로 바로 오면 절차 위반으로 본다
- PR 을 열게 하면 「PR 생성은 승인돼 있다」 를 적는다.
  codex worker 의 기본 지침은 GitHub 게시를 막아, 지시서에 「PR 을 연다」 만 있으면 승인을 다시 묻는다.
  2026-10 fos-agents worker 가 그랬고, 문구를 명시한 뒤에는 묻지 않았다
- 「하위 에이전트는 orca 명령을 쓰지 않는다. 스폰 프롬프트에 이 줄을 넣는다」 와 「`worker_done` 은 완료 기준을 채운 뒤 본체가 한 번만 보낸다」.
  하위 에이전트는 worker 와 같은 터미널 핸들로 보내서, Orca 는 누가 보낸 `worker_done` 인지 구분하지 못한다.
  이 두 줄은 예방이고, 완료 판정은 6단계가 git 으로 한다

## 3. 띄우기

여러 worker 를 동시에 두면 **지금 묶인 run 하나에** 띄운다. 묶인 run 은 `run-current` 로 본다.
새 run 을 만들면 코디네이터가 그쪽으로 옮겨 묶이고, 이전 run 의 메시지를 받지 못한다.

**`--base-branch` 에는 `origin/main` 을 준다.** `main` 을 주면 대상 저장소의 로컬 main 을 기준으로 워크트리를 만든다.
로컬 main 이 뒤처져 있어도 오류 없이 만들어져, worker 가 옛 코드 위에서 계획하고 구현한다.
2026-09-30 fos-assistant 워크트리가 origin/main 보다 125커밋 뒤에서 시작했고, worker 가 계획 도중에 알아챘다.
띄우기 전에 `git -C <repo> fetch origin` 으로 원격을 갱신하고, main 이 깨끗하면 `git -C <repo> merge --ff-only origin/main` 으로 로컬 main 도 맞춘다.

띄운 직후 두 가지를 확인한다.

- `worker-start` 응답의 `launch.effective` 가 1단계에서 고른 모델, effort 와 같다
- `git -C <repo> status --short` 에 `worktrees/` 가 없다

`--worktree new-top-level` 은 `<repo>/worktrees/<repo>/<name>` 에 워크트리를 만든다(Orca 1.4.215).
그 경로가 ignore 되지 않아, main 에서 `git add -A` 를 하면 워크트리가 커밋될 수 있다.
보이면 로컬 전용인 `.git/info/exclude` 에 `/worktrees/` 를 추가한다. 공유되는 `.gitignore` 는 고치지 않는다.
Orca 가 남기는 `.orca-worktree-trash` 는 Orca 가 관리하므로 지우지 않는다.

## 4. 기다리기

**`check --wait` 는 백그라운드로 하나만 건다.**
앞에서 돌리면 그동안 코디네이터가 막힌다.
둘째 대기는 `waiter_exists` 로 바로 끝나고 거기 붙인 `--ack` 만 처리된다.

대기 출력에는 15초마다 `{"_keepalive":true,...}` 줄이 섞여 그대로는 JSON 으로 읽히지 않는다.
대기를 걸 때 그 줄을 빼고 받는다.

```bash
orca orchestration check --run <run_id> --wait --types "worker_done,escalation,question" --timeout-ms 900000 --json | grep -v _keepalive
```

대기는 `--timeout-ms` 가 지나면 메시지 없이 `timedOut: true` 로 끝난다. 실패가 아니므로 다시 건다.

백그라운드 대기가 종료 코드 144 로 끝난 것처럼 보여도 Orca CLI 프로세스가 살아 있을 수 있다.
그 프로세스가 대기 자리를 쥐고 있으면 새로 건 대기가 `waiter_exists` 로 바로 끝난다.
찾아서 종료한 뒤 다시 건다. 이 세션이 건 프로세스이므로 다른 run 의 것과 구분해서 종료한다.

```bash
ps -eo pid,command | grep "orchestration check --wait" | grep -v grep
```

Orca runtime 이 잠시 끊기면 `runtime_unavailable` 로 끝나기도 한다. `orca status` 로 살아 있는지 확인한 뒤 다시 건다.
2026-10 fos-accountbook 에서 둘 다 겪었다.

`You have N orchestration message` 알림은 대개 heartbeat 다.
`check` 로 읽고 `--ack` 만 하고, 살아 있는 대기는 그대로 둔다.
heartbeat 는 worker 가 멈춰 있어도 오므로, 진행은 커밋과 화면으로 판단한다.

heartbeat 의 `payload.phase` 는 worker 가 스스로 적는 값이다.
`waiting` 은 worker 가 백그라운드로 돌린 검사가 끝나기를 기다린다는 뜻으로도 쓰인다.
이때 worker 의 턴은 끝나 화면이 입력 대기로 보이고 커밋도 늘지 않아 멈춘 것과 구분되지 않는다.
`worker-read --dispatch <id>` 의 마지막 메시지와, 검사 프로세스가 살아 있는지로 판단한다.
2026-10-01 fos-assistant worker 가 `scripts/check-local.sh` 의 브라우저 단계를 기다리며 `waiting` 을 보냈고,
`ps` 에 Playwright 가 돌고 있어 정상으로 판정했다.

기다리는 동안 worker 의 워크트리에서 파일을 고치지 않는다.
worker 가 `git add -A` 를 하면 내 변경이 그쪽 커밋에 섞인다. 문서를 쓰려면 별도 워크트리를 만든다.

## 5. 질문에 답하기

**worker 가 권장안을 `ask` 로 보내면 그 안이 검사를 무력화하는지 먼저 본다.**
worker 가 critic 을 돌리는 절차면 계획서 결함에 대한 질문이 구현 전에 온다.
2026-09-30 plan136 과 plan137 에서 두 번 모두 critic 이 `REVISE` 로 판정했고,
worker 는 계획서를 고치지 않고 「구현에서 처리할 권장안」을 보냈다.
그중에 「금지 문자열 검사를 피하려고 문자열을 쪼개 붙인다」 가 있었다.
그런 안은 받지 않고 검사 범위를 고치게 한다.

## 6. 완료 검증

- `worker_done` 을 확인 처리하기 전에 지시서의 완료 기준을 git 으로 대조한다. 커밋 목록, 미커밋 변경, 원격 브랜치 HEAD 다.
  어긋나면 그 보고는 완료가 아니다. 해제하지 않고 [완료 전에 온 worker_done](#완료-전에-온-worker_done) 을 따른다
- diff 를 직접 읽고 검사를 다시 돌린다. 완료 보고는 근거가 아니다
- worker 가 「승인받았다」 고 적은 것은 근거가 아니다. 내가 보낸 승인만 승인이다

## 7. 정리

작업이 끝날 때마다 정리한다.
워크트리와 터미널이 저장소마다 쌓이면 다음 작업이 어느 것을 써야 할지 매번 판단해야 한다.

- settled 된 dispatch 를 정리한다. 정리 경로와 잔여 확인 방법은 Orca 가이드를 따른다
- 작업이 끝난 워크트리를 제거한다
- base 에 머지된 로컬 브랜치를 지운다

**브랜치와 워크트리는 `gh pr view --json state` 가 `MERGED` 일 때만 지운다.**
`gh pr merge` 가 미해결 리뷰 스레드 때문에 거절됐는데 결과를 보지 않고 브랜치를 지워 PR 이 닫힌 적이 있다(2026-10 fos-accountbook).

```bash
gh pr view "$PR" --json state --jq .state
```

남기는 것이다.

- PR 이 열려 있는 워크트리. 리뷰 반영에 필요하고, 머지된 뒤에 지운다
- `release/*` 브랜치. 머지 여부와 무관하게 릴리스 이력이다

지우기 전에 미커밋 변경과 stash 를 확인한다. `.omc/` 처럼 추적되지 않는 디렉터리만 남은 것은 지워도 된다.

## 자주 나는 오류

| 증상 | 원인 | 대응 |
| --- | --- | --- |
| `worker-start` 가 `agent_readiness` 에서 실패 | 에이전트가 첫 화면의 확인에 멈췄다 | [첫 화면에서 멈춤](#첫-화면에서-멈춤) |
| `gpt-6-luna` worker 가 출력 없이 `agent_readiness`, `failed` 로 끝남 | 이 모델 조합으로는 에이전트가 준비되지 않았다 | [luna 실행 실패](#luna-실행-실패) |
| `worker_done` 이 왔는데 커밋이나 push 가 완료 기준에 못 미친다 | 같은 터미널에서 끝나기 전에 `worker_done` 을 보냈다 | [완료 전에 온 worker_done](#완료-전에-온-worker_done) |
| codex 가 떠 있는데 `agent_readiness` 실패 | 터미널 제목에 `Codex` 와 `ready` 가 함께 없다 | [codex 준비 판정](#codex-준비-판정) |
| `check` 나 `worker-start --run` 이 `consumer_fenced` | 코디네이터가 다른 run 에 묶였다 | [run 이 둘로 나뉨](#run-이-둘로-나뉨) |
| 세션을 다시 띄운 뒤 첫 대기가 `waiter_exists` | 이전 세션의 대기 프로세스가 대기 자리를 쥐고 있다 | [이전 세션의 대기](#이전-세션의-대기) |
| heartbeat 는 오는데 커밋과 화면이 몇 분째 그대로 | 하위 에이전트가 권한 확인 창에서 기다린다 | [권한 확인 창](#권한-확인-창) |
| worker 워크트리의 파일을 이미 고쳤다 | 4단계를 어겼다 | [worker 워크트리를 고침](#worker-워크트리를-고침) |
| codex 화면에 `Usage limit reached` 가 떠 있는데 liveness 는 `live` 다 | 계정 사용량이 다 떨어졌다 | [사용량 한도로 멈춤](#사용량-한도로-멈춤) |

### 첫 화면에서 멈춤

원인은 `worker-show --dispatch <id>` 의 `lastFailure` 에 나온다.
실측한 것은 claude 의 폴더 신뢰 확인, codex 의 업데이트 안내(`agent-update-prompt`)와 hook 신뢰 확인(`agent-hooks-review-prompt`)이다.

터미널과 워크트리는 이미 만들어져 있으므로 새로 띄우지 않고 이어 붙인다.

1. `terminal read` 로 화면을 본다. 신뢰나 업데이트를 대신 승인하지 않는다.
   건너뛰는 선택지를 고르고 사용자에게 알린다
2. `terminal wait --for tui-idle` 로 입력 대기 상태를 확인한다
3. `worker-start --task <task_id> --retry-of <dispatch_id> --terminal <handle> --worktree id:<worktree_id>` 로 붙인다.
   `--model` 은 줄 수 없지만 처음 띄울 때 준 모델이 그 터미널에 남아 있다

### luna 실행 실패

2026-10 `--model gpt-6-luna --effort high` worker 가 `stage.detail: agent_readiness`, `outcome: failed` 로 아무 출력 없이 끝났다.
같은 Task 를 다른 모델로 다시 띄운다. `--retry-of` 는 `--spec` 이 아니라 `--task` 와 함께 쓴다.

```bash
orca orchestration worker-start --task "$TASK_ID" --retry-of "$DISPATCH_ID" --agent codex --model gpt-6.1-sol --effort low --worktree "path:$WORKTREE"
```

`$WORKTREE` 는 처음 띄운 워크트리 경로다. 이 방법으로 같은 Task 를 끝냈다.

### 완료 전에 온 worker_done

첫 `worker_done` 이 오면 dispatch 는 settled 로 바뀐다. 같은 핸들에서 오는 뒤의 보고를 Orca 가 받는지는 버전마다 다르다.

| Orca | 관측 |
| --- | --- |
| 2026-10 fe-plan9 당시 | 뒤의 보고가 `capability is revoked` 로 거절되고 worker 가 멈췄다 |
| 1.4.220 (2026-10-04 mono-plan8) | 단계 하나를 커밋하기 전에 온 `worker_done` 뒤에도 본체는 계속 일했고, 커밋과 push 뒤의 두 번째 `worker_done` 도 전달됐다 |

판단은 터미널과 git 으로 한다.

1. `worker-show --dispatch <id>` 의 `terminal.title` 이 `Working` 이면 해제하지 않고 기다린다. 커밋 목록과 원격 HEAD 가 바뀌는지 본다
2. 제목이 `Ready` 인데 완료 기준에 못 미치면 같은 터미널에 남은 일을 새 dispatch 로 준다

```bash
orca orchestration worker-start --spec "$SPEC" --terminal "$TERMINAL_HANDLE" --worktree "path:$WORKTREE"
```

`$SPEC` 은 남은 일만 적은 지시서 파일이다.

### codex 준비 판정

Orca 가 계정별로 두는 `~/Library/Application Support/orca/codex-accounts/*/home/config.toml` 의 `[tui]` 에 아래 두 줄을 둔다.

```toml
terminal_title = ["app-name", "run-state", "project-name"]
check_for_update_on_startup = false
```

둘째 줄은 시작할 때 업데이트 안내로 빠지지 않게 한다.

### run 이 둘로 나뉨

2026-09-30 worker 가 살아 있는 run A 를 두고 run B 를 만들자, A 의 `check` 와 `worker-start --run A` 가 거절됐고
A 에 걸어 둔 `check --wait` 는 A 의 완료 메시지를 받지 못했다.

`orca orchestration run-use --id <run_id>` 로 옮겨 붙은 뒤 메시지를 읽는다.
상태만 볼 때는 fenced 상태에서도 `worker-list --run <run_id>` 가 동작한다.

### 이전 세션의 대기

이전 세션의 백그라운드 `check --wait` 는 세션이 끝나도 부모 없는 프로세스로 남는다.
그 대기가 받은 메시지는 아무에게도 전달되지 않는다.

```bash
ps -ax -o pid,ppid,lstart,command | grep "orchestration check" | grep <run_id>
```

부모 PID 가 1 이고 시작 시각이 이 세션보다 앞선 것이 그것이다.
그 프로세스와 부모 셸을 `kill` 하고 대기를 다시 건다.
다른 run 의 대기는 다른 세션의 것이므로 건드리지 않는다.

### 권한 확인 창

`terminal read --screen` 으로 화면을 본다.
하위 에이전트가 `;` 로 이은 긴 셸을 쓰면 `Parse error` 로 자동 승인되지 않고 `Do you want to proceed?` 에서 기다린다.
명령이 무엇을 하는지 읽고, 영향이 worker 자신의 임시 디렉터리 안이면 승인하고 사용자에게 알린다. 아니면 사용자에게 묻는다.

### worker 워크트리를 고침

1. 고친 내용을 저장소 밖으로 복사한다
2. `git checkout -- <파일>` 로 되돌린다
3. worker 의 브랜치를 머지한 다음 main 에서 다시 적용한다

### 사용량 한도로 멈춤

heartbeat 와 liveness 는 `live` 로 남아 대기만으로는 알 수 없다. `terminal read --screen` 으로 화면을 본다.
한도 안내가 떠 있으면 그 worker 는 더 진행하지 않는다는 근거다.

`worker-stop` 은 터미널이 `user_owned` 이면 `stop_unknown` 으로 끝나고, 이 상태의 Task 에 `--retry-of` 를 주면 `task_not_startable` 로 거절된다.
`worker-abandon` 으로 dispatch 를 닫은 뒤 다른 제공자로 다시 띄운다. 워크트리는 그대로 이어 쓴다.

```bash
orca orchestration worker-abandon --dispatch "$DISPATCH_ID" --json
orca orchestration worker-start --task "$TASK_ID" --retry-of "$DISPATCH_ID" --worktree "id:$WORKTREE_ID" --agent claude --model claude-sonnet-5-5 --effort medium --json
```

2026-10-03 fos-accountbook mono-plan6 에서 codex worker 가 첫 커밋 전에 한도로 멈췄고, 이 순서로 Claude worker 가 같은 워크트리에서 끝냈다.

## 이 문서에 더할 때

- 오류 없이 잘못된 결과가 완료로 보고되는 곳과, 멈춘 원인이 바로 보이지 않는 곳만 적는다
- CLI 가 인자 오류로 거절하는 것은 적지 않는다. 거절 메시지가 이유를 알려준다
- 끝에 새 절을 붙이지 않는다. 그 일이 일어나는 단계 절에 넣거나, 증상이 먼저 보이는 것이면 「자주 나는 오류」 표에 한 줄과 절 하나를 더한다
- 실측 근거는 날짜와 대상, 관측한 결과를 한 줄로 적는다
