#!/usr/bin/env python3
"""
资产元数据索引器
调用 UnrealAgent list_assets / get_asset_info 工具，
把资产元数据序列化为可检索的 Markdown 文档。
需要 UE 编辑器正在运行且 UnrealAgent Plugin 已加载。
"""

import asyncio
import json
from pathlib import Path


async def _fetch_assets(host: str = "127.0.0.1", port: int = 55557) -> list:
    """通过 TCP 向 UnrealAgent 拉取资产列表"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from unreal_agent_mcp.connection import UnrealConnection

    conn = UnrealConnection(host=host, port=port)
    try:
        result = await conn.send_request("list_assets", {
            "include_path": True,
            "max_results": 2000,
        })
        return result.get("assets", []) if isinstance(result, dict) else []
    except Exception as e:
        print(f"  ❌ 连接 UnrealAgent 失败：{e}")
        print("     请确认 UE Editor 正在运行且 UnrealAgent Plugin 已加载")
        return []
    finally:
        await conn.disconnect()


def _asset_to_markdown(asset: dict) -> str:
    """将单个资产元数据序列化为 Markdown"""
    name      = asset.get("name", "Unknown")
    cls       = asset.get("class", "")
    path      = asset.get("path", "")
    package   = asset.get("package", "")

    lines = [f"# {name}\n"]
    if cls:
        lines.append(f"**类型**: `{cls}`\n")
    if path:
        lines.append(f"**路径**: `{path}`\n")
    if package:
        lines.append(f"**包名**: `{package}`\n")

    # 其余字段
    extra = {k: v for k, v in asset.items()
             if k not in ("name", "class", "path", "package")}
    if extra:
        lines.append("\n## 属性\n")
        for k, v in extra.items():
            lines.append(f"- **{k}**: {v}")

    return '\n'.join(lines)


class AssetIndexer:
    """资产元数据索引器"""

    def __init__(self, output_dir: str,
                 host: str = "127.0.0.1", port: int = 55557):
        self.output_dir = Path(output_dir)
        self.host = host
        self.port = port
        self.stats = {'fetched': 0, 'written': 0, 'errors': 0}

    def run(self):
        """同步入口，内部用 asyncio 跑"""
        print(f"\n🎮 连接 UnrealAgent（{self.host}:{self.port}）拉取资产列表...")
        assets = asyncio.run(_fetch_assets(self.host, self.port))

        if not assets:
            print("   ⚠️  未获取到任何资产，跳过索引构建")
            return self.stats

        self.stats['fetched'] = len(assets)
        print(f"   获取到 {len(assets)} 个资产，开始写入索引...")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 按资产类型分组写入，方便检索
        by_class: dict[str, list] = {}
        for asset in assets:
            cls = asset.get("class", "Unknown")
            by_class.setdefault(cls, []).append(asset)

        for cls, items in by_class.items():
            # 每个类型生成一个汇总 md
            safe_cls = cls.replace('/', '_').replace('\\', '_')
            out_path = self.output_dir / f"assets_{safe_cls}.md"
            try:
                lines = [f"# {cls} 资产列表（{len(items)} 个）\n"]
                for item in items:
                    name = item.get("name", "")
                    path = item.get("path", "")
                    lines.append(f"- `{name}` — `{path}`")
                out_path.write_text('\n'.join(lines), encoding='utf-8')
                self.stats['written'] += 1
            except Exception as e:
                print(f"  ❌ 写入 {out_path.name} 失败：{e}")
                self.stats['errors'] += 1

        print(f"   ✅ 写入 {self.stats['written']} 个分类文件 | "
              f"错误 {self.stats['errors']} 个")
        return self.stats


def main():
    import argparse, yaml
    parser = argparse.ArgumentParser(description='资产元数据索引器')
    parser.add_argument('--config', default='../config/settings.yaml')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=55557)
    args = parser.parse_args()

    config_path = Path(args.config)
    if config_path.exists():
        cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
        pi = cfg.get('private_index', {})
        output_dir = str(
            Path(args.config).parent.parent /
            pi.get('assets_output_dir', '../docs/converted/assets')
        )
    else:
        output_dir = '../docs/converted/assets'

    indexer = AssetIndexer(output_dir, host=args.host, port=args.port)
    indexer.run()


if __name__ == '__main__':
    main()