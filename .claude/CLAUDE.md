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

## Setup

Say "setup omc" or run `/oh-my-claudecode:omc-setup`.

<!-- OMC:END -->

## 사용자 배경

사용자는 백엔드 개발자이며 한국 Java 개발 방식에 익숙하고 Python 경험은 적다.

- 머신러닝 용어는 Java와 백엔드 개념에 빗대어 설명한다.
- Python은 Java와 다른 문법만 최소한 짚는다.
- 수학보다 속도, 메모리, 정확도, 배포 영향을 먼저 설명한다.

## 작업 방식

- 명확하고 안전한 로컬 작업은 묻지 않고 완료와 검증까지 진행한다.
- 외부 게시, 파괴적 작업, 권한 부족, 실질적인 범위 변경 앞에서만 확인한다.
- 구현과 중요한 문서의 검토는 가능한 경우 별도 `code-reviewer` 또는 `verifier`에 맡긴다.
- 커밋은 관심사별로 분리한다.

### 한 세션은 한 저장소만 고친다

읽기는 자유롭다. 쓰기만 경계를 지킨다.

- 다른 저장소를 고쳐야 하면 그 저장소의 워크트리에 세션을 따로 띄워 넘긴다.
- **넘기는 방법은 `orchestration` 을 쓴다.** 이쪽 작업이 그 결과에 걸려 있으므로 결과를 받아야 한다.
- 넘길 때 결정하지 못한 것을 함께 적는다. 받는 세션이 그것부터 사용자에게 묻는다.

한 세션이 여러 저장소에 쓰기를 하면 브랜치가 저장소마다 갈리고, 어디가 어느 브랜치에
있는지 매번 되짚어야 한다. 공유 저장소는 다른 작업 브랜치에 체크아웃되어 있는 경우가
많아 무관한 PR 에 얹히기도 한다.

### worker 를 띄웠으면 끝나고 정리한다

`orchestration` 으로 넘긴 작업이 끝나면 그때마다 정리한다. 쌓아두고 나중에 하지 않는다.
워크트리와 터미널이 저장소마다 쌓이면 다음 작업이 어느 것을 써야 할지 매번 판단해야 한다.

정리 범위는 넷이다.

- `worker-release` 로 settled 된 dispatch 를 정리한다
- 작업이 끝난 워크트리를 제거한다
- base 에 머지된 로컬 브랜치를 지운다. `develop` 이 있으면 그것을, 없으면 `master` 를 기준으로 본다
- 남은 worker 터미널을 닫는다. 코디네이터 자신의 터미널은 제외한다

**PR 이 열려 있는 워크트리는 남긴다.** 리뷰 반영이 오면 그 자리가 필요하다. 머지된 뒤에 지운다.
`release/*` 브랜치도 남긴다. 머지 여부와 무관하게 릴리스 이력이다.

지우기 전에 미커밋 변경과 stash 를 확인한다. `.omc/` 처럼 추적되지 않는 디렉터리만 남은 것은 지워도 된다.

#### worker 를 띄울 때의 함정

- **새 워크트리에서 claude 를 처음 띄우면 폴더 신뢰 확인이 떠서 `worker-start` 가 `agent_prompt_stalled` 로 실패한다.**
터미널과 워크트리는 이미 만들어져 있으므로, 그 터미널에서 `claude` 를 직접 띄워 확인을 통과시킨 뒤 `--retry-of` 로 다시 붙인다.
이미 쓰던 워크트리를 재사용하면 이 단계가 없다.
- `**--retry-of` 로 재시도할 때 `--worktree` 를 함께 명시한다.** 빠뜨리면 코디네이터의 워크트리를 가정해 `terminal_worktree_mismatch` 로 거절된다.
- 긴 지시는 앞부분이 잘려 도착할 수 있다. worker 가 되물으면 잘린 부분만 짧게 다시 보낸다.

## 스킬

- 스킬을 만들거나 구조를 바꾸면 `skill-creator`를 사용한다.
- 반복되는 5줄 초과 코드와 heredoc은 `scripts/`로 분리한다.


스킬은 저장소 로컬, 개인 공용 `~/personal/fos-skills/`, 팀 공용 `~/projects/AiSdtSkill/skills/` 셋으로 나뉜다.

**공용 스킬을 고치기 전에 `~/.claude/references/skill-sync.md` 를 읽는다.**
어느 층을 고쳐야 하는지, 어떤 방향으로 전파되는지, 층을 올릴 때 무엇을 하는지가 거기 있다.
개인 공용이 원본이고 팀 공용은 사본이라, 사본을 고치면 다음 내보내기에 덮인다.

스킬을 실행하는 동안 아래를 만나면 그 자리에서 메모해 두고, 작업을 마친 뒤 개선 후보로 정리해 사용자에게 알린다.

- 지시대로 했는데 동작하지 않은 곳
- 우회해야 했던 곳과 실제로 통한 방법
- 스킬이 다루지 않아 사람에게 물어야 했던 판단
- 산문 대신 명령이나 스크립트로 대신할 수 있는 곳

보고는 대상, 판정, 실측 근거를 한 줄씩 담은 표로 한다. 승인받은 항목만 수정하고, 감사 절차가 필요하면 `harness-cleanup` 을 따른다.
CLI 나 외부 도구 자체의 결함이면 스킬을 우회 지침으로 채우지 말고 해당 저장소에 이슈로 등록한다.

## 브라우저

브라우저 작업은 `~/.claude/scripts/browser-driver`를 사용한다.
브라우저 도구를 직접 부르면 실패해도 종료 코드가 0이라 오류가 묻힌다. 드라이버가 이것을 1로 바꾼다.
백엔드 선택과 백엔드별 함정은 그 드라이버의 README가 소유한다.

- 숨은 요소나 겹침 화면은 드라이버의 `js` 명령으로 조작한다.
- JS 인자는 작은따옴표로 감싼다. 큰따옴표로 감싸면 JS 안의 `$(`를 셸이 명령 치환으로 먹는다.
- 고정 대기 대신 드라이버의 `waitjs`로 조건을 기다린다. `sleep`도 동작하지만 화면 반응 시간에 따라 불안정하다.
- 사내 시스템은 세션이 끊기면 로그인 화면으로 조용히 이동한다. 조회 결과가 비면 `url` 명령으로 현재 주소를 먼저 본다.

## 한국어 산출물 점검

한국어로 내보내는 산출물은 내보내기 직전에 한 번 점검한다.
판정 기준은 `~/.claude/rules/korean-style.md` 의 「문장 구성」이다.

파일, PR 본문, 커밋 메시지, 게시글, 아티팩트, 채팅 답변이 모두 대상이다.
편집 훅은 `.md` 파일의 금지어와 괄호 중첩만 잡는다. 나머지는 이 점검이 맡는다.

걸리면 이유를 덧붙이지 말고 문장을 풀어 쓴다.

## 외부 게시와 업무 문체

외부에 등록할 본문은 `content-preview` 스킬을 사용한다.

사용자 업무 글은 업무 글 페르소나를 적용한다.
관리 원본은 `~/.claude/references/work-writing-persona.md` 이며,
작업 로그, 대외 회신, 업무 본문 세 모드의 문체를 정한다.

**페르소나는 본문을 쓰기 시작하기 전에 읽는다.**
Dooray 업무를 생성하거나 수정할 때, 댓글을 달 때, 사내 회신을 쓸 때가 모두 여기 해당한다.
`content-preview` 나 `dooray-task` 를 부르는 시점은 이미 본문이 있는 시점이라 늦다.
다 써놓고 문체를 고치는 것은 처음부터 다시 쓰는 일이 된다.

## 질문

- 선택형 질문에는 `AskUserQuestion`을 사용하고 권장안을 첫 번째에 둔다.
- 처음 보는 결정은 질문 전에 배경과 권장 이유를 설명한다.
- 문맥과 안전한 가정으로 진행할 수 있으면 질문하지 않는다.
- 중첩 인자에 한국어를 직접 쓰면 이스케이프 실수로 글자가 바뀐다.
실측으로 어투가 어토로, 응급이 어때로, 청중이 섬중으로, 회귀가 회기로 바뀌었다.
넷 다 유효한 한글이라 길이 검사로는 잡히지 않는다.
- 한국어 도구 입력은 UTF-8 원문으로 쓰고 `\uXXXX` 값을 손으로 만들지 않는다.
- 선택지 상세는 응답 본문 표에 두어 도구로 넘기는 한국어의 양을 줄이고,
`AskUserQuestion` 에는 짧은 이름만 넣는다.
- 호출 전에 인자를 응답 본문 표에 적은 이름과 글자 단위로 대조한다. 이 대조가 유일한 검출 수단이다.

## 개인 지식과 사내 지식

- 개인 결정, 취향, 학습 내용은 `brain-search` 스킬로 조회한다.
- qmd는 `~/.local/bin-pinned/qmd`를 사용하며 `bun.lock`을 건드려 복구하지 않는다.
- 회사 규칙과 Dooray 업무·위키는 `nbrain` 스킬로 조회한다.
- 비공개 지식을 공개 맥락에 노출하지 않는다.
- 승인 없이 개인 지식 기반을 추가하거나 변경하지 않는다.

### 사내 지식을 언제 꺼내는가

정해진 절차 없이 조사하고 논의하는 구간에서 가장 자주 놓친다.
아래 넷 중 하나를 하려는 순간에 문장을 내보내기 전에 `nbrain` 을 먼저 돌린다. 
내가 모른다고 느끼는지를 판단하지 않는다. 넷은 모두 내 출력에 드러나는 것이라 확인할 수 있다.

- 사내 관행, 절차, 환경 고유 값, 과거 결정을 사용자에게 물으려 할 때
- `없다`, `처음이다`, `확인할 수 없다`, `찾지 못했다` 라고 답하려 할 때
- `아마`, `~인 것 같다` 처럼 추측 표현으로 사내 사실을 말하려 할 때
- 사용자가 사내 사실을 정정했을 때

검색해도 없으면 없다고 말해도 된다. 검색하지 않고 없다고 말하는 것만 금지한다.