# work-board

저장소의 작업 현황을 Claude Code 창으로 본다. 코디네이터(에이전트)가 상태를 갱신하고, 사람은 `/board` 로 본다.

- 창: `/board`. 결정 필요, 진행 중, 대기, 완료 순으로 묶는다. `d` 로 완료를 펼친다
- 상태 줄: 프롬프트 아래에 개수 요약이 5초마다 갱신된다. 파일이 없는 저장소에서는 나오지 않는다
- 파일: git 루트의 `.omc/board.json` (예전 위치 `.omc/handoffs/board.json` 도 읽는다)
- 항목: 제목, 담당·PR, 하위 항목(details), 다음 할 일(next), 워크트리(worktree)
- 워커: `orca orchestration worker-list` 를 15초마다 읽어 항목의 worktree 와 같은 이름의 워커 상태를 붙인다. 이 저장소에서 돌지만 어느 항목에도 없는 워커는 「항목에 없는 워커」 로 모은다
- 진행률: 하위 항목(details)에서 숫자로 시작하는 단계(「1 …」, 끝나면 「✓ 1 …」)를 세어 진행 표시줄을 그린다. 참고 줄은 세지 않고, 단계가 없으면 그리지 않는다. `progress` 필드(「7/10」)가 있으면 그 값이 우선한다. 단계로 나타낼 수 없을 때만 쓴다
- 단계 끝내기: `board.py step <id> <n>` 이 n 번 단계 앞에 「✓ 」 를 붙인다(`--undo` 로 뗀다). `set --progress auto` 는 `progress` 값을 지워 단계 수로 세게 한다
- 갱신: `python3 ~/.claude/mods/work-board/bin/board.py set <id> doing --title "..." --next "..."`

설치: `~/.claude/mods` 를 로컬 마켓플레이스(`local-mods`)로 등록하고 `claude plugin install work-board@local-mods`.
고친 뒤에는 `plugin.json` 의 version 을 올리고 `claude plugin update work-board@local-mods` 후 `/reload-plugins`.
version 을 올리면 dotfiles 저장소(`~`)에 커밋하고 push 까지 한다. 테스트는 `tests/*.test.ts` 만 추적한다.
