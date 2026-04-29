"""Tutorial-specific grounding, filtering, and authoring helpers.

This module upgrades tutorial_writing from a retrieval-snippet formatter into a
retrieval-grounded, LLM-assisted tutorial authoring chain.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

NEGATIVE_TUTORIAL_TERMS = (
    "thirdparty",
    "catch2",
    "cqtest",
    "release-notes",
    "release notes",
    "command-line",
    "command line",
    "contributing",
    "reporters",
    "lowleveltests",
    "low level test",
    "opensource-users",
    "automation",
)

POSITIVE_TUTORIAL_TERMS = (
    "blueprint",
    "character",
    "character movement",
    "movement",
    "pawn",
    "input",
    "enhanced input",
    "widget",
    "editor utility",
    "material",
    "mesh",
    "gameplay",
    "level",
    "camera",
    "animation blueprint",
    "tutorial",
    "walkthrough",
    "quick start",
)


@dataclass
class TutorialGroundingDigest:
    topic: str
    language: str
    audience: str
    learner_level: str
    task_focus: str = ""
    general_concepts: list[str] = field(default_factory=list)
    task_specific_concepts: list[str] = field(default_factory=list)
    core_concepts: list[str] = field(default_factory=list)
    prerequisite_ideas: list[str] = field(default_factory=list)
    implementation_steps: list[str] = field(default_factory=list)
    implementation_path: list[str] = field(default_factory=list)
    validation_steps: list[str] = field(default_factory=list)
    common_failure_points: list[str] = field(default_factory=list)
    recommended_sequence: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    example_ideas: list[str] = field(default_factory=list)
    supporting_references: list[dict[str, str]] = field(default_factory=list)
    grounded_facts: list[str] = field(default_factory=list)
    source_backed_steps: list[str] = field(default_factory=list)
    teaching_glue_points: list[str] = field(default_factory=list)
    instructional_glue_allowed: bool = True
    grounding_status: str = "insufficient"
    grounding_note: str = ""
    rejected_references: list[dict[str, str]] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)


@dataclass
class TutorialAssessment:
    accepted_findings: list[dict[str, Any]]
    rejected_findings: list[dict[str, Any]]
    digest: TutorialGroundingDigest
    quality_status: str
    grounding_note: str
    language: str


@dataclass
class TutorialSections:
    audience: str
    prerequisites: str
    goal: str
    steps: str
    example: str
    faq: str
    grounding_and_supplementation: str
    sources: str


SERVER_ROOT = Path(__file__).resolve().parent.parent / "services" / "rag" / "server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


def detect_language(user_input: str) -> str:
    return "zh" if re.search(r"[\u4e00-\u9fff]", user_input or "") else "en"


def _normalize_text(finding: dict[str, Any]) -> str:
    return " ".join(
        [
            str(finding.get("title", "") or ""),
            str(finding.get("path", "") or ""),
            str(finding.get("snippet", "") or ""),
        ]
    ).lower()


def _extract_task_focus(user_input: str, findings: list[dict[str, Any]]) -> tuple[str, list[str]]:
    lower = (user_input or "").lower()
    focus_map = [
        ("character_movement", ["character movement", "movement", "character", "pawn", "角色移动", "移动", "角色控制"]),
        ("input_binding", ["enhanced input", "input", "binding", "输入", "输入绑定"]),
        ("level_blueprint", ["level blueprint", "关卡蓝图"]),
        ("animation_blueprint", ["animation blueprint", "anim blueprint", "动画蓝图"]),
        ("widget_ui", ["widget", "umg", "ui", "小部件", "界面"]),
        ("blueprint_basics", ["blueprint", "visual scripting", "蓝图", "可视化脚本"]),
    ]
    for focus, terms in focus_map:
        if any(term.lower() in lower or term in user_input for term in terms):
            return focus, terms
    if findings:
        text = _normalize_text(findings[0])
        for focus, terms in focus_map:
            if any(term.isascii() and term in text for term in terms):
                return focus, terms
    return "blueprint_basics", ["blueprint", "蓝图"]


def _focus_display(focus: str, language: str) -> str:
    zh_map = {
        "character_movement": "角色移动",
        "input_binding": "输入绑定",
        "level_blueprint": "关卡蓝图",
        "animation_blueprint": "动画蓝图",
        "widget_ui": "Widget / UI",
        "blueprint_basics": "Blueprint 基础",
    }
    en_map = {
        "character_movement": "Character Movement",
        "input_binding": "Input Binding",
        "level_blueprint": "Level Blueprint",
        "animation_blueprint": "Animation Blueprint",
        "widget_ui": "Widget / UI",
        "blueprint_basics": "Blueprint Basics",
    }
    return zh_map.get(focus, focus) if language == "zh" else en_map.get(focus, focus)


def _focus_signal_terms(task_focus: str) -> list[str]:
    mapping = {
        "character_movement": ["character", "movement", "character movement", "pawn", "input", "enhanced input"],
        "input_binding": ["input", "enhanced input", "binding", "player input"],
        "level_blueprint": ["level blueprint", "level", "event graph"],
        "animation_blueprint": ["animation blueprint", "anim blueprint", "animation"],
        "widget_ui": ["widget", "umg", "editor utility", "ui"],
        "blueprint_basics": ["blueprint", "node", "variable", "editor"],
    }
    return mapping.get(task_focus, ["blueprint"])


def build_tutorial_retry_query(user_input: str, task_focus: str, language: str) -> str:
    focus_display = _focus_display(task_focus, language)
    signals = ", ".join(_focus_signal_terms(task_focus)[:4])
    if language == "zh":
        return f"{user_input}，重点聚焦 {focus_display}，优先检索适合初学者的上手步骤、验证方式、常见坑，以及与 {signals} 相关的官方文档"
    return f"{user_input}, focus on {focus_display}, prioritize beginner setup steps, validation steps, pitfalls, and docs related to {signals}"


def _query_terms(user_input: str, findings: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_\-]+", user_input or ""):
        if len(token) >= 3:
            terms.append(token.lower())
    if findings:
        rewrite = findings[0].get("metadata", {}).get("query_rewrite", {})
        for term in rewrite.get("expanded_terms", []):
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_\-]+", str(term)):
                if len(token) >= 3:
                    terms.append(token.lower())
    seen = set()
    unique: list[str] = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            unique.append(term)
    return unique


def _score_tutorial_finding(
    finding: dict[str, Any], *, user_input: str, query_terms: list[str], focus_terms: list[str]
) -> tuple[float, list[str]]:
    score = float(finding.get("score", 0.0) or 0.0)
    text = _normalize_text(finding)
    reasons: list[str] = []

    negative_hits = [term for term in NEGATIVE_TUTORIAL_TERMS if term in text]
    if negative_hits:
        score -= 0.9 + 0.15 * len(negative_hits)
        reasons.append(f"negative:{', '.join(negative_hits[:3])}")

    positive_hits = [term for term in POSITIVE_TUTORIAL_TERMS if term in text]
    if positive_hits:
        score += 0.2 * min(len(positive_hits), 4)
        reasons.append(f"positive:{', '.join(positive_hits[:3])}")

    anchor_hits = [term for term in query_terms if term in text]
    if anchor_hits:
        score += 0.18 * min(len(anchor_hits), 4)
        reasons.append(f"anchors:{', '.join(anchor_hits[:4])}")

    if "blueprint" in user_input.lower() and "blueprint" in text:
        score += 0.2
        reasons.append("topic_match:blueprint")

    focus_hits = [term for term in focus_terms if term.lower() in text]
    if focus_hits:
        score += 0.32 * min(len(focus_hits), 3)
        reasons.append(f"focus:{', '.join(focus_hits[:3])}")

    if any(term in text for term in ("tutorial", "walkthrough", "quick start", "getting started")):
        score += 0.12
        reasons.append("tutorial_like")

    return score, reasons

def assess_tutorial_grounding(user_input: str, findings: list[dict[str, Any]]) -> TutorialAssessment:
    language = detect_language(user_input)
    focus_key, focus_terms = _extract_task_focus(user_input, findings)
    query_terms = _query_terms(user_input, findings)
    scored: list[tuple[float, list[str], dict[str, Any]]] = []
    for finding in findings:
        adjusted, reasons = _score_tutorial_finding(finding, user_input=user_input, query_terms=query_terms, focus_terms=focus_terms)
        enriched = dict(finding)
        meta = dict(enriched.get("metadata", {}))
        meta["tutorial_relevance_score"] = adjusted
        meta["tutorial_relevance_reasons"] = reasons
        enriched["metadata"] = meta
        scored.append((adjusted, reasons, enriched))

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for adjusted, _, enriched in sorted(scored, key=lambda item: item[0], reverse=True):
        text_blob = _normalize_text(enriched)
        hard_negative = any(term in text_blob for term in NEGATIVE_TUTORIAL_TERMS)
        if adjusted >= 0.55 and not (hard_negative and adjusted < 0.95):
            accepted.append(enriched)
        else:
            rejected.append(enriched)

    accepted = accepted[:5]
    rejected = rejected[:5]

    if not accepted:
        status = "insufficient"
        note = "当前检索结果还不足以支撑一份可靠的初学者教程。" if language == "zh" else "Current retrieval results are not suitable enough for a grounded beginner tutorial."
    elif len(accepted) == 1 or accepted[0]["metadata"].get("tutorial_relevance_score", 0.0) < 0.85:
        status = "weak_grounding"
        note = "当前资料只能部分支撑教程，请保持保守写法，并明确标注教学补全内容。" if language == "zh" else "Tutorial grounding is partial. The final tutorial should stay conservative and label any teaching glue clearly."
    else:
        status = "grounded"
        note = "当前资料已经足以支撑一份面向初学者的引导式教程。" if language == "zh" else "Tutorial grounding is strong enough to support a guided beginner tutorial."

    digest = build_tutorial_digest(
        user_input=user_input,
        language=language,
        accepted_findings=accepted,
        rejected_findings=rejected,
        quality_status=status,
        grounding_note=note,
        task_focus=focus_key,
    )
    return TutorialAssessment(
        accepted_findings=accepted,
        rejected_findings=rejected,
        digest=digest,
        quality_status=status,
        grounding_note=note,
        language=language,
    )


def build_tutorial_digest(
    *,
    user_input: str,
    language: str,
    accepted_findings: list[dict[str, Any]],
    rejected_findings: list[dict[str, Any]],
    quality_status: str,
    grounding_note: str,
    task_focus: str,
) -> TutorialGroundingDigest:
    audience = (
        "UE 初学者或希望快速上手某个主题的开发者"
        if language == "zh"
        else "UE beginners or developers learning the topic for the first time"
    )
    learner_level = "beginner"
    core_concepts: list[str] = []
    general_concepts: list[str] = []
    task_specific_concepts: list[str] = []
    grounded_facts: list[str] = []
    source_backed_steps: list[str] = []
    teaching_glue_points: list[str] = []
    step_candidates: list[str] = []
    caveats: list[str] = []
    references: list[dict[str, str]] = []

    for finding in accepted_findings[:4]:
        title = str(finding.get("title", "") or "").strip()
        snippet = str(finding.get("snippet", "") or "").strip()
        path_str = str(finding.get("path", "") or "").strip()
        if title and title not in core_concepts:
            core_concepts.append(title)
        lowered_title = title.lower()
        focus_terms = _focus_signal_terms(task_focus)
        if task_focus != "blueprint_basics" and any(term in lowered_title or term in snippet.lower() for term in focus_terms):
            if title and title not in task_specific_concepts:
                task_specific_concepts.append(title)
        elif any(term in lowered_title for term in ("blueprint", "editor", "node", "character", "input", "movement")):
            if title and title not in general_concepts:
                general_concepts.append(title)
        if snippet:
            grounded_facts.append(snippet[:220])
            source_backed_steps.append(snippet[:180])
            step_candidates.append(snippet[:180])
        references.append({"title": title or "Untitled source", "path": path_str or "No path provided", "snippet": snippet[:220]})
        if title and task_focus != "blueprint_basics" and title not in teaching_glue_points and any(term in (title + " " + snippet).lower() for term in focus_terms):
            teaching_glue_points.append(title)
        if any(token in snippet.lower() for token in ("version", "deprecated", "editor", "experimental")):
            caveats.append(snippet[:180])

    prerequisite_ideas = [
        "知道如何打开 Unreal Editor，并能找到相关面板、资产或蓝图。"
        if language == "zh"
        else "Know how to open the Unreal Editor and locate the relevant panel or asset.",
        "准备一个小型测试项目或空场景用于验证步骤。"
        if language == "zh"
        else "Have a small test project or empty scene ready for validation.",
    ]
    example_ideas = [
        "创建一个最小练习场景，并在每一步后立刻验证结果。"
        if language == "zh"
        else "Create a tiny practice scene and validate each step immediately.",
    ]
    rejected_refs = [
        {
            "title": str(item.get("title", "") or "Untitled source"),
            "path": str(item.get("path", "") or "No path provided"),
            "snippet": str(item.get("snippet", "") or "")[:160],
        }
        for item in rejected_findings[:3]
    ]
    coverage_gaps: list[str] = []
    if quality_status != "grounded":
        coverage_gaps.append(
            "当前本地资料还不足以为每个教程章节提供完整、初学者友好的步骤支撑。"
            if language == "zh"
            else "The current local docs do not provide enough beginner-friendly step-by-step support for every tutorial section."
        )
    if not accepted_findings:
        coverage_gaps.append(
            "当前没有通过教程相关性筛选的可靠资料。"
            if language == "zh"
            else "No reliable tutorial-grade source passed the relevance gate."
        )

    focus_display = _focus_display(task_focus, language)
    if language == "zh":
        implementation_path = [
            f"先搭出与 {focus_display} 直接相关的最小实现路径。",
            "先完成最小可运行闭环，再补充背景解释和扩展内容。",
            "每完成一个关键步骤就立即验证一次结果。",
        ]
        validation_steps = [
            "确认相关 Blueprint、组件或输入入口已经正确创建。",
            "在关键节点连线或参数设置完成后立即运行预览。",
            "检查实际表现是否已经达到教程目标。",
        ]
        common_failure_points = [
            "把通用 Blueprint 概念误当成当前功能的实操步骤。",
            "还没验证最小闭环就继续堆节点或堆逻辑。",
            "重复术语解释，却没有说明这一步为什么要做。",
        ]
        recommended_sequence = [
            f"先明确本教程聚焦的是 {focus_display}。",
            "再说明前置准备和最小实验环境。",
            "每一步都写清楚做什么、为什么这样做、如何验证。",
            "最后补充常见问题和参考资料。",
        ]
    else:
        implementation_path = [
            f"Start from a minimal reproducible setup for {focus_display}.",
            "Complete the smallest working loop before adding more explanation.",
            "Validate each major step immediately.",
        ]
        validation_steps = [
            "Confirm the relevant Blueprint or component entry exists in the editor.",
            "Run or preview after the key node wiring step.",
            "Check that the observed result matches the tutorial goal.",
        ]
        common_failure_points = [
            "Confusing general Blueprint concepts with task-specific implementation steps.",
            "Adding too many nodes before validating the smallest path.",
            "Repeating editor terms without explaining why the step matters.",
        ]
        recommended_sequence = [
            f"State that the tutorial is focused on {focus_display}.",
            "Set the prerequisites and minimal environment.",
            "Explain what to do, why it matters, and how to validate it.",
            "End with pitfalls and references.",
        ]

    return TutorialGroundingDigest(
        topic=user_input,
        language=language,
        audience=audience,
        learner_level=learner_level,
        task_focus=task_focus,
        general_concepts=general_concepts,
        task_specific_concepts=task_specific_concepts,
        core_concepts=core_concepts,
        prerequisite_ideas=prerequisite_ideas,
        implementation_steps=step_candidates,
        implementation_path=implementation_path,
        validation_steps=validation_steps,
        common_failure_points=common_failure_points,
        recommended_sequence=recommended_sequence,
        caveats=caveats,
        example_ideas=example_ideas,
        supporting_references=references[:3],
        grounded_facts=grounded_facts[:4],
        source_backed_steps=source_backed_steps[:3],
        teaching_glue_points=(teaching_glue_points[:3] or recommended_sequence[:2]),
        instructional_glue_allowed=True,
        grounding_status=quality_status,
        grounding_note=grounding_note,
        rejected_references=rejected_refs,
        coverage_gaps=coverage_gaps,
    )

class TutorialAuthoringService:
    def __init__(self, smart_settings_path: Path | None = None) -> None:
        if smart_settings_path is None:
            smart_settings_path = Path(__file__).resolve().parent.parent / "services" / "rag" / "server" / "rag" / "config" / "settings.yaml"
        self._smart_settings_path = smart_settings_path.resolve()
        self._smart_settings = yaml.safe_load(self._smart_settings_path.read_text(encoding="utf-8")) or {}
        self._modular_root, self._modular_settings_path = self._resolve_modular_paths()
        self._modular_settings = None
        self._llm = None
        self._message_cls = None

    def build_direct_answer(self, *, user_input: str, assessment: TutorialAssessment) -> str:
        try:
            payload = self._author_json(mode="direct_answer", user_input=user_input, digest=assessment.digest)
            body = str(payload.get("body", "") or "").strip()
            if not body:
                return self._fallback_direct_answer(user_input=user_input, assessment=assessment)
            return "\n".join([
                "## 直接回答" if assessment.language == "zh" else "## Direct Answer",
                body,
                "",
                "## 依据说明" if assessment.language == "zh" else "## Grounding Note",
                self._grounding_summary(assessment),
                "",
                "## 参考资料" if assessment.language == "zh" else "## References",
                build_source_lines(assessment.accepted_findings, assessment.grounding_note),
            ])
        except Exception:
            return self._fallback_direct_answer(user_input=user_input, assessment=assessment)

    def build_structured_chat(self, *, user_input: str, assessment: TutorialAssessment) -> str:
        try:
            payload = self._author_json(mode="structured_chat", user_input=user_input, digest=assessment.digest)
            sections = payload.get("sections", []) or []
            lines: list[str] = []
            for item in sections:
                heading = str(item.get("heading", "") or "").strip()
                body = str(item.get("body", "") or "").strip()
                if heading:
                    lines.append(f"## {heading}")
                if body:
                    lines.append(body)
                    lines.append("")
            lines.extend([
                "## 依据与补全说明" if assessment.language == "zh" else "## Grounding and Supplementation",
                self._grounding_summary(assessment),
                "",
                "## 参考资料" if assessment.language == "zh" else "## References",
                build_source_lines(assessment.accepted_findings, assessment.grounding_note),
            ])
            return "\n".join(lines).strip()
        except Exception:
            return self._fallback_structured_chat(user_input=user_input, assessment=assessment)

    def build_deliverable_sections(self, *, user_input: str, assessment: TutorialAssessment) -> TutorialSections:
        try:
            payload = self._author_json(mode="deliverable_file", user_input=user_input, digest=assessment.digest)
            return TutorialSections(
                audience=str(payload.get("audience", "") or assessment.digest.audience),
                prerequisites=self._normalize_list_block(payload.get("prerequisites"), assessment.language),
                goal=str(payload.get("goal", "") or user_input),
                steps=self._normalize_steps(payload.get("steps"), assessment.language),
                example=str(payload.get("example", "") or self._fallback_example(assessment)),
                faq=self._normalize_list_block(payload.get("faq"), assessment.language),
                grounding_and_supplementation=self._grounding_summary(assessment),
                sources=build_source_lines(assessment.accepted_findings, assessment.grounding_note),
            )
        except Exception:
            return self._fallback_deliverable_sections(user_input=user_input, assessment=assessment)

    def _resolve_modular_paths(self) -> tuple[Path, Path]:
        backend_cfg = self._smart_settings.get("backend", {}).get("modular", {})
        config_dir = self._smart_settings_path.parent
        modular_root = (config_dir / backend_cfg.get("repo_root", "../modular")).resolve()
        modular_settings = (config_dir / backend_cfg.get("settings_path", "../modular/config/settings.yaml")).resolve()
        return modular_root, modular_settings

    def _ensure_modular_import_path(self) -> None:
        modular_root_str = str(self._modular_root)
        if modular_root_str in sys.path:
            sys.path.remove(modular_root_str)
        sys.path.insert(0, modular_root_str)
        self._purge_conflicting_src_modules()

    def _purge_conflicting_src_modules(self) -> None:
        src_module = sys.modules.get("src")
        if src_module is None:
            return
        module_file = getattr(src_module, "__file__", None)
        module_path = Path(module_file).resolve() if module_file else None
        if module_path is not None and self._modular_root in module_path.parents:
            return
        for module_name in list(sys.modules.keys()):
            if module_name == "src" or module_name.startswith("src."):
                del sys.modules[module_name]

    def _load_modular_settings(self):
        if self._modular_settings is not None:
            return self._modular_settings
        self._ensure_modular_import_path()
        from src.core.settings import load_settings
        self._modular_settings = load_settings(self._modular_settings_path)
        return self._modular_settings

    def _get_llm(self):
        if self._llm is not None and self._message_cls is not None:
            return self._llm
        self._ensure_modular_import_path()
        from src.libs.llm.base_llm import Message
        from src.libs.llm.llm_factory import LLMFactory
        self._message_cls = Message
        self._llm = LLMFactory.create(self._load_modular_settings())
        return self._llm

    def _author_json(self, *, mode: str, user_input: str, digest: TutorialGroundingDigest) -> dict[str, Any]:
        llm = self._get_llm()
        language_rule = "Write the tutorial body in Simplified Chinese." if digest.language == "zh" else "Write the tutorial body in English."
        mode_contract = {
            "direct_answer": '{"body": "..."}',
            "structured_chat": '{"sections": [{"heading": "...", "body": "..."}]}',
            "deliverable_file": '{"audience": "...", "prerequisites": ["..."], "goal": "...", "steps": [{"title": "...", "what": "...", "why": "...", "checkpoint": "..."}], "example": "...", "faq": ["..."]}',
        }[mode]
        system_prompt = (
            "You are a tutorial author for Unreal Engine learners. "
            "Write a coherent beginner-friendly tutorial first, instead of producing a retrieval report. "
            f"{language_rule} "
            "Use retrieved material only as optional support for terminology, factual constraints, a few key steps, and reference suggestions. "
            "If retrieval is weak, still write a complete and useful tutorial by relying on the skill guidance and conservative Unreal best practices. Do not let low-quality retrieval dictate the tutorial outline. "
            "Keep the body tutorial-like: goal, preparation, ordered steps, why each step matters, checkpoints, and common pitfalls. "
            "Return JSON only."
        )
        digest_json = json.dumps(asdict(digest), ensure_ascii=False, indent=2)
        user_prompt = (
            f"Mode: {mode}\n"
            f"User request: {user_input}\n\n"
            f"Digest:\n{digest_json}\n\n"
            "Important writing requirements:\n"
            "- Teach a beginner in a clear progression.\n"
            "- Explain what to do and why it matters.\n"
            "- Keep references out of the main teaching flow; they will be rendered separately.\n"
            "- Use grounded_facts and source_backed_steps only to lightly support terminology, constraints, and a few key implementation points.\n- Use teaching_glue_points and the skill methodology to make the tutorial complete, readable, and practical.\n- If grounding is weak, stay conservative, avoid hard unsupported claims, and do not turn noisy retrieval into the tutorial backbone.\n\n"
            f"Return exactly this JSON shape: {mode_contract}"
        )
        messages = [
            self._message_cls(role="system", content=system_prompt),
            self._message_cls(role="user", content=user_prompt),
        ]
        response = llm.chat(messages)
        raw = (getattr(response, "content", "") or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            raw = raw.strip()
        return json.loads(raw)

    def _normalize_list_block(self, value: Any, language: str) -> str:
        if isinstance(value, list):
            lines = []
            for item in value:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
            if lines:
                return "\n".join(lines)
        text = str(value or "").strip()
        if text:
            return text
        return "- 当前没有足够可验证的细节。" if language == "zh" else "- No validated supporting detail was available."

    def _normalize_steps(self, value: Any, language: str) -> str:
        if not isinstance(value, list):
            return (
                "1. 当前依据不足，只能先给出保守的教程骨架。\n   - 请把它当作提纲，而不是最终定稿。"
                if language == "zh"
                else "1. Grounding was too weak to produce validated tutorial steps.\n   - Use this as an outline only."
            )
        lines = []
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "") or "").strip() or (f"步骤 {index}" if language == "zh" else f"Step {index}")
            what = str(item.get("what", "") or "").strip()
            why = str(item.get("why", "") or "").strip()
            checkpoint = str(item.get("checkpoint", "") or "").strip()
            lines.append(f"{index}. {title}")
            if what:
                lines.append(f"   - {'做什么' if language == 'zh' else 'What to do'}: {what}")
            if why:
                lines.append(f"   - {'为什么' if language == 'zh' else 'Why it matters'}: {why}")
            if checkpoint:
                lines.append(f"   - {'如何验证' if language == 'zh' else 'Checkpoint'}: {checkpoint}")
        return "\n".join(lines) if lines else (
            "1. 当前依据不足，只能先给出保守的教程骨架。\n   - 请把它当作提纲，而不是最终定稿。"
            if language == "zh"
            else "1. Grounding was too weak to produce validated tutorial steps.\n   - Use this as an outline only."
        )

    def _grounding_summary(self, assessment: TutorialAssessment) -> str:
        if assessment.language == "zh":
            grounded = "以下教程优先依据已检索到的 Unreal Engine 文档中的事实、术语和限制来组织。"
            supplemental = "为了让教学顺序更连贯，系统可能加入少量通用教学补全，例如学习顺序、检查点和提醒；这些补全不应被视为与官方文档同等级的事实依据。"
            insuff = "当前资料还不足以完全支撑高质量教程，因此以下内容应被视为保守草稿或学习骨架。"
        else:
            grounded = "This tutorial prioritizes facts, terminology, and constraints grounded in the retrieved Unreal Engine documentation."
            supplemental = "A small amount of instructional glue may be added for teaching continuity, but it should not be treated as documentation-backed fact."
            insuff = "Current grounding is not strong enough for a fully reliable tutorial, so treat the result as a conservative, partially guided draft."
        if assessment.quality_status == "grounded":
            return f"{grounded}\n\n{supplemental}"
        if assessment.quality_status == "weak_grounding":
            return f"{grounded}\n\n{supplemental}\n\n{assessment.grounding_note}"
        return f"{insuff}\n\n{assessment.grounding_note}"

    def _digest_step_lines(self, assessment: TutorialAssessment) -> list[str]:
        steps: list[str] = []
        for index, item in enumerate(assessment.digest.implementation_steps[:4], start=1):
            text = str(item).strip()
            if not text:
                continue
            if assessment.language == "zh":
                steps.append(f"{index}. 先完成这个关键动作：{text}")
            else:
                steps.append(f"{index}. Practice this grounded point first: {text}")
        if steps:
            return steps
        if assessment.language == "zh":
            return [
                "1. 先明确这份教程最终要帮助读者做成什么。",
                "2. 在最小场景里验证核心功能已经跑通。",
                "3. 只把有依据的事实写成结论，其余内容明确标成教学补全。",
            ]
        return [
            "1. Define the single outcome this tutorial should teach.",
            "2. Validate the core concept in a minimal scene before expanding.",
            "3. Treat unsupported details as teaching glue, not documentation-backed fact.",
        ]

    def _digest_faq_items(self, assessment: TutorialAssessment) -> list[str]:
        items = []
        for item in assessment.digest.caveats[:3]:
            text = str(item).strip()
            if text:
                items.append(text)
        if items:
            return items
        if assessment.language == "zh":
            return [
                "如果某一步缺少明确依据，请把它视为教学补全，而不是文档事实。",
                "先做出最小可运行版本，再继续扩展 Blueprint 逻辑。",
            ]
        return [
            "If a step is not strongly grounded, treat it as teaching glue rather than a documentation-backed fact.",
            "Finish the smallest working version first before expanding the Blueprint setup.",
        ]

    def _fallback_direct_answer(self, *, user_input: str, assessment: TutorialAssessment) -> str:
        steps = self._digest_step_lines(assessment)[:3]
        concepts = [c for c in assessment.digest.core_concepts[:3] if c]
        if assessment.language == "zh":
            concept_line = "、".join(concepts) if concepts else "当前检索到的核心概念"
            return "\n".join([
                "## 直接回答",
                f"围绕 `{user_input}`，建议先抓住 {concept_line} 这些核心概念，再用一个最小练习把关键步骤跑通。",
                "",
                "## 建议起步步骤",
                *steps,
                "",
                "## 依据与补全说明",
                self._grounding_summary(assessment),
                "",
                "## 参考资料",
                build_source_lines(assessment.accepted_findings, assessment.grounding_note),
            ])
        concept_line = ", ".join(concepts) if concepts else "the grounded concepts in the retrieved docs"
        return "\n".join([
            "## Direct Answer",
            f"To start learning `{user_input}`, anchor yourself in {concept_line} and validate one small exercise first.",
            "",
            "## Suggested Next Steps",
            *steps,
            "",
            "## Grounding and Supplementation",
            self._grounding_summary(assessment),
            "",
            "## References",
            build_source_lines(assessment.accepted_findings, assessment.grounding_note),
        ])

    def _fallback_structured_chat(self, *, user_input: str, assessment: TutorialAssessment) -> str:
        concepts = assessment.digest.core_concepts[:4]
        steps = self._digest_step_lines(assessment)
        faq_items = self._digest_faq_items(assessment)
        if assessment.language == "zh":
            concept_lines = [f"- {item}" for item in concepts] or ["- 当前资料主要覆盖 Blueprint 基础概念和编辑器上下文。"]
            faq_lines = [f"- {item}" for item in faq_items]
            return "\n".join([
                "## 目标",
                user_input,
                "",
                "## 核心概念",
                *concept_lines,
                "",
                "## 推荐学习步骤",
                *steps,
                "",
                "## 常见问题与排查",
                *faq_lines,
                "",
                "## 依据与补全说明",
                self._grounding_summary(assessment),
                "",
                "## 参考资料",
                build_source_lines(assessment.accepted_findings, assessment.grounding_note),
            ])
        concept_lines = [f"- {item}" for item in concepts] or ["- Current sources mainly cover Blueprint base classes and editor context."]
        faq_lines = [f"- {item}" for item in faq_items]
        return "\n".join([
            "## Goal",
            user_input,
            "",
            "## Core Concepts",
            *concept_lines,
            "",
            "## Recommended Learning Steps",
            *steps,
            "",
            "## Common Pitfalls",
            *faq_lines,
            "",
            "## Grounding and Supplementation",
            self._grounding_summary(assessment),
            "",
            "## References",
            build_source_lines(assessment.accepted_findings, assessment.grounding_note),
        ])

    def _fallback_deliverable_sections(self, *, user_input: str, assessment: TutorialAssessment) -> TutorialSections:
        zh = assessment.language == "zh"
        steps = self._digest_step_lines(assessment)
        faq_items = self._digest_faq_items(assessment)
        if assessment.quality_status == "insufficient":
            step_block = (
                "1. 当前依据不足，建议先把教程主题收窄到更具体的 UE 功能。\n   - 先把这份文档当作教学骨架，而不是最终定稿。"
                if zh
                else "1. Current grounding is too weak; narrow the tutorial topic to a more specific UE feature.\n   - Treat this document as an outline draft, not a final teaching document."
            )
        else:
            step_block = "\n".join(steps)
        return TutorialSections(
            audience=assessment.digest.audience,
            prerequisites=self._normalize_list_block(assessment.digest.prerequisite_ideas, assessment.language),
            goal=user_input,
            steps=step_block,
            example=self._fallback_example(assessment),
            faq=self._normalize_list_block(faq_items, assessment.language),
            grounding_and_supplementation=self._grounding_summary(assessment),
            sources=build_source_lines(assessment.accepted_findings, assessment.grounding_note),
        )

    def _fallback_example(self, assessment: TutorialAssessment) -> str:
        example_idea = next((item for item in assessment.digest.example_ideas if item), None)
        if example_idea:
            return example_idea
        if assessment.language == "zh":
            return "先设计一个最小验证练习，确认一个核心概念已经跑通，再继续扩展成完整教程。"
        return "Start with a tiny validation exercise that proves one core concept before expanding into a full tutorial."


def _reference_purpose(item: dict[str, Any], zh: bool) -> str:
    text = " ".join([str(item.get("title", "") or ""), str(item.get("snippet", "") or "")]).lower()
    if any(token in text for token in ("character", "movement", "input", "pawn", "controller")):
        return "用于支撑关键实现步骤" if zh else "Supports key implementation steps"
    if any(token in text for token in ("blueprint", "node", "graph", "editor")):
        return "用于校正术语和编辑器上下文" if zh else "Helps validate terminology and editor context"
    if any(token in text for token in ("widget", "material", "mesh", "animation")):
        return "用于补充相关功能背景" if zh else "Adds related feature context"
    return "作为轻量参考资料" if zh else "Used as a lightweight reference"


def build_source_lines(findings: list[dict[str, Any]], grounding_note: str | None = None) -> str:
    zh = bool(grounding_note and any("\u4e00" <= ch <= "\u9fff" for ch in grounding_note))
    lines: list[str] = []
    for item in findings[:3]:
        title = str(item.get("title") or "Untitled source").strip()
        if not title:
            continue
        lines.append(f"- {title}")
        lines.append(f"  - {_reference_purpose(item, zh)}")
    if grounding_note:
        lines.append(f"- {'\u8bf4\u660e' if zh else 'Note'}: {grounding_note}")
    return "\n".join(lines) or ("- \u5f53\u524d\u6ca1\u6709\u53ef\u5c55\u793a\u7684\u53c2\u8003\u8d44\u6599" if zh else "- No displayable references were available.")


_service_singleton: TutorialAuthoringService | None = None


def get_tutorial_authoring_service() -> TutorialAuthoringService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = TutorialAuthoringService()
    return _service_singleton
