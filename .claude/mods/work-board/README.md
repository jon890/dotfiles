# work-board

저장소의 작업 현황을 Claude Code 창으로 본다. 코디네이터(에이전트)가 상태를 갱신하고, 사람은 `/board` 로 본다.

- 창: `/board`. 결정 필요, 진행 중, 대기, 완료 순으로 묶는다. `d` 로 완료를 펼친다
- 상태 줄: 프롬프트 아래에 개수 요약이 5초마다 갱신된다. 파일이 없는 저장소에서는 나오지 않는다
- 파일: git 루트의 `.omc/board.json` (예전 위치 `.omc/handoffs/board.json` 도 읽는다)
- 항목: 제목, 담당·PR, 하위 항목(details), 다음 할 일(next)
- 갱신: `python3 ~/.claude/mods/work-board/bin/board.py set <id> doing --title "..." --next "..."`

설치: `~/.claude/mods` 를 로컬 마켓플레이스(`local-mods`)로 등록하고 `claude plugin install work-board@local-mods`.
고친 뒤에는 `plugin.json` 의 version 을 올리고 `claude plugin update work-board@local-mods` 후 `/reload-plugins`.
