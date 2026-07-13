"""
b2b.10086.cn 公告原文代理服务

b2b.10086.cn 是 SPA 架构，公告详情没有独立 URL。
本模块通过 b2b 的后端 API 直接获取公告原文内容和可分享的链接。
"""

import logging
import ssl
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

B2B_API_BASE = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish"
B2B_SEARCH_URL = "https://b2b.10086.cn/b2b/main/listVendorNotice.html"
TIMEOUT = 15.0


def _get_ssl_context() -> ssl.SSLContext:
    """
    创建兼容 b2b.10086.cn 的 SSL Context。
    b2b 服务器使用旧版 TLS 重协商，Python 3.14+ / OpenSSL 3.x 默认禁用，
    需要启用 SSL_OP_LEGACY_SERVER_CONNECT。
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # SSL_OP_LEGACY_SERVER_CONNECT = 0x4
    ctx.options |= 0x4
    return ctx


# b2b API 返回的 publishType 映射
PUBLISH_TYPE_MAP = {
    "PROCUREMENT": "招采公告",
    "PURCHASE_SERVICE": "采购服务公告",
    "VENDOR": "供应商公告",
}


async def search_announcement(
    title: str,
    publish_type: str = "PROCUREMENT",
    page_size: int = 10,
    page: int = 1,
) -> List[Dict[str, Any]]:
    """
    在 b2b.10086.cn 搜索公告。

    Args:
        title: 公告标题关键词
        publish_type: 公告类型 (PROCUREMENT/PURCHASE_SERVICE/VENDOR)
        page_size: 每页数量
        page: 页码（从1开始）

    Returns:
        匹配的公告列表
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, verify=_get_ssl_context()) as client:
            resp = await client.post(
                f"{B2B_API_BASE}/queryList",
                json={
                    "name": title,
                    "publishType": publish_type,
                    "size": page_size,
                    "current": page,
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

    由于 b2b 是 SPA 且无独立详情页 URL，我们构建搜索页链接。
    使用 searchPage 格式可以直接显示搜索结果。

    Args:
        title: 搜索关键词（截取前30字符）
        publish_type: 公告类型

    Returns:
        b2b 搜索页 URL（可直接显示搜索结果）
    """
    # 截取关键词（太长的标题可能导致搜索无结果）
    keyword = title[:30]
    # URL 编码
    import urllib.parse
    encoded = urllib.parse.quote(keyword, safe="")

    # 使用 searchPage 格式，可以自动显示搜索结果
    # 参考：https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2#/searchPage?value=xxx&noticeType=ALL&current=1
    return f"{B2B_SEARCH_URL}?noticeType=2#/searchPage?value={encoded}&noticeType=ALL&current=1"


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

    # 改进的匹配算法：使用包含关系
    best = None
    best_score = 0

    for item in items:
        item_name = item.get("name", "")
        # 计算匹配度
        # 1. 完全包含标题的核心关键词
        # 2. 计算重叠字符数
        title_clean = title.replace("（", "").replace("）", "").replace("(", "").replace(")", "")
        item_clean = item_name.replace("（", "").replace("）", "").replace("(", "").replace(")", "")

        # 计算交集字符数
        common_chars = set(title_clean) & set(item_clean)
        overlap_ratio = len(common_chars) / max(len(set(title_clean)), 1)

        # 检查是否包含关键关键词
        score = overlap_ratio * 100

        # 如果一个标题完全包含另一个，给予额外加分
        if title_clean in item_name or item_clean in title:
            score += 30

        if score > best_score:
            best_score = score
            best = item

    # 降低匹配阈值：只要有关联就返回
    if best and best_score >= 10:  # 至少有一定关联
        return best

    # 如果有搜索结果，返回第一个（用户可以自己选择）
    return items[0] if items else None


def format_announcement_detail(item: Dict) -> Dict[str, Any]:
    """
    将 b2b API 返回的原始数据格式化为前端可用的结构。

    Args:
        item: b2b API 返回的公告条目

    Returns:
        格式化后的公告详情
    """
    b2b_id = item.get("id", "")
    publish_one_type = item.get("publishOneType", "")
    
    # 根据 publishOneType 构建详情页 URL
    detail_url = _build_detail_url(b2b_id, publish_one_type)
    
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
        "b2b_id": b2b_id,
        "source_url": build_search_url(item.get("name", "")),
        "detail_url": detail_url,
    }


def _build_detail_url(b2b_id: str, publish_one_type: str = "") -> str:
    """
    根据 b2b 公告 ID 和类型构建直达详情页的 URL。
    b2b.10086.cn 是 SPA，详情页通过 hash 路由访问。
    """
    if not b2b_id:
        return ""
    
    # 根据公告类型映射 hash 路由
    route_map = {
        "CANDIDATE_PUBLICITY": "candidatePublicityDetail",
        "PROCUREMENT": "biddingProcurementBulletinDetail",
        "PURCHASE_SERVICE": "purchaseServiceDetail",
        "VENDOR": "vendorNoticeDetail",
    }
    route = route_map.get(publish_one_type, "detailPage")
    
    return f"https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2#/{route}?id={b2b_id}"


async def fetch_announcement_detail(
    b2b_id: str,
    keyword: str = "",
    publish_type: str = "PROCUREMENT",
) -> Optional[Dict[str, Any]]:
    """
    通过 b2b API 获取单条公告的完整详情（含 noticeContent 正文）。

    b2b 的列表接口 queryList 可能不返回完整正文，
    此函数尝试通过 queryById 或重新搜索来获取包含 noticeContent 的详情。

    Args:
        b2b_id: b2b 系统中的公告 ID 或 UUID
        keyword: 搜索关键词（备用）
        publish_type: 公告类型

    Returns:
        包含 notice_content 的详情字典，或 None
    """
    if not b2b_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, verify=_get_ssl_context()) as client:
            # 尝试 queryById 接口
            for id_field in ["id", "uuid"]:
                try:
                    resp = await client.post(
                        f"{B2B_API_BASE}/queryById",
                        json={id_field: b2b_id},
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("code") == 0:
                            detail = data.get("data", {})
                            if detail:
                                logger.info(f"b2b queryById success: {b2b_id}")
                                return format_announcement_detail(detail)
                except Exception:
                    continue

            # 备用方案：扩大搜索范围获取详情
            if keyword:
                items = await search_announcement(keyword, publish_type, page_size=20)
                for item in items:
                    # 查找 noticeContent 不为空的条目
                    if item.get("noticeContent"):
                        logger.info(f"b2b found detail via extended search")
                        return format_announcement_detail(item)

    except Exception as e:
        logger.warning(f"b2b fetch_detail failed for {b2b_id}: {e}")

    return None
