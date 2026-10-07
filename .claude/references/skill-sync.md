# 스킬 층과 동기화

스킬을 고치기 전에 어느 층을 고쳐야 하는지 정한다.
엉뚱한 층을 고치면 다음 내보내기에 덮이거나, 고쳐도 내 환경에 반영되지 않는다.

## 네 층

| 층 | 위치 | 무엇을 두나 | 설치 방식 |
| --- | --- | --- | --- |
| 저장소 로컬 | `<repo>/.claude/skills/` | 그 저장소에서만 뜻이 통하는 스킬 | 저장소를 열면 실린다 |
| 개인 로컬 | `~/.claude/skills/<이름>` 실체 | 아직 쓰임이 굳지 않아 저장소에 올리지 않은 스킬 | 디렉터리 그대로 |
| 개인 공용 | `~/personal/fos-skills/` | 회사와 개인 작업에서 함께 쓰는 스킬 | 플러그인 `fos-skills` |
| 팀 공용 | 팀 저장소 체크아웃 | 사내 업무용이고 팀원도 쓰는 스킬 | 팀 저장소의 플러그인 |

**플러그인 스킬은 체크아웃이 아니라 설치 캐시의 복사본이 실행된다.**
캐시는 `~/.claude/plugins/cache/<마켓플레이스>/<플러그인>/<버전>/` 에 있고, 스킬 이름에 `fos-skills:planning` 처럼 접두사가 붙는다.
체크아웃을 고쳐도 `claude plugin update` 를 하기 전에는 실행되는 내용이 바뀌지 않는다.

지금 무엇이 설치돼 있는지는 아래 두 명령으로 본다.

```bash
claude plugin list
cd ~/.claude/skills && for n in *; do printf '%-24s %s\n' "$n" "$(readlink "$n" || echo '(실체)')"; done
```

`~/.claude/skills/` 에는 개인 공용과 팀 공용을 가리키는 링크를 두지 않는다. 두면 접두사 있는 것과 없는 것 둘로 뜬다.
`~/.claude/scripts/` 와 `~/.claude/rules/` 의 링크는 스킬 링크가 아니다. 체크아웃 안의 검사기와 규칙 파일을 가리키므로 그대로 둔다.

`~/.claude/skills/` 에는 위 네 층에 들지 않는 것도 있다.
다른 저장소의 저장소 로컬 스킬을 가리키는 링크는 링크 대상 저장소에서 고친다.
Orca 가 거는 `../../.agents/skills/` 링크, `ego-browser` 링크, `synced/` 디렉터리는 외부가 관리하므로 고치지 않는다.
`synced/` 는 실체라 위 명령에서 `(실체)` 로 보이지만 개인 로컬 스킬이 아니다.

## 개인 공용과 팀 공용의 관계

**`fos-skills` 가 원본이고 팀 저장소의 것은 사본이다.**
팀원이 저장소를 둘 받지 않아도 되게 사본을 두고, 어긋남은 스크립트가 잡는다.

내보내는 스킬과 공용 도구는 다음 명령으로 확인한다.

```bash
grep -n '^SHARED_' ~/personal/fos-skills/scripts/export-to-team.sh
```

사본이 놓이는 자리는 스킬마다 다르다.

| 원본 | 팀 저장소의 사본 | 팀 저장소에서 싣는 곳 |
| --- | --- | --- |
| `content-preview`, `korean-check` | `plugins/<플러그인>/skills/<이름>/` | 팀 저장소의 플러그인. 개인 공용 플러그인은 이 둘을 싣지 않는다 |
| `planning`, `build-with-teams`, `docs-check`, `review-fix` | `skills/<이름>/` | 기존 링크 설치. 플러그인에 없다 |
| `tools/browser-driver` | `tools/browser-driver/` | 팀 저장소의 플러그인이 링크로 싣는다 |

내보내기 스크립트는 `skills/<이름>` 으로 쓴다.
플러그인이 담는 스킬은 그 자리가 본체를 가리키는 링크라, 스크립트가 링크 너머의 본체에 쓰고 링크는 그대로 남는다.

`harness-cleanup` 과 `pr-review` 는 개인 스킬이라 내보내지 않는다.

**`content-preview` 와 `korean-check` 는 원본만 개인 공용에 있고, 스킬로는 팀 저장소의 플러그인 것이 뜬다.**
개인 공용 플러그인의 `skills` 배열에서 빼고 `~/personal/fos-skills/scripts/export-only-skills.json` 에 적어 두었다.
원본을 고치면 내보내고 팀 저장소의 플러그인을 갱신해야 실행되는 내용이 바뀐다.

```bash
cd ~/personal/fos-skills
./scripts/export-to-team.sh            # 어긋난 파일만 낸다. 어긋나면 종료 코드 1
./scripts/export-to-team.sh --apply    # 원본 내용을 팀 저장소로 복사한다
```

팀 저장소의 작업 트리가 따로 있으면 `TEAM_SKILLS_DIR` 로 그 경로를 준다.

- 방향은 개인 공용에서 팀 공용으로 한쪽이다. 반대 방향 명령은 없다.
- 내보낸 뒤 팀 저장소에서 따로 커밋해야 팀에 전파된다.
- 두 저장소의 frontmatter 규약이 달라 스크립트가 변환한다.
  원본은 `metadata.version`, 팀 저장소는 최상위 `version` 이다.

내보내지 않는 스킬은 한 층에만 있으므로 그 층에서 직접 고친다.

| 스킬 | 소유 | 본체 |
| --- | --- | --- |
| 팀 양식과 사내 시스템 스킬 | 팀 저장소 | `plugins/<플러그인>/skills/<이름>/`. 목록은 `claude plugin list` 와 팀 저장소 문서로 본다 |
| `harness-cleanup`, `pr-review` | 개인 공용 | `~/personal/fos-skills/<이름>/` |
| `presentation`, `meeting-note` | 개인 로컬 | `~/.claude/skills/<이름>/` |

개인 로컬 스킬은 여러 번 써서 절차가 자리를 잡으면 개인 공용으로 올린다.

## 고치기 전에 확인하는 것

1. 그 스킬이 내보내는 목록 안에 있는지 본다. 있으면 **원본을 고친다.**
   팀 저장소의 사본을 고치면 다음 `--apply` 가 그 수정을 알리지 않고 덮어쓴다.
2. 버전을 올린다. 저장소마다 규칙이 다르다.

   | 저장소 | 올리는 것 | 기준이 있는 곳 |
   | --- | --- | --- |
   | `fos-skills` | 스킬의 `metadata.version`. 플러그인 버전은 없고 커밋 SHA 가 버전이다 | `fos-skills/README.md` 의 「버전과 변경 이력」 |
   | 팀 저장소 | 스킬의 `version` 과, 닿은 플러그인의 `plugin.json` `version` | 팀 저장소 `CLAUDE.md` 의 「버전 규칙」 과 「플러그인」 |

   팀 쪽을 먼저 고쳤으면 원본 버전을 팀 버전보다 한 단 위로 올려 내보낸다. 같은 번호를 다시 쓰지 않는다.
   내보내기 스크립트는 팀 버전이 더 높을 때만 막으므로, 번호가 같으면 다른 내용이라도 덮어쓴다.

3. 변경 이력을 적는다. 팀 저장소는 대상마다 파일이 다르다. 어느 파일인지는 팀 저장소 `CLAUDE.md` 의 「CHANGELOG 작성 규칙」 이 소유한다.
4. 내보내는 스킬이면 내보내고, 두 저장소에서 각각 커밋한다.
   사본이 `plugins/` 나 `tools/browser-driver/` 에 닿으면 그 플러그인의 버전도 올린다.
   버전 문자열이 같으면 `claude plugin update` 가 새 복사본을 받지 않는다. CI 도 올리지 않은 변경을 막는다.

## 고친 뒤 이 머신에 반영하기

**머지만으로는 반영되지 않는다.** 갱신 명령을 돌려야 캐시가 바뀐다.
갱신하지 않으면 캐시의 옛 복사본이 실행돼, 이미 고친 함정이 살아 있는 것처럼 보인다.

```bash
# fos-skills: main 에 머지하고 push 한 뒤
claude plugin update fos-skills@fos-skills

# 팀 저장소: main 에 머지된 뒤. 이름은 claude plugin list 로 본다
claude plugin marketplace update <팀 마켓플레이스>
claude plugin update <플러그인>@<팀 마켓플레이스>
```

갱신한 내용은 `/reload-plugins` 나 새 세션에서 적용된다.

머지하기 전에 고친 내용을 써 보려면 작업 트리를 직접 실어 세션을 연다.
설치본과 함께 뜰 때의 동작은 `fos-skills/docs/flow.md` 의 「고치는 동안의 확인」 이 소유한다.

```bash
claude --plugin-dir "$(git rev-parse --show-toplevel)"
```

## 층을 올리고 내릴 때

저장소 로컬과 개인 로컬에서 개인 공용으로, 개인 공용에서 팀 공용으로 올린다.
올리는 시점은 여러 저장소에서 쓸 만하다고 확인됐을 때, 그리고 팀원도 쓸 만할 때다.

**개인 공용으로 올릴 때는 `fos-skills` 의 `.claude-plugin/plugin.json` 에 그 스킬을 더한다.**
스킬 디렉터리를 저장소 루트에 두고 `skills` 배열에 `./<이름>` 한 줄을 더한다.
빠뜨리면 설치해도 그 스킬이 뜨지 않는다. `python3 -m unittest discover -s scripts/tests` 가 배열과 스킬 디렉터리의 어긋남을 잡는다.
올린 뒤에는 `~/.claude/skills/<이름>` 의 실체를 지운다. 남기면 둘로 뜬다.
팀 저장소에서 링크로 설치하던 스킬을 옮겼으면 `~/.claude/team-skills.txt` 에서도 뺀다.
남기면 팀 저장소의 `skills.sh sync` 가 그 링크를 되살려 같은 스킬이 두 번 뜬다.

**쓰임이 굳지 않은 스킬은 개인 로컬로 내린다.**
개인 공용은 반복해서 쓰는 스킬만 담는 층이라, 손대지 않는 스킬이 섞이면 정리 대상이 흐려진다.
내릴 때는 `skills` 배열에서 빼고 디렉터리를 `~/.claude/skills/<이름>` 으로 옮긴다.

커밋은 옮기는 시점에 한 번만 남긴다.
개인 공용에서 팀 공용으로 올리는 것은 이동이 아니라 사본 추가다.
`SHARED_SKILLS` 에 이름을 더하고 내보내면 그때부터 원본과 사본 관계가 된다.
