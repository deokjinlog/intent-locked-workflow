---
description: "사용자가 /list-skills 슬래시를 명시 호출했을 때만 발동. 현재 쓸 수 있는 skill 을 세 그룹(내가 만든 것 / dj-superkit 내장 / 기타)으로 묶어 전부 조회. 읽기 전용."
argument-hint: "(인자 없음)"
---

# List Skills 빌더 (skill 전체 조회)

현재 세션에서 쓸 수 있는 skill 을 **세 그룹으로 묶어 전부** 보여줍니다. 읽기 전용 — 파일을 바꾸지 않습니다.

| 그룹 | 무엇 | `/remove-skill` 로 삭제 |
|---|---|---|
| A. 내가 만든 skill | `/new-skill` 로 만든 것 (출처 표식 `.dj-superkit-skill.json` 보유) | ✅ 가능 |
| B. dj-superkit 내장 skill | 플러그인에 원래 들어 있는 skill | ❌ 불가 (플러그인 소속) |
| C. 기타 | 표식 없이 직접 만든 skill / 다른 플러그인 skill | ❌ 불가 |

> 핵심: **삭제 가능한 건 그룹 A 뿐**입니다. B·C 는 참고용 표시이고 `/remove-skill` 대상이 아닙니다 (내장·남의 skill 을 실수로 지우지 못하게 하는 안전장치).

## 1. 스캔 대상

### 그룹 A — 내가 만든 skill (출처 표식 보유)

- **프로젝트**: `<cwd>/.claude/skills/*/` 중 `.dj-superkit-skill.json` 존재하는 것
- **글로벌**: `~/.claude/skills/*/` 중 `.dj-superkit-skill.json` 존재하는 것

### 그룹 B — intent-locked-workflow 내장 skill

- `~/.claude/plugins/cache/intent-locked-workflow/intent-locked-workflow/<버전>/skills/*/`
- 버전 디렉토리가 여러 개면 **가장 높은 버전** 하나만 사용 (version sort 기준 마지막)

### 그룹 C — 기타 (직접 생성 / 다른 플러그인)

- **직접 생성**: `<cwd>/.claude/skills/*/` + `~/.claude/skills/*/` 중 표식 **없는** 것 (그룹 A 에 안 잡힌 나머지)
- **다른 플러그인**: `~/.claude/plugins/cache/*/*/skills/*/` 중 dj-superkit 제외 → 플러그인 이름으로 묶기

**다른(현재 작업 중이 아닌) 프로젝트의 `.claude/skills/` 는 스캔하지 않습니다.** 현재 프로젝트 + 글로벌 + 플러그인 캐시만 봅니다.

모든 그룹에서 `.removed-<timestamp>` 로 끝나는 디렉토리(`/remove-skill` safe-rename 결과)는 제외합니다.

## 2. 수집 절차

각 skill 에 대해:

1. `<slug>/SKILL.md` frontmatter 에서 `description` 1줄 추출 (실패 / 없음 → "(설명 없음)")
2. 그룹 A 는 스코프 태그 `[프로젝트]` / `[글로벌]` 병기
3. 그룹 C 의 직접 생성분은 `[직접 생성, 프로젝트]` / `[직접 생성, 글로벌]`, 다른 플러그인분은 `[플러그인: <이름>]` 병기
4. (선택) 그룹 A 는 `.dj-superkit-skill.json` 의 `created` 값으로 생성 시각 표시 가능

## 3. 출력 양식

세 그룹으로 묶어 메인 응답으로 출력. 변경 도구(Write/Edit/mutate Bash) 호출 없음 — 읽기 전용.

```
📋 사용 가능한 skill 전체

■ 내가 만든 skill (N개)   ← /remove-skill 로 삭제 가능
- <slug-a> [프로젝트] — <description 1줄>
- <slug-b> [글로벌] — <description 1줄>

■ dj-superkit 내장 skill (N개)
- <slug-c> — <description 1줄>
- <slug-d> — <description 1줄>
  … (내장 skill 전부)

■ 기타 (직접 생성 / 다른 플러그인, N개)
- <slug-e> [직접 생성, 프로젝트] — <description 1줄>
- <slug-f> [플러그인: frontend-design] — <description 1줄>

(스캔 경로: <cwd>/.claude/skills/, ~/.claude/skills/, ~/.claude/plugins/cache/)
```

- 그룹이 비어 있으면 그 그룹에 "- (없음)" 표시.
- **삭제 가능한 건 그룹 A 뿐**임을 그룹 A 헤더 옆에 명시.
- 스캔한 실제 경로를 끝에 명시 (cwd 가 프로젝트 루트가 아닐 가능성 catch).

## 4. 그룹 A 가 비었을 때

그룹 A(내가 만든 skill)가 0개여도 B·C 는 정상 표시하고, 그룹 A 자리에만 안내를 답니다:

```
■ 내가 만든 skill (0개)
- (없음) — /new-skill 로 만들면 여기에 뜹니다.
```

## 5. 금지

- **다른 프로젝트의 `.claude/skills/` 스캔 금지** — 현재 프로젝트 + 글로벌 + 플러그인 캐시만.
- **파일 변경 금지** — 읽기 전용 조회. Write / Edit / mutate Bash 호출 X.
- **삭제 가능 표시는 그룹 A 에만** — B(내장) / C(기타)에 삭제 가능 표시 금지. 사용자가 내장 skill 을 지우려다 차단당하는 혼란 방지.
- **`skills/list-skills/` 로 빌더 변환 금지** — 빌더는 command 로 유지 (자동 발동 사고 방지, META-BUILDER 룰 답습).
- **출처 표식은 신뢰 신호일 뿐 보안 경계 아님** — 사용자가 표식 파일을 수동 복사하면 비-dj-superkit skill 도 그룹 A 에 뜰 수 있음 (낮은 빈도, 수용).
