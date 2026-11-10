# Agents Constrain

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---
name: anti-slop-design
description: >-
  Design or review interface visual identity and polish, avoiding generic AI-template styling. Use
  for visual design, rendered UI audits, or requests for a distinctive, less generic interface.
---

# Anti-slop design

Make the interface specific to its product, content, and audience. Removing familiar visual tells is
not a design direction, and novelty alone is not an improvement.

## Scope and design intent

- User decisions and repository constraints take precedence over stylistic defaults. Preserve
  existing designs, frameworks, accessible primitives, and explicit no-visual-change contracts. Do
  not turn a small edit into a visual overhaul, dependency migration, or design-system rewrite.
- Ground visual choices in the affected product, real content, assets, and existing tokens. Consult
  design contracts, theme docs, or registry configuration when the change touches their decisions;
  resolve drift only within scope and report it otherwise.
- For marketing, editorial, and brand surfaces, a coherent palette, type voice, focal artifact,
  atmosphere, and composition can carry identity. Use only what the brief needs.
- For product, admin, and dense workflow UI, prioritize information architecture, state, data,
  navigation, and useful interactions. Do not force heroes, scenery, giant type, or decorative
  artifacts into task surfaces. Familiar controls and consistent repeated structures are valid.
- Treat inspiration as design-language direction, not content or layout to copy. This does not
  override a user's request to implement a supplied design faithfully.

## References on demand

Load only the reference sections needed for the current decision; no reference is a prerequisite for
every edit.

- [Anti-pattern catalog](references/anti-patterns.md): specific visual tells and corrections when
  designing or reviewing affected typography, color, layout, content, or motion. A requested full
  anti-slop audit covers the catalog across its declared surfaces, not the entire product.
- [Premium patterns and exceptions](references/premium-patterns.md): when choosing a new visual
  direction, judging a context-dependent exception, changing a design contract, or evaluating a
  component tool or registry. The signature formula and named tools are options, not requirements.
- [Implementation recipes and verification](references/implementation-recipes.md): when affected
  work involves stateful controls, data displays, media, responsive or theme behavior, visual
  effects, motion, or rendered verification. Adapt recipes to the existing platform.
- [Design workflow](references/WORKFLOW.md): for substantial design work or an audit, including work
  depth, real and missing material, task-led composition, preserving behavior, representative units,
  and review.

## Implementation boundaries

- Reuse semantic tokens and accessible components. Consolidate repeated overrides at their shared
  source only when that change is in scope. Preserve parallel token and behavior contracts across
  supported themes.
- Named tools are examples, not reasons to install dependencies. Keep the working primitive base,
  framework, styling system, and registry settings. Do not inject global Tailwind into a mature
  non-Tailwind project for one block.
- Use supplied or verified marks and data. Never fabricate customer proof, testimonials, metrics, or
  third-party identities. Create a first-party identity when the brief requires one. Label prototype
  data as sample and represent the actual product truthfully.
- Preserve authorization boundaries: sensitive content and metadata must not be delivered merely to
  hide them on the client. Visual changes must retain accessible semantics, focus behavior,
  contrast, and meaningful state and recovery guidance.
- Rendered content must remain visible if animation never starts or finishes. Preserve static or
  server-rendered fallbacks where available and support reduced motion.
- Implement in-scope controls; static mockup elements must not masquerade as working controls.

## Completion and verification

For rendered changes, inspect the actual affected interface at representative supported viewports,
themes, and states. Exercise changed interactions with applicable pointer, keyboard, or touch input;
include affected uses of shared primitives. Check relevant layout, contrast, focus, content
visibility, motion fallbacks, and runtime errors. Use existing platform tooling and screenshots
where available; do not add dependencies or tests solely to satisfy this skill.

Match verification to the change: a local spacing fix needs rendered geometry checks, not a full
interaction audit. A full UI audit covers every declared surface and its applicable criteria. For
non-rendered changes, use checks of the affected contract. If the interface cannot run, inspect
available renders and code and state what remains unverified.

Compare the result against relevant anti-patterns and their exceptions. Complete authorized in-scope
fixes and recheck affected behavior; revisit cleared areas only for new evidence. Reviews remain
read-only unless fixes are requested. Stop when the requested scope is covered, not when every
optional premium technique has been added.

Distinguish correctness failures, contextual preferences, and optional craft refinements. An
aesthetic convention is not a correctness failure by itself. Keep justified exceptions and report
checks as passed, failed, or not run with evidence that supports the claim.

Report substantive changes or findings, actual rendered checks and interactions tested, and any
remaining limitations. Do not claim checks passed when they did not run.

## Sources

Includes guidance adapted from
[Hallmark](https://github.com/Nutlope/hallmark/tree/6033bab2a8051b5454552d2e8e6cb8f27c483a42). Its
[MIT notice](LICENSES/HALLMARK.txt) is retained.

