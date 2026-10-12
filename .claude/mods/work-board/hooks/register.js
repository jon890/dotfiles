// 저장소의 작업 현황을 창과 상태 줄에 보여 준다.
// 두 곳에서 읽는다.
//   1. 수동 항목: 저장소의 board.json(BOARD_PATHS 순서로 찾는다). 갱신은 플러그인의 bin/board.py 가 한다.
//      형식: { updatedAt: ISO 문자열, items: [{ id, title, status, owner?, pr?, worktree?, next?, details?: string[] }] }
//      worktree 는 그 항목을 맡은 worker 의 워크트리 이름이다. 창이 그 worker 상태를 항목 아래에 붙인다.
//      status: goal(목표), decide(결정 필요), doing(진행 중), wait(대기), done(완료)
//      progress 는 「끝낸 단계/전체 단계」(예: 7/10)이고 진행 표시줄로 그린다.
//   2. 실제 상태: orca orchestration(이 세션이 묶인 run 의 worker 와 답을 기다리는 질문)과 gh(열린 PR, CI).
// 파일은 FILE_MS, 명령은 LIVE_MS 마다 다시 읽는다. 창에서 r 을 누르면 명령을 바로 다시 읽는다.

const PANE = 'work-board'
const BOARD_PATHS = ['.omc/board.json', '.omc/handoffs/board.json']
const FILE_MS = 5000
const LIVE_MS = 45000
const COMMAND_TIMEOUT_MS = 20000
const SECTIONS = [
  { status: 'goal', label: '목표', color: 'magenta', mark: '★' },
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

// 실제 상태. 읽지 못한 원천은 error 에 이유를 남기고 나머지는 그린다.
let live = { at: 0, runId: '', workers: null, questions: null, prs: null, errors: {} }
let liveBusy = false

// ---- 외부 명령 출력을 그릴 값으로 바꾸는 순수 함수(테스트가 직접 부른다) ----

// worker-list --json 의 결과에서 아직 일하는 worker 만 고른다.
export function parseWorkers(stdout) {
  const data = JSON.parse(stdout)
  const workers = (data && data.result && (data.result.workers || data.result.dispatches)) || []
  return workers
    .filter((w) => w.dispatchStatus === 'dispatched')
    .map((w) => {
      const tree = (w.resource && w.resource.worktreeId) || ''
      const path = tree.includes('::') ? tree.split('::').pop() : tree
      return { id: w.dispatchId, state: w.workerState || '', worktree: path.split('/').filter(Boolean).pop() || '' }
    })
}

// check --peek 의 출력에서 답을 기다리는 질문과 escalation 의 수를 센다.
// 본문에 제어 문자가 섞이면 JSON 으로 읽히지 않으므로 type 칸만 센다.
export function countQuestions(stdout) {
  const found = stdout.match(/"type"\s*:\s*"(question|escalation)"/g)
  return found ? found.length : 0
}

// gh pr list --json 의 결과를 PR 한 줄씩으로 바꾼다.
export function parsePullRequests(stdout) {
  const rows = JSON.parse(stdout)
  return rows.map((pr) => {
    const checks = Array.isArray(pr.statusCheckRollup) ? pr.statusCheckRollup : []
    let pass = 0
    let fail = 0
    let pending = 0
    for (const check of checks) {
      const result = String(check.conclusion || check.state || '').toUpperCase()
      if (result === 'SUCCESS' || result === 'SKIPPED' || result === 'NEUTRAL') pass += 1
      else if (result === 'FAILURE' || result === 'ERROR' || result === 'CANCELLED' || result === 'TIMED_OUT') fail += 1
      else pending += 1
    }
    return {
      number: pr.number,
      title: pr.title || '',
      branch: pr.headRefName || '',
      draft: Boolean(pr.isDraft),
      merge: pr.mergeStateStatus || '',
      pass,
      fail,
      pending,
    }
  })
}

// 워크트리 이름이 브랜치 이름이거나 그 끝(<owner>/<워크트리>)인 PR 을 worker 에 붙인다.
export function prFor(worker, prs) {
  if (!worker.worktree || !Array.isArray(prs)) return null
  return prs.find((pr) => pr.branch === worker.worktree || pr.branch.endsWith('/' + worker.worktree)) || null
}

// 항목의 worktree 와 이름이 같은 worker 를 찾는다.
export function workerFor(item, workers) {
  if (!item || !item.worktree || !Array.isArray(workers)) return null
  return workers.find((worker) => worker.worktree === item.worktree) || null
}

// 어느 항목(완료 제외)에도 붙지 않은 worker 만 고른다.
export function unmappedWorkers(items, workers) {
  if (!Array.isArray(workers)) return workers
  const claimed = new Set(items.filter((item) => item.status !== 'done' && item.worktree).map((item) => item.worktree))
  return workers.filter((worker) => !claimed.has(worker.worktree))
}

// worker 한 줄: 워크트리, 붙은 PR 과 CI, ready 가 아닌 상태.
export function workerLine(worker, prs) {
  const pr = prFor(worker, prs)
  return (worker.worktree || worker.id) + (pr ? '  #' + pr.number + ' ' + checkSummary(pr) : '')
    + (worker.state && worker.state !== 'ready' ? '  ' + worker.state : '')
}

// 「7/10」 을 진행 표시줄 한 줄로 바꾼다. 형식이 틀리면 null.
// 하위 항목 중 '✓' 로 시작하는 끝난 단계를 접는다. 펼치면 그대로, 접으면 끝난 단계 수를 한 줄로 앞에 둔다
export function detailLines(details, expanded) {
  if (expanded) return details.map((text) => ({ text }))
  const finished = details.filter((text) => text.startsWith('✓'))
  const rest = details.filter((text) => !text.startsWith('✓')).map((text) => ({ text }))
  return finished.length ? [{ folded: finished.length }, ...rest] : rest
}

export function progressBar(progress, width = 20) {
  const match = /^\s*(\d+)\s*\/\s*(\d+)\s*$/.exec(String(progress || ''))
  if (!match) return null
  const total = Number(match[2])
  const done = Math.min(Number(match[1]), total)
  if (total <= 0) return null
  const filled = Math.round((done / total) * width)
  return '█'.repeat(filled) + '░'.repeat(width - filled) + ' ' + done + '/' + total + ' (' + Math.round((done / total) * 100) + '%)'
}

// PR 한 줄의 CI 요약.
export function checkSummary(pr) {
  const total = pr.pass + pr.fail + pr.pending
  if (total === 0) return 'CI 없음'
  const parts = ['CI ' + pr.pass + '/' + total]
  if (pr.fail > 0) parts.push('실패 ' + pr.fail)
  if (pr.pending > 0) parts.push('진행 ' + pr.pending)
  return parts.join(' · ')
}

// 상태 줄 한 줄. 실제 상태와 수동 항목을 함께 센다.
export function statusLine(items, state) {
  const count = (status) => items.filter((item) => item.status === status).length
  const parts = []
  const decide = count('decide') + (state.questions || 0)
  if (decide > 0) parts.push('결정 필요 ' + decide)
  if (Array.isArray(state.workers)) parts.push('worker ' + state.workers.length)
  if (Array.isArray(state.prs)) {
    const failing = state.prs.filter((pr) => pr.fail > 0).length
    parts.push('PR ' + state.prs.length + (failing > 0 ? '(CI 실패 ' + failing + ')' : ''))
  }
  if (count('doing') > 0) parts.push('진행 ' + count('doing'))
  if (count('wait') > 0) parts.push('대기 ' + count('wait'))
  return parts.length === 0 ? '' : parts.join(' · ') + '   /board'
}

// ---- 읽기 ----

async function run($, argv) {
  const { exitCode, stdout, stderr } = await $.process.run(argv, { timeoutMs: COMMAND_TIMEOUT_MS })
  if (exitCode !== 0) throw new Error((stderr || stdout || '종료 코드 ' + exitCode).trim().split('\n')[0])
  return stdout
}

function refreshStatus($) {
  const items = board && Array.isArray(board.items) ? board.items : []
  $.ui.status(statusLine(items, live))
  $.ui.invalidate('ui.render')
}

async function loadFile($) {
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
    board = null
    boardPath = ''
    raw = ''
  } else if (found !== boardPath || text !== raw) {
    boardPath = found
    raw = text
    try {
      board = JSON.parse(text)
    } catch (failure) {
      board = { items: [], error: String(failure && failure.message ? failure.message : failure) }
    }
  }
  refreshStatus($)
}

async function loadLive($) {
  if (liveBusy) return
  liveBusy = true
  const next = { at: 0, runId: '', workers: null, questions: null, prs: null, errors: {} }
  try {
    try {
      const current = JSON.parse(await run($, ['orca', 'orchestration', 'run-current', '--json']))
      const runInfo = current && current.result && current.result.run
      next.runId = runInfo && runInfo.id ? runInfo.id : ''
    } catch (failure) {
      next.errors.workers = String(failure.message || failure)
    }
    if (next.runId) {
      try {
        next.workers = parseWorkers(await run($, ['orca', 'orchestration', 'worker-list', '--run', next.runId, '--json']))
      } catch (failure) {
        next.errors.workers = String(failure.message || failure)
      }
      try {
        next.questions = countQuestions(await run($, ['orca', 'orchestration', 'check', '--run', next.runId,
          '--peek', '--types', 'question,escalation', '--json']))
      } catch (failure) {
        next.errors.questions = String(failure.message || failure)
      }
    }
    try {
      next.prs = parsePullRequests(await run($, ['gh', 'pr', 'list', '--state', 'open', '--limit', '30',
        '--json', 'number,title,isDraft,mergeStateStatus,headRefName,statusCheckRollup']))
    } catch (failure) {
      next.errors.prs = String(failure.message || failure)
    }
    next.at = await $.clock.now()
    live = next
  } finally {
    liveBusy = false
  }
  refreshStatus($)
}

function ago(at) {
  const time = typeof at === 'number' ? at : Date.parse(at || '')
  if (!time) return '-'
  const minutes = Math.max(0, Math.round((now - time) / 60000))
  if (minutes < 1) return '방금'
  if (minutes < 60) return minutes + '분 전'
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return hours + '시간 전'
  return Math.floor(hours / 24) + '일 전'
}

// ---- 훅 ----

export function register(on) {
  on('session.start', async ($, e, next) => {
    await loadFile($)
    $.clock.every(FILE_MS, () => loadFile($))
    $.clock.every(LIVE_MS, () => loadLive($))
    loadLive($)
    await $.command.register({ name: 'board', description: '작업 현황 창 열기', immediate: true })
    return next(e)
  })

  on('command.run', { command: 'board' }, async ($) => {
    await loadFile($)
    loadLive($)
    await $.ui.open({ id: PANE, title: '작업 현황', closeOnEscape: true })
    return {}
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const items = board && Array.isArray(board.items) ? board.items : []

    const box = (key, color, label, children) => Box({
      key,
      flexDirection: 'column',
      borderStyle: 'round',
      padding: 1,
      gap: 1,
      children: [Text({ bold: true, color, children: [label] }), ...children],
    })
    const dim = (key, text) => Text({ key, dimColor: true, wrap: 'wrap', children: [text] })

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
          ...(progressBar(item.progress) ? [Text({ key: 'bar', color: section.color, children: ['  ' + progressBar(item.progress)] })] : []),
          ...(!done && item.worktree ? [workerFor(item, live.workers)
            ? Text({ key: 'w', color: 'yellow', wrap: 'wrap', children: ['  ⚙ worker ' + workerLine(workerFor(item, live.workers), live.prs)] })
            : Text({ key: 'w', dimColor: true, wrap: 'wrap', children: ['  ⚙ worker 없음 (' + item.worktree + ')'] })] : []),
          ...(!done && Array.isArray(item.details) ? detailLines(item.details, showDone).map((line, i) =>
            line.folded
              ? dim('d-' + i, '  ✓ 끝난 단계 ' + line.folded + '개 (d 를 누르면 펼쳐요)')
              : Text({ key: 'd-' + i, wrap: 'wrap', children: ['  • ' + line.text] })) : []),
          ...(item.next && !done ? [Text({ wrap: 'wrap', children: ['  → ' + item.next] })] : []),
        ],
      })
    }

    // 결정 필요: worker 질문 수와 수동 decide 항목
    const decideRows = items.filter((item) => item.status === 'decide')
    const questions = live.questions || 0
    const decideView = decideRows.length + questions === 0 ? [] : [box('live-decide', 'red',
      '결정 필요  ' + (decideRows.length + questions), [
        ...(questions > 0 ? [Text({ key: 'q', wrap: 'wrap', children: ['◆ worker 질문 ' + questions + '건이 답을 기다려요'] })] : []),
        ...decideRows.map((item) => itemView(item, SECTIONS[1])),
      ])]

    // worker: 이 세션이 묶인 run 에서 일하는 worker 중 어느 항목에도 붙지 않은 것
    const loose = unmappedWorkers(items, live.workers)
    const mapped = Array.isArray(live.workers) && Array.isArray(loose) ? live.workers.length - loose.length : 0
    const workerView = (live.workers === null || (mapped > 0 && loose && loose.length === 0)) && !live.errors.workers ? [] : [box('live-workers', 'yellow',
      (mapped > 0 ? '항목에 안 붙은 worker  ' : 'worker  ') + (loose ? loose.length : '-'),
      live.errors.workers
        ? [dim('we', '읽지 못했어요: ' + live.errors.workers)]
        : loose.length === 0
          ? [dim('w0', mapped > 0 ? '모든 worker 가 항목에 붙어 있어요' : '일하는 worker 가 없어요')]
          : loose.map((worker) => Text({ key: 'w-' + worker.id, wrap: 'wrap', children: ['▶ ' + workerLine(worker, live.prs)] })))]

    // 열린 PR: Draft/Ready, CI 요약, 머지 상태
    const prView = live.prs === null && !live.errors.prs ? [] : [box('live-prs', 'cyan',
      '열린 PR  ' + (live.prs ? live.prs.length : '-'),
      live.errors.prs
        ? [dim('pe', '읽지 못했어요: ' + live.errors.prs)]
        : live.prs.length === 0
          ? [dim('p0', '열린 PR 이 없어요')]
          : live.prs.map((pr) => Box({
            key: 'pr-' + pr.number,
            flexDirection: 'column',
            children: [
              Text({ bold: true, wrap: 'wrap', children: ['#' + pr.number + ' ' + pr.title] }),
              Text({
                color: pr.fail > 0 ? 'red' : undefined,
                dimColor: pr.fail === 0,
                wrap: 'wrap',
                children: ['  ' + (pr.draft ? 'Draft' : 'Ready') + '  ·  ' + checkSummary(pr) + '  ·  ' + pr.merge],
              }),
            ],
          })))]

    // 수동 항목: 진행, 대기, 완료
    const manualView = (section) => {
      const rows = items.filter((item) => item.status === section.status)
      if (rows.length === 0) return []
      const collapsed = section.status === 'done' && !showDone
      return [box('section-' + section.status, section.color, section.label + '  ' + rows.length,
        collapsed ? [dim('fold', 'd 를 누르면 펼쳐요')] : rows.map((item) => itemView(item, section)))]
    }

    const nothing = !board && live.workers === null && live.prs === null
    return Box({
      flexDirection: 'column',
      gap: 1,
      children: [
        Box({
          flexDirection: 'row',
          columnGap: 2,
          children: [
            Text({ dimColor: true, children: [
              '실제 상태 ' + (live.at ? ago(live.at) : '읽는 중') + (live.runId ? '  ·  ' + live.runId : '')
                + (board ? '  ·  수동 ' + ago(board.updatedAt) : ''),
            ] }),
            Button({
              key: 'refresh',
              label: liveBusy ? '읽는 중' : '새로 읽기',
              hotkey: 'r',
              plain: true,
              onPress: () => { loadLive($) },
            }),
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
        ...(board && board.error ? [Text({ color: 'red', wrap: 'wrap', children: ['board.json 을 읽지 못했어요: ' + board.error] })] : []),
        ...(nothing ? [dim('none', '보여 줄 작업이 없어요. orca run 이나 열린 PR, ' + BOARD_PATHS[0] + ' 중 하나가 있어야 해요.')] : []),
        ...manualView(SECTIONS[0]),
        ...decideView,
        ...workerView,
        ...prView,
        ...SECTIONS.slice(2).flatMap(manualView),
      ],
    })
  })
}
