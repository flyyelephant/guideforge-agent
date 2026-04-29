"""Lightweight terminology bridge for Chinese UE queries.

This module keeps a small, high-value bilingual term map. It is intentionally
simple: the goal is to improve hit rate against the current English document
corpus without introducing a heavy translation system.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TerminologyMatch:
    source: str
    replacements: tuple[str, ...]


# Keep this list small and high-signal. It should be easy to expand when real
# search misses are observed in developer-center workflows.
_TERMINOLOGY: tuple[TerminologyMatch, ...] = (
    TerminologyMatch("蓝图", ("Blueprint", "visual scripting")),
    TerminologyMatch("可视化脚本", ("Blueprint visual scripting", "visual scripting")),
    TerminologyMatch("可视化脚本系统", ("Blueprint visual scripting", "visual scripting")),
    TerminologyMatch("动画蓝图", ("Animation Blueprint",)),
    TerminologyMatch("关卡蓝图", ("Level Blueprint",)),
    TerminologyMatch("编辑器工具", ("Editor tools", "Editor Utility")),
    TerminologyMatch("编辑器测试面板", ("Unreal Editor test panel", "Editor Utility Widget")),
    TerminologyMatch("小部件", ("Widget", "UMG")),
    TerminologyMatch("材质", ("Material", "shader")),
    TerminologyMatch("网格", ("Mesh", "Static Mesh", "Skeletal Mesh")),
    TerminologyMatch("建模", ("modeling", "modeling tools")),
    TerminologyMatch("三角形数量", ("triangle count", "polygons", "mesh complexity")),
    TerminologyMatch("面数", ("polygon count", "triangle count")),
    TerminologyMatch("多边形", ("polygons", "polygon count")),
    TerminologyMatch("关卡", ("Level", "level design")),
    TerminologyMatch("游戏玩法", ("Gameplay", "gameplay system")),
    TerminologyMatch("碰撞", ("Collision",)),
    TerminologyMatch("骨骼网格", ("Skeletal Mesh",)),
    TerminologyMatch("静态网格", ("Static Mesh",)),
    TerminologyMatch("编辑器", ("Unreal Editor", "Editor")),
)


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[一-鿿]", text or ""))


def expand_terms(query: str) -> list[str]:
    query = (query or "").strip()
    if not query:
        return []

    expanded: list[str] = []
    seen: set[str] = set()
    for item in _TERMINOLOGY:
        if item.source in query:
            for candidate in item.replacements:
                normalized = candidate.strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    expanded.append(normalized)
    return expanded
