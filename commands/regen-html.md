# /regen-html

`<slug>` 인자 optional. 누락 시 `scripts/auto_flow.find_latest_slug(Path("docs/features"))` 호출 → 가장 최근 폴더 자동 선택.

이 슬래시 명령은 **`docs-pretty` 의 `.html` 생성 subagent 만 명시 호출**합니다. `.md` 변경 시 자동 발동 X — 사용자 명시 호출 또는 `change-propagation` 마지막 단계 자동 호출 (v2.2.1+) 만 발동.

## 동작

1. 인자 `<slug>` 확인 (또는 latest slug 추론)
2. `docs/features/<slug>/<slug>-{requirements,tech-design,implementation-plan}.md` 중 존재하는 모든 `.md` 검출
3. 각 `.md` 에 대해 Subagent dispatch:
   - `subagent_type`: `general-purpose`
   - `model`: `sonnet`
   - `run_in_background`: `true` (fire-and-forget)
   - `prompt`: `skills/docs-pretty/html-companion-prompt.md` (`<ABSOLUTE_MD_PATH>` + `<ABSOLUTE_HTML_PATH>` 인자 주입)
4. 이전 subagent 살아있으면 cancel + 새 dispatch (디바운스 3초)
5. 완료 notify 받으면 `.js-super/html-regen.log` silent log
6. 메인 즉시 다음 turn — 결과 대기 X

## 사용 시점

- `change-propagation` 마지막 단계에서 자동 발동 (v2.2.1+)
- 사용자가 `.md` 직접 편집 (오타 fix 등) 후 `.html` 갱신 원할 때 명시 호출
- `.html` 부재 / stale 인지 시 사용자 명시 호출

## 영구 생략

- AskUserQuestion 게이트 — fire-and-forget 의도상 사용자 입력 wait X
- `.md` 가공 (v2.2.0 의 A 책임 제거)
- 결과 dispatch 노출 — silent log 만

## 다음 단계

자동 chain 없음. 1회성 액션.
