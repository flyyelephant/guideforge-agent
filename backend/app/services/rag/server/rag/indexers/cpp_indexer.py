#!/usr/bin/env python3
"""
C++ 源码索引器
扫描 .h/.cpp 文件，提取类定义、函数签名、注释，转为 Markdown 片段
供 SimpleRAGClient 关键词检索使用。支持增量索引（mtime 缓存）。
"""

import os
import re
import json
from pathlib import Path


# ── 正则：提取 C++ 结构 ────────────────────────────────────
_RE_CLASS    = re.compile(r'class\s+\w+_API\s+(\w+)\s*(?::\s*[^{]+)?\{', re.MULTILINE)
_RE_STRUCT   = re.compile(r'struct\s+\w+_API\s+(\w+)', re.MULTILINE)
_RE_FUNC     = re.compile(
    r'(?:(?:virtual|static|FORCEINLINE|inline)\s+)*'
    r'(?:[\w:<>*&\s]+?)\s+'
    r'(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?[;{]',
    re.MULTILINE
)
_RE_BLOCK_COMMENT = re.compile(r'/\*\*(.*?)\*/', re.DOTALL)
_RE_LINE_COMMENT  = re.compile(r'//([^\n]+)')


def _extract_info(content: str) -> dict:
    """从 C++ 文件内容中提取关键信息"""
    classes   = _RE_CLASS.findall(content)
    structs   = _RE_STRUCT.findall(content)
    functions = _RE_FUNC.findall(content)
    block_comments = [c.strip() for c in _RE_BLOCK_COMMENT.findall(content)]
    line_comments  = [c.strip() for c in _RE_LINE_COMMENT.findall(content)
                      if len(c.strip()) > 10]

    _skip = {'if', 'for', 'while', 'switch', 'return', 'else', 'do'}
    functions = [f for f in dict.fromkeys(functions) if f not in _skip]

    return {
        'classes':       list(dict.fromkeys(classes)),
        'structs':       list(dict.fromkeys(structs)),
        'functions':     functions[:50],
        'comments':      block_comments[:20],
        'line_comments': line_comments[:30],
    }


def _to_markdown(rel_path: str, info: dict) -> str:
    """将提取的信息序列化为 Markdown"""
    lines = [f"# {rel_path}\n"]

    if info['classes']:
        lines.append("## 类定义\n")
        for c in info['classes']:
            lines.append(f"- `{c}`")
        lines.append("")

    if info['structs']:
        lines.append("## 结构体\n")
        for s in info['structs']:
            lines.append(f"- `{s}`")
        lines.append("")

    if info['functions']:
        lines.append("## 函数\n")
        for f in info['functions']:
            lines.append(f"- `{f}`")
        lines.append("")

    if info['comments']:
        lines.append("## 文档注释\n")
        for c in info['comments']:
            short = c.replace('\n', ' ').strip()[:300]
            lines.append(f"> {short}\n")

    return '\n'.join(lines)


class CppIndexer:
    """C++ 源码增量索引器"""

    def __init__(self, source_dir: str, output_dir: str, cache_file: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.cache_file = Path(cache_file)
        self.cache: dict = self._load_cache()
        self.stats = {'scanned': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {}

    def _save_cache(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(
            json.dumps(self.cache, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def _output_path(self, cpp_file: Path) -> Path:
        rel = cpp_file.relative_to(self.source_dir)
        stem = str(rel).replace(os.sep, '_').replace('/', '_')
        return self.output_dir / f"{stem}.md"

    def index_file(self, cpp_file: Path) -> bool:
        """索引单个文件，返回是否有更新"""
        mtime = str(cpp_file.stat().st_mtime)
        cache_key = str(cpp_file)

        if self.cache.get(cache_key) == mtime:
            self.stats['skipped'] += 1
            return False

        try:
            content = cpp_file.read_text(encoding='utf-8-sig', errors='replace')
            info = _extract_info(content)
            md = _to_markdown(str(cpp_file.relative_to(self.source_dir)), info)

            out = self._output_path(cpp_file)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md, encoding='utf-8')

            self.cache[cache_key] = mtime
            self.stats['updated'] += 1
            return True

        except Exception as e:
            print(f"  ❌ {cpp_file.name}: {e}")
            self.stats['errors'] += 1
            return False

    def run(self, extensions: tuple = ('.h', '.cpp')):
        """扫描并增量更新索引"""
        print(f"\n🔍 扫描 C++ 源码：{self.source_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        files = [
            f for f in self.source_dir.rglob('*')
            if f.suffix in extensions
            and f.is_file()
            and 'Intermediate' not in f.parts
            and 'Binaries' not in f.parts
        ]
        self.stats['scanned'] = len(files)
        print(f"   找到 {len(files)} 个文件")

        for f in files:
            self.index_file(f)

        self._save_cache()
        print(f"   ✅ 更新 {self.stats['updated']} 个 | "
              f"跳过 {self.stats['skipped']} 个 | "
              f"错误 {self.stats['errors']} 个")
        return self.stats


def main():
    import argparse
    import yaml
    parser = argparse.ArgumentParser(description='C++ 源码索引器')
    parser.add_argument('--config', default='../config/settings.yaml')
    args = parser.parse_args()

    config_path = Path(args.config)
    if config_path.exists():
        cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
        pi = cfg.get('private_index', {})
        source_dir = pi.get('project_source_path', '.')
        output_dir = str(Path(args.config).parent.parent / pi.get('cpp_output_dir', '../docs/converted/cpp_source'))
        cache_file = str(Path(args.config).parent.parent / pi.get('cache_file', '../docs/converted/.index_cache.json'))
    else:
        source_dir = '.'
        output_dir = '../docs/converted/cpp_source'
        cache_file = '../docs/converted/.index_cache.json'

    indexer = CppIndexer(source_dir, output_dir, cache_file)
    indexer.run()


if __name__ == '__main__':
    main()