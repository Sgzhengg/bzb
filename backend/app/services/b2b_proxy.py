"""
b2b.10086.cn 公告原文代理服务

b2b.10086.cn 是 SPA 架构，公告详情没有独立 URL。
本模块通过 b2b 的后端 API 直接获取公告原文内容和可分享的链接。
"""

import logging
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

B2B_API_BASE = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish"
B2B_SEARCH_URL = "https://b2b.10086.cn/b2b/main/listVendorNotice.html"
TIMEOUT = 15.0

# b2b API 返回的 publishType 映射
PUBLISH_TYPE_MAP = {
    "PROCUREMENT": "招采公告",
    "PURCHASE_SERVICE": "采购服务公告",
    "VENDOR": "供应商公告",
}


async def search_announcement(
    title: str,
    publish_type: str = "PROCUREMENT",
    page_size: int = 5,
) -> List[Dict[str, Any]]:
    """
    在 b2b.10086.cn 搜索公告。

    Args:
        title: 公告标题关键词
        publish_type: 公告类型 (PROCUREMENT/PURCHASE_SERVICE/VENDOR)
        page_size: 每页数量

    Returns:
        匹配的公告列表
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{B2B_API_BASE}/queryList",
                json={
                    "name": title,
                    "publishType": publish_type,
                    "size": page_size,
                    "current": 1,
                    "sfactApplColumn5": "PC",
                },
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                logger.warning(f"b2b API error: {data.get('msg')}")
                return []

            items = data.get("data", {}).get("content", [])
            logger.info(f"b2b search: '{title}' -> {len(items)} results")
            return items

    except Exception as e:
        logger.error(f"b2b search failed for '{title}': {e}")
        return []


def build_search_url(title: str, publish_type: str = "PROCUREMENT") -> str:
    """
    构建 b2b.10086.cn 搜索页 URL。

    由于 b2b 是 SPA 且无独立详情页 URL，我们构建搜索页链接，
    用户点击后可以在搜索框中看到预填的关键词，手动点击搜索即可。

    Args:
        title: 搜索关键词（截取前30字符）
        publish_type: 公告类型

    Returns:
        b2b 搜索页 URL
    """
    # 截取关键词（太长的标题可能导致搜索无结果）
    keyword = title[:30]
    # URL 编码
    import urllib.parse
    encoded = urllib.parse.quote(keyword, safe="")
    
    if publish_type == "VENDOR":
        return f"{B2B_SEARCH_URL}?noticeType=2#/supplierBulletin?name={encoded}"
    else:
        return f"{B2B_SEARCH_URL}?noticeType=2#/biddingProcurementBulletin?name={encoded}"


def find_best_match(items: List[Dict], title: str) -> Optional[Dict]:
    """
    从搜索结果中找到最匹配的公告。

    Args:
        items: 搜索结果列表
        title: 原始标题

    Returns:
        最佳匹配项，或 None
    """
    if not items:
        return None

    # 简单匹配：找标题最相似的
    best = None
    best_score = 0

    for item in items:
        item_name = item.get("name", "")
        # 计算匹配字符数
        score = sum(1 for c in title if c in item_name)
        if score > best_score:
            best_score = score
            best = item

    # 至少匹配 50% 的字符
    if best and best_score >= len(title) * 0.3:
        return best
    return items[0] if items else None


def format_announcement_detail(item: Dict) -> Dict[str, Any]:
    """
    将 b2b API 返回的原始数据格式化为前端可用的结构。

    Args:
        item: b2b API 返回的公告条目

    Returns:
        格式化后的公告详情
    """
    return {
        "title": item.get("name", ""),
        "publish_date": item.get("publishDate", ""),
        "publish_type": PUBLISH_TYPE_MAP.get(item.get("publishType", ""), item.get("publishType_dictText", "")),
        "publish_one_type": item.get("publishOneType_dictText", ""),
        "company": item.get("companyTypeName", ""),
        "deadline": item.get("tenderSaleDeadline", ""),
        "bid_date": item.get("backDate", ""),
        "notice_content": item.get("noticeContent"),
        "uuid": item.get("uuid", ""),
        "b2b_id": item.get("id", ""),
        "source_url": build_search_url(item.get("name", "")),
    }
