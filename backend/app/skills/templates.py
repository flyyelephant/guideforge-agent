"""Legacy in-code skill fallbacks.

This module is no longer the primary source of skill body content. Production
workflow skills should live in file-based directories under `backend/app/skills/`
with `_meta.json` and `skill.md`.

Current role:
- Provide a migration-safe fallback if a file-based skill is missing or incomplete.
- Keep the workflow chain running during the transition.

Safe deletion condition:
- All production skills used by the runtime have been migrated to file-based
  assets and validated.
- The loader no longer needs in-code fallback for any active `skill_key`.
"""

from __future__ import annotations

SKILL_TEMPLATES = {
    "tutorial_writing_skill": """
[Skill: tutorial_writing_skill]
Goal:
- Produce a practical tutorial that teaches a UE topic to a clearly identified audience.

Method:
- First clarify the topic, target audience, and expected outcome if they are vague.
- Use `search_ue_docs` to ground the tutorial with engine facts, recommended steps, and references.
- If `search_project_examples` exists, use it only when examples would materially improve the tutorial.
- Read the tutorial template before drafting the final document.
- End by writing a markdown file artifact instead of leaving the result only in chat.
""".strip(),
    "proposal_generation_skill": """
[Skill: proposal_generation_skill]
Goal:
- Turn a product or implementation request into a structured proposal with rationale, design, risks, and next steps.

Method:
- Clarify target users, scope boundaries, and constraints when the request is underspecified.
- Use `search_ue_docs` to gather engine constraints, relevant concepts, and supporting references.
- If `search_project_examples` exists, use it when examples can strengthen the proposed direction.
- Read the proposal template before composing the final structure.
- Finish by writing a markdown proposal artifact with source references.
""".strip(),
    "workflow_support_skill": """
[Skill: workflow_support_skill]
Goal:
- Convert a vague process question into an executable workflow with phases, outputs, dependencies, and risks.

Method:
- Clarify team context, time horizon, deliverable expectations, and constraints if they are missing.
- Use `search_ue_docs` to ground the workflow in UE guidance and established engine concepts.
- If `search_project_examples` exists, use it for implementation patterns or team examples.
- Read the workflow template before drafting the final document.
- Finish by writing a markdown workflow artifact with references.
""".strip(),
}
