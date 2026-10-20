import { test, expect } from 'claude-code/testing'
import { parseWorkers, countQuestions, parsePullRequests, prFor, checkSummary, statusLine, workerFor, unmappedWorkers, workerLine, progressBar, stepProgress, itemProgress, detailLines, mainRoot, mergeVerdict, sortPullRequests, parseQuestions, questionText, START_PROMPT } from '../hooks/register.js'

test('일하는 worker 만 고르고 워크트리 이름을 꺼낸다', () => {
  const stdout = JSON.stringify({ result: { workers: [
    { dispatchId: 'a', dispatchStatus: 'dispatched', workerState: 'ready',
      resource: { worktreeId: 'x::/repo/worktrees/repo/ci-path-filter' } },
    { dispatchId: 'b', dispatchStatus: 'completed', workerState: 'succeeded', resource: { worktreeId: 'x::/repo/w/old' } },
  ] } })
  expect(parseWorkers(stdout)).toEqual([{ id: 'a', state: 'ready', worktree: 'ci-path-filter' }])
})

test('질문과 escalation 만 세고 heartbeat 는 세지 않는다', () => {
  const stdout = '{"messages":[{"type": "question"},{"type":"heartbeat"},{"type":"escalation"},{"type":"status"}]}'
  expect(countQuestions(stdout)).toBe(2)
})

test('PR 의 CI 결과를 통과, 실패, 진행으로 나누고 worker 에 붙인다', () => {
  const prs = parsePullRequests(JSON.stringify([{
    number: 503, title: 'CI 필터', headRefName: 'jon890/ci-path-filter', isDraft: false, mergeStateStatus: 'CLEAN',
    statusCheckRollup: [{ conclusion: 'SUCCESS' }, { conclusion: 'FAILURE' }, { state: 'PENDING' }, { conclusion: 'SKIPPED' }],
  }]))
  expect(prs[0]).toMatchObject({ number: 503, pass: 2, fail: 1, pending: 1, draft: false })
  expect(checkSummary(prs[0])).toBe('CI 2/4 · 실패 1 · 진행 1')
  expect(prFor({ id: 'a', state: '', worktree: 'ci-path-filter' }, prs)?.number).toBe(503)
  expect(prFor({ id: 'b', state: '', worktree: 'path-filter' }, prs)).toBe(null)
})

test('상태 줄은 질문과 수동 decide 를 합쳐 결정 필요로 센다', () => {
  const line = statusLine([{ status: 'decide' }, { status: 'doing' }],
    { questions: 2, workers: [{}, {}], prs: [{ fail: 1 }, { fail: 0 }] })
  expect(line).toBe('결정 필요 3 · worker 2 · PR 2(CI 실패 1) · 진행 1   /board')
  expect(statusLine([], { questions: null, workers: null, prs: null })).toBe('')
})

test('항목의 worktree 로 worker 를 붙이고, 안 붙은 worker 만 따로 고른다', () => {
  const workers = [{ id: 'a', state: 'ready', worktree: 'ci-path-filter' }, { id: 'b', state: 'busy', worktree: 'other' }]
  const items = [{ id: 'x', status: 'doing', worktree: 'ci-path-filter' }, { id: 'y', status: 'done', worktree: 'other' }]
  expect(workerFor(items[0], workers)?.id).toBe('a')
  expect(unmappedWorkers(items, workers).map((w) => w.id)).toEqual(['b'])
  const prs = [{ number: 503, branch: 'jon890/ci-path-filter', pass: 9, fail: 0, pending: 0 }]
  expect(workerLine(workers[0], prs)).toBe('ci-path-filter  #503 CI 9/9')
  expect(workerLine(workers[1], prs)).toBe('other  busy')
})

test('진행 표시줄은 끝낸 단계 비율로 칸을 채운다', () => {
  expect(progressBar('7/10', 10)).toBe('███████░░░ 7/10 (70%)')
  expect(progressBar('3 / 4', 4)).toBe('███░ 3/4 (75%)')
  expect(progressBar('abc')).toBe(null)
  expect(progressBar('1/0')).toBe(null)
})

test('진행률은 숫자로 시작하는 단계 줄에서 센다', () => {
  expect(stepProgress(['✓ 1 a', '✓ 2 b', '3 c', '4 d'])).toBe('2/4')
  expect(stepProgress(['1 a', '2 b'])).toBe('0/2')
  expect(stepProgress(['참고: x', '✓ 메모', '✓ 1 a', '2 b'])).toBe('1/2')
  expect(stepProgress(['참고만 있다'])).toBe(null)
  expect(stepProgress(undefined)).toBe(null)
})

test('progress 가 있으면 단계 수보다 우선한다', () => {
  expect(itemProgress({ progress: '7/10', details: ['✓ 1 a', '2 b'] })).toBe('7/10')
  expect(itemProgress({ details: ['✓ 1 a', '2 b'] })).toBe('1/2')
  expect(itemProgress({ title: 'x' })).toBe(null)
})

test('접으면 끝난 단계를 수 한 줄로 줄이고 펼치면 그대로 둔다', () => {
  const details = ['✓ 1 a', '✓ 2 b', '▶ 3 c', '◇ 4 d']
  expect(detailLines(details, false)).toEqual([{ folded: 2 }, { text: '▶ 3 c' }, { text: '◇ 4 d' }])
  expect(detailLines(details, true)).toEqual([{ text: '▶ 3 c' }, { text: '◇ 4 d' }, { text: '✓ 1 a', done: true }, { text: '✓ 2 b', done: true }])
  expect(detailLines(['◇ 1 a'], false)).toEqual([{ text: '◇ 1 a' }])
})

test('git 공통 디렉터리에서 주 checkout 의 root 를 꺼낸다', () => {
  expect(mainRoot('/repo/.git\n')).toBe('/repo')
  expect(mainRoot('/repo/.git/')).toBe('/repo')
  expect(mainRoot('/bare.git')).toBe('')
})

test('Ready 이고 필수 검사가 통과한 PR 을 머지 가능으로 보고 맨 위에 둔다', () => {
  const pr = (number, draft, merge, extra = {}) => ({ number, title: '', draft, merge, pass: 9, fail: 0, pending: 0, failed: [], ...extra })
  const prs = [
    pr(1, true, 'CLEAN'),
    pr(2, false, 'BLOCKED', { pending: 3 }),
    pr(3, false, 'UNSTABLE', { fail: 1, failed: ['claude-review'] }),
    pr(4, false, 'BLOCKED', { fail: 1, failed: ['backend'] }),
    pr(5, false, 'DIRTY'),
  ]
  expect(mergeVerdict(prs[2]).label).toBe('머지 가능')
  expect(mergeVerdict(prs[3]).label).toBe('CI 실패')
  expect(mergeVerdict(prs[0]).label).toBe('CI 통과, Ready 전')
  expect(sortPullRequests(prs).map((p) => p.number)).toEqual([3, 2, 4, 5, 1])
})

test('답을 기다리는 질문의 본문과 보낸 worker 를 꺼낸다', () => {
  const stdout = '{"ok":true,"result":{"messages":[{"id":"m1","type":"question","from_handle":"dispatch:ctx_a","body":"둘 중\n무엇으로 할까요?","payload":"{\\"dispatchId\\":\\"ctx_a\\",\\"question\\":\\"A 와 B 중 무엇으로 할까요?\\"}","created_at":"2026-10-12T10:00:00Z"},{"id":"m2","type":"status","body":"x"}]}}'
  const questions = parseQuestions(stdout)
  expect(questions.length).toBe(1)
  expect(questions[0].dispatch).toBe('ctx_a')
  expect(questions[0].text).toBe('A 와 B 중 무엇으로 할까요?')
  expect(questionText('가'.repeat(10), 5)).toBe('가가가가…')
  expect(parseQuestions('깨진 {"type": "question"').length).toBe(1)
})

test('오늘 시작 요청은 board 갱신, 완료 비우기, 정리, 감시, 보고를 모두 담는다', () => {
  expect(START_PROMPT).toContain('완료(done) 항목은 비운다')
  expect(START_PROMPT).toContain('현재 저장소의 남은 워크트리')
  expect(START_PROMPT).toContain('.claude/orch-overlay.md 의 정리 규칙')
  expect(START_PROMPT).not.toMatch(/fos-|세 저장소/)
  expect(START_PROMPT).toContain('orch-watch')
  expect(START_PROMPT).toContain('정할 것은 바로 물어본다')
})
