<!-- OMC:START -->
<!-- OMC:VERSION:4.8.2 -->

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

<agent_catalog>
Prefix: `oh-my-claudecode:`. See `agents/*.md` for full prompts.

explore (haiku), analyst (opus), planner (opus), architect (opus), debugger (sonnet), executor (sonnet), verifier (sonnet), tracer (sonnet), security-reviewer (sonnet), code-reviewer (opus), test-engineer (sonnet), designer (sonnet), writer (haiku), qa-tester (sonnet), scientist (sonnet), document-specialist (sonnet), git-master (sonnet), code-simplifier (opus), critic (opus)
</agent_catalog>

<tools>
External AI: `/team N:executor "task"`, `omc team N:codex|gemini "..."`, `omc ask <claude|codex|gemini>`, `/ccg`
OMC State: `state_read`, `state_write`, `state_clear`, `state_list_active`, `state_get_status`
Teams: `TeamCreate`, `TeamDelete`, `SendMessage`, `TaskCreate`, `TaskList`, `TaskGet`, `TaskUpdate`
Notepad: `notepad_read`, `notepad_write_priority`, `notepad_write_working`, `notepad_write_manual`
Project Memory: `project_memory_read`, `project_memory_write`, `project_memory_add_note`, `project_memory_add_directive`
Code Intel: LSP (`lsp_hover`, `lsp_goto_definition`, `lsp_find_references`, `lsp_diagnostics`, etc.), AST (`ast_grep_search`, `ast_grep_replace`), `python_repl`
</tools>

<skills>
Invoke via `/oh-my-claudecode:<name>`. Trigger patterns auto-detect keywords.

Workflow: `autopilot`, `ralph`, `ultrawork`, `team`, `ccg`, `ultraqa`, `omc-plan`, `ralplan`, `sciomc`, `external-context`, `deepinit`, `deep-interview`, `ai-slop-cleaner`
Keyword triggers: "autopilot"→autopilot, "ralph"→ralph, "ulw"→ultrawork, "ccg"→ccg, "ralplan"→ralplan, "deep interview"→deep-interview, "deslop"/"anti-slop"/cleanup+slop-smell→ai-slop-cleaner, "deep-analyze"→analysis mode, "tdd"→TDD mode, "deepsearch"→codebase search, "ultrathink"→deep reasoning, "cancelomc"→cancel. Team orchestration is explicit via `/team`.
Utilities: `ask-codex`, `ask-gemini`, `cancel`, `note`, `learner`, `omc-setup`, `mcp-setup`, `hud`, `omc-doctor`, `omc-help`, `trace`, `release`, `project-session-manager`, `skill`, `writer-memory`, `ralph-init`, `configure-notifications`, `learn-about-omc` (`trace` is the evidence-driven tracing lane)
</skills>

<team_pipeline>
Stages: `team-plan` → `team-prd` → `team-exec` → `team-verify` → `team-fix` (loop).
Fix loop bounded by max attempts. `team ralph` links both modes.
</team_pipeline>

<verification>
Verify before claiming completion. Size appropriately: small→haiku, standard→sonnet, large/security→opus.
If verification fails, keep iterating.
</verification>

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
State: `.omc/state/`, `.omc/state/sessions/{sessionId}/`, `.omc/notepad.md`, `.omc/project-memory.json`, `.omc/plans/`, `.omc/research/`, `.omc/logs/`
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
- 커밋은 관심사별로 분리하며, 사용자가 요청하지 않으면 커밋하거나 푸시하지 않는다.
- 새 전역 규칙은 `~/.claude/CLAUDE.md`, 저장소 전용 규칙은 해당 저장소 지침에 기록한다.

## 스킬

- 관련 스킬이 명백하면 파일이나 도구를 다루기 전에 현재 `SKILL.md`를 읽고 따른다.
- 스킬을 만들거나 구조를 바꾸면 `skill-creator`를 사용한다.
- 반복되는 5줄 초과 코드와 heredoc은 `scripts/`로 분리한다.
- 수정 전 실제 관리 원본을 확인하고, 요청 없이 기존 스킬을 삭제하지 않는다.

스킬을 실행하는 동안 아래를 만나면 그 자리에서 메모해 두고, 작업을 마친 뒤 개선 후보로 정리해 사용자에게 알린다.

- 지시대로 했는데 동작하지 않은 곳
- 우회해야 했던 곳과 실제로 통한 방법
- 스킬이 다루지 않아 사람에게 물어야 했던 판단
- 산문 대신 명령이나 스크립트로 대신할 수 있는 곳

보고는 대상, 판정, 실측 근거를 한 줄씩 담은 표로 한다. 승인받은 항목만 수정하고, 감사 절차가 필요하면 `harness-cleanup` 을 따른다.
근거는 실행 결과와 이력으로 남긴다. "이제는 안 틀릴 것 같다" 같은 추정은 개선 근거로 쓰지 않는다.
CLI 나 외부 도구 자체의 결함이면 스킬을 우회 지침으로 채우지 말고 해당 저장소에 이슈로 등록한다.

## 브라우저

브라우저 작업은 Orca를 우선하고 `~/.claude/scripts/orca-browser.sh`를 사용한다.

- `orca wait --load`는 이미 로드된 페이지에서도 시간 초과가 나므로 사용하지 않는다.
- `orca click`, `fill`, `select`는 CSS 선택자가 아니라 화면 요소 참조를 받는다.
- 숨은 요소나 겹침 화면은 헬퍼의 `js` 명령으로 조작한다.

## 외부 게시와 업무 문체

외부에 등록할 본문은 `content-preview` 스킬을 사용한다.
채팅 안의 본문과 HTML 미리보기를 함께 보여준 뒤 그 턴을 끝낸다.
등록 확인은 사용자가 미리보기를 읽은 다음 턴에 받는다.

사용자 본인 명의의 업무 글은 같은 스킬이 가리키는 문체 참조를 적용한다.

## 질문

- 선택형 질문에는 `AskUserQuestion`을 사용하고 권장안을 첫 번째에 둔다.
- 처음 보는 결정은 질문 전에 배경과 권장 이유를 설명한다.
- 문맥과 안전한 가정으로 진행할 수 있으면 질문하지 않는다.
- 한국어 도구 입력은 UTF-8 원문으로 쓰고 `\uXXXX` 값을 손으로 만들지 않는다.

## 개인 지식과 사내 지식

- 개인 결정, 취향, 학습 내용은 `brain-search` 스킬로 조회한다.
- qmd는 `~/.local/bin-pinned/qmd`를 사용하며 `bun.lock`을 건드려 복구하지 않는다.
- 회사 규칙과 Dooray 업무·위키는 `nbrain` 스킬로 조회한다.
- 환경 고유 값을 추측해야 하는 순간에는 해당 지식원을 먼저 검색한다.
- 비공개 지식을 공개 맥락에 노출하지 않는다.
- 승인 없이 개인 지식 기반을 추가하거나 변경하지 않는다.
