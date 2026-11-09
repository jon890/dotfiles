# 스킬 층과 동기화

스킬을 고치기 전에 어느 층을 고쳐야 하는지 정한다.
엉뚱한 층을 고치면 다음 내보내기에 덮이거나, 고쳐도 내 환경에 반영되지 않는다.

이 문서는 공개 저장소 fos-skills, 팀 저장소, 이 머신의 `~/.claude/skills` 를 잇는 지도만 갖는다.
각 저장소 안의 절차는 그 저장소 문서가 소유하므로 여기에 옮기지 않고 가리킨다.

## 네 층

| 층 | 위치 | 무엇을 두나 | 설치 방식 |
| --- | --- | --- | --- |
| 저장소 로컬 | `<repo>/.claude/skills/`, `<repo>/.agents/skills/` | 그 저장소에서만 뜻이 통하는 스킬 | 저장소를 열면 실린다 |
| 개인 로컬 | `~/.claude/skills/<이름>` 실체 | 아직 쓰임이 굳지 않아 저장소에 올리지 않은 스킬 | 디렉터리 그대로 |
| 개인 공용 | `~/personal/fos-skills/skills/<이름>/` | 회사와 개인 작업에서 함께 쓰는 스킬 | 플러그인 `fos-skills` |
| 팀 공용 | `~/projects/AiSdtSkill/plugins/<플러그인>/skills/<이름>/` | 사내 업무용이고 팀원도 쓰는 스킬 | 팀 저장소의 플러그인 `nhn-dev`, `ai-sdt` |

**플러그인 스킬은 체크아웃이 아니라 설치 캐시의 복사본이 실행된다.**
체크아웃을 고쳐도 머지하고 갱신하기 전에는 실행되는 내용이 바뀌지 않는다. 아래 「고친 뒤 이 머신에 반영하기」 를 따른다.

`~/.claude/skills/` 에는 개인 공용과 팀 공용을 가리키는 링크를 두지 않는다. 두면 접두사 있는 것과 없는 것 둘로 뜬다.
그 밖에 `~/.claude/skills/` 에 있는 것은 이렇게 다룬다.

- 다른 저장소의 저장소 로컬 스킬을 가리키는 링크는 링크 대상 저장소에서 고친다.
- Orca 가 거는 `../../.agents/skills/` 링크, `ego-browser` 링크, `synced/` 디렉터리는 외부가 관리하므로 고치지 않는다. `synced/` 는 실체지만 개인 로컬 스킬이 아니다.
- `~/.claude/scripts/` 와 `~/.claude/rules/` 의 링크는 스킬 링크가 아니라 체크아웃 안의 검사기와 규칙 파일이다. 링크 목록과 옮길 때의 처리는 `~/personal/fos-skills/docs/code-architecture.md` 의 「저장소 밖에서 이 저장소를 가리키는 경로」 가 소유한다.

지금 무엇이 설치돼 있는지는 아래 두 명령으로 본다.

```bash
claude plugin list
cd ~/.claude/skills && for n in *; do printf '%-24s %s\n' "$n" "$(readlink "$n" || echo '(실체)')"; done
```

## 고치기 전에 어느 층인지 정한다

1. **팀 저장소로 내보내는 스킬이면 fos-skills 의 원본을 고친다.** 팀 저장소의 사본을 고치면 다음 내보내기가 알리지 않고 덮어쓴다.
   내보내는 목록은 아래 명령으로 본다.

   ```bash
   grep -n 'SHARED_SKILLS\|SHARED_TOOLS' ~/personal/fos-skills/scripts/export-to-team.ts
   ```

   내보내기의 구조는 `~/personal/fos-skills/docs/code-architecture.md` 의 「팀 저장소 내보내기」, 옵션은 `~/personal/fos-skills/scripts/export-to-team.ts` 머리 주석이 소유한다.
2. **내보내지 않는 스킬은 그 스킬이 있는 층에서 직접 고친다.** 위 「네 층」 표의 위치가 본체다.
3. **버전과 변경 이력은 저장소 규칙을 따른다.**
   fos-skills 는 `README.md` 의 「버전과 변경 이력」, 팀 저장소는 `CLAUDE.md` 의 「버전 규칙」 과 「CHANGELOG 작성 규칙」 이 소유한다.
4. **내보내기는 원본이 main 에 머지된 뒤 원본을 고친 쪽이 한다.** 코디네이터가 머지하는 흐름이면 머지 직후 코디네이터가 낸다.
   머지 전에 내보내면 팀 저장소에 main 에 없는 내용이 들어간다. 내보낸 뒤 팀 저장소에서 따로 PR 을 열어야 팀에 전파된다.

## 고친 뒤 이 머신에 반영하기

**머지만으로는 반영되지 않는다.** 마켓플레이스와 플러그인을 갱신해야 캐시가 바뀌고, `/reload-plugins` 나 새 세션에서 적용된다.

```bash
# fos-skills: main 에 머지된 뒤
claude plugin marketplace update fos-skills
claude plugin update fos-skills@fos-skills

# 팀 저장소: main 에 머지된 뒤
claude plugin marketplace update ai-sdt-skills
claude plugin update nhn-dev@ai-sdt-skills
claude plugin update ai-sdt@ai-sdt-skills
```

머지 전에 고친 내용을 써 보는 방법은 fos-skills `README.md` 의 「고치는 동안」 이 소유한다.

## 층을 올리고 내릴 때

저장소 로컬과 개인 로컬에서 개인 공용으로, 개인 공용에서 팀 공용으로 올린다.
올리는 시점은 여러 저장소에서 쓸 만하다고 확인됐을 때, 그리고 팀원도 쓸 만할 때다.

- **개인 공용으로 올릴 때**는 fos-skills `README.md` 의 「스킬을 더할 때」 를 따른다. 올린 뒤에는 `~/.claude/skills/<이름>` 의 실체를 지운다. 남기면 둘로 뜬다.
- **팀 공용으로 올릴 때**는 이동이 아니라 사본 추가다. `export-to-team.ts` 의 `SHARED_SKILLS` 에 이름을 더하고 내보내면 그때부터 원본과 사본 관계가 된다.
- **쓰임이 굳지 않은 스킬은 개인 로컬로 내린다.** 개인 공용은 반복해서 쓰는 스킬만 담는 층이라, 손대지 않는 스킬이 섞이면 정리 대상이 흐려진다. fos-skills 의 매니페스트에서 빼고 디렉터리를 `~/.claude/skills/<이름>` 으로 옮긴다.
