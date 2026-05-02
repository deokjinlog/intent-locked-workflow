# js-superpowers 플러그인 — 설계 문서 (Design Spec)

- **작성일**: 2026-05-02
- **작성자**: 이진섭 (dlwlstjq410@gmail.com)
- **플러그인 명**: js-superpowers v0.1.0
- **upstream**: superpowers 5.0.7 (Jesse Vincent, MIT)
- **상태**: 초안 (사용자 리뷰 대기)

---

## 1. 목적과 배경

superpowers 플러그인의 기존 워크플로우(brainstorming → writing-plans → executing-plans)는 강력하지만, 한국어 기반 1인/소수 개발 환경에서 다음이 부족하다:

1. **기획 레벨 요구사항(PRD)** 단계가 없다 — `spec.md`가 곧장 기술 설계로 진입
2. 설계 변경 시 **상위/하위 산출물의 cascading 동기화**가 수동
3. 메인 에이전트의 **정합성 + 코드 임팩트 검증** 게이트가 self-review 외엔 약함
4. 코드 변경 시 **변경 전 코드 보존**이 git 외 별도 트레이스가 없음
5. 위험/사이드이펙트 코드 지점에 대한 **표준화된 주석 규약**이 없음
6. 기능 구현 후 **API 자동 테스트**(데이터 획득까지 포함)가 워크플로우에 통합되지 않음

js-superpowers는 superpowers 베이스를 vendoring하여 위 6가지 갭을 메우는 한국형 워크플로우 확장 플러그인이다.

---

## 2. 아키텍처 개요

### 2.1 플러그인 형태

- superpowers-main 코드를 본 저장소 루트에 풀-카피 (vendored)
- `.claude-plugin/plugin.json` 의 이름/버전/upstream 필드 갱신
- upstream rebase 추적용으로 `upstream` 메타데이터 보관

### 2.2 워크플로우 파이프라인

```
/brainstorm    →  요구사항.md (PRD)            [기존 skill 수정]
     ↓
/design        →  개발방향.md (기술 설계)       [신규]
     ↓ ── 메인 에이전트 검증 게이트 (정합성 + 코드 임팩트)
/write-plan    →  구현계획서.md (단계별 plan)   [기존 skill 수정]
     ↓ ── 메인 에이전트 검증 게이트 (정합성 + 코드 임팩트)
/execute-plan  →  코드 구현 + 위험 주석 + 변경이력 기록  [기존 skill 수정]
     ↓
/api-test      →  DB SQL 안내 → 사용자 paste → pytest 시나리오 생성/실행 [신규]
```

### 2.3 디렉터리 구조 (변경/신규분만)

```
js-superpowers/
├── .claude-plugin/plugin.json       # 이름·upstream 갱신
├── skills/
│   ├── brainstorming/                # 수정: 산출물 = 요구사항.md
│   ├── writing-plans/                # 수정: 산출물 = 구현계획서.md, 검증 게이트
│   ├── executing-plans/              # 수정: 위험 주석 + 변경이력 자동 기록
│   ├── designing-direction/          # 신규: 개발방향.md
│   ├── verifying-spec/               # 신규: 메인이 정합성+임팩트 자체검증
│   ├── change-propagation/           # 신규: cascading 자동 감지·제안
│   ├── change-history/               # 신규: 3-MD 하단 이력 기록 규약
│   ├── risk-annotation/              # 신규: 위험 주석 형식 + 자동 부착
│   └── api-auto-testing/             # 신규: SQL→paste→pytest 시나리오
├── commands/
│   ├── brainstorm.md                 # 수정
│   ├── write-plan.md                 # 수정
│   ├── execute-plan.md               # 수정
│   ├── design.md                     # 신규
│   └── api-test.md                   # 신규
└── hooks/                            # 그대로
```

### 2.4 산출물 위치 (피처 단위)

```
docs/features/2026-05-02-<feature-slug>/
├── 요구사항.md
├── 개발방향.md
├── 구현계획서.md
└── api-tests/
    ├── conftest.py
    ├── scenario-001-<name>.py
    └── results/2026-05-02-1430.json
```

날짜는 **생성일 stamp(불변 ID)** — 작업 기간 길어도 폴더명 그대로 유지.

---

## 3. 3-MD 문서 스키마

### 3.1 요구사항.md (PRD, 기획 레벨, 기술 무관)

```markdown
# 요구사항: <피처명>
## 1. 배경/목적
## 2. 사용자 스토리 / 시나리오
## 3. 기능 요구사항 (FR)
## 4. 비기능 요구사항 (NFR)
## 5. 범위 밖 (Out of Scope)
## 6. 수용 기준 (Acceptance Criteria)

---
## 변경이력
```

### 3.2 개발방향.md (기술 설계, 기존 spec.md 상위호환)

```markdown
# 개발방향: <피처명>
## 1. 아키텍처 개요
## 2. 영향 받는 컴포넌트/파일
## 3. 데이터 모델/스키마 변경
## 4. 외부 인터페이스 (API, 이벤트)
## 5. 핵심 결정 + 대안 비교
## 6. 위험/사이드이펙트 (preliminary)
## 7. 테스트 전략

---
## 변경이력
```

### 3.3 구현계획서.md (단계별 plan)

```markdown
# 구현계획서: <피처명>
## 1. 단계별 작업
## 2. 위험 코드 지점
## 3. 롤백 전략

---
## 변경이력
```

---

## 4. 변경이력 항목 스키마

3개 MD 공통, 구조화 필드 강제 (역검색·자동화 활용).

```markdown
### [YYYY-MM-DD HH:MM] [요구사항-수정 | 개발방향-수정 | 구현계획서-수정 | 코드-수정 | API테스트]
- **id**: CH-YYYYMMDD-NNN          ← 자동 생성, grep 가능 ID
- **이유**: <왜 바꿨나>
- **무엇이**: <어느 섹션/필드/파일>
- **영향범위**: <하위 MD 또는 코드 어느 부분이 같이 갱신됐는지>
- **연관 항목**: CH-... (선행/관련)
```

### 4.1 코드-수정 항목 추가 필드 (구현계획서.md 한정)

```markdown
- **위험 카테고리**: side-effect | race | breaking | perf
- **변경 전 코드** (file:line)
  ```python
  # 이전 코드 그대로
  ```
- **변경 후 코드**
  ```python
  # 새 코드
  ```
```

### 4.2 API테스트 항목 (구현계획서.md 한정)

```markdown
- **시나리오 파일**: api-tests/scenario-001-<name>.py (N tests)
- **결과**: PASS x / FAIL y / ERROR z
- **실패 상세**: <실패 케이스 요약>
- **결과 파일**: api-tests/results/<timestamp>.json
- **다음 액션**: <필요 시 코드 수정 제안>
```

---

## 5. 메인 에이전트 검증 게이트 (verify-spec)

### 5.1 발동 시점

기존 superpowers self-review를 **그대로 유지**한 뒤, 추가로:

1. `/design` 종료 직전 — 요구사항.md ↔ 개발방향.md
2. `/write-plan` 종료 직전 — 요구사항.md + 개발방향.md ↔ 구현계획서.md

요구사항.md는 source of truth라 검증 대상 아님.

### 5.2 수행 주체

**메인 에이전트가 직접 수행**. 별도 verifier 서브에이전트는 만들지 않는다. 이유:
- 직전 brainstorming/writing-plans 대화 컨텍스트 보존 → 정확도 ↑
- 사용자가 검증 과정을 그대로 볼 수 있음 (transparency)
- 컨텍스트 핸드오프 손실 없음

단 **임팩트 분석이 광범위(많은 파일 grep 필요)할 때만** 메인 판단으로 Explore 서브에이전트 1회 호출 가능 (read-only, 컨텍스트 보호).

### 5.3 절차 (verifying-spec skill)

1. 직전 산출 MD + 모든 상위 MD를 Read
2. **A) 정합성 체크** — 상위 MD의 모든 FR/결정이 하위에 반영됐는지, 충돌·모순 점검
3. **C) 코드 임팩트** — 명시 파일/함수 존재 여부, 호출처(grep), 사이드이펙트 후보 식별
4. 결과를 마크다운 보고서로 정리: `누락 N건 / 모순 N건 / 영향 파일 N개 / 위험 지점 N개`
5. 사용자에 표시 → 사용자 결정(무시/수정) → 수정 시 해당 단계 skill 재진입

---

## 6. 변경 전파 (cascading update)

### 6.1 발동 방식 (하이브리드)

- **자연어 자동 감지** — 메인이 사용자 메시지에서 변경 레벨(요구사항/개발방향/구현계획서/코드) 판정 → 영향 받는 하위 산출물에 대해 검증 게이트 실행 → "다음 항목들이 함께 갱신될 수 있습니다: …" 사용자 승인 후 진행
- **명시적 override** — 사용자가 "요구사항만, 하위는 건드리지 마"처럼 범위 명시 시 그 지시 우선

### 6.2 영향 매트릭스

| 변경 위치 | 자동 영향 검토 대상 |
|---|---|
| 요구사항.md | 개발방향.md + 구현계획서.md + 코드 |
| 개발방향.md | 구현계획서.md + 코드 |
| 구현계획서.md | 코드 |
| 코드 직접 변경 | 구현계획서.md 변경이력만 (역방향 기록) |

### 6.3 처리 책임 (change-propagation skill)

1. 변경 레벨 식별
2. 영향 매트릭스 적용
3. 사용자 승인 게이트
4. 갱신 후 변경이력 entry 자동 작성

---

## 7. 위험 주석 규약

### 7.1 형식

```python
# ⚠️ RISK(<category>): <reason> — by <컨텍스트>
```

- 카테고리(고정 4종): `side-effect` | `race` | `breaking` | `perf`
- `<reason>`: 자유 한국어
- `<컨텍스트>`: 자유 텍스트, 권장 default = 현재 피처 슬러그 (예: `by 공지사항-개발`)
- grep 패턴: `RISK\(`

예시:
```python
# ⚠️ RISK(side-effect): 잔액이 -로 갈 수 있음 — by 공지사항-개발
# ⚠️ RISK(perf): N+1 쿼리 가능 — by 알림-리스트-개선
# ⚠️ RISK(breaking): 응답 스키마 변경 — by 결제-v2
```

### 7.2 부착 시점 (둘 다)

1. **메인이 코드 작성/수정 중** — `executing-plans` skill에서 위험 후보 자기 점검 → 해당 라인 위에 자동 부착
2. **메인 검증 단계(§5)** — 임팩트 분석 중 식별된 기존 코드의 위험 지점에도 부착 제안 → 사용자 승인 후 추가

두 경우 모두 변경이력에 어느 CH-id에서 부착됐는지 기록.

### 7.3 risk-annotation skill 책임

- 카테고리 정의/예시
- 부착 형식 규약
- **위험 후보 자기 점검 체크리스트 (명시 항목)**:
  1. **복잡 분기 / 순서 종속** — 수정 대상 함수가 다중 if/else, switch, early-return, 또는 호출 순서에 의존하는 흐름이라면 → `side-effect` 카테고리로 부착 (이 항목이 가장 빈번하게 사이드이펙트의 진원지)
  2. **외부 시스템 변경** — DB write, 파일 I/O, 네트워크 호출, 캐시 invalidate → `side-effect`
  3. **전역/공유 상태 변경** — module-level 변수, 싱글턴, 클래스 변수, lock 없는 동시 접근 → `race`
  4. **public 함수 시그니처/응답 스키마 변경** — 호출처 파급 → `breaking`
  5. **루프 안에서 쿼리/네트워크 호출** — N+1, 큰 루프 → `perf`
  6. **재귀/순회 깊이 가변** — 입력에 따라 폭발 가능 → `perf`
- 메인이 코드 변경 직전 위 6개 항목을 자기 점검(stdin 안 표시)하고 해당하면 자동 부착
- grep 기반 기존 위험 주석 수집 절차 (`grep -rn "RISK("`)

---

## 8. 변경 전 코드 보존

`executing-plans`가 코드 변경 시 반드시 수행:

1. 변경 직전 원본 코드를 Read로 확보
2. Edit 수행
3. 구현계획서.md 변경이력에 [코드-수정] 항목 자동 추가 (§4.1 풀 스키마: id/이유/무엇이/영향범위/위험 카테고리/변경 전 코드/변경 후 코드)
4. 요구사항.md / 개발방향.md 변경이력에는 코드 본문 안 들어가고 **요약 + 연관 CH-id 링크만**

---

## 9. API 자동 테스트 파이프라인

### 9.1 진입점

`/api-test` 슬래시 — 사용자 명시 트리거 only, 자동 실행 없음.

### 9.2 단계

1. **API 인벤토리 추출** — 메인이 구현계획서.md + 코드 Read → 새 API 엔드포인트 + 입력 파라미터 + 인증 요구 식별
2. **테스트 데이터 SQL 안내** — 메인이 사용자에게 SQL 제시 → 사용자 백엔드 DB에서 실행 후 결과 paste → 메인이 시나리오 데이터로 활용
3. **시나리오 코드 자동 생성** — pytest + requests 기반, `docs/features/<...>/api-tests/scenario-NNN-<name>.py`. 공통은 `conftest.py`로 추출 (베이스 URL, 헤더, 인증 토큰). 시나리오: happy path 1 + edge case 2~3
   - **인증 토큰 획득**: 메인이 먼저 프로젝트 코드(라우터, auth 미들웨어, 로그인 엔드포인트)를 Grep/Read로 탐색해 auth 패턴 식별 → 자동으로 적절한 fixture 생성:
     - JWT/세션 로그인 엔드포인트 발견 시 → `login()` 호출 fixture
     - 정적 토큰(env var) 패턴 발견 시 → `os.environ` 기반 fixture
     - OAuth/외부 IdP 등 모호하면 → 그때만 사용자에 질문
4. **자동 실행 + 결과 검증** — 메인이 Bash로 `pytest scenario-*.py -v --tb=short --json-report --json-report-file=results/<timestamp>.json` (의존성: `pytest`, `requests`, `pytest-json-report` — 첫 사용 시 자동 install 안내)
5. **결과 기록** — 구현계획서.md 변경이력에 [API테스트] 항목 자동 추가 (§4.2)
6. **실패 시 후속** — 메인이 사용자에 "코드 수정 필요해 보임, 진행?" 제안 → `/execute-plan` 재진입 (cascading 없이 코드만 수정)

### 9.3 보안

- 인증/시크릿은 사용자에게 물어 환경변수 / `.env.test`로만 사용
- 코드/문서에 시크릿 박지 않음
- DB는 사용자 paste만, MCP DB 커넥터 사용 안 함

---

## 10. 슬래시 커맨드 진입점 정리

| 커맨드 | 상태 | 동작 |
|---|---|---|
| `/brainstorm` | 수정 | 요구사항.md 산출 |
| `/design` | 신규 | 개발방향.md 산출 + 검증 게이트 |
| `/write-plan` | 수정 | 구현계획서.md 산출 + 검증 게이트 |
| `/execute-plan` | 수정 | 코드 구현 + 위험 주석 + 변경이력 |
| `/api-test` | 신규 | API 자동 테스트 파이프라인 |

기존 superpowers의 다른 커맨드(예: `/loop`, `/schedule` 등)는 그대로 유지.

---

## 11. 향후 작업 (out of scope, 별도 spec)

- 사용자 정의 위험 카테고리 확장
- MCP DB 커넥터 옵션 추가 (현 단계에서는 보안상 제외)

---

## 12. 미결 / 후속 결정 사항

(현재 없음 — 이전 두 항목은 §7.3, §9.2.3에 결정 사항으로 통합됨)
