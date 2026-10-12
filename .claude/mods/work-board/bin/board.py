#!/usr/bin/env python3
"""저장소의 작업 현황 파일(board.json)을 고친다. work-board mod 가 이 파일을 읽어 /board 창에 보여 준다.

파일 위치: git 루트의 .omc/board.json. 이미 .omc/handoffs/board.json 이 있으면 그것을 쓴다. --file 로 바꿀 수 있다.

사용:
  board.py set <id> [<status>] [--title T] [--owner O] [--pr P] [--next N] [--detail D ...]
  (값을 '' 로 주면 그 칸을 지운다. --detail 은 여러 번 줄 수 있고 주면 하위 항목 전체를 바꾼다. --detail '' 은 지운다)
  board.py del <id>
  board.py list
status: decide(결정 필요) | doing(진행 중) | wait(대기) | done(완료)
"""
import argparse, datetime, json, os, subprocess, sys

STATUSES = ('decide', 'doing', 'wait', 'done')

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
    ap.add_argument('cmd', choices=('set', 'del', 'list'))
    ap.add_argument('id', nargs='?')
    ap.add_argument('status', nargs='?', choices=STATUSES)
    for key in ('title', 'owner', 'pr', 'next'):
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
    if a.cmd == 'del':
        board['items'] = [i for i in board['items'] if i['id'] != a.id]
    else:
        item = next((i for i in board['items'] if i['id'] == a.id), None)
        if item is None:
            if not a.status:
                sys.exit('새 항목에는 status 가 필요하다')
            item = {'id': a.id, 'title': a.title or a.id}
            board['items'].append(item)
        if a.status:
            item['status'] = a.status
        for key in ('title', 'owner', 'pr', 'next'):
            value = getattr(a, key)
            if value == '':
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
