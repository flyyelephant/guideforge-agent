---
name: Workflow Support
description: Method guidance for grounded workflow support.
task_type: workflow_support
version: "1"
---

# Workflow Support Skill

## What This Skill Does

Helps turn a process question into an actionable workflow with phases, outputs, dependencies, and risks. The goal is to help the user progress a task, coordinate work, or review a process in a way that can actually be followed.

## Core Principle

Workflow support is not about listing concepts or slogans. It is about creating a sequence of work that someone can execute, review, and adapt.

## Workflow

### Step 1: Clarify the operational context
Clarify first when any of these are missing:
- The workflow topic
- Team context or execution environment
- Time horizon or delivery pressure
- Constraints or dependencies
- Whether the user wants quick advice, structured workflow guidance, or a formal workflow document

Without this context, workflow advice easily becomes generic and low value.

### Step 2: Ground the workflow
Use retrieved documentation to identify:
- Relevant UE concepts, process constraints, or supporting practices
- Terms and dependencies that shape the workflow
- Source material that can justify the proposed phases or checks

Use retrieval to improve the structure and realism of the workflow. Do not just restate retrieved snippets.

### Step 3: Organize by response mode
`direct_answer`
- Describe the core path briefly.
- Focus on the most useful next phases or checkpoints.
- Do not force file generation.
- Include concise references when grounded sources exist.

`structured_chat`
- Organize the workflow into clear phases or sections in chat.
- Include outputs, dependencies, or risks where useful.
- Keep it operational, not abstract.

`deliverable_file`
- Produce a formal workflow document using the workflow template.
- Make the file usable for review, planning, or handoff.
- Include references in the final deliverable.

### Step 4: Be explicit when evidence is limited
If grounding is strong:
- Use the retrieved material to shape phases, warnings, and dependencies.
- Keep the references visible.

If grounding is weak or missing:
- Say that the workflow is a draft or planning scaffold.
- Avoid acting as if the sequence is validated.
- Point out what needs further confirmation.

## Grounding and Sources

When sources are available:
- Use them to support phase logic, dependencies, and risk notes.
- Surface those sources in direct answers, structured chat, and deliverable files.
- Keep the reference section readable and traceable.

When sources are not available:
- Do not fake certainty.
- Reduce the strength of your claims.
- Make the lack of grounded support visible to the user.

## Anti-patterns

Do not:
- Produce empty process slogans with no execution value
- Write a workflow that has no phases, outputs, or ownership implications
- Pretend a weakly grounded workflow is validated guidance
- Turn structured_chat into a long, shapeless essay
- Force file output when the user only wants practical next-step guidance
- Treat this skill as an executor or planner implementation layer

## Quality Check

- [ ] The workflow can be followed as a sequence of work
- [ ] Phases or major steps are clear
- [ ] Outputs, dependencies, or risks are visible where needed
- [ ] Retrieved material is used to ground the advice
- [ ] Response mode is respected
- [ ] Weak grounding is stated explicitly when relevant
- [ ] The result helps move work forward instead of just describing process ideas
