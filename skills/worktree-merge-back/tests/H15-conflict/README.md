# H15 — Step 3 conflict

## Scenario

Step 3 (parent 흡수 단계) 에서 main + feature 가 동일 파일 동일 라인 수정 → 충돌 → 사용자 수동 해결 → 정상 진행.

## Setup

1. `git worktree add ../feature-y -b feature-y`
2. feature-y 에서 `README.md` 라인 1 수정 ("from feature") + commit
3. main 에서 같은 `README.md` 라인 1 수정 ("from main") + commit
4. main 변경을 origin 에 push (Step 3 가 `git fetch origin` + `git merge origin/main` 패턴이라 필요)

## Trigger

feature-y 에서 `/worktree-merge-back` 호출.

## Expected

1. Guard 통과
2. Step 1 — clean (이미 commit 됨)
3. Step 2 — parent 추론
4. Step 3 — `git merge origin/main` → **충돌**. 충돌 파일 노출 (`README.md`). 메인 에이전트가 자동 해결 시도 X.
5. AskUserQuestion `[수동 해결 + commit 완료 / abort]` 발화
6. 사용자가 수동 `<<<<<<<` 마커 처리 후 `git add README.md && git commit` 한 뒤 "수동 해결 + commit 완료" 선택
7. Step 4 — merge-base 검증 통과 → merge commit 메시지 → 머지 실행
8. Step 5 — 사후 처리

## Catch

- 충돌 노출 시점 메인 에이전트가 `git checkout --ours` / `--theirs` / 임의 Edit 시도 0건
- AskUserQuestion 발화 (elicitation_dialog 매처 트리거)
- abort 선택 시 `git merge --abort` 후 즉시 skill 종료 (Step 4 진행 X)
