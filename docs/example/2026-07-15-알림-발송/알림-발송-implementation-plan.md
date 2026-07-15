---
commit_policy: per-task
---

# 알림 발송 구현계획서

> **intent-locked-workflow 예시 산출물** — `/writing-plans` 가 만드는 **③ 계획** 이고,
> `/executing-plans` 가 이 문서를 읽어 **④ 실행**합니다. 하단 변경이력은 실행이 남긴 기록입니다.
> 상위 문서: [요구사항](알림-발송-requirements.md) · [개발방향](알림-발송-tech-design.md)

## 0. 작업 의존 관계 (DAG)

```
Task 1 (알림 엔티티) ──┬──▶ Task 3 (생성 서비스) ──▶ Task 4 (워커 + 재시도)
Task 2 (사용자 설정) ──┘
       │
       └──────────────▶ Task 5 (조회/읽음 API)

wave 1: Task 1 · Task 2   (서로 독립 — 동시 진행)
wave 2: Task 3 · Task 5   (Task 5 는 Task 1 만 필요)
wave 3: Task 4
```

## 1. 단계별 작업

### Task 1 — 알림 엔티티 + 마이그레이션

**Model**: haiku · **의존**: 없음

1. `tests/test_notification_entity.py` — 기본 상태 `대기`, `dedup_key` 없으면 거부. **실패 확인.**
2. `models/notification.py` 생성 → 통과.
3. 마이그레이션 — `notifications` 테이블 + `dedup_key` **unique 인덱스**.

**검증**: `pytest tests/test_notification_entity.py` 통과 + 같은 `dedup_key` 2회 삽입 시 DB 예외.

---

### Task 2 — 사용자 알림 설정

**Model**: haiku · **의존**: 없음 *(Task 1 과 동시 진행 가능)*

1. `tests/test_notification_pref.py` — 미설정 시 기본 켜짐, 끄면 꺼짐. **실패 확인.**
2. `models/notification_pref.py` + 마이그레이션 → 통과.

**검증**: `pytest tests/test_notification_pref.py` 통과.

---

### Task 3 — 알림 생성 서비스

**Model**: sonnet · **의존**: Task 1, Task 2

1. `tests/test_notification_service.py` — 설정 꺼짐 → 생성 0건, 같은 이벤트 2회 → 1건. **실패 확인.**
2. `services/notification_service.py` — 설정 확인 → `대기` 로 DB 기록 → 큐 투입 (결정 3 순서 준수).

**원본** (`services/notification_service.py` — 신규 파일)
```python
# (신규)
```

**수정 후**
```python
def create(self, user_id: int, event_type: str, event_id: str) -> list[Notification]:
    # ⚠️ RISK(side-effect): DB 기록 전에 큐로 보내면 큐 유실 시 흔적이 없음
    #                       — 반드시 '대기' 저장 후 큐 투입 (NFR-3 / 결정 3)
    made = []
    for channel in ("push", "email"):
        if not self.prefs.enabled(user_id, event_type, channel):
            continue
        key = f"{user_id}:{event_type}:{event_id}:{channel}"
        try:
            n = self.repo.insert(user_id, event_type, channel, status="대기", dedup_key=key)
        except UniqueViolation:
            continue  # ⚠️ RISK(breaking): 중복은 조용히 skip — 재시도가 새 행을 만들면 안 됨
        self.queue.push(n.id)
        made.append(n)
    return made
```

**검증**: `pytest tests/test_notification_service.py` 통과 (중복 테스트 포함).

---

### Task 4 — 발송 워커 + 재시도

**Model**: sonnet · **의존**: Task 3

> **CH-003 반영됨** — 아래 2번은 실행 중 발견으로 갱신된 내용입니다. 하단 변경이력 참조.

1. `tests/test_notification_worker.py` — 워커 2대 동시 집기 → 한 대만, 3회 실패 → `실패` 보존. **실패 확인.**
2. `workers/notification_worker.py` — **같은 알림 행을 재사용**하며 `attempts` 증가 + `next_retry_at` 백오프.

**수정 후** (발췌)
```python
def claim(self, notification_id: int) -> Notification | None:
    # ⚠️ RISK(race): 조건부 UPDATE 로만 집을 것. SELECT 후 UPDATE 로 나누면
    #                워커 2대가 같은 건을 동시에 집어 중복 발송됨 (NFR-2)
    rows = self.repo.update_where(
        id=notification_id, expect_status="대기", set_status="발송중",
    )
    return rows[0] if rows else None   # 못 집으면 다른 워커가 이미 가져간 것

def retry(self, n: Notification) -> None:
    # ⚠️ RISK(breaking): 재시도는 '같은 행' 재사용. 새 행을 만들면 dedup_key unique 위반이자
    #                    사용자에겐 중복 알림 — 의도("귀찮게 하지 않게") 위반
    n.attempts += 1
    if n.attempts >= 3:
        n.status = "실패"          # 조용히 버리지 않음 (FR-5)
    else:
        n.status = "대기"
        n.next_retry_at = now() + backoff(n.attempts)
    self.repo.save(n)
```

**검증**: `pytest tests/test_notification_worker.py` — 동시성 · 재시도 · 실패 보존 통과.

---

### Task 5 — 조회 / 읽음 API

**Model**: haiku · **의존**: Task 1 *(Task 3 과 동시 진행 가능)*

1. `tests/test_notifications_api.py` — 목록 · 읽음 · 설정 변경 상태코드. **실패 확인.**
2. `api/notifications.py` 구현.

**검증**: `pytest tests/test_notifications_api.py` 통과.

## 2. 위험 코드 지점

| 위치 | 카테고리 | 내용 |
|---|---|---|
| `notification_service.py` `create()` | **side-effect** | DB 기록 전 큐 투입 시 유실 — 순서 고정 |
| `notification_service.py` `create()` | **breaking** | 중복 삽입 예외를 삼키지 않으면 재시도마다 새 행 |
| `notification_worker.py` `claim()` | **race** | 조건부 UPDATE 아니면 워커 2대 중복 발송 |
| `notification_worker.py` `retry()` | **breaking** | 재시도가 새 행을 만들면 중복 알림 = 의도 위반 |

## 3. 롤백 전략

1. task 단위 commit → 문제 task 만 `git revert`.
2. 마이그레이션 `downgrade()` — `notifications` · `notification_prefs` 제거.
3. 워커는 별도 프로세스 — 중지해도 기존 API 영향 없음. 알림은 `대기` 로 남아 재기동 시 복구.

## 변경이력

| CH-id | 일시 | 종류 | 내용 | 사유 |
|---|---|---|---|---|
| CH-001 | 2026-07-15 13:20 | [구현계획-신규] | 최초 작성 (Task 1~5, DAG 3 wave, 위험 4건) | ③ 계획 게이트 통과 |
| CH-002 | 2026-07-15 14:05 | [코드-수정] (batch: tasks 1..3) | 엔티티 · 설정 · 생성 서비스 구현. RISK 2건 부착. 연관 commit `3f1a20b`..`9c4d81e` | ④ 실행 — wave 1~2 계획대로 완료 |
| **CH-003** | 2026-07-15 14:31 | **[계획-수정]** | Task 4 의 "재시도 시 **새 알림 행 생성**" → "**같은 행 재사용 + attempts 증가**" 로 변경. 개발방향 위험표에도 동일 반영 | **실행 중 발견** — 계획대로 새 행을 만들면 `dedup_key` unique 에 걸림. `dedup_key` 에 시도 번호를 붙이면 제약은 피하지만 **사용자에게 중복 알림** = 의도("귀찮게 하지 않게") 배신. 코드에서 우회하지 않고 `change-propagation` 으로 **개발방향 → 계획 순으로 갱신 후 재개** |
| CH-004 | 2026-07-15 15:02 | [코드-수정] (batch: tasks 4..5) | 워커 · 재시도 · API 구현. RISK(race) 1건 부착. 연관 commit `a70f3c2`..`e11b944` | ④ 실행 — CH-003 갱신본 기준으로 재개 |
| CH-005 | 2026-07-15 15:15 | [검증] | 동시성 · 멱등성 · 실패 보존 테스트 통과. 누락/초과 작업 없음 | 실행 후 자체 검증 |
