<div align="center">

# 🔒 intent-locked-workflow

### 기획 의도를 고정하고, 그 위에서만 코드가 자란다.

하나의 아이디어를 **바로 코드로 쓰지 않습니다.**
`기획 → 설계 → 계획 → 실행` 4단계 게이트를 통과시키며,
각 단계를 **당신이 직접 확인하고** 넘어가는 AI 워크플로.

<br/>

### 빨리 가는 게 아니라, 제대로 간다.

<br/>

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-1.3.0-7c3aed?style=flat-square&labelColor=0d1117">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-Plugin-a78bfa?style=flat-square&labelColor=0d1117">
  <img alt="Skills" src="https://img.shields.io/badge/skills-27-06b6d4?style=flat-square&labelColor=0d1117">
  <img alt="Upstream" src="https://img.shields.io/badge/superpowers-5.0.7%20계승-f97316?style=flat-square&labelColor=0d1117">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square&labelColor=0d1117">
  <img alt="Zero deps" src="https://img.shields.io/badge/dependencies-zero-22c55e?style=flat-square&labelColor=0d1117">
</p>

<sub>upstream <a href="https://github.com/obra/superpowers">superpowers</a> 5.0.7 (MIT, Jesse Vincent) 의 프로덕션 안전성 확장</sub>

</div>

<br/>

## 왜 만들었는가

AI는 코드를 너무 빨리 짭니다. 문제는 속도가 아니라 **방향**입니다 —
잘못된 이해 위에서 빠르게 달리면, 빠르게 멀어집니다.

그래서 이 도구는 맨 먼저 **기획 의도를 고정(lock)** 합니다.
한 번 잠근 의도는 아래 단계에서 함부로 바뀌지 않고, 설계·계획·코드는 **그 의도를 향해서만** 자랍니다.
매 단계 끝에는 게이트가 있고, 게이트는 **사람이 확인해야** 열립니다.

> 빨리 가는 게 아니라, 제대로 간다.

<br/>

## 이것은 코드 생성기가 아닙니다

자동완성 도구가 아닙니다. AI를 더 빨리 달리게 하는 물건이 아닙니다.
**AI가 제멋대로 못 가게 붙잡는 레일**이자, **기획 의도를 잠그는 자물쇠**입니다.

- 각 단계의 끝에는 **게이트**가 있고, 게이트는 **당신만** 엽니다.
- 자잘한 건 알아서, **위험한 결정만** 물어봅니다 — 자리에 없어도 OS 알람으로 catch.
- 위험한 코드엔 `# RISK` 주석, 문서엔 "왜 · 언제 · 무엇이" 변경이력이 자동으로 쌓입니다.

<br/>

## 다른 방식과 뭐가 다른가

| 방식 | 흐름 | 무슨 일이 생기나 |
|---|---|---|
| 그냥 시키기 | 요청 → 코드 | 이해가 틀려도 **끝까지** 달림 |
| 🔒 **intent-locked** | 기획 → 설계 → 계획 → 실행 *(게이트 4개)* | 틀리면 **그 단계에서** 잡히고, **의도는 안 흔들림** |

<br/>

## 4단계, 그리고 게이트

각 단계는 문서 하나를 남기고, 끝에서 게이트가 열립니다.

| 단계 | 스킬 | 산출물 | 게이트에서 확인 |
|---|---|---|---|
| **① 기획** | `/brainstorming` | 요구사항.md | 의도가 맞나? *(여기서 잠금)* |
| **② 설계** | `/tech-design` | 기술설계.md | 의도대로 설계됐나? |
| **③ 계획** | `/writing-plans` | 구현계획.md | 계획이 의도를 벗어나지 않나? |
| **④ 실행** | `/executing-plans` | 코드 + 변경이력 + 위험주석 | 계획 그대로 실행됐나? |

나중에 요구사항이 바뀌면? **아래 3개 문서가 자동으로 따라옵니다.** 의도가 성역이라, 위가 바뀌면 아래도 정합을 맞춰요.

산출물은 **세 얼굴**로 남습니다 — AI가 읽는 `.md`, 사람이 보는 `.html` 사본, 코드에 붙는 `# RISK` 주석.

<br/>

## 지금 바로 시작

```
/plugin marketplace add deokjinlog/intent-locked-workflow
/plugin install intent-locked-workflow@intent-locked-workflow
```

설치하고 세션 한 번 재시작한 뒤:

```
/brainstorming 사용자 잔액 출금 기능
```

→ 첫 게이트가 열립니다. 답하면 다음 단계로.

<br/>

## 안에 뭐가 들었나 — 스킬 27

| 그룹 | 스킬 |
|---|---|
| **워크플로 코어 (4)** | brainstorming · tech-design · writing-plans · executing-plans |
| **자동 흐름 (4)** | auto-brainstorming · auto-tech-design · auto-writing-plans · auto-executing-plans |
| **upstream 원본 (3)** | og-brainstorming · og-writing-plans · og-executing-plans |
| **문서·시각화 (3)** | generating-html · code-pretty · change-history |
| **검증·거버넌스 (4)** | verifying-spec · verification-before-completion · change-propagation · risk-annotation |
| **서브에이전트 (2)** | dj-superkit-sub-driven · subagent-driven-development |
| **테스트·디버깅 (2)** | test-driven-development · systematic-debugging |
| **리뷰·마무리 (3)** | requesting-code-review · receiving-code-review · finishing-a-development-branch |
| **API 테스트 (1)** | api-auto-testing |
| **메타 (1)** | using-superpowers |

> 명령어도 있어요 — `/audit-risk`(배포 전 보안·거버넌스 감사), `/fast-tasks`(잡일 묶어 처리), `/sync-html`, 빌더 3종(`/list-skills` · `/new-skill` · `/remove-skill`).

<br/>

## 파일 구조

```
intent-locked-workflow/
├── skills/          # 27개 스킬 — 워크플로 4단계 + 자동 / 검증 / 리뷰 …
├── commands/        # 슬래시 명령 — 감사 · 잡일 · 빌더
├── hooks/           # 세션 훅 — 스킬 자동 발동
├── scripts/         # 결정론적 헬퍼 — 게이트 · 변경이력 · DAG
└── .claude-plugin/  # 플러그인 매니페스트
```

<br/>

## superpowers 계승

이 저장소는 [superpowers](https://github.com/obra/superpowers) v5.0.7 (MIT, Jesse Vincent) 위에 **프로덕션 안전성**(단계 게이트 · 변경이력 · 위험 주석 · 서브에이전트 wave-parallel · `.html` 사본 · 보안 감사)을 얹은 파생 프로젝트예요. 원본 흐름 그대로가 필요하면 `/og-brainstorm` · `/og-write-plan` · `/og-execute-plan` 로 쓸 수 있어요.

<br/>

## 라이선스

**MIT** (upstream superpowers 와 동일) · 버그 / 제안: [GitHub Issues](https://github.com/deokjinlog/intent-locked-workflow/issues)

<br/>

---

<div align="center">
<sub><b>빨리 가는 게 아니라, 제대로 간다.</b></sub>
</div>
