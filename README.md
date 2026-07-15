<p align="center">
  <img src="https://raw.githubusercontent.com/deokjinlog/intent-locked-workflow/main/assets/banner.svg" alt="intent-locked-workflow — 기획 의도를 고정하고, 그 위에서만 코드가 자란다" width="100%">
</p>

<div align="center">

### 기획 의도를 고정하고, 그 위에서만 코드가 자란다

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-1.5.0-7c3aed?style=flat-square&labelColor=0d1117">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-Plugin-a78bfa?style=flat-square&labelColor=0d1117">
  <img alt="Skills" src="https://img.shields.io/badge/skills-27-06b6d4?style=flat-square&labelColor=0d1117">
  <img alt="Upstream" src="https://img.shields.io/badge/superpowers-5.0.7%20계승-f97316?style=flat-square&labelColor=0d1117">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square&labelColor=0d1117">
</p>

<sub>upstream <a href="https://github.com/obra/superpowers">superpowers</a> 5.0.7 (MIT, Jesse Vincent) 의 프로덕션 안전성 확장</sub>

<br/>
<br/>

<sub>
  <a href="#왜-만들었는가">왜</a>
  &nbsp;·&nbsp;
  <a href="#다른-방식과-뭐가-다른가">뭐가-다른가</a>
  &nbsp;·&nbsp;
  <a href="#4단계-그리고-게이트">4단계</a>
  &nbsp;·&nbsp;
  <a href="docs/세-문서-읽는-법.md">세 문서 읽는 법</a>
  &nbsp;·&nbsp;
  <a href="#지금-바로-시작">시작하기</a>
  &nbsp;·&nbsp;
  <a href="#스킬-27개">스킬</a>
</sub>

</div>

<br/>

> ## 코드보다 먼저, 의도를 맞춘다.
>
> 하나의 아이디어를 **바로 코드로 쓰지 않습니다.**
> `기획 → 설계 → 계획 → 실행` 네 단계를 지나며,
> 각 단계 끝의 게이트를 **사람이 직접 확인하고** 넘어가는 AI 워크플로입니다.

---

## 왜 만들었는가

AI는 코드를 너무 빨리 짭니다. 문제는 속도가 아니라 **방향**이에요.
잘못 이해한 채로 빠르게 달리면, 빠르게 멀어집니다.

더 근본적인 문제는 **소통**입니다.
기획자의 머릿속 의도, 개발자가 이해한 것, AI가 실제로 만든 것 —
이 셋이 조용히 어긋난 채 코드가 쌓이면, 다 만들고 나서야 "이게 아닌데"가 나옵니다.

그래서 코드보다 먼저 **문서**를 만듭니다.
기획 의도를 잠그고, 요구사항 · 설계 · 계획 문서로 눈에 보이게 남겨요.
**같은 문서를 보며 "이게 맞다"를 확인한 다음**에야 코드가 시작됩니다.

---

## 어떻게 붙잡나

- **게이트** — 각 단계 끝에서 열리고, **사람만** 엽니다.
- **알람** — 자잘한 건 알아서, 위험한 결정만 물어봐요. 자리에 없어도 OS 알람이 잡아줍니다.
- **`.html` 사본** — 산출 문서를 사람이 읽는 사본으로도 남겨, 코드를 몰라도 게이트에서 검토하게.
- **`# RISK` · 변경이력** — 위험한 코드엔 주석, 문서엔 "왜 · 언제 · 무엇이" 가 자동으로 쌓입니다.

---

## 다른 방식과 뭐가 다른가

| | 그냥 AI에게 시키기 | intent-locked-workflow |
|---|---|---|
| **흐름** | 요청 → 바로 코드 | 기획 → 설계 → 계획 → 실행 *(게이트 4개)* |
| **이해가 틀리면** | 끝까지 달린 뒤 발견 | **그 단계에서** 잡힘 |
| **기획 의도** | 코드 짜다 슬금슬금 바뀜 | **잠겨서** 안 흔들림 |
| **기획자와 소통** | 다 만든 화면을 보고서야 | 문서 · `.html` 사본으로 **단계마다** |
| **바뀔 때** | 여기저기 수동으로 고침 | 위가 바뀌면 아래 문서가 **자동으로 따라옴** |

---

## 4단계, 그리고 게이트

각 단계는 문서 하나를 남기고, 끝에서 게이트가 열립니다.
문서는 그대로 **기획자와의 소통 자료**가 됩니다.

| 단계 | 스킬 | 산출물 | 게이트에서 확인하는 것 |
|---|---|---|---|
| **① 기획** | `/brainstorming` | 요구사항.md | 의도가 맞나? *(여기서 잠금)* |
| **② 설계** | `/tech-design` | 기술설계.md | 의도대로 설계됐나? |
| **③ 계획** | `/writing-plans` | 구현계획.md | 계획이 의도를 벗어나지 않나? |
| **④ 실행** | `/executing-plans` | 코드 + 변경이력 + 위험주석 | 계획 그대로 실행됐나? |

**②설계와 ③계획이 헷갈린다면** — 설계는 *"뭘 만들 건가"*(구조 · 데이터 · 결정), 계획은 *"어떤 순서로 지을 건가"*(task 분해 · 순서 · 검증)입니다. **도면과 공정표**의 차이예요.

④만 문서가 없는 게 아닙니다. 규칙은 **"고친 문서에 기록을 남긴다"** 인데, ④는 문서가 아니라 **코드**를 고치므로 자기가 소비한 계획서 하단에 남깁니다.

나중에 요구사항이 바뀌면 **아래 세 문서가 자동으로 따라옵니다.** 위가 바뀌면 아래도 정합을 맞춰요.

> 📖 **[세 문서 읽는 법](docs/세-문서-읽는-법.md)** — `FR`·`AC` 가 뭔지, 변경이력이 왜 *"이전 버전과의 diff"* 가 아닌지, 왜 계획서만 길어지는지. 이 워크플로를 처음 쓸 때 헷갈리는 것들을 모아 답합니다.

---

## 실제로 뭐가 나오나

예시를 지어낼 필요가 없습니다 — **이 도구는 자기 자신을 이 워크플로로 개발했거든요.**
[`docs/features/`](docs/features/) 에 **기능 24개의 실제 산출물**이 그대로 있습니다. 그중 하나:

#### [v2.5 — `--no-ask` 플래그](docs/features/2026-05-24-v2.5-no-ask-flag/)

| 단계 | 산출물 | 이게 무슨 문서인가 |
|---|---|---|
| **① 기획** | [요구사항](docs/features/2026-05-24-v2.5-no-ask-flag/v2.5-no-ask-flag-requirements.md) `136줄` · [`.html` 사본](docs/features/2026-05-24-v2.5-no-ask-flag/v2.5-no-ask-flag-requirements.html) | **계약** — 뭘 하고, 뭘 **안** 하나 |
| **② 설계** | [개발방향](docs/features/2026-05-24-v2.5-no-ask-flag/v2.5-no-ask-flag-tech-design.md) `292줄` | **도면** — 왜 이 방법인가 |
| **③ 계획** | [구현계획서](docs/features/2026-05-24-v2.5-no-ask-flag/v2.5-no-ask-flag-implementation-plan.md) `425줄` | **공정표 + 부품** — 코드·명령어·기대출력이 다 박힘 |
| **④ 실행** | ③ 하단 `## 변경이력` | 코드는 소스 트리로, 흔적은 여기로 |

**`.html` 사본**이 "같은 문서, 두 얼굴"입니다 — AI 는 `.md` 를, 사람은 `.html` 을 봅니다. 내용은 1:1이고, 기획자가 코드를 몰라도 게이트에서 검토하라고 있는 장치예요. *(내려받아 더블클릭하면 열립니다 — 외부 의존 0)*

**④ 가 남긴 것** — 꾸며낸 예시가 아니라 그 계획서에 실제로 박혀 있는 줄입니다 *(길어서 줄임)*:

> `[코드-수정]` **`CH-20260524-004`** `| 2026-05-24 | v2.5.0 Wave 0~4 batch |`
> Wave 0 (**`fc3f7cf`**): CLAUDE.md 결합 메모 · Wave 1 (**`521ef86`**): PRD 4 skill 분기 · Wave 2 (**`d51035e`**): reference 4 skill · Wave 3 (**`8e15be5`**): commands 8 본문 · Wave 4 (**`b846957`**): 6 manifest 통일 2.4.2 → 2.5.0

**커밋 5개가 Wave 5개에 그대로 매핑됩니다.** 데모용으로 만든 게 아니라, 이 저장소가 실제로 그렇게 만들어졌어요.

> 📖 세 문서가 왜 저런 성격이고 **③만 왜 긴지**는 → **[세 문서 읽는 법](docs/세-문서-읽는-법.md)**

---

## 지금 바로 시작

Claude Code 안에서:

```
/plugin marketplace add deokjinlog/intent-locked-workflow
/plugin install intent-locked-workflow@intent-locked-workflow
```

설치하고 세션을 한 번 재시작한 뒤:

```
/brainstorming 사용자 잔액 출금 기능
```

첫 게이트가 열립니다. 답하면 다음 단계로 넘어가요.

<details>
<summary><b>이미 설치했다면 — 업데이트</b></summary>

<br/>

**마켓플레이스를 먼저 당기고, 그 다음 플러그인을 올립니다. 둘 다 해야 해요.**
마켓플레이스가 옛 버전에 묶여 있으면 플러그인도 안 올라갑니다.

```bash
claude plugin marketplace update intent-locked-workflow
claude plugin update intent-locked-workflow@intent-locked-workflow
```

**적용은 세션을 재시작해야 됩니다.** 안 하면 옛 버전이 계속 로드돼서, 슬래시 메뉴에 예전 스킬 이름이 그대로 보여요. 지금 뭐가 깔려 있는지는 `claude plugin list` 로 확인합니다.

</details>

---

## 스킬 27개

| 그룹 | 스킬 |
|---|---|
| **워크플로 코어 (4)** | brainstorming · tech-design · writing-plans · executing-plans |
| **자동 흐름 (4)** | auto-brainstorming · auto-tech-design · auto-writing-plans · auto-executing-plans |
| **upstream 원본 (3)** | og-brainstorming · og-writing-plans · og-executing-plans |
| **문서 · 시각화 (3)** | generating-html · code-pretty · change-history |
| **검증 · 거버넌스 (4)** | verifying-spec · verification-before-completion · change-propagation · risk-annotation |
| **서브에이전트 (2)** | subagent-driven · subagent-driven-development |
| **테스트 · 디버깅 (2)** | test-driven-development · systematic-debugging |
| **리뷰 · 마무리 (3)** | requesting-code-review · receiving-code-review · finishing-a-development-branch |
| **API 테스트 (1)** | api-auto-testing |
| **메타 (1)** | using-superpowers |

명령어도 있어요 — `/audit-risk`(배포 전 보안 감사), `/fast-tasks`(잡일 묶어 처리), `/sync-html`, 빌더 3종(`/list-skills` · `/new-skill` · `/remove-skill`).

---

## superpowers 계승

[superpowers](https://github.com/obra/superpowers) 5.0.7 (MIT, Jesse Vincent) 위에 프로덕션 안전성을 얹은 파생 프로젝트입니다.
원본 흐름 그대로가 필요하면 `/og-brainstorm` · `/og-write-plan` · `/og-execute-plan` 로 쓸 수 있어요.

---

<div align="center">
<br/>
<sub><b>코드보다 먼저, 의도를 맞춘다.</b></sub>
</div>
