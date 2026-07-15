---
commit_policy: per-task
---

# 사용자 잔액 출금 구현계획서

> **intent-locked-workflow 예시 산출물** — `/writing-plans` 가 만드는 **③ 계획** 단계 문서이고,
> `/executing-plans` 가 이 문서를 읽어 **④ 실행**합니다. 하단 변경이력은 실행이 남긴 기록입니다.
> 상위 문서: [요구사항](잔액-출금-requirements.md) · [개발방향](잔액-출금-tech-design.md)

## 1. 단계별 작업

### Task 1 — 출금 건 엔티티 + 마이그레이션

**Model**: haiku · **의존**: 없음

1. `tests/test_withdrawal_entity.py` 작성 — 상태 기본값 `대기`, 금액 음수 거부. **실패 확인.**
2. `models/withdrawal.py` 생성 → 테스트 통과.
3. 마이그레이션 생성 (`withdrawals` 테이블 + `idem_key` unique).

**검증**: `pytest tests/test_withdrawal_entity.py` 전부 통과.

---

### Task 2 — 잔액 차감/복원 (동시성)

**Model**: sonnet · **의존**: Task 1

1. `tests/test_account_balance.py` 작성 — 동시 2건 신청 시 하나만 성공. **실패 확인.**
2. `models/account.py` 에 차감/복원 추가. `SELECT FOR UPDATE` 적용.

**원본** (`models/account.py:41`)
```python
def debit(self, amount: int) -> None:
    self.balance -= amount
```

**수정 후**
```python
def debit(self, amount: int) -> None:
    # ⚠️ RISK(race): 잔액 행 잠금 없이 호출하면 동시 요청에 잔액이 음수가 됨
    #                — 반드시 SELECT FOR UPDATE 로 잠근 세션에서 호출할 것 (NFR-1)
    if amount <= 0:
        raise ValueError("amount must be positive")
    if self.balance < amount:
        raise InsufficientBalance(self.balance, amount)
    self.balance -= amount
```

**검증**: `pytest tests/test_account_balance.py` — 동시성 테스트 포함 통과.

---

### Task 3 — 신청/취소 서비스

**Model**: sonnet · **의존**: Task 2

1. `tests/test_withdrawal_service.py` — 신청→취소→잔액 복원 왕복, 완료 건 취소 거부. **실패 확인.**
2. `services/withdrawal_service.py` 구현 — 차감 + 건 생성을 **한 트랜잭션**으로.

**검증**: 왕복 테스트 통과, 완료 건 취소 시 거부.

---

### Task 4 — API 3개

**Model**: haiku · **의존**: Task 3

1. `tests/test_withdrawals_api.py` — 3개 엔드포인트 상태코드. **실패 확인.**
2. `api/withdrawals.py` 구현.

**검증**: `pytest tests/test_withdrawals_api.py` 전부 통과.

## 2. 위험 코드 지점

| 위치 | 카테고리 | 내용 |
|---|---|---|
| `models/account.py:41` `debit()` | race | 잠금 없이 호출 시 잔액 음수 — RISK 주석 부착 |
| `services/withdrawal_service.py` | side-effect | 차감 후 예외 시 돈만 사라짐 — 트랜잭션 경계 필수 |
| `models/account.py` `debit()` 호출자 | breaking | 적립/환불도 같은 메서드 사용 — 시그니처 유지 확인 |

## 3. 롤백 전략

1. 코드는 task 단위 commit → 문제 task 만 `git revert`.
2. 마이그레이션은 `downgrade()` 로 `withdrawals` 테이블 제거.
3. `models/account.py` 는 기존 메서드 시그니처를 유지하므로, 되돌려도 적립/환불 영향 없음.

## 변경이력

| CH-id | 일시 | 종류 | 내용 | 사유 |
|---|---|---|---|---|
| CH-001 | 2026-07-15 13:10 | [구현계획-신규] | 최초 작성 (Task 1~4, 위험 3건) | ③ 계획 게이트 통과 |
| CH-002 | 2026-07-15 14:38 | [코드-수정] (batch: tasks 1..4) | 엔티티 · 잔액 차감/복원 · 서비스 · API 구현. RISK(race) 1건 부착 (`account.py:41`). 연관 commit `a1b2c3d`..`f4e5d6c` | ④ 실행 — 계획 그대로 완료 |
| CH-003 | 2026-07-15 14:52 | [검증] | 동시성 테스트 2건 추가 통과, 누락/초과 작업 없음 | 실행 후 자체 검증 |
