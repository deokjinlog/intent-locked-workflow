# 프로덕션 품질 기준 — 실무 프론트 그라운딩

레퍼런스: **Linear · Vercel · Stripe · Notion · shadcn/ui · Radix**. "AI-generic" 티 안 나게, 실무에 바로 쓸 품질로 만들 때 이 기준을 지킨다. (스타일 [금지]와 별개로 모든 스타일에 공통 적용)

## 1. 스페이싱 — 8px 그리드
모든 여백·간격은 **4/8px 배수**(4·8·12·16·24·32·48·64). 임의 값(13px·27px) 금지. 일관된 리듬이 실무 티의 핵심.

## 2. 타이포 스케일
**제한된 스케일**(예: 12·14·16·20·24·32·48). 본문 14~16px, line-height 1.5~1.6. 큰 제목 letter-spacing −0.02em. 위계가 크기·굵기·색으로 명확히.

## 3. 컴포넌트 충실도 (shadcn/Radix 수준)
- **버튼**: primary/secondary/ghost 변형 + hover·active·focus·disabled 상태를 다 그린다. 일관된 height(36~40px)·radius·padding.
- **인풋/검색**: border + focus ring, placeholder, (필요 시) label·helper text.
- **카드**: 일관된 padding·radius·border/shadow 토큰.
- **테이블**: 정렬 헤더, hairline row, hover, 상태 배지(색+텍스트).
- 정적 목업 금지 — **상태(hover/focus/active/disabled/empty)를 실제로 표현**.

## 4. 색·테마 — CSS 변수
색은 CSS custom properties(`--bg`·`--fg`·`--muted`·`--border`·`--primary`…)로. 다크모드는 변수 스왑. 시맨틱 색(success/warning/danger/info) 일관, 대비 4.5:1+.

## 5. 레이아웃
CSS **Grid = 페이지 구조**, **Flexbox = 컴포넌트 정렬**. max-width 컨테이너(1200~1280px) + 일관된 gutter. 반응형 브레이크포인트(640/768/1024) 명확.

## 6. 디테일 (실무 티)
미묘한 1px 저대비 border · 정교한 radius(6~12px) · 절제된 elevation shadow · optical alignment · 실제 마이크로카피(placeholder·empty state·helper) · 일관된 아이콘(스트로크 굵기·크기).

## 안티 패턴 (AI-generic 냄새 — 피할 것)
- 보라 그라디언트 일색, 이모지 아이콘 남발, 과한 글로우
- 임의 여백·제각각 radius (8px 그리드 무시)
- 상태 없는 정적 버튼, placeholder 없는 인풋
- 중앙정렬 남발, 위계 없는 균일 텍스트, 스톡 느낌
- 개인 실명 (브랜드·역할·이니셜만)

> 요약: **8px 리듬 · 제한된 스케일 · 상태를 다 그린 컴포넌트 · CSS 변수 테마 · 절제된 디테일.** Linear/Stripe 를 옆에 열어놓고 만든 것처럼 — 그 스타일의 개성은 유지하되 마감은 프로덕션급.
