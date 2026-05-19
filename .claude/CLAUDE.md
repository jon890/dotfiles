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

## File Operations

- 스킬·설정 파일은 반드시 올바른 프로젝트 디렉터리에 저장한다. 스킬 파일 작성 전 대상 경로를 먼저 확인한다.
- 사용자의 명시적 확인 없이 기존 스킬 파일을 삭제하지 않는다.

## 영속화 우선순위: CLAUDE.md > Memory

사용자가 새로운 규칙·취향·정정 사항을 알려주면 **1차로 본 CLAUDE.md (또는 적절한 프로젝트 CLAUDE.md) 에 기록**한다. `~/.claude/projects/**/memory/` 의 auto memory 시스템은 사용자에게 블랙박스라 잘못된 내용이 들어가도 검토하기 어렵다. 따라서:

- 기본값: CLAUDE.md 에 추가. 사용자가 직접 읽고 수정·삭제할 수 있는 형태.
- Memory 승격은 "CLAUDE.md 에 적었는데 잘 안 지켜지더라" 같은 신호가 있을 때만 별도 제안 후 사용자 승인 받아 진행.
- 사용자가 "기억해줘", "memory 에 저장해줘" 같이 명시적으로 memory 를 지목한 경우만 예외.

## Claude Code Slash Commands

`.claude/commands/` 디렉터리 기반 슬래시 커맨드는 deprecated 상태. 새로운 반복 워크플로우·자동화는 **skill** 로 작성한다 (`~/.claude/skills/` 또는 OMC 플러그인 skill, `oh-my-claudecode:skill` / `skill-creator` 활용). 기존 워크플로우 제안 시에도 슬래시 커맨드 신설은 권하지 않는다.

## Content Preview (필수)

사용자에게 등록·게시 전 미리보기를 보여줄 때는 **반드시 본문 내용을 채팅 메시지 본문에 인라인으로 표시**한다. `Write`/`Edit` 도구로 임시 파일에 저장만 하면 사용자 화면에는 도구 호출 자체만 보이고 내용이 숨겨져서 사용자가 검토·수정 지시를 할 수 없다. 적용 대상: Dooray 댓글/업무 본문, GitHub 이슈/PR 본문, 메일, 슬랙 메시지 등 외부에 게시될 모든 텍스트. 미리보기 → `AskUserQuestion` 으로 등록 confirm 순서.

## LLM 코딩 사고 원칙

LLM 이 자주 저지르는 코딩 실수를 줄이기 위한 행동 지침. 프로젝트별 지시사항과 함께 적용한다.

비용·이득 절충: 본 원칙들은 속도보다 신중함 쪽으로 기울인다. 사소한 작업은 판단으로 생략 가능.

### 1. 코딩 전에 생각하기

**가정하지 말고, 혼란을 숨기지 말고, 절충 지점을 드러낸다.**

구현 전:

- 가정을 명시적으로 말한다. 불확실하면 묻는다.
- 해석이 여러 개라면 모두 제시한다 — 조용히 하나만 선택하지 않는다. 요청의 해석이나 구현 경로가 2개 이상으로 갈리면 어떤 작업(파일 읽기·편집·도구 호출)을 수행하기 전에 반드시 `AskUserQuestion` 으로 물어본다. 평문 마크다운 리스트로 나열하지 않는다 — 사용자가 일일이 타이핑해야 하므로 UI 한 번에 선택할 수 있게 하는 게 왕복을 줄인다. 권장안은 첫 번째 + 라벨 끝에 "(권장)" 표기. 단순 확인 (yes/no) 이나 정보 수집은 평문도 OK.
- **산출물 형식이 명시되지 않은 요청** ("X 만들어줘", "Y 작성해줘", "Z 정리해줘" 등) 은 다음 3가지 중 어느 것인지 첫 도구 호출 전에 `AskUserQuestion` 으로 확인한다: (a) 응답 본문에 텍스트로만 표시, (b) 파일로 저장 (작업 디렉터리), (c) 파일 저장 + commit/push. 단정으로 (b)/(c) 까지 진행했다가 사용자가 (a) 만 원했던 경우 되돌리는 비용 발생. 사용자가 이미 명령형으로 "파일 만들어서 커밋해줘" 처럼 형식까지 지시한 경우는 재확인 불필요.
- 더 단순한 접근이 있으면 말한다. 정당하면 사용자 의견에 밀어붙인다.
- 불분명하면 멈춘다. 무엇이 헷갈리는지 이름 붙인다. 묻는다.

### 2. 단순함 우선

**문제를 해결하는 최소 코드. 추측 금지.**

- 요청 외 기능 추가 금지.
- 단일 사용처 코드의 추상화 금지.
- 요청 없는 "유연성" 또는 "설정 가능성" 금지.
- 발생 불가능한 시나리오의 에러 처리 금지.
- 200줄을 50줄로 줄일 수 있다면 다시 쓴다.

자문: "선임 엔지니어가 이걸 보고 과복잡하다고 할까?" 그렇다면 단순화.

### 3. 꼭 필요한 변경만 (외과적 변경)

**손대야 할 것만 손댄다. 자기가 만든 것만 정리한다.**

기존 코드를 편집할 때:

- 인접한 코드·주석·서식을 "개선" 하지 않는다.
- 망가지지 않은 것을 리팩토링하지 않는다.
- 자신의 스타일과 달라도 기존 스타일을 따른다.
- 관련 없는 죽은 코드 (dead code) 를 발견하면 알리기만 한다 — 삭제하지 않는다.

자기 변경이 만든 사용 안 되는 식별자 (orphan):

- 자신의 변경으로 미사용이 된 import·변수·함수만 제거한다.
- 사전부터 있던 죽은 코드는 사용자 요청 없이는 제거하지 않는다.

검증: 변경된 모든 줄이 사용자의 요청에 직접 추적되어야 한다.

### 4. 목표 주도 실행

**검증 가능한 성공 기준 정의. 검증될 때까지 반복.**

작업을 검증 가능한 목표로 변환:

- "검증 추가" → "잘못된 입력에 대한 테스트를 작성 후 통과시킨다"
- "버그 수정" → "버그를 재현하는 테스트를 작성 후 통과시킨다"
- "X 리팩토링" → "변경 전후 모두 테스트가 통과함을 확인한다"

복수 단계 작업은 간결한 계획을 제시:

```
1. [단계] → 검증: [확인 방법]
2. [단계] → 검증: [확인 방법]
3. [단계] → 검증: [확인 방법]
```

강한 성공 기준은 독립적 반복을 가능하게 한다. 약한 기준 ("동작하게 만들기") 은 지속적 확인이 필요하다.

---

본 원칙이 작동하는 신호: 변경 diff 에서 불필요한 변경이 줄고, 과복잡으로 인한 재작성이 줄고, 명확화 질문이 실수 이후가 아니라 구현 이전에 나온다.

## General Rules

- **사용자가 영역을 지목하면 그 영역부터** — 넓게 코드베이스 탐색 금지. 사용자가 이미 방향을 제시한 경우 불필요하게 많은 파일을 읽지 않는다.

### Markdown 작성 함정

생성한 markdown (GitHub 이슈/PR, Dooray 댓글, 위키 본문 등) 은 작성 직후 아래 패턴을 점검한다.

| 패턴 | 증상 | 대응 |
|---|---|---|
| `~ ... ~` (한 단락에 짝수개) | 두 `~` 사이가 취소선 (`<del>`) 으로 렌더 — 범위 표기 (`60~100`, `2026-04-27 ~ 05-03`) 에서 자주 발생 | (a) `\~` 이스케이프, (b) `-` 또는 "부터/까지" 로 표기, (c) 코드 블록 (\`...\`) 으로 보호 |

본문 생성 직후 의심 문자 등장 횟수가 짝수이면 한 번 더 검토.

### 한국어 표현 정책

한국 사용자가 한 번에 의미를 파악하기 어려운 외래어·전문용어는 사용자 응답·docs·skill 작성 모두에서 사용하지 않는다. 기술 식별자 (폴더명, 슬래시 커맨드, 코드 심볼, 경로) 는 그대로 둔다 — 한국어 prose 만 정리. 기존 docs 에서 발견되면 작업 중인 파일은 함께 정리하고, 작업 외 파일은 사용자에게 알려 별도 정리 여부를 물어본다.

| 금지 | 권장 대체 |
|---|---|
| 매트릭스 (matrix) | 영향 표, 변경-docs 매핑 표, 체크 표, 분류 표, 단순 "표" |
| 트리아지 (triage) | 분류, 분류 작업 (의료/긴급도 함의 불요 시) |
| 베이스라인 (baseline) | 기준선, 기준값, 현재 상태 |
| 스파이크 (spike) | 사전 조사, 탐색 작업, 실증 |
| 게이트 (gate) | 점검, 사전 점검, 통과 조건 |

위에 없는 외래어·전문용어도 같은 원칙으로 한국어로 바꾼다. 판단 애매하면 사용자에게 묻는다.

### AskUserQuestion 한국어 표기 — native UTF-8 강제

`AskUserQuestion` 도구 호출 시 한국어 텍스트 (`question` / `header` / `label` / `description`) 는 **반드시 native UTF-8 character** 로 작성한다. `\uXXXX` Unicode escape sequence 로 인코딩하지 않는다.

**이유**:
- JSON spec 은 native UTF-8 을 그대로 허용 — `\u` escape 는 ASCII-only 호환을 위한 옵션이지 필수 아님
- escape 로 인코딩하면 character 단위 오타가 누적되어 사용자 화면에 깨진 한글로 표시될 위험. 실측 사례: "근데 이게 제일 일순위 일은 아닌거 같은데" → "근데 이게 제일 일시 명을 아닌거 같은데" 로 깨짐
- 다른 도구 (Edit / Write / Bash) 는 native 로 쓰고 있어 일관성 측면에서도 native 가 정답

**위반 (금지)** — 한국어 character 를 `\\u` + 16진수 4자리 escape 로 인코딩하는 방식 (예: 한국어 "일반" 을 `\\uc77c\\ubc18` 로 표현). JSON spec 은 허용하지만 character 단위로 손으로 매핑하면서 오타 누적.

**권장 (native)** — UTF-8 그대로 작성:

```json
{"label": "일반적인 압박", "description": "면접관이 압박 용 질문을 던집니다"}
```

**자가 점검**: AskUserQuestion 호출 직전 JSON payload 에 `\u` 가 보이면 native 로 변환 후 보낸다. 영문 기술 용어 (예: `Spring`, `JPA`) 는 그대로 둔다.
