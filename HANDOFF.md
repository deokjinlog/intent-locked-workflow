# js-super Plugin — Handoff

> 다음 에이전트가 이 문서만 보고 이어 작업할 수 있도록 정리한 인수인계서.
> 마지막 갱신: 2026-05-02 (v1.0.2 푸시 완료 시점)

---

## 프로젝트 한 줄 요약

**Claude Code 플러그인** — superpowers 5.0.7 베이스 위에 한국형 spec-driven 워크플로우를 얹은 v1.0.2.

- 저장소: `/Users/goldenplanet/jinsup_space/js-super`
- GitHub: `https://github.com/LonerStayle/js-super` (마켓플레이스 shorthand: `LonerStayle/js-super`)
- 작성자: 이진섭 (dlwlstjq410@gmail.com)
- 라이선스: MIT (upstream 동일)

## Goal

superpowers 의 검증된 워크플로우(brainstorming → writing-plans → executing-plans)를 그대로 두면서, **한국어 1인/소수 개발 환경**용 spec-driven 확장 추가:

1. **3-MD 산출물 분리** — `<slug>-requirements.md` (PRD) → `<slug>-tech-design.md` (기술 설계) → `<slug>-implementation-plan.md` (단계별 plan)
2. **메인 검증 게이트** (verifying-spec) — 정합성 + 코드 임팩트 4축 보고서, 메인 직접 수행
3. **변경이력 자동 누적** (change-history) — 구조화 entry, CH-id 자동, before/after 코드 보존
4. **변경 전파** (change-propagation) — 자연어 변경 요청 → 영향 매트릭스 → 사용자 승인 cascading
5. **위험 주석** (risk-annotation) — `# ⚠️ RISK(side-effect|race|breaking|perf): reason — by ctx` 표준 + 6-체크리스트
6. **API 자동 테스트** (api-auto-testing) — `/api-test`, SQL 안내 → paste → pytest 시나리오 자동 생성/실행
7. **워크트리 빠른 생성** (setting-up-worktrees) — `/worktree feature-a feature-b ...`, `.env*` 자동 복사

## Current Progress (v1.0.2)

### ✅ 완료된 것

**플러그인 구조**
- 9개 신규 skill (change-history / brainstorming(수정) / designing-direction(신규) / writing-plans(수정) / executing-plans(수정) / verifying-spec / change-propagation / risk-annotation / api-auto-testing / setting-up-worktrees)
- 6개 슬래시 커맨드 (`/brainstorm`, `/design`, `/write-plan`, `/execute-plan`, `/api-test`, `/worktree`)
- 2개 helper Python 스크립트 (`scripts/change_id.py`, `scripts/detect_auth.py`) — TDD, 7/7 tests passing
- 1개 템플릿 (`templates/api-tests/conftest.py.template`)

**문서**
- `README.md` — 6개 기능 + 워크플로우 다이어그램 + 설치 (A. GitHub-hosted / B. 로컬) + 빠른 시작 + 워크트리 + 의존성 + upstream 관계
- `docs/superpowers/specs/2026-05-02-js-superpowers-design.md` — 설계 문서
- `docs/superpowers/plans/2026-05-02-js-superpowers.md` — 구현 plan
- `docs/migrations/2026-05-02-rename-to-js-super.md` — js-superpowers → js-super 마이그레이션 가이드
- `docs/plugin-update.md` — 플러그인 업데이트 절차 cheat sheet

**git 상태**
- main 브랜치, GitHub `LonerStayle/js-super` 에 push 완료
- 마지막 commit: `6f9dad5 코드 변경 기록 타이밍을 최후로 이동 (병목 문제 제거)`
- 태그 미적용 (`git tag v1.0.2 && git push --tags` 미수행 — 필요 시 진행)

### 🔄 워크플로우 동작 (v1.0.2 기준)

```
/brainstorm    → <slug>-requirements.md (PRD)
                  → "designing-direction 으로 진행할까요?" 게이트 → 승인 시 자동 invoke
/design        → <slug>-tech-design.md (기술 설계)
                  → verifying-spec 자동 실행 (보고서 + doc 단일 게이트)
                  → 승인 시 자동으로 writing-plans invoke
/write-plan    → <slug>-implementation-plan.md
                  → verifying-spec 자동 실행 + 단일 게이트
                  → Subagent-Driven / Inline 선택
/execute-plan  → 코드 구현
                  → per-task batched discipline (Phase 1: per-edit 빠른 단계 → Phase 2: task 끝에 변경이력 1번 batch)
/api-test      → SQL 안내 → paste → pytest 시나리오 → 결과를 변경이력에 기록
```

산출물 위치: `docs/features/YYYY-MM-DD-<slug>/{<slug>-requirements.md, <slug>-tech-design.md, <slug>-implementation-plan.md, api-tests/}`

## What Worked

- **superpowers 풀 vendoring** — fork 대신 vendor + custom skill 추가가 깔끔. plugin.json `upstream` 필드로 베이스 추적.
- **Skill 본문은 영어, 도메인 식별자만 한국어** — LLM 인스트럭션 정확도 ↑, 한국 정체성 유지. 한국어 유지 항목: 파일명(`<slug>-requirements.md`), 섹션 헤더(`변경이력`), entry 태그(`[코드-수정]`), 카테고리, 사용자 출력 prompt.
- **TaskCreate per Checklist 항목** — 진행 트래킹 + 단계 누락 방지. using-superpowers SKILL에 "TaskCreate 언어를 사용자 대화 언어와 매칭" 룰 추가됨.
- **단일 통합 게이트** (designing-direction / writing-plans) — verifying-spec 보고서 + doc 을 한 메시지에 묶어 1번 승인. doc 승인 따로, verify 승인 따로 시키던 어색함 제거.
- **per-task batched logging** (v1.0.2 핵심) — 변경이력 entry 를 매 코드 변경마다 X → task당 1번. 구현계획서.md Read+Edit 호출 N→1배 감소.
- **Trivial-Edit Exception** (v1.0.1) — ≤3 lines + 로직 변경 없음 + 0/6 risk = 풀 schema 생략, 한 줄 entry. 타이포/주석 정리에서 큰 차이.
- **Step 4 (Verify) 제거** (v1.0.1) — Edit 후 재 Read로 RISK 주석 검증하던 redundant 단계 제거.
- **GitHub shorthand `LonerStayle/js-super`** — 마켓플레이스 등록 시 `.git` 풀 URL 대신 shorthand 쓰면 UI 표시도 깔끔하게 `LonerStayle/js-super`.
- **`/plugin marketplace update <name>`** — name 기반 (source URL 아님). marketplace.json 의 `name` 필드가 호출 키.

## What Didn't Work

- **TaskCreate 언어가 영어로 default** — 사용자가 한국어 대화 중인데 task 내용이 영어로 나오던 문제. using-superpowers 에 명시적 매칭 룰 추가로 해결.
- **per-edit logging 패턴** (v1.0.0) — 매 코드 변경마다 변경이력 entry append → 구현계획서.md 비대화 + Read 비용 누적 → /execute-plan 체감 느림. v1.0.2 의 batched 방식으로 해결됨.
- **5-step discipline 의 Verify 단계** (v1.0.0) — Edit 후 재 Read 로 검증, redundant. v1.0.1 에서 제거.
- **doc 승인 + verify 승인 두 단계 게이트** — 사용자가 같은 산출물을 두 번 결정해야 했음. v1.0.1 에서 단일 통합 게이트로 변경.
- **Korean reply token 열거** (`ㅇㅇ`/`응`/`잠깐` 등) — skill 본문에 명시 → LLM 인스트럭션이 한국어 의성어로 오염. 영어 baseline + "parse intent (approve/hold/unclear)" 로 변경.
- **GNG-* 회사 티켓명 placeholder** — 초기 worktree skill 예시에 실제 회사 티켓명이 들어가 있던 사고. `feature-a/b/c` 로 모두 스크럽.
- **로컬 절대 경로 (`/Users/goldenplanet/...`) README 노출** — 다른 사용자가 쓸 수 없는 경로. `<JS_SUPER_PATH>` placeholder + 환경변수 export 안내로 변경.
- **Python subprocess (`scripts/change_id.py`) 호출 비용** — 사용자가 의심한 후보였으나 측정해보니 ~400ms 정도, 실제 dominant factor 아님. 그대로 유지.

## 알려진 한계 (Risk Register)

- `detect_auth.py` regex 단순 — `/auth/login`·`/login` 만 매치, OAuth 등 미감지 → "unknown" 반환 시 사용자 직접 입력 fallback
- `change-history` 강제는 soft enforcement — Claude 가 안 invoke 하면 entry 누락 가능. acceptance grep 으로 보강.
- 큰 task 의 batched entry 가 단일 entry 로 매우 길어질 수 있음 (per-task 디자인의 트레이드오프) — 단일 task 가 너무 크면 plan 작성 시 더 잘게 쪼개도록 권장.

## Next Steps

### 🔴 즉시 (사용자 액션)

- [ ] **Claude Code 세션 재시작** — v1.0.2 skill 본문 반영 (`/plugin marketplace update js-super` + `/plugin update js-super@js-super` 후)
- [ ] **`git tag v1.0.2 && git push origin v1.0.2`** — 태그 push 안 했으면 진행 (다른 사용자가 특정 버전 install 가능하게)

### 🟡 단기 (다음 세션)

- [ ] **첫 진짜 피처로 dogfood** — `/brainstorm <피처명>` → `/design` → `/write-plan` → `/execute-plan` → `/api-test` 한 사이클을 진짜로 돌려보고 발견되는 문제 follow-up plan 으로 정리. 특히 v1.0.2 batched logging 이 의도대로 동작하는지 확인.
- [ ] **per-task batched entry 형식 검증** — task 안에서 코드 5번 변경했을 때 변경이력에 entry 1개 (`[코드-수정] (task: ...)` 태그) 만 추가되고 풀 before/after 가 task scope 으로 묶여 잘 표시되는지 확인.
- [ ] **README "첫 사용 빠른 시작" 갱신** — 진짜 피처 결과로 placeholder 예시 대체.

### 🟢 중기 (필요 시)

- [ ] `detect_auth.py` regex 확장 — 현실 백엔드 패턴(JWT 다양한 path, OAuth, API key 등) 더 많이 감지
- [ ] **옵션 C 적용 검토** — `subagent-driven-development` 모드의 reviewer subagent 2개 생략 (`--fast` 플래그). 일상 작업에서 task당 ~50% 빠르지만 자동 review 손실. 필요 느낄 때만.
- [ ] **upstream superpowers 5.0.8+ 나오면 rebase** — 현재 5.0.7 vendoring. plugin.json `upstream.version` 필드로 추적 중.
- [ ] **CHANGELOG.md 작성** — 버전별 변경사항을 별도 파일로 정리 (현재는 git commit 메시지에만 있음).

### 🟢 장기 (out of scope, 별도 spec)

- 사용자 정의 위험 카테고리 확장 (현재 4종 고정)
- MCP DB 커넥터 옵션 (현재는 SQL paste only — 보안상 의도)

## 핵심 파일 (다음 에이전트가 자주 봐야 할 것)

- `skills/executing-plans/SKILL.md` — v1.0.2 의 핵심 변경(per-task batched discipline)
- `skills/change-history/SKILL.md` — entry schema (batched / legacy / trivial 3 form)
- `skills/risk-annotation/SKILL.md` — 6-checklist
- `skills/using-superpowers/SKILL.md` — TaskCreate 언어 매칭 룰
- `.claude-plugin/plugin.json` — version, homepage, repository
- `.claude-plugin/marketplace.json` — 마켓플레이스 메타데이터
- `docs/superpowers/specs/2026-05-02-js-superpowers-design.md` — 원래 설계 의도
- `docs/plugin-update.md` — 업데이트 절차 cheat sheet

## 작업 컨벤션 (다음 에이전트 주의사항)

- **skill 본문은 영어, 한국어는 식별자/사용자 출력 문구만** — LLM 인스트럭션 정확도 위함
- **버전 bump 시 3 파일 동시 수정** — `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `package.json` 모두 같은 숫자
- **민감정보 (회사 티켓명/실 경로) 노출 금지** — `<placeholder>` 또는 `feature-a/b/c` 사용
- **사용자가 한국어로 대화하면 답변과 TaskCreate 모두 한국어로** (using-superpowers SKILL의 Conversation Language Mirroring 룰)
- **변경이력 entry, 마이그레이션 문서 등 사용자가 보는 산출물은 한국어 OK**

## 다음 세션 시작 예시

새 conversation 에서:

```
/Users/goldenplanet/jinsup_space/js-super/HANDOFF.md 읽고 이어가자
```

또는 구체 작업이면:

```
HANDOFF.md 읽고, Next Steps 의 "첫 진짜 피처로 dogfood" 부터 진행해줘.
피처명은 <기능명>. /brainstorm 으로 시작.
```
