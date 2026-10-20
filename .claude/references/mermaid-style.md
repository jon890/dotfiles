# mermaid 기본 스타일 (B: 주체별 색과 곡선)

사용자가 2026-10-20 다섯 스타일을 견줘 고른 기본값이다. mermaid 그림을 만들 때 따로 말이 없으면 이 스타일을 쓴다.

## 적용 방법

- HTML 페이지: 그림마다 frontmatter 로 config 를 싣는다. mermaid 11 기준이다.
- 두레이, GitHub 처럼 렌더러 버전을 모르는 곳: frontmatter 대신 첫 줄에 `%%{init: <같은 JSON>}%%` 를 쓴다.
- HTML 에서는 `.mermaid, .mermaid * { font-family: 'Noto Sans KR', sans-serif; }` 를 두고, 글꼴을 불러온 뒤(`await document.fonts.ready`) `mermaid.run` 을 부른다.
  - `<pre class="mermaid">` 의 고정폭 글꼴이 라벨에 상속되어 글자가 잘리는 것을 실측했다.

## flowchart config

```json
{"theme":"base","themeVariables":{"fontFamily":"'Noto Sans KR', sans-serif","fontSize":"14px","lineColor":"#7A8594","primaryTextColor":"#1D1F23","edgeLabelBackground":"#FFFFFF","clusterBkg":"#FAFAFA"},"flowchart":{"curve":"basis","nodeSpacing":40,"rankSpacing":60,"padding":14}}
```

주체(subgraph)마다 색 하나를 준다. 다섯 색을 순서대로 쓴다.

```
  classDef c1 fill:#E8F1FB,stroke:#3B7DD8,stroke-width:1.5px,color:#0B2545
  classDef c2 fill:#E9F7EF,stroke:#2E9E5B,stroke-width:1.5px,color:#0E3B22
  classDef c3 fill:#FFF4E0,stroke:#E09A1A,stroke-width:1.5px,color:#4A3000
  classDef c4 fill:#F3EAFB,stroke:#8E4EC6,stroke-width:1.5px,color:#2E1145
  classDef c5 fill:#FDECEC,stroke:#D64545,stroke-width:1.5px,color:#4A0F0F
  style <subgraph1> fill:#F6FAFE,stroke:#3B7DD8,stroke-dasharray:4 3
  style <subgraph2> fill:#F5FBF7,stroke:#2E9E5B,stroke-dasharray:4 3
  style <subgraph3> fill:#FFFAF0,stroke:#E09A1A,stroke-dasharray:4 3
  style <subgraph4> fill:#FAF5FD,stroke:#8E4EC6,stroke-dasharray:4 3
  style <subgraph5> fill:#FEF6F6,stroke:#D64545,stroke-dasharray:4 3
```

주체 배정은 그림마다 고정해 같은 주체가 늘 같은 색이 되게 한다. 저장소별 배정은 그 저장소 문서에 둔다.
아직 만들지 않은 경로는 점선 화살표(`-.->`)로 그린다.

## sequenceDiagram config

```json
{"theme":"base","themeVariables":{"fontFamily":"'Noto Sans KR', sans-serif","fontSize":"14px","actorBkg":"#E8F1FB","actorBorder":"#3B7DD8","actorTextColor":"#0B2545","signalColor":"#5A6472","signalTextColor":"#1D1F23","noteBkgColor":"#FFF4E0","noteBorderColor":"#E09A1A","labelBoxBkgColor":"#F3EAFB","labelBoxBorderColor":"#8E4EC6","loopTextColor":"#2E1145"},"sequence":{"mirrorActors":false,"actorMargin":60,"boxMargin":8,"noteMargin":10}}
```

## HTML 확대 보기

HTML 페이지에 mermaid 그림을 넣으면 `~/.claude/references/assets/mermaid-zoom.html` 의 내용을 `</body>` 바로 앞에 붙인다.
그림을 누르면 전체 화면에서 휠로 확대·축소하고, 끌어서 이동하고, Esc 로 닫는다. 외부 라이브러리 없이 동작한다.

## 두레이

두레이 업무 본문의 ```mermaid 코드 블록은 그림으로 그려진다(2026-10-20 사용자 확인).
config 는 frontmatter 대신 첫 줄 `%%{init: ...}%%` 로 싣는다. 확대 보기 스크립트는 두레이에 넣을 수 없다.
