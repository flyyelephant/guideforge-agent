---
name: Proposal Generation
description: Method guidance for grounded proposal generation.
task_type: proposal_generation
version: "1"
---

# Proposal Generation Skill

## What This Skill Does

Helps transform a request into a structured proposal with background, target scenario, recommended direction, risks, and next steps. The goal is to help the user make or evaluate a decision, not just read a knowledge summary.

## Core Principle

A proposal is not a documentation dump. It should reduce ambiguity, frame tradeoffs, and recommend a direction that the user can actually act on.

## Workflow

### Step 1: Clarify the proposal boundary
Clarify first when any of these are unclear:
- What is being proposed
- Who the proposal is for
- What constraints matter
- What success looks like
- Whether the user wants a quick recommendation, structured analysis, or a formal proposal document

A proposal without scope is usually just a vague essay. Avoid that.

### Step 2: Ground the proposal
Use retrieved documentation to understand:
- Relevant UE capabilities and limitations
- Constraints that affect feasibility
- Concepts or subsystems that should shape the recommendation
- Sources that justify the proposed direction

Use retrieved material to support the proposal's reasoning. Do not merely attach citations after the fact.

### Step 3: Organize by response mode
`direct_answer`
- Provide the clearest recommendation and why it is the safest or most practical path.
- Keep it concise.
- Do not force document output.
- Include a compact source-aware references block when grounded evidence exists.

`structured_chat`
- Present a structured recommendation in chat.
- Typical sections can include goal, recommended direction, key tradeoffs, risks, and references.
- This should feel like decision support, not like raw research notes.

`deliverable_file`
- Produce a formal proposal deliverable using the proposal template.
- Make the structure readable for review and follow-up.
- Keep references visible in the final file.

### Step 4: Handle uncertainty explicitly
If grounding is strong:
- Make clear, evidence-backed recommendations.
- Tie major claims to the most relevant retrieved material.

If grounding is weak or missing:
- Avoid pretending the proposal is validated.
- Frame the output as a draft recommendation or planning scaffold.
- State what still needs confirmation.

## Grounding and Sources

When sources are available:
- Use them to support feasibility, constraints, and rationale.
- Preserve source visibility in chat and file outputs.
- Prefer fewer relevant sources over noisy lists.

When sources are missing or weak:
- Say so clearly.
- Avoid overconfident solution language.
- Keep recommendations proportional to the available evidence.

## Anti-patterns

Do not:
- Turn the proposal into a knowledge notebook
- List facts without recommending a direction
- Pretend unsupported assumptions are grounded conclusions
- Fill the proposal with generic framework language and no decision value
- Force file generation when the user only wants direction or analysis
- Treat this skill as a tool-calling executor

## Quality Check

- [ ] The proposal has a clear recommendation or decision direction
- [ ] Scope, user scenario, and constraints are visible
- [ ] Retrieved material supports reasoning, not just citations
- [ ] Response mode is respected
- [ ] Risks and uncertainties are explicit
- [ ] If grounding is weak, the output says so clearly
- [ ] The result helps someone decide, not just read
