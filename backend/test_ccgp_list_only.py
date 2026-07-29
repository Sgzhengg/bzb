"""
测试ccgp适配器的列表页采集功能（跳过详情页）
"""
import sys, os
import logging
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters.ccgp_adapter import CcgpAdapter
from bs4 import BeautifulSoup
import httpx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_list_parsing():
    """测试列表页解析功能"""
    print("=" * 70)
    print("测试 ccgp 适配器 - 列表页采集功能")
    print("=" * 70)

    adapter = CcgpAdapter({'max_pages': 1})

    # 测试不同的公告类型
    test_cases = [
        ("中央公开招标", "https://www.ccgp.gov.cn/cggg/zygg/gkzb/index.htm"),
        ("中央竞争性磋商", "https://www.ccgp.gov.cn/cggg/zygg/jzxcs/index.htm"),
        ("地方公开招标", "https://www.ccgp.gov.cn/cggg/dfgg/gkzb/index.htm"),
    ]

    results = {}

    for name, url in test_cases:
        print(f"\n{'=' * 70}")
        print(f"测试: {name}")
        print(f"URL: {url}")
        print(f"{'=' * 70}")

        try:
            # 获取列表页
            html = adapter._fetch_list_page(url)
            if not html:
                print(f"[FAIL] 获取列表页失败")
                results[name] = {"success": False, "error": "获取列表页失败"}
                continue

            print(f"[OK] 列表页获取成功 (HTML长度: {len(html)} 字符)")

            # 解析列表页（传入list_url以正确处理相对路径）
            items = adapter.parse_list(html, list_url=url)

            print(f"[OK] 解析到 {len(items)} 条公告")

            # 显示前5条
            print(f"\n前5条公告:")
            for i, item in enumerate(items[:5]):
                title = item.get('title', 'N/A')
                url = item.get('url', 'N/A')
                date = item.get('date', 'N/A')
                print(f"  [{i+1}] {title[:60]}")
                print(f"       日期: {date}")
                print(f"       链接: {url[:80]}")

            # 检查URL格式是否正确
            if items:
                first_url = items[0].get('url', '')
                if first_url.startswith('https://www.ccgp.gov.cn'):
                    print(f"\n[OK] URL格式正确（使用列表页作为基准）")
                else:
                    print(f"\n[WARN] URL格式可能有问题: {first_url}")

            results[name] = {
                "success": True,
                "count": len(items),
                "sample": items[0] if items else None
            }

        except Exception as e:
            print(f"[FAIL] 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results[name] = {"success": False, "error": str(e)}

    # 汇总结果
    print(f"\n{'=' * 70}")
    print("测试结果汇总")
    print(f"{'=' * 70}")

    for name, result in results.items():
        if result.get("success"):
            count = result.get("count", 0)
            print(f"[OK] {name}: 成功解析 {count} 条")
        else:
            error = result.get("error", "未知错误")
            print(f"[FAIL] {name}: 失败 ({error})")

    return results


def test_multiple_pages():
    """测试多页采集"""
    print(f"\n{'=' * 70}")
    print("测试多页采集功能")
    print(f"{'=' * 70}")

    adapter = CcgpAdapter({'max_pages': 3})

    # 测试中央公开招标的前3页
    base_url = "https://www.ccgp.gov.cn/cggg/zygg/gkzb/index.htm"

    print(f"\n采集中央公开招标前3页...")

    all_items = []
    for page in range(1, 4):
        if page == 1:
            url = base_url
        else:
            url = f"https://www.ccgp.gov.cn/cggg/zygg/gkzb/index_{page}.htm"

        print(f"\n[第{page}页] 获取: {url}")

        try:
            html = adapter._fetch_list_page(url)
            if html:
                items = adapter.parse_list(html, list_url=url)
                print(f"  解析到 {len(items)} 条")
                all_items.extend(items)
            else:
                print(f"  获取失败")
                break
        except Exception as e:
            print(f"  错误: {e}")
            break

    print(f"\n[OK] 总共采集到 {len(all_items)} 条公告")

    # 检查是否有重复
    titles = [item.get('title', '') for item in all_items]
    unique_titles = len(set(titles))
    print(f"[OK] 去重后: {unique_titles} 条 (重复率: {(len(titles)-unique_titles)/len(titles)*100:.1f}%)")

    return all_items


def test_ad_filtering():
    """测试广告类关键词过滤"""
    print(f"\n{'=' * 70}")
    print("测试广告类关键词过滤")
    print(f"{'=' * 70}")

    from app.services.keyword_filter import filter_advertisement_projects

    adapter = CcgpAdapter({'max_pages': 1})

    # 获取一页数据
    url = "https://www.ccgp.gov.cn/cggg/zygg/gkzb/index.htm"
    html = adapter._fetch_list_page(url)
    items = adapter.parse_list(html, list_url=url)

    print(f"\n原始采集: {len(items)} 条公告")

    # 测试关键词过滤
    ad_count = 0
    ad_items = []

    for item in items:
        title = item.get('title', '')
        result = filter_advertisement_projects(title)

        if result.get('is_ad'):
            ad_count += 1
            ad_items.append({
                'title': title,
                'category': result.get('category', ''),
                'matched_keywords': result.get('matched_keywords', [])
            })

    print(f"[OK] 广告类: {ad_count} 条")
    print(f"[SKIP]  非广告类: {len(items) - ad_count} 条")

    if ad_items:
        print(f"\n广告类项目示例:")
        for i, item in enumerate(ad_items[:5]):
            print(f"  [{i+1}] {item['title'][:60]}")
            print(f"       分类: {item['category']}")
            print(f"       关键词: {', '.join(item['matched_keywords'][:3])}")

    return ad_items


if __name__ == "__main__":
    print("开始测试 ccgp 列表页采集功能...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试1: 列表页解析
    list_results = test_list_parsing()

    # 测试2: 多页采集
    multi_results = test_multiple_pages()

    # 测试3: 广告过滤
    ad_results = test_ad_filtering()

    print(f"\n{'=' * 70}")
    print("测试完成！")
    print(f"{'=' * 70}")
