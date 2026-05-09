# 요구사항: 서브에이전트 병렬화

> **Mode:** Socratic (free-form). Downstream `designing-direction` reads this prose without expecting fixed PRD section IDs.

## 배경

`js-super-subagent-driven-development` 는 현재 task 를 순차로 dispatch 한다. upstream 의 3-stage (impl + spec-reviewer + final code reviewer) 는 task N 의 코드리뷰 결과로 N+1 방향이 바뀔 수 있어 직렬이 강제되지만, js-super 는 final code reviewer 단계가 빠져 있어 cross-task 의존이 없다. 즉 task 간 논리 의존성과 파일 충돌만 회피하면 자연스럽게 병렬화 가능.

또 v1.1.13 에서 implementer / spec-reviewer 둘 다 sonnet 으로 핀했는데, upstream 의 4-조건 룰 (mechanical 1-2 파일 → haiku) 은 미응용 상태. plan 의 task 마다 적정 모델이 다른데 메인이 그 차이를 dispatch 시점에 모름 → cost saving 절반만 누림.

이번 피처는 두 개선을 한 릴리즈에 묶는다 — 둘 다 `js-super-subagent-driven-development` dispatch 직전 "메인이 plan 을 한 번 더 읽고 파라미터를 준비" 라는 같은 confluence 에서 만나기 때문.

## 목적

- **속도**: 독립 task 그룹은 wave 단위 병렬 dispatch 로 처리 시간 단축
- **비용**: task 별 모델 힌트로 mechanical task 는 haiku, 통합/디버깅 task 는 sonnet 으로 dispatch 비용 적정화
- **안전망**: 잘못된 병렬 → 파일 충돌 → silent overwrite 회귀 방지를 위해 wave 시작 전 dry-run 충돌 검사
- **단순함**: 사용자 의사결정 추가 X (게이트 늘리지 않음). plan 만 정확하면 자동 동작.

## 사용자 스토리

`/execute-plan` 을 실행하고 게이트 #14 에서 "서브에이전트" 를 선택한 사용자는, 메인이 plan 을 읽고 즉시 wave 구조를 알려준 뒤 wave 단위로 진행 상황만 받는다. task 단위 알림은 없다 (병렬 인터리브로 혼란하므로). wave 1개라도 실패하면 메인이 격리하고 통과한 형제는 그대로 commit, 실패 task 의 후행 의존만 차단해 다음 wave 로 진행한다.

## 핵심 결정

### D1. 스코프 — `js-super-subagent-driven-development` 만

인라인 모드 (`executing-plans`) 는 단일 컨텍스트 직진이 핵심 가치. 병렬 부적합. 게이트 #14 의 2지선다 (인라인 / 서브에이전트) 그대로 유지. 사용자가 "서브에이전트" 선택 시 자동으로 병렬 흐름.

### D2. DAG 추론 — 메인이 JIT, plan 만 보고

서브에이전트 모드 시작 시점에 메인 에이전트가 `<slug>-implementation-plan.md` 를 읽고 task 간 partial order 를 계산한다. 같은 그래프 안에 두 종류의 edge:

- **파일 충돌 edge**: task A 와 B 가 같은 파일을 건드리면 directional edge (작성 순서대로)
- **논리 의존 edge**: task B 가 task A 의 산출물 (helper 함수, 신규 파일, schema 등) 에 의존하면 edge

두 edge 의 결합으로 wave 분할. plan 의 task block 이 충분히 명세되어 있다면 메인이 추론 가능. plan frontmatter 에 별도 `depends_on:` / `touches:` 필드 추가 X.

### D3. 활성화 — 항상 자동

메인이 그린 DAG 에 wave > 1 이 있으면 자동 병렬. wave = 1 (모든 task 가 직선 의존) 이면 자연스럽게 sequential 과 동일하게 동작. 사용자에게 "병렬 켤까?" 묻지 않음. 게이트 추가 X.

### D4. Entry guard — plan 없으면 거부

`<slug>-implementation-plan.md` 가 없으면 `js-super-subagent-driven-development` 는 즉시 종료. "plan 없이 병렬 실행" 시나리오는 의미 없음 — DAG 추론 근거가 없다. `/write-plan` 먼저 돌리라는 한 줄 안내.

### D5. 충돌 검출 — wave 시작 전 dry-run

사용자 승인 게이트 추가 X. 대신 wave 안 implementer 들이 dispatch 직전 "내가 건드릴 파일" 을 선언하고, 메인이 wave 안 충돌 검사. 충돌 발견 시 wave 재분할 후 진행. (구현 디테일은 designing-direction 에서.)

### D6. 커밋 정책 — 단일 워킹트리 + wave 단위 직렬 commit

워크트리 분리 X. 같은 wave 안 task 들은 병렬 dispatch 후, 메인이 wave 끝나면 task 순서대로 stage + commit. 다음 wave 시작은 직전 wave 의 commit 완료 후. DAG 가 충돌 없는 그룹만 한 wave 로 묶었으므로 race 위험 없음.

### D7. 실패 격리

wave 안 task 1개 실패 (구현 에러 / spec-review FAIL):

- 통과한 형제는 그대로 commit
- 실패 task 만 격리, 메인이 사용자에게 보고
- DAG 에서 실패 task 의 후행 의존만 차단, 나머지는 다음 wave 진행

전체 abort 안 함. 자원 낭비 회피.

### D8. spec-reviewer 도 페어 단위 병렬

wave 의 task A (implementer → spec-reviewer 페어) 와 task B 페어가 동시 실행. wave 별 2-phase (모든 impl 끝 → 모든 review 일괄) 아님. 페어 단위 독립이 최대 속도.

### D9. 사용자 가시성 — wave 단위 요약

각 task 시작/끝 알림 X (병렬 인터리브 혼란). wave 단위만:

```
Wave 2/4 시작: task 3,5,7 병렬 실행…
Wave 2/4 완료: 3✓ 5✓ 7✗ (task 7 spec FAIL — 후행 task 9 차단)
```

### D10. Task별 모델 힌트 (v1.1.14 부록 통합)

plan 의 task block 에 `Model:` 필드 추가:

```markdown
## Task N: <task name>
- **Files**: ...
- **Model**: haiku | sonnet | opus
- **Tests**: ...
- **Steps**: ...
```

평가 룰 (writing-plans 스킬 본문에 명시):

- 코드 중심 + 1-2 파일 + 명확 spec → `haiku`
- 코드 다중 파일 / 디버깅 / 패턴 매칭 → `sonnet`
- Korean prose 조작 (skill 본문 / MD 편집) → `sonnet` (Haiku rephrasing risk)
- 설계 / 광범위 이해 → `opus`

dispatch 시 메인이 task 의 `Model:` 필드를 읽어 implementer-prompt 의 `model:` 으로 주입. 필드 없으면 sonnet 디폴트 (v1.1.13 이전 plan 호환).

### D11. spec-reviewer 모델 — sonnet 고정

implementer 의 `Model:` 미러링 / 한 단계 다운 모두 overengineering. spec review 는 본질적으로 명세-코드 대조라 sonnet 한 모델로 일관 처리. task block 에 `Reviewer Model:` 필드 추가 X.

## 인터랙션 흐름 (요약)

```
사용자: /execute-plan
↓ 게이트 #14: "서브에이전트" 선택
↓ js-super-subagent-driven-development 진입
↓ Entry guard: plan 존재 확인 (없으면 종료)
↓ 메인: plan 읽기 → DAG 추론 → wave 분할 → 각 task 의 Model 필드 로딩
↓ Wave 1 시작 안내 (task 목록만)
↓   페어 병렬 dispatch (task A 의 impl→review, task B 의 impl→review, …)
↓   각 implementer 가 dispatch 직전 file-touch 선언 → 메인 dry-run 충돌 검사 (충돌 시 wave 재분할)
↓   wave 끝남 → 메인이 task 순서대로 stage + commit
↓ Wave 1 완료 요약 (✓/✗ + 차단된 후행)
↓ Wave 2 진행 (실패 task 후행은 제외)
↓ … 모든 wave 끝나면 end-of-run consolidator (변경이력 1회 정리, 기존 v1.1.7 패턴 유지)
↓ finishing-a-development-branch 로 인계
```

## 범위 밖

- **인라인 모드 (`executing-plans`) 병렬화** — D1 에서 명시적 제외. 인라인의 단일 컨텍스트 직진 철학 보존.
- **DAG 사용자 승인 게이트** — D5 에서 명시적 제외. 사용자 의사결정 부담 추가 X.
- **워크트리 격리** — D6 에서 명시적 제외. 단일 워킹트리 + 직렬 commit 으로 충분.
- **Reviewer 별 모델 힌트** — D11 에서 overengineering 으로 판단. sonnet 고정.
- **plan 작성 시점에 `depends_on:` / `touches:` schema 추가** — D2 에서 제외. 메인이 task 설명만 보고 추론.
- **opus reviewer 시나리오** — D11 fixed sonnet 정책으로 자동 제외.
- **cross-feature 동시 실행** — 한 번에 하나의 plan 만. 멀티-plan 병렬은 별도 spec.

## 수용 기준 (간소)

- DAG wave > 1 인 plan 으로 `js-super-subagent-driven-development` 실행 시, wave 1 안 task 들이 병렬 dispatch (실측: wave 시작 시각 ↔ 첫 task 응답 도착 시각 비교) 됨
- wave 1 task 1개에 spec FAIL 강제 주입 시, 통과 형제 commit + 실패 task 격리 + 후행 task 차단 동작 검증
- plan 없는 상태에서 `js-super-subagent-driven-development` 호출 시 entry guard 발동 + 즉시 종료
- task block 에 `Model: haiku` 박힌 plan 으로 실행 시, 그 task 의 implementer dispatch 가 haiku 모델로 호출 (로그/대시보드에서 확인)
- task block 에 `Model:` 필드 없는 v1.1.13 이전 plan 으로 실행 시, sonnet 디폴트로 정상 작동 (backward compat)
- spec-reviewer 는 모든 task 에서 sonnet 으로 dispatch (implementer 모델과 무관)

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-05-10] [요구사항-수정]
- **id**: CH-20260510-001
- **이유**: 신규 피처 brainstorming 결과 (병렬화 + Task별 모델 힌트 통합 PRD 최초 생성)
- **무엇이**: 서브에이전트-병렬화-requirements.md 전체 (배경/목적/사용자 스토리/핵심 결정 D1~D11/인터랙션 흐름/범위 밖/수용 기준)
- **영향범위**: 없음 (최초 생성)
