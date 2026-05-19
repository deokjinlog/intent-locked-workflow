# /sync-html

`<slug>` 인자 optional. 누락 시 `scripts/auto_flow.find_latest_slug(Path("docs/features"))` 호출 → 가장 최근 폴더 자동 선택. `--rebuild` 플래그 optional.

이 슬래시 명령은 **feature 디렉토리의 `.md` 내용을 `.html` 시각화 사본으로 sync** 합니다. 기존 `.html` 의 디자인 (레이아웃·색·여백) 은 보존 + 내용만 갱신. `--rebuild` 명시 시만 디자인 처음부터 재생성.

## 동작

1. 인자 `<slug>` 확인 (또는 latest slug 추론) + `--rebuild` 플래그 검출
2. `docs/features/<slug>/<slug>-{requirements,tech-design,implementation-plan}.md` 중 존재하는 모든 `.md` 검출
3. 각 `.md` 에 대해 같은 위치의 `.html` 존재 여부 확인 후 3-way 분기:

| 케이스 | 동작 |
|---|---|
| `.html` 없음 | 디자인 + 생성 (generating-html 동등 경로 — design 자유 결정) |
| `.html` 존재 | 기존 `.html` 을 subagent 에 같이 입력 → 디자인·레이아웃·색·여백 보존 + 내용만 sync |
| `--rebuild` 플래그 | `.html` 존재 무시 → 디자인 처음부터 재생성 (기존 디자인 폐기) |

4. Subagent dispatch (각 `.md` 별):
   - `subagent_type`: `general-purpose`
   - `model`: `sonnet`
   - `run_in_background`: `true` (fire-and-forget)
   - `prompt`: 분기에 따라 동등 + 내용 sync 룰 / 처음부터 디자인 룰
5. 메인 즉시 다음 turn — 결과 대기 X

## `--rebuild` 경고

> `--rebuild` 사용 시 **기존 디자인이 폐기됩니다**. `.html` 은 `.gitignore` 대상이라 **git revert 로 복원 불가**. 디자인 다시 만들 의도일 때만 사용하세요.

## 사용 시점

- `change-propagation` 후 사용자 명시 호출 — `.md` 사후 cascade 반영을 `.html` 에 sync
- `.html` 부재 / stale 인지 시 사용자 명시 호출
- 디자인 자체 변경 원할 때 `--rebuild` 명시 호출

## 영구 생략

- AskUserQuestion 게이트 — fire-and-forget 의도상 사용자 입력 wait X
- `.md` 가공 (`.md` 는 source-of-truth, 손대지 않음)
- 결과 dispatch 노출 — silent

## 다음 단계

자동 chain 없음. 1회성 액션.
