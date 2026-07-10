---
name: dispatching-parallel-agents
description: Use when a task splits into N independent sub-tasks that should run concurrently — fan-out → collect → synthesize. Examples — generating design variations, multi-angle review/audit, per-file analysis, multi-source research. Dispatches all sub-agents in ONE message for true parallelism, each with an individualized prompt from a shared template (only the variable part differs), isolates failures, then collects and synthesizes. This is the lightweight fan-out pattern (main agent issues concurrent subagent calls). For HEAVY deterministic orchestration (loops, barriers, token budget, retries) use the Workflow tool instead. 범용 병렬 처리 스킬 — 특정 워크플로에 묶이지 않음.
---

# Dispatching Parallel Agents (범용 fan-out 병렬 처리)

한 작업이 **서로 독립적인 N개 하위작업**으로 쪼개질 때, 보조 에이전트 여러 개를 **진짜 병렬**로 돌려 결과를 모은다. 재사용 패턴 — `/design-gallery`(아키타입 9개), `/audit-risk`(리뷰 각도 5개), 파일별 분석, 멀티소스 리서치가 전부 이 형태.

> 이건 **plan 실행에 묶이지 않은 범용** 병렬 스킬이다. (`dj-superkit-sub-driven` 은 구현계획 실행 전용, 이건 아무 fan-out 작업에나 쓴다.)

## 언제 쓰나

- 하위작업들이 **서로 독립** (한 개의 결과가 다른 개의 입력이 아님)
- 각자 **다른 관점/변수**로 같은 종류의 작업 (fan-out)
- 결과를 모아 **하나로 합침** (collect → synthesize)

**안 씀**: 순차 의존(A→B→C), 단일 작업, 결정론적 루프·배리어·예산이 꼭 필요한 경우(→ `Workflow` 도구).

## 핵심 4원칙 (안 지키면 실패)

### 1. 개별 프롬프트 (템플릿 + 변수 치환)

공통 뼈대 프롬프트 1개를 정하고, **변수 부분만** 각 에이전트마다 바꾼다 (아키타입 / 리뷰 각도 / 파일 등). 다 같은 프롬프트로 돌리면 결과가 비슷하게 나온다(mode collapse). **뼈대는 같아야 일관성**, **변수는 달라야 다양성**.

### 2. 한 응답에 동시 dispatch = 진짜 병렬

N개 Agent(Task) 호출을 **한 번의 응답(메시지)에 전부** 넣는다. 그래야 동시에 돈다. **하나씩 순차로 부르면 병렬이 아니다** — 이게 제일 흔한 실수. (독립 호출은 같은 응답 블록에 모아라.)

### 3. 실패 격리

하나가 죽어도 나머지는 진행한다. 결과를 모을 때 실패분(null)을 **걸러낸다**. 하나 실패로 전체 중단 X.

### 4. 수집 → 합성

N개 결과를 모아 **하나의 산출물**(갤러리 / 보고서 / 요약)로 합친다. "N개 던지고 끝"이 아니라 합성까지가 이 스킬의 끝.

## 절차

1. **분해** — 작업을 독립 하위작업 N개로. 각각의 **변수**를 정의 (예: 아키타입 목록).
2. **템플릿** — 공통 프롬프트 뼈대 + 변수 슬롯 하나.
3. **동시 dispatch** — 한 응답에 N개 Agent 호출. 각 호출은 변수만 치환된 개별 프롬프트.
4. **격리 수집** — 전부 완료 대기, 실패분 필터.
5. **합성** — 하나의 결과물로 모음.

## Workflow 도구와의 관계

| | 이 스킬 (가벼움) | `Workflow` 도구 (무거움) |
|---|---|---|
| 방식 | 메인이 한 응답에 동시 Agent 호출 | 결정론적 오케스트레이션 스크립트 |
| 언제 | 대부분의 fan-out (독립 N개) | 루프 / 배리어 / 예산 / 재시도 필요 시 |
| opt-in | 불필요 (그냥 발동) | 명시 필요 ("ultracode" / "workflow로 돌려줘") |

## Anti-Patterns

| Wrong | Right |
|---|---|
| 하나씩 순차 dispatch | 한 응답에 N개 동시 호출 |
| 다 같은 프롬프트 | 변수만 다른 개별 프롬프트 (공통 템플릿) |
| 하나 실패 → 전체 중단 | 실패 격리 + null 필터 |
| N개 만들고 끝 | 수집 → 합성까지 |
| 의존 있는 작업을 병렬로 | 독립일 때만 (의존이면 순차 / Workflow) |
| N을 무작정 크게 (30+) | 다양성 확보되는 선에서 (보통 5~12) |

## Related Skills

- `dj-superkit-sub-driven` — **구현계획 실행 전용** wave-parallel (이건 범용 fan-out).
- `Workflow` 도구 — 결정론적 병렬 오케스트레이션 (무거운 버전).
- 이 패턴을 쓰는 명령: `/design-gallery`(아키타입 fan-out), `/audit-risk`(리뷰 각도 fan-out).
