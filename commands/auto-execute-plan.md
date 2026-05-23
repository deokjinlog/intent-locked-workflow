---
description: 자동 흐름의 4단계 진입 (마지막) — implementation-plan.md 가 있는 상태에서 보조 에이전트 강제로 여러 작업 동시 진행 (승인 게이트 자동 통과) + 실패 격리 + 마무리 자동.
---

# /auto-execute-plan

`<slug>` 인자는 선택입니다. 누락 시 가장 최근 implementation-plan.md 를 자동으로 선택합니다. 이 슬래시는 `auto-executing-plans` skill 을 호출합니다.

동작은 보조 에이전트 강제로 `js-super-sub-driven` 호출 (승인 게이트 자동 통과 명시 적용). 실패한 task 가 있어도 격리해서 나머지 task 는 계속 진행하고, 마지막에 결과를 모아서 마무리합니다.

종료 시점 메시지에 commit 개수 / RISK 카운트 / 멈춘 task 목록이 노출됩니다.
