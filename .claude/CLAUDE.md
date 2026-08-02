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

## 브라우저 자동화: Orca 내장 브라우저

브라우저를 조작해야 하는 작업(사내 결재 서식 작성, GRM 공수 입력, 미리보기 띄우기)은 **Orca 내장 브라우저**를 쓴다.
`orca` CLI 의 Browser Automation 명령군(`tab create`·`goto`·`snapshot`·`eval`·`screenshot` 등)이 진입점이다.

직접 `orca` 를 부르지 말고 공용 헬퍼 `~/.claude/scripts/orca-browser.sh` 를 쓴다 — `orca` 는 **실패해도 종료 코드가 0** 이라 오류가 조용히 묻히는데, 헬퍼가 `ok:false` 를 종료 코드 1 로 바꿔 준다.

```bash
H=~/.claude/scripts/orca-browser.sh
PAGE=$($H open "<url>")               # 탭 생성 + 로드 완료 대기 → page id
$H js     "$PAGE" "<JS>"              # 페이지에서 JS 실행
$H waitjs "$PAGE" "<조건 JS>" 10000   # 조건이 참이 될 때까지 대기
$H url    "$PAGE"                     # 현재 URL
$H snap   "$PAGE"                     # 접근성 snapshot (ref=e1 형태)
$H nav    "$PAGE" "<url>"             # 이동 + 로드 완료 대기
$H close  "$PAGE"
```

실측으로 확인한 함정 두 가지:

- **`orca wait --load` 는 쓰지 않는다** — 이미 로드된 페이지에서도 항상 timeout 이다. 헬퍼의 `open`/`nav`/`waitjs` 를 쓴다.
- **`orca click`·`fill`·`select` 는 CSS 선택자를 받지 않고 snapshot ref 만 받는다** — hidden element 나 overlay 를 다룰 때는 `$H js` 로 `querySelector(...)` 를 직접 조작한다.

**주의**: OMC `/team`·`/omc-teams` 는 내부적으로 tmux 바이너리를 직접 호출하므로 tmux 는 별도로 설치돼 있어야 한다.

## 백그라운드 작업 대기 (sleep 금지)

`sleep N; <확인>` 패턴으로 백그라운드 작업 완료를 기다리지 않는다.
harness 가 `sleep` 선행 패턴을 차단하므로 처음부터 올바른 도구를 쓴다.

- **완료 대기** (한 번 알림): `run_in_background: true` 로 실행 → 완료 시 자동 알림.
- **조건 폴링** (반복 확인): `Monitor` 의 until-loop (`until <조건>; do sleep N; done`) → 조건 충족 시 알림.
- 배포·빌드·큐 비우기 등 외부 상태 대기는 모두 위 둘 중 하나로.

## 셸 환경: zsh `noclobber` 켜짐 (덮어쓰기 silent 실패)

이 사용자의 zsh 는 `noclobber` 가 켜져 있다.
이미 존재하는 파일에 `명령 > 기존파일` 로 리다이렉트하면 셸이 거부하고 (`file exists`), 그 명령의 출력이 파일에 **안 들어간다**.
거부돼도 기존 파일이 그대로 남아, 옛 내용을 새 내용으로 착각하는 묻혀버린 실패가 된다 (실측: 재생성해도 옛 내용이 그대로 유지됨).

- **기본**: 같은 경로에 다시 쓸 때는 먼저 `rm -f <경로>` 후 `>`, 또는 `>|` (zsh 강제 덮어쓰기) 를 쓴다.
- 이건 특정 도구 (`gh`·`dooray`·`mktemp`) 만의 문제가 아니라 **모든 `>` 리다이렉트에 적용되는 환경 특성**이다.
- 새 파일 생성은 영향 없다 — 기존 파일을 덮어쓸 때만 주의한다.
- heredoc (`cat > f <<EOF`) 도 `f` 가 이미 있으면 같은 함정. `cat >| f` 또는 사전 `rm`.

## 스킬 우선순위 (충돌 시)

1. **사용자 명시 지시** (본 CLAUDE.md, 프로젝트 지시, 직접 요청) — 최우선
2. **스킬 워크플로**
3. **기본 동작**

스킬이 "항상 X 하라"고 해도, 사용자가 "이번엔 X 하지 마"라고 하면 사용자를 따른다.

## 스킬 작성 규칙

스킬을 새로 만들거나 수정·검증할 때는 별도 rules 를 따른다.

- 스킬 **신규 생성·품질 검증** 시에는 `/skill-creator:skill-creator` 를 호출해 그 워크플로우(초안 → 테스트 → 평가 → 개선)를 따른다. 사소한 오타 수정은 예외.
- 반복 레시피는 SKILL.md inline 이 아니라 `scripts/` 로 분리한다 (5줄 초과 / heredoc / 매 실행 반복 중 하나면 분리).

구조·progressive disclosure·description 작성·문체·검증 전체: @~/.claude/rules/skill-authoring.md

## File Operations

- 스킬·설정 파일은 반드시 올바른 프로젝트 디렉터리에 저장한다. 스킬 파일 작성 전 대상 경로를 먼저 확인한다.
- 사용자의 명시적 확인 없이 기존 스킬 파일을 삭제하지 않는다.

## 구현·산출물 review는 별도 lane에서 (self-approval 금지)

작성한 메인 세션이 같은 컨텍스트에서 자기 산출물을 직접 승인하지 않는다.
작성자가 곧 검토자이면 편향·놓침이 생기고, authoring 맥락에 갇혀 결함을 못 본다.

- task 파일, 구현 결과, PR diff의 review는 메인 세션이 직접 self-approve하지 말고 **별도 review agent(`code-reviewer`/`verifier`) 또는 팀(`/team`)에 위임**한다.
- 메인 세션은 위임 결과(GO/NO-GO 판정과 severity별 근거)를 받아 **merge/commit 판단만** 한다.
- 위임 프롬프트에 검토 대상(브랜치·diff·파일)과 검증 축을 명확히 전달한다. 위임한 review를 메인이 다시 처음부터 반복하지 않는다.
- **예외**: 별도 agent가 환경 제약(sandbox·권한·worktree 경로 차단)으로 대상에 접근할 수 없으면, 메인이 직접 검증하되 결과 보고에 *"독립 review 불가 — 메인 직접 검증"*임을 명시한다. 이때도 검증 근거(diff 실측·테스트·grep)는 반드시 남긴다.
- 이유: 같은 active 컨텍스트의 self-approval은 신뢰할 수 없다. 작성과 검토를 별도 lane으로 분리해야 결함이 드러난다.

## Git 커밋 규칙 — 관심사 단위 원자적 분리

커밋은 항상 **관심사 단위로 나눠서 원자적으로** 만든다. 한 커밋은 하나의 논리적 변경만 담는다. 모든 프로젝트에 공통 적용한다.

- 한 작업에서 서로 다른 관심사의 변경이 동시에 발생해도 **각각 별도 커밋**으로 분리한다 (예: 문서 본문 수정과 설정·룰 파일 수정 → 2개 커밋).
- 사용자가 "여기까지 커밋 푸시" 라고 해도 자동으로 한 커밋에 합치지 않는다. 변경 묶음을 먼저 식별하고 관심사별로 stage → commit 을 반복한다.
- 예외: 같은 관심사의 자명한 부산물은 한 커밋에 묶어도 된다 (예: HTML 과 그로부터 생성된 PDF, 새 문서와 해당 README 인덱스 갱신).
- 프로젝트에 자체 Git 커밋 규칙이 있으면 그쪽을 우선한다 (본 규칙은 기본값).

## 영속화 우선순위: CLAUDE.md > Memory

사용자가 새로운 규칙·취향·정정 사항을 알려주면 **1차로 본 CLAUDE.md (또는 적절한 프로젝트 CLAUDE.md) 에 기록**한다.

이유:
`~/.claude/projects/**/memory/` 의 auto memory 시스템은 사용자에게 블랙박스다.
잘못된 내용이 들어가도 사용자가 검토·수정하기 어렵다.

규칙:

- **기본값**: CLAUDE.md 에 추가. 사용자가 직접 읽고 수정·삭제할 수 있는 형태.
- **Memory 승격**: "CLAUDE.md 에 적었는데 잘 안 지켜지더라" 같은 신호가 있을 때만 별도 제안. 사용자 승인 후 진행.
- **예외**: 사용자가 "기억해줘", "memory 에 저장해줘" 같이 명시적으로 memory 를 지목한 경우.

## Content Preview (필수)

외부에 게시·등록되는 본문(Dooray 댓글·업무, GitHub 이슈·PR, 메일·슬랙, 위키)은 등록 전 반드시 미리보기를 보여준다. 사용자가 "미리보기"라고 명시하지 않아도 외부에 나갈 텍스트를 등록하려는 순간이면 적용한다. 로컬 파일 작성·코드 커밋은 대상 아님.

- **채팅 인라인 본문과 실제 렌더링 HTML 을 함께** 띄운다. `Write`/`Edit` 로 임시 파일에만 저장하면 내용이 숨겨져 사용자가 검토·수정할 수 없다.
- 순서: 본문 작성 → 자가 점검 → 미리보기(턴 종료) → 사용자 응답 → 등록.
- **미리보기와 `AskUserQuestion` 을 같은 턴에 묶지 않는다** — 모달이 본문을 가려 읽기 전에 결정을 강요한다.

절차·자가 점검 체크리스트·HTML 생성기(Dooray·GitHub) 사용법은 `content-preview` skill 을 연다.

## 채팅 응답의 다이어그램 — mermaid 는 렌더되지 않는다

채팅 세션은 ```mermaid``` 블록을 렌더하지 못하고 코드 그대로 보여 준다.
그래서 채팅 응답에 다이어그램을 넣으려는 순간, mermaid 로 적고 끝내지 말고 **HTML 로 가시화해 보여줄지 사용자에게 묻는다.**

- 적용 시점: 흐름·호출 관계·분기·시퀀스·아키텍처 계층을 채팅 응답 안에서 설명하려 할 때.
- 묻는 방법: 답변 본문은 글과 표로 먼저 전달하고, 끝에 HTML 가시화 여부를 확인한다.
  사용자가 이미 "html로 보여줘" 라고 했으면 묻지 않고 바로 만든다.
- 만들 때는 `Artifact` 로 게시한다. 설계 기준은 `artifact-design` skill 을 먼저 연다.
- 이건 채팅 응답에만 해당한다.
  GitHub·Dooray 같은 외부 게시물은 mermaid 를 렌더하므로 `@~/.claude/rules/markdown-readability.md` 의 "mermaid 우선" 규칙을 그대로 따른다.

## 질문·제안은 AskUserQuestion 으로

- 옵션·다음 단계·개선안을 제안할 때 평문 나열 대신 `AskUserQuestion` 을 쓴다.
  사용자가 클릭 한 번에 고르게 하는 것이 기본이다.
  - 권장안을 첫 번째에 두고 라벨 끝에 "(권장)" 을 표기한다.
  - 예외: 단순 yes/no 확인, 또는 사용자가 이미 방향을 명시한 경우.
- **질문 직전에 설명을 먼저 한다** — 옵션 description 만으로 처음 보는 개념·절차를 전달하려 하지 않는다.
- **처음 보는 개념·절차에 대한 결정이면 설명과 질문을 다른 턴으로 나눈다** — 같은 턴에 묶으면 모달이 본문을 가려 설명을 읽기 전에 결정을 강요한다.
- **산출물 형식 미명시 요청은 형식을 먼저 확인한다** — "X 만들어줘" / "Z 정리해줘" 류는 첫 도구 호출 전에 셋 중 무엇인지 묻는다.
  - (a) 응답 본문에 텍스트로만 표시
  - (b) 파일로 저장
  - (c) 파일 저장 후 commit·push
  - 예외: "파일 만들어서 커밋해줘" 처럼 형식까지 지시받은 경우.

## General Rules

- **사용자가 영역을 지목하면 그 영역부터** — 넓게 코드베이스 탐색 금지. 사용자가 이미 방향을 제시한 경우 불필요하게 많은 파일을 읽지 않는다.

### 마크다운 가독성 + 작성 함정

문서·docs·skill·외부 게시물(GitHub PR·Dooray·메일 등) 의 마크다운 가독성 규칙은 단일 소스로 분리되어 있다.
담긴 내용은 세 가지다.

- 형식 10규칙과 자가 점검
- 작성 함정 (`~` 취소선, `§`, heredoc escape)
- 내용 slop 방지 (중복, 과잉, padding)

@~/.claude/rules/markdown-readability.md

### 한국어 표현 정책

한국 사용자가 한 번에 의미를 파악하기 어려운 외래어·전문용어는 사용자 응답·docs·skill 작성 모두에서 사용하지 않는다.
기술 식별자 (폴더명, 슬래시 커맨드, 코드 심볼, 경로) 는 그대로 둔다 — 한국어 prose 만 정리한다.

외래어 매핑 표·영문 관용 유지·문장 종결 규칙·자가 점검: @~/.claude/rules/korean-style.md
프로젝트 고유 매핑은 각 프로젝트의 `korean-style.md` 가 위 글로벌 규칙에 더한다 (있을 때만).

### AskUserQuestion 한국어 표기 — native UTF-8 강제

`AskUserQuestion` 의 한국어(`question`/`header`/`label`/`description`)는 **native UTF-8 그대로** 타이핑한다.
Edit/Write 에 문자열 쓰듯 완성된 한글을 그대로 옮긴다.

**위험한 것은 escape 자체가 아니라 hex 를 손으로 계산하는 것이다.**
JSON 파서는 `한` 과 `한` 을 같은 값으로 읽으므로, 정확히 쓰면 escape 는 무해하다.
문제는 계산을 틀렸을 때다. 결과가 문법적으로 정상인 한글이라 깨진 것으로 보이지 않고 **단어만 틀린다.**
2026-07-29 세션에서 "브"(`브`) 대신 `버` 를 써서 "서브에이전트" 가 "서버에이전트" 로 나갔다.
같은 세션에서 여섯 번 연속 어기고, 지적받아 설명한 직후에도 한 번 더 반복했다.

- **근본 차단**: "이 글자를 `\uXXXX` 로 어떻게 쓰지" 라는 생각이 스치면 그게 위반 신호다. hex 계산 시도 자체를 하지 않는다.
- **자가 점검 (전송 직전)**: payload 를 그대로 읽어 자연스러운 한국어인지 확인한다. 영문 기술 용어(`Spring` 등)는 그대로 둔다.
- **훅으로 막을 수 없다 (실측)**: JSON 파서가 escape 를 디코딩한 뒤 훅에 넘기므로, payload 에는 escape 가 하나도 남지 않는다.
  `\u` 를 찾는 `PreToolUse` 훅을 붙여 확인했고 payload 의 백슬래시 개수가 0 이었다.
  기계적 차단을 다시 제안하지 않는다 — 남은 수단은 작은 모델이 단어의 실재성을 판정하는 `prompt` 훅뿐이고, 그것도 확률적이다.

## 사용자 배경

사용자는 딥러닝·모델 지식이 없는 **백엔드 개발자**다. 한국 Java 개발자 스타일에 익숙하고 Python 경험은 적다.
머신러닝·모델 얘기가 나오면 아래 방식으로 전달한다.

- 딥러닝 용어(AMP, FP16, activation, backbone 등)는 Java·백엔드 개념에 빗대어 푼다.
  - 예: FP16 → "숫자 정밀도를 double 대신 float 처럼 낮춰 메모리 절반·속도 향상".
  - 예: activation 메모리 → "함수 호출 스택에 쌓이는 임시 변수가 차지하는 메모리".
- Python 문법은 생략하지 말고 Java 와 다른 점 위주로 최소한 짚는다.
- 코드를 보여줄 때 "왜"를 백엔드 관점(리소스 관리, 설정값 스위치, 배포 영향)으로 설명한다.
- 과한 수학·모델 이론은 피하고, 실무 영향(속도·메모리·정확도 트레이드오프)을 결론 위주로 전달한다.

## 개인 Brain (fos-brain) 연동

사용자는 `~/personal/fos-brain` 에 Karpathy 스타일 개인 지식 기반(brain)을 운영한다.
두 네임스페이스 — `public`(루트 `wiki/`·`raw/`), `private/` — 로 나뉘며 뒤쪽은 gitignore 다. (사내 팀 지식은 brain 이 아니라 nbrain/Dooray 위키에 둔다.)
검색은 qmd MCP 서버(`qmd-brain`)가 모든 세션에 상시 제공한다.

### 검색 방법 (how)

- **도구**: qmd MCP `qmd-brain` (상시 제공 — 컬렉션·쿼리 타입·예시는 MCP 서버 지침 참조). MCP 없으면 qmd CLI. 워크플로는 `brain-search` skill.
- **컬렉션**: `brain-wiki`·`brain-raw` (공개), `brain-private` (로컬 전용).
- **라우팅**: 검색 전 각 네임스페이스 `wiki/INDEX.md` (살아있는 카탈로그)로 후보 영역을 잡고 qmd 로 좁힌다.
- **qmd 복구**: `better-sqlite3 재컴파일` 류 에러는 node ABI 불일치 — `touch ~/.bun/install/global/node_modules/@tobilu/qmd/bun.lock` 로 복구 시도 (원리는 `~/personal/fos-brain/CLAUDE.md` "런타임 함정").

### 자동 참조 (search)

다음 상황에서는 답하기 전에 brain 을 먼저 조회한다 (qmd MCP `qmd-brain` 또는 `brain-search` skill):

- 사용자의 과거 결정·취향·업무 스타일·학습 내용이 답에 영향을 줄 수 있을 때
- "예전에", "내 스타일", "전에 정했던", "내가 어떻게 했더라" 류의 질문
- 사용자의 다른 프로젝트·하네스·컨벤션을 참고해야 할 때
- **환경 고유 값을 확신 없이 추측하려는 순간** (프로파일·appkey·프로젝트 코드·호스트명·계정·경로 등) — 토픽이 아니라 "추측하려는 나 자신"이 신호다. 코드·문서에서 확인 안 되면 추측 전 brain 먼저. 단 이런 사실이 해당 프로젝트 CLAUDE.md 에 이미 적혀 있으면 그쪽이 우선이고 조회 불필요.

무관한 일반 코딩 작업에는 끼어들지 않는다 (brain 이 답을 더 좋게 만들 때만 참조).
인용 시 출처 페이지와 네임스페이스를 밝힌다. 비공개(private) 내용을 공개 맥락에 노출하지 않는다.

### 승인형 등록 (add) — 자동 쓰기 금지

세션에서 **재사용 가치가 있는 durable 지식**(의사결정·패턴·학습·취향·업무 방식)이 나오면 brain 등록을 *제안*한다.

- **절대 사용자 승인 없이 brain 에 쓰지 않는다.**
- 순서: 핵심 요약 미리보기(채팅 인라인) → 어느 네임스페이스에 넣을지 포함해 `AskUserQuestion` 으로 확인 → 승인 시에만 `brain-add` 실행.
- 등록 후 INDEX·log 갱신, public 변경이면 commit·push 까지는 별도 승인 절차를 따른다.
- 일시적·세션 한정 정보는 등록하지 않는다 (brain 은 compounding 자산).

자세한 워크플로우는 `brain-add` / `brain-search` / `brain-lint` skill 과 `~/personal/fos-brain/CLAUDE.md` 스키마를 따른다.

## 사내 지식 (nbrain) 연동

회사 규칙·사내 지식은 `nbrain` skill 로 조회한다.
NHN 사내 VectorSearch API 로 Dooray 위키·업무·드라이브를 시맨틱 검색하는 팀 공용 스킬이다 (`AiSdtSkill` 레포, `~/.claude/skills/nbrain` symlink 설치).
개인 종속값(사번·space)은 `~/.claude/nbrain.config.json` 에 있다.

### fos-brain ↔ nbrain 경계

- **개인·크로스프로젝트 지식** (내 결정·취향·학습·다른 프로젝트 컨벤션) → `fos-brain` (qmd).
- **사내 지식·회사 규칙** (Dooray 업무·위키, 팀 컨벤션, 사내 시스템) → `nbrain`.

### 언제 nbrain 을 조회하나

답하기 전에 nbrain 을 먼저 조회한다:

- 회사·팀 고유 규칙이 답에 영향을 줄 때 — Dooray 업무·PR 제목 컨벤션, 태그·CC 규칙, 사내 배포·인프라 관례.
- 사내 시스템·과거 업무·팀 결정을 참고해야 할 때 ("예전 업무", "사내에서", "팀에서 어떻게").
- 사내 고유 값을 확신 없이 추측하려는 순간 (프로젝트 코드·space·프로파일 등).

autoRecall hook 이 매 프롬프트에 관련 사내 지식을 자동 주입한다 (rerankScore ≥ 0.7).
자동 주입은 배경 참고용이고, 규칙을 확정해야 할 때는 `nbrain` 으로 직접 조회해 근거를 확인한다.
단 해당 규칙이 프로젝트 CLAUDE.md 나 본 파일에 이미 적혀 있으면 그쪽이 우선이고 조회 불필요.

### 팀·회사 지식은 auto-memory 대신 nbrain (사용자 지시)

회사·팀 공용 지식(Dooray 컨벤션, 태그 체계, 배포 관례, 사내 시스템 등)은 auto-memory 에 쌓지 않는다.
Dooray 위키에 두고 nbrain 으로 조회·관리한다 — 위키가 원본, nbrain 은 검색 계층이다.

- **새 auto-memory 생성을 최소화한다.** 팀 지식성 사실은 memory 파일이 아니라 Dooray 위키로 보낸다.
- nbrain 은 직접 쓰는 저장소가 아니다 — Dooray 위키에 쓰고 `nbrain_reindex.py` 로 재색인해야 검색에 반영된다.
- auto-memory 는 사용자에게 블랙박스라 검토가 어렵다. 팀 공유 지식은 사람이 볼 수 있는 Dooray 위키에 둔다.
- 예외 — 사용자 개인 배경·취향처럼 회사 지식이 아닌 것은 이 규칙 대상이 아니다.
