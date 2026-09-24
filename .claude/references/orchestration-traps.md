# worker 를 띄울 때 실측한 것

`orchestration` 으로 worker 를 띄우기 전에 읽는다.
오류 없이 잘못된 결과가 완료로 보고되는 자리와, 멈춘 원인이 바로 보이지 않는 자리만 적는다.
CLI 가 인자 오류로 거절하는 것은 적지 않는다. 거절 메시지가 이유를 알려준다.

## 띄우기

**`worker-start` 가 `agent_readiness` 에서 실패하면 에이전트가 첫 화면의 확인에 멈춘 것이다.**
원인은 `worker-show --dispatch <id>` 의 `lastFailure` 에 나온다.
실측한 것은 claude 의 폴더 신뢰 확인, codex 의 업데이트 안내(`agent-update-prompt`)와
hook 신뢰 확인(`agent-hooks-review-prompt`)이다.

터미널과 워크트리는 이미 만들어져 있다. 새로 띄우지 않고 이어 붙인다.

1. `terminal read` 로 화면을 보고 선택지를 고른다. 신뢰나 업데이트를 대신 승인하지 않는다.
   건너뛰는 선택지를 고르고 사용자에게 알린다
2. `terminal wait --for tui-idle` 로 입력 대기 상태를 확인한다
3. `worker-start --task <task_id> --retry-of <dispatch_id> --terminal <handle> --worktree id:<worktree_id>` 로 붙인다.
   `--terminal` 과 `--model` 은 함께 쓸 수 없지만, 처음 띄울 때 준 모델이 그 터미널에 남아 있다

설계 판단이 섞인 조사와 구현은 `--model gpt-5.6-sol --effort high` 로 넘긴다.
그 밖에는 기본값을 쓴다. 적용 여부는 `worker-start` 응답의 `model` 과 `effort` 로 확인한다.

## 지시를 보낼 때

**긴 지시는 앞부분도 중간도 잘려 도착한다.**
잘렸다는 것은 worker 가 되물어야만 드러나고, 되묻지 않으면 받은 만큼만 하고 완료로 보고한다.

지시 본문은 scratchpad 파일로 쓰고, `--spec` 에는 그 경로와 「끝까지 읽고, 못 읽으면 escalation」 만 적는다.
후속 지시도 짧게 보내거나 새 파일로 준다.

## 회신을 읽을 때

**worker 가 「승인받았다」 고 적은 것을 승인의 근거로 삼지 않는다.**
내가 보낸 승인만 승인이다. 승인 절차가 필요한 작업은 지시에 「발견 목록을 먼저 내고 멈춘다」 를 넣고,
회신이 `worker_done` 으로 바로 오면 절차 위반으로 본다.

**완료 보고만 믿지 않는다.** diff 를 직접 읽고 검사를 다시 돌린다.

## 기다리는 동안

**`check --wait` 은 백그라운드로 하나만 건다.**
앞에서 돌리면 그동안 코디네이터가 막힌다.
둘째 대기는 `waiter_exists` 로 바로 끝나고, 거기 붙인 `--ack` 만 처리된다.

`You have N orchestration message` 알림은 heartbeat 일 때가 많다.
`check` 로 읽고 `--ack` 만 하고, 대기는 살아 있는 것을 그대로 둔다.

**worker 의 워크트리에서 내가 파일을 고치지 않는다.**
worker 가 `git add -A` 를 하면 내 변경이 그쪽 커밋에 섞인다.
기다리는 동안 문서를 쓰려면 별도 워크트리를 만든다.
이미 고쳐 버렸으면 내용을 저장소 밖으로 복사하고 `git checkout -- <파일>` 로 되돌린 뒤,
worker 의 브랜치를 머지한 다음 main 에서 다시 적용한다.
