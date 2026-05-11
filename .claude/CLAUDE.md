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

## Terminal Environment: cmux

This environment runs on **cmux** (not plain tmux). Rules file: `~/.claude/rules/cmux-guide.md`.

<cmux_environment>
**Use cmux CLI instead of tmux when manually controlling the terminal.**

Detection pattern:
```bash
if command -v cmux &>/dev/null && [ -n "$CMUX_WORKSPACE_ID" ]; then
  cmux new-split right && cmux send --surface surface:2 "cmd\n"
else
  tmux split-window -h && tmux send-keys "cmd" C-m
fi
```

Key commands: `cmux read-screen`, `cmux capture-pane`, `cmux send --surface ID "cmd\n"`, `cmux focus --surface ID`, `cmux browser`, `cmux wait-for`

Agent Teams: `cmux claude-teams '<prompt>'` — sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` automatically.

**Note:** OMC `/team` and `/omc-teams` internally call `execFile('tmux', ...)` — tmux binary must remain installed separately. Use cmux only for manual terminal operations.
</cmux_environment>

## Dooray Integration

- Dooray 태스크 업데이트는 본문(post body)을 수정하지 않고 댓글(comment)로 작성한다.
- 주간 보고 등 정기 업데이트도 기존 태스크의 댓글로 추가한다.

## File Operations

- 스킬·설정 파일은 반드시 올바른 프로젝트 디렉터리에 저장한다. 스킬 파일 작성 전 대상 경로를 먼저 확인한다.
- 사용자의 명시적 확인 없이 기존 스킬 파일을 삭제하지 않는다.

## Content Preview (필수)

사용자에게 등록·게시 전 미리보기를 보여줄 때는 **반드시 본문 내용을 채팅 메시지 본문에 인라인으로 표시**한다. `Write`/`Edit` 도구로 임시 파일에 저장만 하면 사용자 화면에는 도구 호출 자체만 보이고 내용이 숨겨져서 사용자가 검토·수정 지시를 할 수 없다. 적용 대상: Dooray 댓글/업무 본문, GitHub 이슈/PR 본문, 메일, 슬랙 메시지 등 외부에 게시될 모든 텍스트. 미리보기 → `AskUserQuestion` 으로 등록 confirm 순서.

## General Rules

- 이슈 조사 시 사용자가 특정 영역을 지목했다면, 넓게 코드베이스를 탐색하기 전에 그 영역부터 먼저 확인한다. 사용자가 이미 방향을 제시한 경우 불필요하게 많은 파일을 읽지 않는다.
- 요청의 해석이나 구현 경로가 2개 이상으로 갈린다면, 어떤 작업(파일 읽기·편집·도구 호출)을 수행하기 전에 반드시 `AskUserQuestion` 으로 물어본다. 평문 마크다운 리스트로 나열하지 않는다 — 사용자가 일일이 타이핑해야 하므로 UI 한 번에 선택할 수 있게 하는 게 왕복을 줄인다. 권장안은 첫 번째 + 라벨 끝에 "(권장)" 표기. 단순 확인(yes/no)이나 정보 수집은 평문도 OK. 모호한 의도를 일방적으로 해석해 진행했다가 전체 경로를 되돌리는 비용이 사전 확인 비용보다 항상 크다 (예: "fos-blog 문제" 가 블로그 게시물인지 스킬 전파인지, AGENTS.md 와 CLAUDE.md 를 통합할지 분리 유지할지 등은 첫 도구 호출 전에 묻는다).
- **산출물 형식이 명시되지 않은 요청** ("X 만들어줘", "Y 작성해줘", "Z 정리해줘" 등) 은 다음 3가지 중 어느 것인지 첫 도구 호출 전에 `AskUserQuestion` 으로 확인한다: (a) 응답 본문에 텍스트로만 표시, (b) 파일로 저장 (작업 디렉터리), (c) 파일 저장 + commit/push. 단정으로 (b) 또는 (c) 까지 진행했다가 사용자가 (a) 만 원했던 경우 revert commit + push 비용 발생. 사용자가 이미 명령형으로 "파일 만들어서 커밋해줘" 처럼 형식까지 지시한 경우는 재확인 불필요.
- Markdown 본문(GitHub 이슈/PR, Dooray 댓글, 위키 등)을 생성할 때 `~` 문자 사용에 주의한다. 한 단락에 `~`가 두 번 이상 등장하면 markdown 파서가 두 `~` 사이를 취소선(`<del>`)으로 렌더링한다. 범위 표기(`60~100`, `30분~1시간`, `2026-04-27 ~ 05-03`)를 여러 개 쓸 때 의도치 않은 취소선이 발생하기 쉽다. 대응: (a) 백슬래시 이스케이프 `\~` 사용, (b) `-`나 "부터/까지" 같은 다른 표기로 변경, (c) 코드 블록(\`...\`) 안에 넣어 보호. 본문 생성 직후 `~` 등장 횟수를 확인해서 짝수개면 검토.
- 한국 사용자가 한 번에 의미를 파악하기 어려운 외래어·전문용어는 사용자 응답·docs/skill 작성·갱신 모두에서 사용하지 않는다. 한국어 일반어로 풀어쓴다. 기술 식별자(폴더명, 슬래시 커맨드, 코드 심볼, 경로) 는 그대로 둔다 — 한국어 prose 만 정리. 기존 docs 에서 발견되면 작업 중인 파일은 함께 정리하고, 작업 외 파일은 사용자에게 알려 별도 정리 여부를 물어본다.
  - "매트릭스(matrix)" → "영향 표", "변경-docs 매핑 표", "체크 표", "분류 표", 단순 "표"
  - "트리아지(triage)" → "분류", "분류 작업", "주간 에러 분류 자동화" 등 (의료/긴급도 함의가 없는 일반 분류 작업이면 그냥 "분류")
  - 위에 없는 외래어/전문용어도 같은 원칙으로 한국어로 바꾼다. 판단 애매하면 사용자에게 묻는다.

## Git & PR Conventions

PR 제목은 반드시 아래 형식을 따른다:

```
type(scope): description
```

예시:
- `feat(backend): add Prometheus config`
- `fix(database): resolve Redis connection timeout`
- `docs(task): add NSC slot engine abstraction`

이 형식에서 절대 벗어나지 않는다.
