---
name: risk-annotation
description: Use during /execute-plan whenever code is created or modified, and during verifying-spec when surveying existing code. Applies a 6-item self-checklist to detect side-effect/race/breaking/perf risks, then attaches standardized "# ⚠️ RISK(category): reason — by context" comments to risky lines and records the placement in change-history.
---

# Risk Annotation (Auto-Attach RISK Comments)

This skill is the source of truth for the four risk categories and the comment format used across the plugin. It is invoked from `executing-plans` (every code edit) and from `verifying-spec` (when surveying existing impacted code).

<HARD-GATE>
Before committing any code edit, you MUST run the 6-item self-checklist below on the changed lines AND the surrounding control flow. If any item triggers, attach a standardized RISK comment to the relevant line BEFORE the commit.
</HARD-GATE>

## Comment Format

```python
# ⚠️ RISK(<category>): <reason> — by <context>
```

Rules:
- `RISK(...)` portion is fixed (grep pattern: `RISK\(`)
- Categories are exactly one of four: `side-effect | race | breaking | perf`
- `<reason>` is free-form Korean (or English where the codebase is English)
- `<context>` is free-form. Default = the current feature slug (e.g., `by 공지사항-개발`). The user may override.
- Once attached, NEVER edit the comment to "update" the context after the feature is done. The comment is historical record.

## Examples

```python
# 1. 복잡 분기 + 외부 시스템
def process_order(order):
    if order.status == "pending":
        if order.amount > 100000:
            # ⚠️ RISK(side-effect): 큰 주문 처리 중 결제 게이트웨이 호출 — by 결제-v2
            charge_via_gateway(order)
        ...

# 2. 루프 내 쿼리
def get_summaries(user_ids):
    summaries = []
    for uid in user_ids:
        # ⚠️ RISK(perf): N+1 쿼리 가능 — by 알림-리스트-개선
        summaries.append(db.query("SELECT ... WHERE id=?", uid))
    return summaries

# 3. 응답 스키마 변경
def get_user(user_id):
    user = ...
    # ⚠️ RISK(breaking): 응답에 phone 필드 추가, 클라이언트 호환성 확인 — by 회원-정보-확장
    return {"id": user.id, "name": user.name, "phone": user.phone}
```

## 6-Item Self-Checklist

Run this for every code edit. Self-check (don't ask the user). If any trigger fires, attach the RISK comment.

| # | Trigger condition | Category |
|---|---|---|
| 1 | **Complex branching / order dependency** — adding/modifying code inside multi-branch (if/else, switch), early-return, or order-sensitive flow | `side-effect` |
| 2 | **External system change** — DB write, file I/O, network call, cache invalidation added or modified | `side-effect` |
| 3 | **Global / shared state mutation** — module-level variable, singleton, class variable, lock-free concurrent access | `race` |
| 4 | **Public function signature / response schema change** — argument/return/exception types modified, REST response field added/removed/renamed | `breaking` |
| 5 | **In-loop query or network call** — `for`/`while` body issuing DB queries or external HTTP, large collection traversal | `perf` |
| 6 | **Recursion / variable-depth traversal** — recursive function, tree/graph walk where input depth varies | `perf` |

Item 1 is the most frequent source of unintended side effects (the user's primary concern). Pay extra attention there.

## Process Flow

```dot
digraph risk_flow {
    "Code edit imminent\n(executing-plans context)" [shape=box];
    "Run 6-item self-checklist" [shape=box];
    "Any trigger?" [shape=diamond];
    "Determine category" [shape=box];
    "Compose RISK comment\n(category + reason + context)" [shape=box];
    "Insert comment above the risky line" [shape=box];
    "Set 위험 카테고리 in change-history entry" [shape=box];
    "No annotation" [shape=oval];
    "Done" [shape=doublecircle];

    "Code edit imminent\n(executing-plans context)" -> "Run 6-item self-checklist";
    "Run 6-item self-checklist" -> "Any trigger?";
    "Any trigger?" -> "Determine category" [label="yes"];
    "Any trigger?" -> "No annotation" [label="no"];
    "Determine category" -> "Compose RISK comment\n(category + reason + context)";
    "Compose RISK comment\n(category + reason + context)" -> "Insert comment above the risky line";
    "Insert comment above the risky line" -> "Set 위험 카테고리 in change-history entry";
    "Set 위험 카테고리 in change-history entry" -> "Done";
    "No annotation" -> "Done";
}
```

## Existing-Code Survey (verifying-spec context)

When `verifying-spec` performs §C code impact analysis, it may discover existing code (not just newly edited) that hits the 6-checklist. In that case:

1. Grep impacted callers / functions
2. For each, run the 6-checklist
3. If a trigger fires on existing code, **propose the annotation to the user first** (do NOT silently edit existing code)
4. On approval: attach the comment + write a `[코드-수정]` change-history entry

The "propose first" rule for existing-code annotations distinguishes survey from in-flight edits — survey is reactive, in-flight edits are proactive.

## Anti-Patterns

| Wrong | Right |
|---|---|
| "This change is small, probably no risk" | Always run the 6-checklist. 0/6 means no annotation, but the check happened. |
| Skipping ambiguous category | Default to `side-effect` if truly ambiguous. Refine over time. |
| Adding a doc-link tail (`[<slug>-implementation-plan.md#CH-...]`) to the comment | The user works solo on those docs. Comment stays self-contained. Context tag only. |
| Editing existing risk comments to "update" context | Historical record — don't edit. Add a new comment if needed. |

## Red Flags

| Thought | Reality |
|---|---|
| "Annotations clutter the code" | Grep `RISK\(` aggregates them when you need them. Worth the noise. |
| "I'll batch annotations after committing" | After commit, before-snapshot is gone. Annotate before commit. |
| "Item 1 (complex branching) is too vague" | If you're inside any if/else/switch/early-return when adding code — fire item 1. |

## Acceptance

After every code edit during /execute-plan:
1. The 6-checklist was run (silently, no user prompt)
2. If any trigger fired, the matching `# ⚠️ RISK(...)` comment was inserted above the relevant line
3. The change-history `[코드-수정]` entry has its `위험 카테고리` field set (or omitted if 0/6 triggered)
4. `grep -rn "RISK(" <changed file>` finds the new annotations

## Related Skills

- `executing-plans` — invokes this on every code edit
- `verifying-spec` — invokes this during §C impact survey
- `change-history` — uses the chosen category in the `위험 카테고리` field of [코드-수정] entries
