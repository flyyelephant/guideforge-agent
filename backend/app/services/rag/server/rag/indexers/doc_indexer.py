#!/usr/bin/env python3
"""
私有文档索引器
支持导入 .md / .html / .pdf 格式，统一转为 Markdown 后输出
供 SimpleRAGClient 关键词检索使用。
"""

import os
import shutil
from pathlib import Path


def _html_to_md(html_content: str) -> str:
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        return h.handle(html_content)
    except ImportError:
        import re
        return re.sub(r'<[^>]+>', '', html_content)


def _pdf_to_md(pdf_path: str) -> str:
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(pdf_path)
        return text or ""
    except ImportError:
        return f"# {Path(pdf_path).stem}\n\n(需要安装 pdfminer.six 才能提取 PDF 内容)"


class DocIndexer:
    """私有文档增量索引器"""

    SUPPORTED = {'.md', '.html', '.htm', '.pdf'}

    def __init__(self, source_dir: str, output_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.stats = {'scanned': 0, 'copied': 0, 'converted': 0, 'errors': 0}

    def index_file(self, doc_file: Path):
        suffix = doc_file.suffix.lower()
        if suffix not in self.SUPPORTED:
            return

        self.stats['scanned'] += 1
        stem = str(doc_file.relative_to(self.source_dir)).replace(os.sep, '_').replace('/', '_')
        out_path = self.output_dir / f"{stem}.md"

        try:
            if suffix == '.md':
                shutil.copy2(doc_file, out_path)
                self.stats['copied'] += 1

            elif suffix in ('.html', '.htm'):
                content = doc_file.read_text(encoding='utf-8', errors='ignore')
                out_path.write_text(_html_to_md(content), encoding='utf-8')
                self.stats['converted'] += 1

            elif suffix == '.pdf':
                out_path.write_text(_pdf_to_md(str(doc_file)), encoding='utf-8')
                self.stats['converted'] += 1

        except Exception as e:
            print(f"  ❌ {doc_file.name}: {e}")
            self.stats['errors'] += 1

    def run(self):
        print(f"\n📂 扫描私有文档：{self.source_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for f in self.source_dir.rglob('*'):
            if f.is_file() and f.suffix.lower() in self.SUPPORTED:
                self.index_file(f)

        print(f"   ✅ 复制 {self.stats['copied']} 个 | "
              f"转换 {self.stats['converted']} 个 | "
              f"错误 {self.stats['errors']} 个")
        return self.stats


def main():
    import argparse
    import yaml
    parser = argparse.ArgumentParser(description='私有文档索引器')
    parser.add_argument('--config', default='../config/settings.yaml')
    args = parser.parse_args()

    config_path = Path(args.config)
    if config_path.exists():
        cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
        pi = cfg.get('private_index', {})
        source_dir = pi.get('private_docs_path', '.')
        output_dir = str(Path(args.config).parent.parent / pi.get('docs_output_dir', '../docs/converted/private_docs'))
    else:
        source_dir = '.'
        output_dir = '../docs/converted/private_docs'

    indexer = DocIndexer(source_dir, output_dir)
    indexer.run()


if __name__ == '__main__':
    main()