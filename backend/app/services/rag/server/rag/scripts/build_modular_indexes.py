"""Build modular indexes from SmartUEAssistant local knowledge directories."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


SMART_RAG_ROOT = Path(__file__).resolve().parents[1]
SMART_SERVER_ROOT = SMART_RAG_ROOT.parent
SMART_PROJECT_ROOT = SMART_SERVER_ROOT.parent
SMART_SETTINGS_PATH = SMART_RAG_ROOT / "config" / "settings.yaml"


def _load_smart_settings() -> dict:
    with SMART_SETTINGS_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _resolve(path_str: str | None, base: Path) -> Path | None:
    if not path_str:
        return None
    return (base / path_str).resolve()


def _iter_files(root: Path, extensions: set[str]):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build MODULAR collections from SmartUEAssistant knowledge data")
    parser.add_argument("--source", choices=["all", "docs", "code", "assets"], default="all")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    smart_cfg = _load_smart_settings()
    modular_cfg = smart_cfg.get("backend", {}).get("modular", {})
    ingestion_cfg = modular_cfg.get("ingestion", {})

    modular_root = _resolve(modular_cfg.get("repo_root", "../modular"), SMART_SETTINGS_PATH.parent)
    modular_settings_path = _resolve(modular_cfg.get("settings_path", "../modular/config/settings.yaml"), SMART_SETTINGS_PATH.parent)
    if modular_root is None or modular_settings_path is None:
        raise RuntimeError("modular backend paths are not configured")

    sys.path.insert(0, str(modular_root))

    from src.core.settings import load_settings
    from src.ingestion.pipeline import IngestionPipeline

    modular_settings = load_settings(modular_settings_path)

    # SmartUE keeps source ownership in its own settings file and only delegates
    # ingestion mechanics to the vendored MODULAR runtime.
    plans = [
        (
            "docs",
            modular_cfg.get("docs_collection", "ue_docs"),
            _resolve(ingestion_cfg.get("docs_input_dir", "../../../knowledge/ue_docs/raw/markdown"), SMART_SETTINGS_PATH.parent),
            {".md", ".markdown", ".udn", ".txt"},
        ),
        (
            "code",
            modular_cfg.get("code_collection", "cpp_source"),
            _resolve(ingestion_cfg.get("code_input_dir", "../../../knowledge/cpp_source/converted"), SMART_SETTINGS_PATH.parent),
            {".md", ".markdown", ".txt"},
        ),
        (
            "assets",
            modular_cfg.get("assets_collection", "project_assets"),
            _resolve(ingestion_cfg.get("assets_input_dir", "../../../knowledge/project_assets"), SMART_SETTINGS_PATH.parent),
            {".md", ".markdown", ".txt", ".json"},
        ),
    ]

    selected = [plan for plan in plans if args.source in ("all", plan[0])]
    if not selected:
        print("No ingestion source selected.")
        return 1

    overall_failures = 0

    for source_name, collection, input_dir, extensions in selected:
        if input_dir is None or not input_dir.exists():
            print(f"[skip] {source_name}: input dir not found -> {input_dir}")
            continue

        files = list(_iter_files(input_dir, extensions))
        if not files:
            print(f"[skip] {source_name}: no matching files in {input_dir}")
            continue

        print(f"[start] {source_name}: {len(files)} files -> collection={collection}")
        pipeline = IngestionPipeline(modular_settings, collection=collection, force=args.force)

        success_count = 0
        failure_count = 0

        try:
            for index, file_path in enumerate(files, start=1):
                result = pipeline.run(str(file_path))
                if result.success:
                    success_count += 1
                    print(f"[ok]   {source_name} {index}/{len(files)} {file_path.name}")
                else:
                    failure_count += 1
                    print(f"[fail] {source_name} {index}/{len(files)} {file_path.name}: {result.error}")
        finally:
            pipeline.close()

        overall_failures += failure_count
        print(f"[done] {source_name}: success={success_count} failure={failure_count}")

    return 1 if overall_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
