"""
钉钉机器人消息推送服务

配置：在 .env 中设置 BZB_DINGTALK_WEBHOOK_URL
用法：
    from app.services.notification import notify_collection_done
    await notify_collection_done("公告", 12, "广东")
"""

import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _send_dingtalk(title: str, text: str):
    """发送 Markdown 消息到钉钉机器人。"""
    if not settings.DINGTALK_WEBHOOK_URL:
        return

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": text,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.DINGTALK_WEBHOOK_URL, json=payload)
            if resp.status_code == 200:
                logger.info(f"📲 钉钉通知已发送: {title}")
            else:
                logger.warning(f"钉钉通知失败: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"钉钉通知异常: {e}")


async def notify_collection_done(kind: str, count: int, province: str = ""):
    """
    采集完成通知。

    Args:
        kind: "公告" 或 "中标结果"
        count: 新增数量
        province: 采集省份（空=全国）
    """
    if count <= 0:
        return

    location = province or "全国"
    title = f"📋 新{kind}采集完成"

    text = (
        f"## 📋 标中宝 采集完成\n\n"
        f"- **类型**：{kind}\n"
        f"- **地区**：{location}\n"
        f"- **新增**：{count} 条\n\n"
        f"> 请登录系统查看详情：[标中宝]({settings.SITE_URL})"
    )

    await _send_dingtalk(title, text)
