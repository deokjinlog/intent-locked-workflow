---
description: "사용자가 /remove-skill 슬래시를 명시 호출했을 때만 발동. 글로벌 ~/.claude/skills/<slug>/ 디렉토리를 안전하게 정리 (default = .removed-<timestamp> 로 rename, --force = rm -rf hard-delete)."
argument-hint: "<slug> [--force] [--dry-run]"
---

# Remove Skill 빌더 (글로벌 skill 정리)

`/new-skill` 로 만든 skill 을 글로벌 `~/.claude/skills/<slug>/` 에서 정리합니다. default 는 safe-rename (회복 가능), `--force` 는 hard-delete (회복 불가).

## 1. 사전 검증

`$ARGUMENTS` 첫 토큰이 slug 인자입니다 (필수). 누락 시 다음 안내 후 중단:

> 어떤 skill 을 정리할지 slug 를 알려주세요.
>
> 예: `/remove-skill auto-format-md` (safe-rename)
> 예: `/remove-skill --dry-run auto-format-md` (미리보기)
> 예: `/remove-skill auto-format-md --force` (회복 불가 hard-delete)

## 2. 입력 파싱

`$ARGUMENTS` 토큰 분해:

- **첫 kebab-case 토큰** → slug 인자
- **`--force` / `--dry-run` 토큰** → 플래그로 인식 (위치 무관)

예시:
```
/remove-skill auto-format-md --dry-run
↓
- slug: "auto-format-md"
- 플래그: ["--dry-run"]
```

## 3. 존재 검증 + 메타데이터 수집

LS 도구로 `~/.claude/skills/<slug>/` 디렉토리 존재 확인:

- **존재 X** → § 4 의 부재 분기로
- **존재 Y** → 디렉토리 크기 (LS 결과의 파일 size 합) + SKILL.md 의 마지막 수정 timestamp 수집

수집된 메타데이터는 보고 양식 (§ 5) 에서 사용. 미확보 시 "<unknown>" 표시.

## 4. 분기 실행

### 4-1. 부재 (~/.claude/skills/<slug>/ 가 없음)

LS 도구로 `~/.claude/skills/` 전체 목록 가져와서 abort 메시지에 현재 글로벌 skill 목록 표시. § 5-4 보고 양식 사용. 변경 X.

### 4-2. `--dry-run` 명시 (변경 X)

§ 5-3 보고 양식으로 메인 응답 — 어떤 디렉토리가 어디로 rename / 삭제되는지 안내. Bash / Edit / Write 도구 호출 X.

### 4-3. default safe-rename

Bash 도구로 1 줄 호출:

```bash
mv ~/.claude/skills/<slug> ~/.claude/skills/<slug>.removed-$(date +%Y%m%d%H%M%S)
```

성공 시 § 5-1 보고. timestamp 는 단위 unique 보장 (동시 호출 0 가정).

### 4-4. `--force` 명시 (옵트인 hard-delete)

Bash 도구로 1 줄 호출:

```bash
rm -rf ~/.claude/skills/<slug>
```

회복 불가. § 5-2 보고 (회복 불가 강조).

## 5. 보고 양식

### 5-1. Safe-rename 성공

```
✅ ~/.claude/skills/<slug>/ 가 안전 정리되었습니다.

rename: ~/.claude/skills/<slug>/ → ~/.claude/skills/<slug>.removed-<timestamp>/

회복하려면: mv ~/.claude/skills/<slug>.removed-<timestamp> ~/.claude/skills/<slug>
완전 삭제하려면: rm -rf ~/.claude/skills/<slug>.removed-<timestamp>/

자동 발동이 즉시 차단됐는지 확인하려면 /reload-plugins 한 번 호출해주세요.
```

### 5-2. `--force` hard-delete 성공

```
✅ ~/.claude/skills/<slug>/ 가 영구 삭제되었습니다.

⚠️ 회복 불가. 다시 만들려면 /new-skill <slug> "..." 로 재생성해주세요.

자동 발동이 즉시 차단됐는지 확인하려면 /reload-plugins 한 번 호출해주세요.
```

### 5-3. Dry-run

```
ℹ️ /remove-skill <slug> 미리보기 (--dry-run, 변경 X)

기존 경로: ~/.claude/skills/<slug>/ (<크기> KB, 마지막 수정 <timestamp>)
변경 예정: ~/.claude/skills/<slug>.removed-<timestamp>/ (safe-rename)

--force 옵션 시 회복 불가 hard-delete.

옵션 빼고 재호출하면 실제 변경 적용.
```

### 5-4. Skill 부재 abort

```
⚠️ ~/.claude/skills/<slug>/ 가 존재하지 않습니다.

현재 글로벌 skill 디렉토리 목록:
- <slug-1>
- <slug-2>
- <slug-3>
- ...

slug 명을 다시 확인해주세요.
```

## 6. 금지

- **slug 인자 누락 시 abort** — `/new-skill` 과 달리 slug 는 필수 (정리 대상 명확성)
- **`--force` 자동 적용 금지** — 옵트인 플래그 명시한 경우만 hard-delete
- **다른 위치 (`<plugin>/skills/` / 프로젝트 `.claude/skills/`) 검증 금지** — 빌더 latency 보존. 다른 위치 정리는 사용자 catch 영역
- **rename 후 자동 발동 차단 보장 명시 X** — 보고 메시지에 `/reload-plugins` 호출 안내만 (사용자 catch 영역)
- **`.removed-<timestamp>` 디렉토리 추가 정리 자동 호출 금지** — 사용자가 직접 정리 (보고 메시지에 안내만)
