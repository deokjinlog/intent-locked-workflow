# Worktree Merge-Back

워크트리에서 진행한 feature 작업을 parent (main) 워크트리로 안전하게 머지. "Merge down before merging up" 패턴 — 충돌 해결은 feature sandbox 에서만, parent 워크트리는 항상 깨끗.

**Announce at start:** "I'm using the worktree-merge-back skill — feature → parent merge with sandbox conflict resolution."

## 사용자 질문 룰 (v2.0.3+) — 항상 AskUserQuestion

이 skill 흐름 안에서 사용자에게 질문할 일이 생기면 **반드시** `AskUserQuestion`
도구로 호출한다. 산문으로 "~ 할까요?" 한 줄 던지지 마라.

### Why

Notification 훅 (`elicitation_dialog` 매처) 이 알람을 발화하려면 도구 호출이
실제로 일어나야 함. 산문 질문은 훅이 못 잡아서 사용자가 놓침 (v1.1.8 신고 재발).

### How to apply

- clarifying / Socratic / 모호점 확인 / 게이트 / 모드 선택 — 모두 포함
- 단답 yes/no 도 prose X → `AskUserQuestion` choices `[yes, no]` 사용
- 다중 선택은 enum choices 또는 multi-question batching (의미 결합 시 max 4 questions[])
- **예외**: 본문 자체의 알람-friendly 안내문은 질문 아니라 안내 — 도구 호출 불필요

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

## Process

### Step 1 — Working tree 검사 + commit 확인

- `git status --porcelain` 비어있음 → Step 2 자동 진행
- 변경사항 있음 → AskUserQuestion:

```python
AskUserQuestion(questions=[{
    "question": "Working tree 에 변경사항이 있습니다. 어떻게 처리할까요?",
    "header": "Working tree",
    "options": [
        {"label": "지금 commit", "description": "다음 turn 에 commit 메시지 입력 → skill 이 commit 후 Step 2 진행"},
        {"label": "직접 처리 후 재호출", "description": "skill 종료. 사용자가 수동 commit 후 재호출"}
    ],
    "multiSelect": False
}])
```

"지금 commit" 선택 시 → 사용자가 다음 turn 에 메시지 prose 로 입력 → `git commit -m "<msg>"` 실행 후 Step 2.

### Step 2 — Parent worktree 추론

```bash
# main worktree path + branch 추출
MAIN_INFO=$(git worktree list --porcelain | head -3)
MAIN_PATH=$(echo "$MAIN_INFO" | awk '/^worktree / {print $2; exit}')
MAIN_BRANCH=$(echo "$MAIN_INFO" | awk '/^branch / {print $2; exit}' | sed 's|refs/heads/||')

# 비표준 구조 차단
WT_COUNT=$(git worktree list | wc -l)
if [ "$WT_COUNT" -lt 2 ]; then
  echo "❌ feature 워크트리 없음. 현재 main 워크트리 1개만 존재."
  exit 1
fi
```

추론 실패 시 (multi-parent / nested) → 명시 차단 + 사용자가 수동 머지 안내.

### Step 3 — Parent 변경사항 흡수 (feature 쪽으로)

```bash
git fetch origin
git merge origin/$MAIN_BRANCH
```

**충돌 발생 시**:

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

자동 해결 시도 **절대 X** (한쪽 임의 채택 = 데이터 손실 위험).

abort 선택 시 → `git merge --abort` 실행. 실패 시 "수동 정리 필요" 안내 후 종료.

### Step 4 — Parent 워크트리로 머지

Pre-check (R3 mitigation):

```bash
# Step 3 흡수 가정 검증 — feature HEAD 가 parent 의 후손인지
git merge-base --is-ancestor origin/$MAIN_BRANCH HEAD || {
  echo "❌ Step 3 흡수 가정 깨짐. Step 3 중간 다른 작업 발생 의심. 수동 머지 필요."
  exit 1
}
```

검증 통과 시 merge commit 메시지 확인:

```python
AskUserQuestion(questions=[{
    "question": "Parent 워크트리로 머지합니다. merge commit 메시지를 어떻게 할까요?",
    "header": "Merge msg",
    "options": [
        {"label": "기본 메시지 사용", "description": "Merge branch '<feature>' into <parent>"},
        {"label": "직접 입력", "description": "다음 turn 에 메시지 prose 입력"}
    ],
    "multiSelect": False
}])
```

머지 실행:

```bash
FEATURE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git -C "$MAIN_PATH" merge --no-ff "$FEATURE_BRANCH" -m "<msg>"
```

`git -C` 사용 (cwd 변경 X — skill 종료 후 사용자가 feature 워크트리에 그대로 유지).

### Step 5 — 사후 처리 (multi-question batching, 모두 default no)

```python
AskUserQuestion(questions=[
    {
        "question": "워크트리를 제거할까요?",
        "header": "Worktree 제거",
        "options": [
            {"label": "no", "description": "그대로 두기 (default)"},
            {"label": "yes", "description": "git worktree remove <path> 실행"}
        ],
        "multiSelect": False
    },
    {
        "question": "feature 브랜치를 삭제할까요?",
        "header": "브랜치 삭제",
        "options": [
            {"label": "no", "description": "그대로 두기 (default)"},
            {"label": "yes", "description": "git branch -d <branch> 실행 (--force 안 함)"}
        ],
        "multiSelect": False
    },
    {
        "question": "parent 를 remote 에 push 할까요?",
        "header": "Push",
        "options": [
            {"label": "no", "description": "로컬에만 머지 유지 (default)"},
            {"label": "yes", "description": "git push origin <parent> (--force 절대 X)"}
        ],
        "multiSelect": False
    }
])
```

각각 yes 선택된 항목만 실행. worktree remove 실패 (uncommitted 변경) 시 force 여부 추가 AskUserQuestion (default normal).

## Anti-Patterns

| Wrong | Right |
|---|---|
| main 워크트리에서 invoke 후 그대로 진행 | HARD-GATE 차단. feature worktree 안에서만. |
| Step 3 충돌을 자동 해결 (ours / theirs) | NEVER. 사용자 판단. |
| Step 4 를 Step 3 흡수 검증 없이 진행 | merge-base 검증 필수 (R3). |
| `git push --force` 사용 | NEVER. normal push 만 (백로그 § Non-goals). |
| `cd <parent-path> && git ...` 패턴 | `git -C <parent-path>` 사용. cwd 변경 X. |
| worktree remove 시 --force default | normal 시도 후 실패 시만 사용자 명시 force. |
| 사후 처리 default yes | 모두 default no. 명시 yes 만 실행. |
| Step 별 실패 시 다음 자동 진행 | 즉시 중단. 사용자가 수동 정리. |

## Related Skills

- `setting-up-worktrees` — 워크트리 생성 페어 (백로그 § 결합, 영향 0)
- `finishing-a-development-branch` — 테스트 게이트 + 종료 메시지 (자동 호출 X)
- `change-history` — 본 skill 영향 0 (git 조작만, MD 안 건드림)
