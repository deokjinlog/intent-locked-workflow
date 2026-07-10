---
name: design-gallery
description: Use when the user wants to explore and COMPARE MULTIPLE UI/screen design directions at once (not build one final page) — triggers like "디자인 시안 여러 개 뽑아줘", "여러 스타일로 화면 디자인 보여줘", "이 화면 디자인 방향들 비교하고 싶어", "12가지 스타일로 대시보드 뽑아줘". Takes a design brief + fixed content, generates N distinct HTML design variations IN PARALLEL (each a different visual style — SF HUD / SaaS / brutalist / glass / editorial / luxury dark …), assembles a viewable gallery to compare, then the user picks one and its design tokens seed the project. Parallel generation uses the Claude Code Workflow TOOL when possible (this skill's instructions authorize that opt-in; the Workflow tool works even in the VS Code extension where the /workflows VIEW command is missing); falls back to concurrent subagent dispatch. NOT for building a single finalized page (that is normal implementation).
---

# Design Gallery — 여러 스타일 화면 디자인 병렬 생성

디자인 브리프 하나로 **서로 다른 비주얼 스타일 N개(기본 12)를 병렬로** 생성해 HTML 갤러리로 한눈에 비교한다. 고른 시안에서 디자인 토큰을 뽑아 프로젝트 기준으로 삼는다.

## 핵심 원칙 (안 지키면 실패)

1. **개수보다 다양성** — 각 시안은 **확실히 다른 스타일** 강제. 같은 프롬프트로 여러 개 = 절반이 비슷(mode collapse).
2. **내용 고정** — 모든 시안이 **같은 콘텐츠·섹션·카피**. 디자인만 비교 (내용 다르면 사과 vs 오렌지).
3. **병렬 생성** — N개를 **동시에** (순차 금지).
4. **선택 → 기준화** — 고른 시안의 **디자인 토큰**(색·폰트·간격·컴포넌트)을 뽑아 `design-system.md` 로. ("예쁜 거 고르고 끝" 방지)

## 스타일 방향 (기본 12개, `--count K` / 사용자 지정으로 조절)

| # | 슬러그 | 스타일 | 특징 |
|---|---|---|---|
| 01 | sf-hud | SF 게임 HUD | 네온 시안/마젠타, 글로우, 각진 프레임, 모노스페이스 수치 |
| 02 | public-portal | 공공데이터 포털 | 화이트 베이스, 정적, 명료한 표 중심, 신뢰감 |
| 03 | trendy-saas | 트렌디 SaaS | 파스텔 그라디언트, 큰 라운드, 여백 많은 Linear/Vercel 느낌 |
| 04 | dense-terminal | 고밀도 터미널 | Bloomberg처럼 정보 꽉 찬 다크 스크린 |
| 05 | neumorphism | 뉴모피즘/소프트 | 부드러운 입체감, 소프트 섀도 |
| 06 | brutalism | 브루탈리즘 | 굵은 보더, 원색, 의도적 투박함 |
| 07 | glassmorphism | 글래스모피즘 | 반투명 블러 레이어, 그라데이션 배경 |
| 08 | minimal-mono | 미니멀 모노크롬 | 흑백 + 포인트 컬러 하나 |
| 09 | retro-pixel | 레트로/픽셀 | 8비트 감성, 네온/그리드 |
| 10 | editorial | 에디토리얼 | 잡지처럼 세리프 타이포 중심, 그리드 |
| 11 | nature-organic | 네이처/오가닉 | 어스톤, 곡선, 자연 질감 |
| 12 | luxury-dark | 럭셔리 다크 | 골드 포인트, 프리미엄 금융 느낌 |

사용자가 다른 스타일을 지정하거나 자기 프롬프트를 주면 그걸 우선한다.

## Process

### Step 1. 브리프 + 공유 콘텐츠 확정

- 사용자 프롬프트/브리프를 받는다 (화면·제품 종류, 섹션 목록, 실제 카피 짧게).
- 부족하면 `AskUserQuestion` 으로 1~2개만 질문 (섹션 구성 / 스타일 개수).
- 이 콘텐츠는 **모든 시안이 공유** (라운드 내내 고정).

### Step 2. 병렬 생성 — Workflow 우선, 폴백 subagent

**우선 경로 — Claude Code `Workflow` 도구** (이 스킬 지시가 명시 opt-in 을 authorize. Workflow 도구는 VS Code 에서도 호출됨 — 없는 건 `/workflows` "보는 화면"뿐):

- fan-out 스크립트로 **12개 스타일을 `parallel()` 로 동시 생성**.
- 각 agent 프롬프트 = **[공통 콘텐츠(Step 1)] + [배정 스타일 1개] + [self-contained .html 규칙]**.
- 예시 스크립트:

```js
export const meta = {
  name: 'design-gallery',
  description: 'N개 스타일 화면 디자인 병렬 생성',
  phases: [{ title: 'Generate' }],
}
const CONTENT = `...Step 1 에서 확정한 공유 콘텐츠...`
const STYLES = [
  { slug: 'sf-hud',        brief: 'SF 게임 HUD — 네온 시안/마젠타, 글로우, 각진 프레임, 모노스페이스' },
  // ... 12개 (위 표)
]
const results = await parallel(STYLES.map(s => () =>
  agent(
    `${CONTENT}\n\n[스타일] ${s.brief}\n` +
    `이 콘텐츠를 위 스타일로 self-contained .html 한 장으로 만들어라 ` +
    `(인라인 CSS/JS만, 외부 의존성 0, 오프라인 렌더). 파일: ${s.slug}.html`,
    { label: `gen:${s.slug}`, phase: 'Generate' }
  )
))
return results.filter(Boolean)
```

**폴백 경로 — Workflow 를 못 쓰면**(도구 미가용/에러): **한 응답에 N개 Agent 호출을 전부 넣어** 동시 dispatch (순차 금지). 실패 격리(null 필터).

각 생성물 저장: `docs/design-gallery/<YYYY-MM-DD>-<슬러그>/01-sf-hud.html` … `12-luxury-dark.html`
- **self-contained** (인라인만, 외부 CDN·폰트·이미지 0, 오프라인 렌더)
- `frontend-design` 원칙 (의도적 타이포·색·레이아웃)

### Step 3. 갤러리 index.html

- 번호 카드 그리드 + 각 카드 `<iframe>` 미리보기 + **"열기 / 다운로드"** 버튼 (참고 스샷처럼)
- self-contained, 다크 배경, 반응형
- 저장: `docs/design-gallery/<...>/index.html`
- 사용자에게 **경로 안내** + "몇 번이 맘에 드세요? (1~2개)" (`AskUserQuestion`)

### Step 4. 선택 → 디자인 토큰

고른 시안에서 뽑아 `docs/design-gallery/<...>/design-system.md`:
- **색 팔레트** (primary/bg/surface/text/accent hex)
- **타이포** (heading/body 폰트·크기 스케일)
- **간격** 스케일
- **컴포넌트** (버튼/카드/입력) 기본 스타일

이 `design-system.md` 가 이후 **기획→구현 워크플로의 디자인 기준**. (원하면 `--refine <번호>` 로 고른 방향 안에서 3~4개 변주 라운드)

## Checklist

- [ ] Step 1 — 브리프 + 공유 콘텐츠 확정 (부족하면 질문)
- [ ] Step 2 — N개 스타일 병렬 생성 (Workflow 우선 / subagent 폴백)
- [ ] Step 3 — 갤러리 index.html + 선택 질문
- [ ] Step 4 — 고른 시안 → design-system.md 토큰 추출

## Anti-Patterns

| Wrong | Right |
|---|---|
| 순차 생성 (하나씩) | **병렬** (Workflow parallel / 한 응답에 동시 dispatch) |
| 다 같은 스타일/프롬프트 | 스타일 12개 확실히 다르게 |
| 시안마다 콘텐츠가 다름 | **콘텐츠 고정** — 디자인만 비교 |
| `.html` 외부 CDN 참조 | self-contained (오프라인 렌더) |
| 고르고 끝 | **토큰 추출**까지 (design-system.md) |
| `/workflows` 뷰 없다고 Workflow 포기 | Workflow **도구**는 호출됨 (뷰만 CLI에서) → 우선 사용 |

## Related Skills / Tools

- `generating-html` — HTML 생성 엔진 (스타일 시안·갤러리 생성에 재활용)
- `Workflow` 도구 — 병렬 생성 우선 경로 (fan-out `parallel()`)
- `frontend-design` — 의도적 비주얼 디자인 원칙
