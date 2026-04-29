---
name: Tutorial Writing
description: Method guidance for grounded tutorial generation.
task_type: tutorial_writing
version: "1"
---

# Tutorial Writing Skill

## What This Skill Does

Helps turn a UE topic into a tutorial that is actually useful for learning: clear audience, clear goal, practical steps, and visible grounding from retrieved sources.

## Core Principle

A tutorial is not a pile of notes or copied documentation. It should help the reader successfully do one thing, understand why the steps matter, and know where the guidance came from.

## Workflow

### Step 1: Clarify the learning target
Clarify first when any of these are missing or vague:
- The tutorial topic
- The intended audience
- The expected learning outcome
- The delivery boundary: quick guidance, structured walkthrough, or formal document

Do not start writing a full tutorial if the user has not made the teaching goal clear enough.

### Step 2: Ground the content
Use retrieved documentation as the factual base for the tutorial.

Use retrieval to identify:
- The relevant UE concept, subsystem, or workflow
- The most useful sequence of actions or checks
- Important caveats, version-sensitive notes, and terminology
- Source material worth citing in the final answer or file

Do not copy the documentation verbatim. Convert the retrieved material into teachable steps, examples, warnings, and checkpoints.

### Step 3: Organize by response mode
`direct_answer`
- Give the shortest useful path.
- Focus on the core recommendation or first steps.
- Do not force file generation.
- Still include a concise source-aware references block when grounded results exist.

`structured_chat`
- Organize the answer into clear sections such as goal, steps, pitfalls, and references.
- Be more complete than direct_answer, but keep it chat-oriented.
- Do not pretend it is a formal tutorial document.

`deliverable_file`
- Organize the content as a proper tutorial deliverable.
- Use the tutorial template structure.
- Ensure the file reads like a usable tutorial, not a search report.
- Include a reference section in the final markdown.

### Step 4: Handle weak grounding honestly
If grounding is strong:
- Use the retrieved sources to support steps, examples, and caveats.

If grounding is weak or missing:
- Do not present strong claims as settled facts.
- State that the tutorial is only a draft scaffold or high-level guidance.
- Make the lack of reliable references visible in the response or file.

## Grounding and Sources

When sources are available:
- Use them to support key steps and important warnings.
- Preserve source visibility in direct answers, structured chat, and deliverable files.
- Prefer the most relevant sources over dumping many weak references.

When sources are not available:
- Say so clearly.
- Reduce certainty.
- Avoid sounding authoritative on unsupported details.

## Anti-patterns

Do not:
- Copy long chunks of documentation into the tutorial
- Write a tutorial that never makes the audience explicit
- Turn the answer into a loose knowledge summary with no learning path
- Pretend the tutorial is grounded when retrieval did not provide usable support
- Force markdown output when the user only wants guidance in chat
- Treat this skill as an executor or tool-calling script

## Quality Check

- [ ] The tutorial teaches one clear outcome
- [ ] The audience is explicit or reasonably inferred
- [ ] Steps are practical, ordered, and teachable
- [ ] Retrieved sources are used as grounding, not pasted raw
- [ ] Response mode is respected
- [ ] If grounding is weak, that weakness is made explicit
- [ ] The result feels like a tutorial, not a documentation digest
