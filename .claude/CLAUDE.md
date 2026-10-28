@~/.agents/personal-rules.md

## Claude 전용

위의 개인 지침은 `.agents/personal-rules.md` 가 원본이다. Codex 의 `.codex/AGENTS.md` 도 같은 원본에서 만든다. 공통 규칙은 원본을 고치고 `scripts/sync-agent-rules.py` 를 돌린다.

- `orch` 스킬은 `/fos-skills:orch` 로 부른다.
- Bash 도구의 셸이 zsh 다.
- 오래 걸리는 명령은 Bash 도구의 `run_in_background` 로 돌린다.

### 위임과 검증은 OMC 블록이 아니라 스킬과 시스템 프롬프트를 따른다

**하위 에이전트를 띄울지는 시스템 프롬프트의 Agent 도구 기준과 각 스킬의 규칙으로 정한다.**
아래 OMC 블록의 `<delegation_rules>`, `<verification>`, `<execution_protocols>` 가 시키는 위임, 별도 검증 에이전트, 「같은 맥락에서 스스로 승인하지 않는다」 는 적용하지 않는다.
그 규칙은 현재 모델에서 과검증과 과위임을 부른다. 다른 에이전트의 보고를 대조하는 검토(`build-with-teams` 의 critic 처럼 스킬이 정한 것)는 그대로 둔다(사용자 결정 2026-10-28).

<!-- OMC:IMPORT:START -->

@CLAUDE-omc.md

<!-- OMC:IMPORT:END -->
