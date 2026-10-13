#!/usr/bin/env python3
"""저장소의 작업 현황 파일(board.json)을 고친다. work-board mod 가 이 파일을 읽어 /board 창에 보여 준다.

파일 위치: git 루트의 .omc/board.json. 이미 .omc/handoffs/board.json 이 있으면 그것을 쓴다. --file 로 바꿀 수 있다.

사용:
  board.py set <id> [<status>] [--title T] [--owner O] [--pr P] [--next N] [--worktree W] [--progress N/M] [--detail D ...]
  (--worktree 는 그 항목을 맡은 worker 의 워크트리 이름이다. 창이 그 worker 상태를 항목 아래에 붙인다)
  (값을 '' 로 주면 그 칸을 지운다. --detail 은 여러 번 줄 수 있고 주면 하위 항목 전체를 바꾼다. --detail '' 은 지운다)
  board.py step <id> <n> [--undo]   (n 번 단계 줄 앞에 「✓ 」 를 붙인다. --undo 는 뗀다)
  board.py del <id>
  board.py list
status: goal(목표) | decide(결정 필요) | doing(진행 중) | wait(대기) | done(완료)
진행률은 단계 줄에서 센다. --progress 는 단계로 나타낼 수 없을 때만 쓴다
  하위 줄을 「1 …」, 끝나면 「✓ 1 …」 로 쓰면 창이 숫자로 시작하는 줄을 세어 진행 표시줄을 그린다. 참고 줄은 세지 않는다
  --progress N/M 은 「끝낸 단계/전체 단계」 (예: 7/10) 를 직접 적고 단계 수보다 앞선다. 주지 않으면 기존 값을 지우지 않는다
  --progress auto 는 값을 지워 단계 수로 세게 한다
"""
import argparse, datetime, json, os, re, subprocess, sys

STATUSES = ('goal', 'decide', 'doing', 'wait', 'done')

def board_path(explicit):
    if explicit:
        return explicit
    try:
        root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        root = os.getcwd()
    legacy = os.path.join(root, '.omc/handoffs/board.json')
    return legacy if os.path.exists(legacy) else os.path.join(root, '.omc/board.json')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('set', 'step', 'del', 'list'))
    ap.add_argument('id', nargs='?')
    ap.add_argument('status', nargs='?')
    ap.add_argument('--undo', action='store_true')
    for key in ('title', 'owner', 'pr', 'next', 'worktree', 'progress'):
        ap.add_argument('--' + key)
    ap.add_argument('--detail', action='append')
    ap.add_argument('--file')
    a = ap.parse_args()
    path = board_path(a.file)
    board = json.load(open(path)) if os.path.exists(path) else {'items': []}
    if a.cmd == 'list':
        for item in board['items']:
            print(item.get('status', '?').ljust(7), item['id'].ljust(16), item.get('title', ''))
        return
    if not a.id:
        sys.exit('id 가 필요하다')
    if a.cmd == 'step':
        item = next((i for i in board['items'] if i['id'] == a.id), None)
        if item is None:
            sys.exit('항목이 없다: ' + a.id)
        if not (a.status or '').isdigit():
            sys.exit('step 에는 단계 번호가 필요하다')
        number = int(a.status)
        details = item.get('details') or []
        for index, line in enumerate(details):
            m = re.match(r'^(✓ )?(\d+) ', line)
            if m and int(m.group(2)) == number:
                body = line[len('✓ '):] if m.group(1) else line
                details[index] = body if a.undo else '✓ ' + body
                break
        else:
            sys.exit('%d 번 단계 줄이 없다' % number)
    elif a.cmd == 'del':
        board['items'] = [i for i in board['items'] if i['id'] != a.id]
    else:
        item = next((i for i in board['items'] if i['id'] == a.id), None)
        if item is None:
            if not a.status:
                sys.exit('새 항목에는 status 가 필요하다')
            item = {'id': a.id, 'title': a.title or a.id}
            board['items'].append(item)
        if a.status:
            if a.status not in STATUSES:
                sys.exit('status 는 %s 중 하나다' % '|'.join(STATUSES))
            item['status'] = a.status
        for key in ('title', 'owner', 'pr', 'next', 'worktree', 'progress'):
            value = getattr(a, key)
            if value == '' or (key == 'progress' and value == 'auto'):
                item.pop(key, None)
            elif value is not None:
                item[key] = value
        if a.detail is not None:
            lines = [d for d in a.detail if d]
            if lines:
                item['details'] = lines
            else:
                item.pop('details', None)
    board['updatedAt'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(board, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

if __name__ == '__main__':
    main()
