---
id: decompose
category: planning
description: Break goals into actionable work under uncertainty, surface assumptions, and route tasks
triggers:
  - "plan the project"
  - "break down"
  - "decompose"
  - "write a paper"
  - "build X"
  - "multi-month"
  - "epic"
bases: [base-task-tracking, base-handover]
---

# Decompose

Break goals into actionable work under genuine uncertainty.

## Routing Signals

- Multi-month projects (dissertations, books, grants)
- "What does X actually require?"
- Vague deliverable, unclear dependencies
- Path forward is unknown

## NOT This Workflow

- Known tasks, clear steps → [[design]]
- Pure information request → [[simple-question]]

## Unique Steps

1. Articulate the goal clearly
2. Surface assumptions (what must be true?)
3. Find affordable probes (cheapest way to validate?)
4. Create coarse components (don't over-decompose)
5. Ensure at least one task is actionable NOW
6. Route task assignments:
   - **Mechanical work** (create, implement, fix, update, refactor) → `assignee: polecat`
   - **Judgment-call tasks** (review, evaluate, decide, design choices) → `assignee: null` (unassigned backlog)
   - **Explicit override** → only assign to `nic` when user explicitly requests it

## Key Principle

We decompose to **discover what we don't know**, not because we know what to do.

## Pattern References

For detailed guidance on decomposition patterns, see the [[planning]] skill:

- [[spike-patterns]] - When to investigate vs commit; spike completion checklist
- [[dependency-types]] - Hard vs soft dependency decisions; human handoff patterns
- [[knowledge-flow]] - Propagating findings between siblings; confirmed vs TBD tables

## Quick Reference

### Spike vs Placeholder

| Situation                              | Use Spike            | Use Placeholder   |
| -------------------------------------- | -------------------- | ----------------- |
| "We don't know if X is possible"       | Investigate first    |                   |
| "We know X is needed, details TBD"     |                      | Capture intent    |
| "Implementation approach is unclear"   | Prototype/probe      |                   |

### Dependency Selection

**Ask: "What happens if the dependency never completes?"**

- **Impossible or wrong output** → `depends_on` (hard)
- **Still valid but less informed** → `soft_depends_on` (soft)

## Project Structure

Tasks cluster in visualizations based on their parent chain reaching a canonical project file.

**Checklist:**

1. **Project file exists**: `$ACA_DATA/{project}/{project}.md` with `type: project`
2. **Root goals link to project**: Goals have `parent: {project-id}`
3. **Tasks link to goals**: Every task has `parent:` pointing up the chain
4. **Project field matches**: `project: {slug}` matches the project file's `id:`

<<<<<<< HEAD
=======
**Structure:**
```
{project}.md (type: project)
├── {goal}.md (type: goal, parent: project-id)
│   └── {task}.md (type: task, parent: goal-id, project: slug)
```

**Diagnosis**: If tasks with `project: X` don't cluster, check whether `X.md` exists with `type: project`. Missing project files are a common cause of orphaned-looking tasks.

## Priority and Weight Semantics

When assigning priority during decomposition, understand how priority and weight interact:

### Priority (P0-P4): Creator's Urgency Assessment

| Level | Meaning | Use When |
|-------|---------|----------|
| **P0** | Critical blocker | Production down, data loss risk |
| **P1** | Needed this week | Deliverable with an imminent deadline |
| **P2** | Normal (default) | Standard work, no unusual urgency |
| **P3** | Low priority | Nice to have, do when bandwidth allows |
| **P4** | Someday/maybe | Backlog, aspirational |

**Rule: Default to P2. Only use P1 for deliverables needed this week.**

### Weight (computed): Systemic Importance

`downstream_weight` is computed automatically by the fast-indexer via BFS through `blocks` and `soft_blocks` edges. It answers: "What does completing this task unblock?"

- A task blocking 5 other tasks has higher weight than an isolated task
- Tasks on the critical path to goals with due dates get extra weight via `stakeholder_exposure`
- Weight is not set by humans — it emerges from the graph structure

### Sort Order

Ready tasks are sorted by: **priority ASC, downstream_weight DESC, order, title**

This means:
- Among P2 tasks, the one that unblocks the most work comes first
- A P2 task with high weight sorts after all P1 tasks but before other P2 tasks
- Priority is the primary sort axis; weight breaks ties within the same priority level

### Common Mistakes

- **Priority inflation**: Setting P1 on everything because it "feels important." If >25% of tasks are P1, priority has lost its meaning.
- **Ignoring weight**: Manually reordering tasks instead of letting the graph determine systemic importance.
- **Confusing urgency with importance**: P1 = "needed this week" (urgency), high weight = "unblocks many things" (importance). They are orthogonal.

>>>>>>> 4912fc9 (feat: task graph governance reform — hierarchy warnings, weight surfacing, audit script)
## Anti-Patterns

- Expanding everything at once (premature detail)
- Blocking on ambiguity (create placeholder tasks instead)
- Hidden assumptions (planning as if everything is known)
- **Isolated spikes**: Completing investigation without propagating findings to parent
- **Missing sequencing**: Implementation tasks that don't depend_on their investigation spikes
- **Missing project anchors**: Creating goals/tasks with `project: X` but no `X.md` project file exists
- **Reflexive task creation**: Creating tasks without knowing the action path
- **Prose instead of structure**: Writing relationships as prose when they should be graph edges
