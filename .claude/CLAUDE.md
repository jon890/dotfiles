@~/.agents/personal-rules.md

## Claude 전용

위의 개인 지침은 `.agents/personal-rules.md` 가 원본이다. Codex 의 `.codex/AGENTS.md` 도 같은 원본에서 만든다. 공통 규칙은 원본을 고치고 `scripts/sync-agent-rules.py` 를 돌린다.

### 언어와 메모리

- 응답과 질문(AskUserQuestion 의 질문, 선택지, 설명 포함), 보고는 모두 한국어로 쓴다. 하위 에이전트나 worker 가 영어로 보고해도 한국어로 옮겨 전한다(사용자 결정 2026-11-23).
- 자동 메모리(메모리 폴더와 `MEMORY.md`)를 쓰지 않는다. 사용자가 정한 규칙은 지침 문서에 둔다(사용자 결정 2026-11-23).

### 세션 환경

- fos-skills 플러그인을 갱신한 뒤에는 재시작을 권하지 않고 `/reload-plugins` 를 쳐 달라고 한다. 상주 루프(orch-loop)는 별도 프로세스라 따로 다시 띄운다(옛 자동 메모리에서 옮김, 2026-11-24).
- `claude --resume` 뒤 Bash 의 `ORCA_TERMINAL_HANDLE` 이 옛 값이면 orca orchestration 이 `no_active_sender_terminal` 로 거절한다. `orca terminal list --json` 으로 이 저장소의 내 터미널을 찾아 `orca orchestration run-use --id <run> --from <h>` 로 다시 묶고 이후 Bash 앞에 `export ORCA_TERMINAL_HANDLE=<h>` 를 둔다.

### 위임과 검증은 OMC 블록이 아니라 스킬과 시스템 프롬프트를 따른다

**하위 에이전트를 띄울지는 시스템 프롬프트의 Agent 도구 기준과 각 스킬의 규칙으로 정한다.**
아래 OMC 블록의 `<delegation_rules>`, `<verification>`, `<execution_protocols>` 가 시키는 위임, 별도 검증 에이전트, 「같은 맥락에서 스스로 승인하지 않는다」 는 적용하지 않는다.
그 규칙은 현재 모델에서 과검증과 과위임을 부른다. 다른 에이전트의 보고를 대조하는 검토(`plan` 의 critic 처럼 스킬이 정한 것)는 그대로 둔다(사용자 결정).

<!-- OMC:IMPORT:START -->

@CLAUDE-omc.md

<!-- OMC:IMPORT:END -->
