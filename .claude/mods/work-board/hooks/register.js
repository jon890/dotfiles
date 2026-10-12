// 저장소의 작업 현황 파일(board.json)을 읽어 창과 상태 줄에 보여 준다.
// 파일 위치는 BOARD_PATHS 순서로 찾는다. 갱신은 플러그인의 bin/board.py 가 한다.
// 파일 형식: { updatedAt: ISO 문자열, items: [{ id, title, status, owner?, pr?, next?, details?: string[] }] }
// status: decide(결정 필요), doing(진행 중), wait(대기), done(완료)

const PANE = 'work-board'
const BOARD_PATHS = ['.omc/board.json', '.omc/handoffs/board.json']
const SECTIONS = [
  { status: 'decide', label: '결정 필요', color: 'red', mark: '◆' },
  { status: 'doing', label: '진행 중', color: 'yellow', mark: '▶' },
  { status: 'wait', label: '대기', color: 'cyan', mark: '◇' },
  { status: 'done', label: '완료', color: 'green', mark: '✓' },
]

let board = null
let boardPath = ''
let raw = ''
let now = 0
let showDone = false

async function load($) {
  now = await $.clock.now()
  let found = ''
  let text = ''
  for (const candidate of BOARD_PATHS) {
    if (await $.fs.exists(candidate)) {
      found = candidate
      text = await $.fs.read(candidate)
      break
    }
  }
  if (!found) {
    if (board !== null || boardPath !== '') {
      board = null
      boardPath = ''
      raw = ''
      $.ui.status('')
      $.ui.invalidate('ui.render')
    }
    return
  }
  if (found === boardPath && text === raw) {
    $.ui.invalidate('ui.render')
    return
  }
  boardPath = found
  raw = text
  try {
    board = JSON.parse(text)
  } catch (failure) {
    board = { items: [], error: String(failure && failure.message ? failure.message : failure) }
  }
  const items = Array.isArray(board.items) ? board.items : []
  const count = (status) => items.filter((item) => item.status === status).length
  const decide = count('decide')
  $.ui.status((decide > 0 ? '결정 필요 ' + decide + ' · ' : '') + '진행 ' + count('doing') + ' · 대기 ' + count('wait')
    + ' · 완료 ' + count('done') + '   /board')
  $.ui.invalidate('ui.render')
}

function ago(iso) {
  const at = Date.parse(iso || '')
  if (!at) return iso || '-'
  const minutes = Math.max(0, Math.round((now - at) / 60000))
  if (minutes < 1) return '방금'
  if (minutes < 60) return minutes + '분 전'
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return hours + '시간 전'
  return Math.floor(hours / 24) + '일 전'
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    await load($)
    $.clock.every(5000, () => load($))
    await $.command.register({ name: 'board', description: '작업 현황 창 열기', immediate: true })
    return next(e)
  })

  on('command.run', { command: 'board' }, async ($) => {
    await load($)
    await $.ui.open({ id: PANE, title: '작업 현황', closeOnEscape: true })
    return {}
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)

    if (!board) {
      return Box({
        flexDirection: 'column',
        gap: 1,
        children: [
          Text({ bold: true, children: ['이 저장소에는 작업 현황 파일이 없습니다.'] }),
          Text({ dimColor: true, wrap: 'wrap', children: [BOARD_PATHS.join(' 또는 ') + ' 를 찾습니다.'] }),
          Text({ dimColor: true, wrap: 'wrap', children: ['만들기: python3 ~/.claude/mods/work-board/bin/board.py set <id> doing --title "..."'] }),
        ],
      })
    }

    const items = Array.isArray(board.items) ? board.items : []

    const itemView = (item, section) => {
      const meta = [item.owner, item.pr].filter(Boolean)
      const done = section.status === 'done'
      return Box({
        key: 'item-' + item.id,
        flexDirection: 'column',
        children: [
          Box({
            flexDirection: 'row',
            columnGap: 1,
            children: [
              Text({ color: section.color, children: [section.mark] }),
              done
                ? Text({ dimColor: true, wrap: 'wrap', children: [item.title || item.id] })
                : Text({ bold: true, wrap: 'wrap', children: [item.title || item.id] }),
            ],
          }),
          ...(meta.length ? [Text({ dimColor: true, wrap: 'wrap', children: ['  ' + meta.join('  ·  ')] })] : []),
          ...(!done && Array.isArray(item.details)
            ? item.details.map((line, i) => Text({ key: 'd-' + i, wrap: 'wrap', children: ['  • ' + line] }))
            : []),
          ...(item.next && !done ? [Text({ wrap: 'wrap', children: ['  → ' + item.next] })] : []),
        ],
      })
    }

    const sectionView = (section) => {
      const rows = items.filter((item) => item.status === section.status)
      if (rows.length === 0) return []
      const collapsed = section.status === 'done' && !showDone
      return [
        Box({
          key: 'section-' + section.status,
          flexDirection: 'column',
          borderStyle: 'round',
          padding: 1,
          gap: 1,
          children: [
            Text({ bold: true, color: section.color, children: [section.label + '  ' + rows.length] }),
            ...(collapsed
              ? [Text({ dimColor: true, children: ['d 를 누르면 펼칩니다'] })]
              : rows.map((item) => itemView(item, section))),
          ],
        }),
      ]
    }

    return Box({
      flexDirection: 'column',
      gap: 1,
      children: [
        Box({
          flexDirection: 'row',
          columnGap: 2,
          children: [
            Text({ dimColor: true, children: ['갱신 ' + ago(board.updatedAt) + '  ·  ' + boardPath] }),
            Button({
              key: 'toggle-done',
              label: showDone ? '완료 접기' : '완료 펼치기',
              hotkey: 'd',
              plain: true,
              onPress: () => {
                showDone = !showDone
                $.ui.invalidate('ui.render')
              },
            }),
          ],
        }),
        ...(board.error ? [Text({ color: 'red', wrap: 'wrap', children: ['board.json 을 읽지 못했습니다: ' + board.error] })] : []),
        ...SECTIONS.flatMap(sectionView),
      ],
    })
  })
}
