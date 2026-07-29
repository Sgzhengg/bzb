"""
直接测试广东政府广告招标采集（gd_zbtb, gd_ygp, ccgp）
"""
import sys, os, logging, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_gov")

def test_adapter(adapter_name, adapter_class, config):
    """测试单个适配器"""
    logger.info(f"\n{'='*60}")
    logger.info(f"  测试适配器: {adapter_name}")
    logger.info(f"{'='*60}")
    
    try:
        adapter = adapter_class(config)
        logger.info(f"  适配器初始化成功: {adapter.get_source_name()}")
        
        # 只测试第1页列表
        logger.info(f"  正在抓取第1页列表...")
        html = adapter.fetch_list(page=1)
        
        if not html or len(html) < 100:
            logger.warning(f"  ⚠️ 第1页返回内容过短 ({len(html) if html else 0} 字符)")
            return {"adapter": adapter_name, "status": "empty", "items": []}
        
        logger.info(f"  获取到 HTML ({len(html)} 字符), 正在解析...")
        items = adapter.parse_list(html)
        
        logger.info(f"  ✅ 解析到 {len(items)} 条记录")
        for i, item in enumerate(items[:5]):
            logger.info(f"    [{i+1}] {item.get('title', 'N/A')[:60]}")
            logger.info(f"        日期: {item.get('publish_date', 'N/A')}")
            logger.info(f"        链接: {item.get('detail_url', 'N/A')[:80]}")
        
        return {"adapter": adapter_name, "status": "ok", "count": len(items), "items": items}
        
    except Exception as e:
        logger.error(f"  ❌ 适配器 {adapter_name} 测试失败: {e}", exc_info=True)
        return {"adapter": adapter_name, "status": "error", "error": str(e)}


def main():
    results = {}
    
    # 测试 gd_zbtb (广东招标投标监管网)
    try:
        from adapters.gd_zbtb_adapter import GzZbtbAdapter
        config = {
            "search_keyword": "广东移动 广告",
            "max_pages": 1,
            "min_delay": 2.0,
            "max_delay": 4.0,
            "max_retries": 2,
            "timeout": 30,
        }
        results["gd_zbtb"] = test_adapter("gd_zbtb", GzZbtbAdapter, config)
    except Exception as e:
        logger.error(f"导入 gd_zbtb_adapter 失败: {e}")
        results["gd_zbtb"] = {"status": "import_error", "error": str(e)}
    
    # 测试 gd_ygp (广东公共资源交易平台)
    try:
        from adapters.gd_ygp_adapter import GdYgpAdapter
        config = {
            "search_keyword": "广东移动 广告",
            "max_pages": 1,
            "min_delay": 2.0,
            "max_delay": 4.0,
            "max_retries": 2,
            "timeout": 30,
        }
        results["gd_ygp"] = test_adapter("gd_ygp", GdYgpAdapter, config)
    except Exception as e:
        logger.error(f"导入 gd_ygp_adapter 失败: {e}")
        results["gd_ygp"] = {"status": "import_error", "error": str(e)}
    
    # 汇总
    print(f"\n{'='*60}")
    print("  📊 测试汇总")
    print(f"{'='*60}")
    for name, r in results.items():
        status = r.get("status", "unknown")
        count = r.get("count", 0)
        emoji = "✅" if status == "ok" and count > 0 else "⚠️" if status == "ok" else "❌"
        print(f"  {emoji} {name}: status={status}, count={count}")
    
    return results


if __name__ == "__main__":
    main()
