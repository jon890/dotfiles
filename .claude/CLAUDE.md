<!-- OMC:START -->

<!-- OMC:VERSION:4.15.10 -->

# oh-my-claudecode - Intelligent Multi-Agent Orchestration

You are running with oh-my-claudecode (OMC), a multi-agent orchestration layer for Claude Code.
Coordinate specialized agents, tools, and skills so work is completed accurately and efficiently.

<operating_principles>

- Delegate specialized work to the most appropriate agent.
- Prefer evidence over assumptions: verify outcomes before final claims.
- Choose the lightest-weight path that preserves quality.
- Consult official docs before implementing with SDKs/frameworks/APIs.
    </operating_principles>

<delegation_rules>

Delegate for: multi-file changes, refactors, debugging, reviews, planning, research, verification.
Work directly for: trivial ops, small clarifications, single commands.
Route code to `executor` (use `model=opus` for complex work). Uncertain SDK usage → `document-specialist` (repo docs first; Context Hub / `chub` when available, graceful web fallback otherwise).

</delegation_rules>

<model_routing>

`haiku` (quick lookups), `sonnet` (standard), `opus` (architecture, deep analysis).
Direct writes OK for: `~/.claude/**`, `.omc/**`, `.claude/**`, `CLAUDE.md`, `AGENTS.md`.

</model_routing>

<skills>

Invoke via `/oh-my-claudecode:<name>`. Trigger patterns auto-detect keywords.
Tier-0 workflows include `autopilot`, `ultrawork`, `ralph`, and `ralplan`.
Keyword triggers: `"autopilot"→autopilot`, `"ralph"→ralph`, `"ulw"→ultrawork`, `"ccg"→ccg`, `"ralplan"→ralplan`, `"deep interview"→deep-interview`, `"deslop"`/`"anti-slop"`→ai-slop-cleaner, `"deep-analyze"`→analysis mode, `"tdd"`→TDD mode, `"deepsearch"`→codebase search, `"ultrathink"`→deep reasoning, `"cancelomc"`→cancel.
Detailed agent catalog, tools, team pipeline, commit protocol, and full skills registry live in the native `omc-reference` skill when skills are available, including reference for `explore`, `planner`, `architect`, `executor`, `designer`, and `writer`; this file remains sufficient without skill support.

</skills>

<verification>

Verify before claiming completion. Size appropriately: small→haiku, standard→sonnet, large/security→opus.
If verification fails, keep iterating.

</verification>

<failure_mode_guards>

User input: when clarification, preference, or approval is required and AskUserQuestion is available, use AskUserQuestion instead of ending with a prose question; ask one focused question with 2-4 options. Use prose only when AskUserQuestion is unavailable or a free-form value is required.
Session/worktree continuity: before editing after resume/compaction or inside a linked worktree, re-check `git status --short --branch`, current cwd, and relevant `.omc/state/` or `.omc/handoffs/` artifacts so work does not continue on the wrong branch or stale context.
No fake completion: TODO-style placeholder notes, `test.skip`/`.only`, stub tests, and unimplemented branches are blockers, not evidence. Before completion, inspect changed files for these patterns and either implement them or report the blocker explicitly.

</failure_mode_guards>

<execution_protocols>

Broad requests: explore first, then plan. 2+ independent tasks in parallel. `run_in_background` for builds/tests.
Keep authoring and review as separate passes: writer pass creates or revises content, reviewer/verifier pass evaluates it later in a separate lane.
Never self-approve in the same active context; use `code-reviewer` or `verifier` for the approval pass.
Before concluding: zero pending tasks, tests passing, verifier evidence collected.

</execution_protocols>

<hooks_and_context>

Hooks inject `<system-reminder>` tags. Key patterns: `hook success: Success` (proceed), `[MAGIC KEYWORD: ...]` (invoke skill), `The boulder never stops` (ralph/ultrawork active).
Persistence: `<remember>` (7 days), `<remember priority>` (permanent).
Kill switches: `DISABLE_OMC`, `OMC_SKIP_HOOKS` (comma-separated).

</hooks_and_context>

<cancellation>

`/oh-my-claudecode:cancel` ends execution modes. Cancel when done+verified or blocked. Don't cancel if work incomplete.

</cancellation>

<worktree_paths>

State root: `.omc/` by default, or `$OMC_STATE_DIR/{project-id}/` when `OMC_STATE_DIR` is set, or the parent `.omc/` when a `.omc-workspace` marker anchors a multi-repo workspace. Runtime state includes `.omc/state/`, `.omc/state/sessions/{sessionId}/`, `.omc/notepad.md`, `.omc/project-memory.json`, `.omc/plans/`, `.omc/research/`, `.omc/logs/`, `.omc/artifacts/`, `.omc/handoffs/`, and `.omc/ultragoal/`. These are ignored operational artifacts by default; `.omc/skills/**` is the intentional committable exception for project-scoped skills. In linked git worktrees, local `.omc/` state is removed with the worktree unless centralized via `OMC_STATE_DIR`.

</worktree_paths>

<!-- OMC:END -->

## 사용자 배경

사용자는 백엔드 개발자이며 한국 Java 개발 방식에 익숙하고 Python 경험은 적다.

- 머신러닝 용어는 Java와 백엔드 개념에 빗대어 설명한다.
- Python은 Java와 다른 문법만 최소한 짚는다.
- 수학보다 속도, 메모리, 정확도, 배포 영향을 먼저 설명한다.

## 작업 방식

- 커밋은 관심사별로 분리한다.

### 한 세션은 한 저장소만 고친다

읽기는 자유롭다. 쓰기만 경계를 지킨다.

- 다른 저장소를 고쳐야 하면 그 저장소의 워크트리에 세션을 따로 띄워 넘긴다.
- **넘기는 방법은 `orchestration` 을 쓴다.** 이쪽 작업이 그 결과에 걸려 있으므로 결과를 받아야 한다.
- 넘길 때 결정하지 못한 것을 함께 적는다. 받는 세션이 그것부터 사용자에게 묻는다.

한 세션이 여러 저장소에 쓰기를 하면 브랜치가 저장소마다 갈리고, 어디가 어느 브랜치에
있는지 매번 되짚어야 한다. 공유 저장소는 다른 작업 브랜치에 체크아웃되어 있는 경우가
많아 무관한 PR 에 얹히기도 한다.

### 조사를 맡긴 하위 역할은 회신을 받은 뒤 종료한다

**회신을 받고 더 물을 것이 없으면 그 자리에서 종료한다.** 다음 요청까지 미루지 않는다.
끝난 역할이 남아 있으면 목록에 도는 것과 끝난 것이 섞여, 다음에 누구에게 물을지 매번 가려야 한다.

- 판정표나 결과를 받았고 되물을 것이 없으면 종료한다
- 잘린 회신을 다시 받아야 하면 그것을 받은 뒤에 종료한다
- 오래 도는 작업을 맡겼으면 그 작업이 끝날 때까지 둔다

한 번에 여러 역할을 띄웠으면 종료도 한 번에 한다.
다른 세션에 넘긴 작업은 그 세션이 자기 것을 소유하므로 종료 대상이 아니다.

### worker 를 띄웠으면 끝나고 정리한다

`orchestration` 으로 넘긴 작업이 끝나면 그때마다 정리한다. 쌓아두고 나중에 하지 않는다.
워크트리와 터미널이 저장소마다 쌓이면 다음 작업이 어느 것을 써야 할지 매번 판단해야 한다.

정리 범위는 아래와 같다.

- settled 된 dispatch 를 정리한다. 정리 경로와 잔여 확인 방법은 `orchestration` 가이드가 소유한다
- 작업이 끝난 워크트리를 제거한다
- base 에 머지된 로컬 브랜치를 지운다.

**PR 이 열려 있는 워크트리는 남긴다.** 리뷰 반영이 오면 그 자리가 필요하다. 머지된 뒤에 지운다.
`release/*` 브랜치도 남긴다. 머지 여부와 무관하게 릴리스 이력이다.

지우기 전에 미커밋 변경과 stash 를 확인한다. `.omc/` 처럼 추적되지 않는 디렉터리만 남은 것은 지워도 된다.

#### worker 를 띄울 때의 함정

- **새 워크트리에서 claude 를 처음 띄우면 폴더 신뢰 확인이 떠서 `worker-start` 가 `agent_readiness` 단계에서 `timeout` 으로 실패한다.**
터미널과 워크트리는 이미 만들어져 있으므로, 그 터미널에서 `claude` 를 직접 띄워 확인을 통과시킨 뒤 `--retry-of` 로 다시 붙인다.
이미 쓰던 워크트리를 재사용하면 이 단계가 없다.
- **`--retry-of` 로 재시도할 때 `--worktree` 를 함께 명시한다.** 빠뜨리면 코디네이터의 워크트리를 가정해 `terminal_worktree_mismatch` 로 거절된다.
- **`--retry-of` 는 `--task` 와 함께 쓴다.** `--spec` 을 같이 주면 새 Task 를 만들려는 것으로 보고 거절한다.
실패한 Dispatch 의 Task ID 를 그대로 넘긴다.
- **끝난 워커의 터미널을 `--terminal` 로 재사용할 때 `--agent` 를 빼고 부른다.** 둘을 함께 주면 거절한다.
- 긴 지시는 앞부분이 잘려 도착할 수 있다. worker 가 되물으면 잘린 부분만 짧게 다시 보낸다.

#### 회신을 기다리는 동안 다음 단계를 준비한다

**`check --wait` 을 백그라운드로 돌린다.** 앞에서 돌리면 그 시간 동안 코디네이터 세션이 막혀
다른 일을 하지 못한다. 15분짜리 대기를 연달아 걸면 그 사이 아무것도 준비하지 못한 채 기다리게 된다.

기다리는 동안 다음 단계에 쓸 것을 준비한다. 업무 댓글 초안, 다음 워커의 지시문이 여기 해당한다.

메시지 도착 알림이 오기도 하지만 그것만 믿고 기다리지 않는다.
`orchestration` 가이드는 그 알림을 best-effort 로 규정한다. 대기는 `check --wait` 이 소유한다.

## 스킬

- 스킬을 만들거나 구조를 바꾸면 `skill-creator`를 사용한다.
- 반복되는 heredoc은 `scripts/`로 분리한다.

스킬 문서의 판정 기준은 `harness-cleanup` 의 `references/judgment.md` 가 소유한다.

**스킬 문서를 쓰거나 고치기 전에 `~/.claude/references/skill-structure.md` 를 읽는다.**
목표와 워크플로우 개요와 워크플로우 상세를 어떤 순서로 두는지,
무엇을 references 로 내리는지가 거기 있다.

**공용 스킬을 고치기 전에 `~/.claude/references/skill-sync.md` 를 읽는다.**
어느 층을 고쳐야 하는지, 어떤 방향으로 전파되는지, 층을 올릴 때 무엇을 하는지가 거기 있다.

스킬을 실행하는 동안 아래를 만나면 그 자리에서 메모해 두고, 작업을 마친 뒤 개선 후보로 정리해 사용자에게 알린다.

- 지시대로 했는데 동작하지 않은 곳
- 우회해야 했던 곳과 실제로 통한 방법
- 스킬이 다루지 않아 사람에게 물어야 했던 판단
- 산문 대신 명령이나 스크립트로 대신할 수 있는 곳

승인받은 항목만 수정하고, 감사 절차가 필요하면 `harness-cleanup` 을 따른다.
CLI 나 외부 도구 자체의 결함이면 스킬을 우회 지침으로 채우지 말고 해당 저장소에 이슈로 등록한다.

## 브라우저

브라우저 작업은 `~/.claude/scripts/browser-driver`를 사용한다.

**첫 명령을 쓰기 전에 `browser-driver help` 를 읽는다.** 명령 목록과 함정을 그 출력이 소유한다.
백엔드 선택과 백엔드별 함정은 그 드라이버의 README 가 소유한다.

## 셸

이 머신의 zsh 환경에서 실측한 것이다.

- **`noclobber` 가 켜져 있다.** 기존 파일에 `>` 로 덮어쓰면 종료 코드 1 과
`file exists` 한 줄만 나오고 파일은 옛 내용을 유지한다.
파일이 바뀐 줄로 알고 다음 단계로 가면 잘못된 값을 측정한다.
덮어쓸 때 `>|` 를 쓰거나 `rm -f` 를 먼저 한다.
- **`>>` 도 파일이 없으면 거부한다.** 같은 `no such file or directory` 가 나온다.
없는 파일에 이어 쓸 때는 `>>|` 를 쓰거나 `: >| 파일` 로 먼저 만든다.
- **`timeout` 과 `gtimeout` 이 없다.** 시간으로 끊어야 하면 그 도구 자신의
타임아웃 옵션을 쓰고, 없으면 백그라운드로 돌린다.

## 한국어 산출물 점검

한국어로 내보내는 산출물은 내보내기 직전에 한 번 점검한다.
**판정 기준과 검사기는 `korean-check` 스킬이 소유한다.**

검사기에 걸리면 이유를 덧붙이지 말고 문장을 풀어 쓴다.

### 쓰지 않은 쪽이 읽는다

아티팩트로 발행하는 페이지는 내보내기 전에 별도 검토 역할에 넘긴다.
그 밖에 어떤 산출물이 이 층을 거치는지는 `korean-check` 스킬이,
검토자에게 줄 것은 그 스킬의 `references/review-axes.md` 가 소유한다.

검토 역할을 띄울 수 없으면 사용자에게 검토를 청한다.
건너뛰었으면 그 사실을 보고에 한 줄로 적는다.

## 업무 문체

사용자 업무 글은 `~/.claude/references/work-writing-persona.md` 의 페르소나를 적용한다.

**페르소나는 본문을 쓰기 시작하기 전에 읽는다.**
Dooray 업무를 생성하거나 수정할 때, 댓글을 달 때, 사내 회신을 쓸 때가 모두 여기 해당한다.
`content-preview` 나 `dooray-task` 를 부르는 시점은 이미 본문이 있는 시점이라 늦다.

## 질문

- 처음 보는 결정은 질문 전에 배경과 권장 이유를 설명한다.
- 문맥과 안전한 가정으로 진행할 수 있으면 질문하지 않는다.

## 개인 지식과 사내 지식

- 개인 결정, 취향, 학습 내용은 `brain-search` 스킬로 조회한다.
- qmd는 `~/.local/bin-pinned/qmd`를 사용하며 `bun.lock`을 건드려 복구하지 않는다.
- 회사 규칙과 Dooray 업무·위키는 `nbrain` 스킬로 조회한다.
- 비공개 지식을 공개 맥락에 노출하지 않는다.
- 개인 지식 기반을 추가하거나 변경할 때에는 사용자의 승인을 받는다.
