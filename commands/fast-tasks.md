---
description: 다중 가벼운 task 를 한 batch 로 처리 (Socratic 2~3 Q × N + 단일 MD + parallel dispatch). 명시 슬래시 호출만 — 자동 발동 X.
---

# /fast-tasks

`brainstorming → designing-direction → writing-plans → executing-plans` 풀 흐름이 무거운 케이스를 위한 **별도 lightweight 경로**. **명시 `/fast-tasks` 호출 시에만 발동** — skill 형태 X (자동 description 매칭 안 됨).

## 언제 사용

- 사용자에게 task **5~15개** 한꺼번에 할당됨
- 각 task 가 **서로 종속도 낮음** (대부분 독립 또는 짧은 chain)
- 풀 brainstorming 흐름은 비현실적 (3-MD × 10 = 너무 무거움)
- 단일 피처 단위로 묶기도 어색

## 의도된 트레이드오프

본 흐름은 **가벼움이 디자인 의도**. 다음 항목은 영구히 생략:

| 항목 | 풀 흐름 | fast-tasks |
|---|---|---|
| `<slug>-tech-design.md` | ✅ | ❌ 생략 |
| `<slug>-implementation-plan.md` | ✅ | ❌ 생략 |
| `verifying-spec` | ✅ | ❌ 생략 |
| 변경이력 footer | ✅ | ❌ 생략 |
| `risk-annotation` | ✅ | ❌ 생략 |
| `docs-pretty` / `code-pretty` | ✅ | ❌ 생략 |
| AskUserQuestion 게이트 | ✅ 다수 | ❌ Socratic Q 외 X |

→ 최종 산출물은 단일 `<batch-slug>-tasks.md` **1 파일** + 실제 코드 변경만.

## Process — 메인 에이전트가 직접 수행

### Step 1 — Per-task Mini Socratic

사용자 첫 입력에서 task 목록 파싱 (보통 거친 한 줄씩). 각 task **마다** 메인이 Socratic 질문 **2~3개** 던짐 (**3개 초과 금지**).

- 라운드 N회 (task 수 만큼): task 1 질문 → 답 → task 2 질문 → 답 → ...
- 질문 목표: 각 task 의 **명세 (입력/출력/제약)** 최소한 명확화
- 답이 충분히 명확하면 2개로 끝, 모호하면 3개까지

### Step 2 — 단일 `<batch-slug>-tasks.md` 작성

산출물 1개:

```
docs/features/YYYY-MM-DD-fast-tasks-<batch-slug>/<batch-slug>-tasks.md
```

본문 구조:

```markdown
# <Batch slug> — Fast tasks (N개)

## Task 1: <title>
- 명세: <Socratic 합의된 내용>
- 영향 파일: <메인 추정>

## Task 2: <title>
...

## Task N: <title>
...

---

## 병렬화 계획 (DAG)

- Chain A: 1 → 4 → 5   (이유: 4 가 1 산출물 의존, 5 가 4 산출물 의존)
- Chain B: 2 → 7       (이유: 7 이 2 export 사용)
- Independent: 3, 6, 8, 9, 10

총 5 stream → 5 서브에이전트 병렬:
- subagent_1: 1 → 4 → 5
- subagent_2: 2 → 7
- subagent_3: 3
- subagent_4: 6
- subagent_5: 8 → 9 → 10
```

### Step 3 — Smart Parallel Dispatch

메인이 §병렬화 계획 읽고:

- **Chain (순차 종속)**: 하나의 서브에이전트가 chain 순서대로 처리 (e.g. 1 끝나면 4, 4 끝나면 5)
- **Independent**: 각각 별도 서브에이전트로 동시 dispatch (Agent tool multi-call single message)
- **극단 케이스**: 모두 독립이면 N 병렬
- **종속 판단**: LLM 휴리스틱 (메인이 §명세 + 영향 파일 보고 추론). 사용자 명시 X.

각 서브에이전트는 **commit 자체 수행** (per-task commit). 메인은 dispatch + 결과 종합만.

### Step 4 — 결과 요약

모든 서브에이전트 종료 후 메인이 한 줄 요약:

```
✅ fast-tasks <batch-slug> 완료: N tasks / M commits / 0 blocked.
   다음 단계: PR 또는 git merge 직접.
```

→ AskUserQuestion 게이트 X. 사용자가 직접 후속 처리.

## Non-goals (이 흐름은 안 함)

- 사용자가 명시 종속 그래프 그려주는 모드 (LLM 휴리스틱만)
- chain 내부 task 실패 시 자동 재시도 (사용자가 수동 재실행)
- 변경이력 / RISK 사후 보강 (영구히 생략 — "가벼움"이 의도)
- 풀 brainstorming 흐름으로 fallback (사용자가 원하면 별도 `/brainstorm` 호출)

## 입력 예시

사용자 한 turn 에 task 목록 통째로:

```
/fast-tasks

이번 스프린트 할당 10개:
1) 로그인 페이지 다크모드 토글 추가
2) /api/users GET endpoint 추가 (페이지네이션)
3) Button 컴포넌트 size variant (sm/md/lg)
4) 로그인 페이지 다크모드 토글 다국어
5) 다크모드 prefs Cookie 저장
6) Footer 카피라이트 연도 자동 갱신
7) /api/users 의 응답 캐싱 (5분)
8) README 한국어 추가
9) README 영문 보강
10) CI 워크플로우 Node 22 추가
```

→ 메인이 10개 인식 후 Step 1 라운드 진입.

## 발동 트리거

**명시 `/fast-tasks` 슬래시 호출만**. 자동 description 매칭 X (skill 형태 안 만듦 — 사용자 명시 의도 표현 보존).

## 결합 / 영향 범위

- `brainstorming` / `designing-direction` / `writing-plans` / `executing-plans` 본문 변경 0 (독립 경로)
- `auto-*` 본문 변경 0
- `js-super-sub-driven` 의 wave-parallel 분담 로직 부분 패턴 차용 (chain/independent 분류 + dispatch) — 본 skill 변경 X
- preflight.py 영향 0
- 단일 `commands/fast-tasks.md` 만 추가, `skills/` 영향 0
