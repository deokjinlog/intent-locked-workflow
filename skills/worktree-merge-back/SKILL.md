# Worktree Merge-Back (v2.0.5 slim)

워크트리에서 진행한 feature 작업을 parent (main) 워크트리로 안전하게 머지. "Merge down before merging up" 패턴 — 충돌 해결은 feature sandbox 에서만, parent 워크트리는 항상 깨끗.

**Announce at start:** "I'm using the worktree-merge-back skill — feature → parent merge with sandbox conflict resolution."

## When to Use

- 사용자가 명시적으로 `/worktree-merge-back` 또는 본 skill 호출 시에만
- 자동 발동 경로 없음 — `finishing-a-development-branch` 등 다른 skill 의 자동 호출 X
- 의도 명확 분기점 (사용자가 머지 의사 결정 완료한 시점)

## HARD-GATE — Worktree-Only

이 skill 은 **feature worktree 안에서만 사용 가능**. main 워크트리 또는 일반 작업트리에서 호출 시 즉시 차단.

```bash
# Guard 검출 (deterministic)
CURRENT_PATH=$(pwd)
MAIN_WORKTREE=$(git worktree list --porcelain | awk '/^worktree / {print $2; exit}')
if [ "$CURRENT_PATH" = "$MAIN_WORKTREE" ]; then
  echo "❌ 이 skill 은 worktree 안에서만 사용 가능합니다."
  echo "   현재: $CURRENT_PATH (main 워크트리)"
  echo "   먼저 \`/worktree <feature-name>\` 으로 워크트리 진입 후 재호출하세요."
  exit 1
fi
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "❌ git 저장소가 아닙니다."
  exit 1
}
```

추가로 `git worktree list` 결과가 1개 (main 만 존재) 면 차단 — feature 워크트리 없음.

## Process (v2.0.5+ — 게이트 1건 only, 나머지 자동 진행)

기존 v2.0.4 의 게이트 4건 (Step 1/3/4/5) 을 **Step 3 충돌 게이트 1건** 으로 슬림. 나머지는 default 권장사항 자동 진행 + 안전성 안내문.

### Step 1 — Working tree 검사 (자동, 게이트 X)

```bash
git status --porcelain
```

- 비어있음 → Step 2 자동 진행
- 변경사항 있음 → **즉시 종료 + 안내**:

```
❌ Working tree 에 변경사항이 있습니다.
   먼저 수동으로 commit 또는 stash 한 뒤 본 skill 을 재호출하세요.
   (skill 이 임의 commit 메시지를 생성하지 않습니다 — 사용자 의도 보존)
```

→ 게이트 없음. 사용자가 직접 처리 후 재호출. 자동 commit 안 함 (메시지 임의 생성 = 사용자 의도 손상).

### Step 2 — Parent worktree 추론 (자동)

```bash
MAIN_INFO=$(git worktree list --porcelain | head -3)
MAIN_PATH=$(echo "$MAIN_INFO" | awk '/^worktree / {print $2; exit}')
MAIN_BRANCH=$(echo "$MAIN_INFO" | awk '/^branch / {print $2; exit}' | sed 's|refs/heads/||')

WT_COUNT=$(git worktree list | wc -l)
if [ "$WT_COUNT" -lt 2 ]; then
  echo "❌ feature 워크트리 없음. 현재 main 워크트리 1개만 존재."
  exit 1
fi
```

추론 실패 (multi-parent / nested) → 명시 차단 + 종료.

### Step 3 — Parent 변경사항 흡수 (feature 쪽으로) — **유일한 게이트**

```bash
git fetch origin
git merge origin/$MAIN_BRANCH
```

**충돌 발생 시** — AskUserQuestion 게이트 (안전성, 데이터 손실 위험):

```python
AskUserQuestion(questions=[{
    "question": "Step 3 머지 충돌이 발생했습니다. 충돌 파일을 수동 해결 후 commit 하셨나요?",
    "header": "충돌 처리",
    "options": [
        {"label": "수동 해결 + commit 완료", "description": "Step 4 진행"},
        {"label": "abort", "description": "git merge --abort 실행 후 skill 종료"}
    ],
    "multiSelect": False
}])
```

자동 해결 시도 **절대 X** (한쪽 임의 채택 = 데이터 손실 위험). 이 게이트가 본 skill 의 유일한 AskUserQuestion 호출.

충돌 없으면 → Step 4 자동 진행.

### Step 4 — Parent 워크트리로 머지 (자동, default 기본 메시지)

Pre-check (R3 mitigation):

```bash
git merge-base --is-ancestor origin/$MAIN_BRANCH HEAD || {
  echo "❌ Step 3 흡수 가정 깨짐. Step 3 중간 다른 작업 발생 의심. 수동 머지 필요."
  exit 1
}
```

검증 통과 시 default 기본 메시지로 자동 머지:

```bash
FEATURE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git -C "$MAIN_PATH" merge --no-ff "$FEATURE_BRANCH" \
  -m "Merge branch '$FEATURE_BRANCH' into $MAIN_BRANCH"
```

→ 게이트 없음. 메시지 customize 원하면 사용자가 직접 `git -C <main-path> commit --amend` 로 수정 (Step 4 이후 자유).

### Step 5 — 사후 처리 안내 (자동, 게이트 X)

사후 처리 (worktree 제거 / 브랜치 삭제 / push) 는 모두 default no — skill 이 자동 실행하지 않음. 종료 메시지 한 줄로 안내:

```
✅ Merge 완료. Feature 워크트리: <FEATURE_BRANCH> → <MAIN_BRANCH> (commit: <merge-sha>)

다음 단계 (필요 시 직접 실행):
  - 워크트리 제거: git worktree remove <feature-path>
  - 브랜치 삭제:   git branch -d <feature-branch>
  - Remote push:   git -C <main-path> push origin <main-branch>
```

→ 사용자가 의도에 맞게 직접 선택. `setting-up-worktrees` 의 "keep worktree" / "discard" 자유 결정 보존.

## Anti-Patterns

| Wrong | Right |
|---|---|
| main 워크트리에서 invoke 후 그대로 진행 | HARD-GATE 차단. feature worktree 안에서만. |
| Step 3 충돌을 자동 해결 (ours / theirs) | NEVER. 사용자 판단. (유일한 게이트) |
| Step 4 를 Step 3 흡수 검증 없이 진행 | merge-base 검증 필수 (R3). |
| `git push --force` 사용 | NEVER. push 자체를 skill 이 하지 않음 (Step 5 안내만). |
| `cd <parent-path> && git ...` 패턴 | `git -C <parent-path>` 사용. cwd 변경 X. |
| 사후 처리 자동 실행 (worktree 제거 / push) | 모두 안내만. 사용자가 직접. |
| Step 1 dirty 시 임의 commit 메시지 생성 | NEVER. 즉시 종료 + 사용자 재호출 안내. |

## Why v2.0.5 slim

- v2.0.4 출시 후 사용자 dogfood 결과 게이트 4건이 마찰 → 1건으로 축소.
- 안전성 핵심 (Step 3 충돌 자동 해결 금지) 은 게이트 유지.
- 나머지 3건은 "default 권장사항" 자동 진행 + 안내문 (사용자 의도 보존 + 마찰 ↓).

## Related Skills

- `setting-up-worktrees` — 워크트리 생성 페어 (영향 0)
- `finishing-a-development-branch` — 테스트 게이트 + 종료 메시지 (자동 호출 X)
- `change-history` — 본 skill 영향 0 (git 조작만, MD 안 건드림)
