import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api.v1.awards import _import_to_db

async def test():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    adapter = "all"
    province = ""

    print(f"测试导入: adapter={adapter}, province={province or '全国'}")
    print(f"backend_dir: {backend_dir}")

    # 检查 JSON 文件
    import json
    json_path = os.path.join(backend_dir, "output", f"winning_results_{adapter}_quanguo.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"JSON 文件存在: {json_path}")
        print(f"total_items: {data.get('total_items')}")

        # 检查 items 结构
        adapters = data.get("adapters", [])
        if adapters:
            items = adapters[0].get("items", [])
            print(f"items 数量: {len(items)}")
            if items:
                print(f"第一条记录:")
                print(f"  title: {items[0].get('title', '')[:50]}...")
                print(f"  winner_name: {items[0].get('winner_name', '')}")
                print(f"  source_url: {items[0].get('source_url', '')[:60]}...")

                # 检查是否有重复的 source_url
                urls = {}
                for i, item in enumerate(items[:20]):
                    url = item.get('source_url', '')
                    if url:
                        urls.setdefault(url, []).append(i)
                dup_urls = {k: v for k, v in urls.items() if len(v) > 1}
                if dup_urls:
                    print(f"\n发现重复的 source_url（前20条）:")
                    for url, indices in list(dup_urls.items())[:3]:
                        print(f"  {url[:50]}... 出现 {len(indices)} 次")
    else:
        print(f"JSON 文件不存在: {json_path}")
        return

    # 调用导入
    print("\n开始导入...")
    imported = await _import_to_db(backend_dir, adapter, province)
    print(f"\n导入完成: {imported} 条")

if __name__ == "__main__":
    asyncio.run(test())
