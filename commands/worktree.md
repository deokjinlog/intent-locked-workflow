---
description: 현재 프로젝트 루트의 .worktrees/ 아래에 워크트리를 만들고 .env* 파일을 자동 복사합니다. 단수/복수 모두 지원.
---

# /worktree

이 커맨드는 `setting-up-worktrees` skill을 invoke 합니다.

## 사용 예

**단수:**
```
/worktree feature-a
```

**복수:**
```
/worktree feature-a feature-b feature-c
```

**자연어 (인수 없이 호출 후 대화):**
```
/worktree
워크트리 3개 만들어줘. 브랜치는 feature-a, feature-b, feature-c.
```

티켓명(`TICKET-123-기능명`)을 그대로 브랜치명으로 사용해도 됩니다 (한글/특수문자 OK).

## 동작

- 위치: `<프로젝트 루트>/.worktrees/<브랜치명>/`
- 브랜치 없으면 현재 HEAD에서 새로 생성, 있으면 그대로 사용
- **`.env*` 자동 복사**: 프로젝트 루트의 `.env`, `.env.local`, `.env.production` 등 모든 `.env*` 파일을 각 워크트리에 그대로 복사 (사용자에게 묻지 않음). `.env.example`/`.env.sample`/`.env.template` 같은 커밋된 템플릿은 제외.
- `.worktrees/` 가 `.gitignore` 에 없으면 자동 추가
- 이미 같은 path 가 있으면 skip + notice (덮어쓰기 X)

## 전제

현재 디렉터리가 git 저장소여야 함. 아니면 `git init` 안내.
