"""
LLM 驱动的招标公告分类器

在关键词匹配无法确定时，使用 DeepSeek 对公告全文进行语义理解，
判断是否属于广告营销类招标项目。

设计原则:
  - 仅作为关键词过滤的兜底，不替代关键词匹配
  - 同步接口（内部用 asyncio.run 桥接），适配现有采集流程
  - 超时 15s，失败时返回非广告类（宁可漏判也不错判）
"""

import json
import logging
import re
from typing import Dict, Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# 广告赛道定义（用于 LLM prompt）
AD_CATEGORIES = """
- 广告创意设计：广告设计、VI设计、品牌视觉、全案策划、平面设计
- 物料制作印刷：宣传物料、喷绘写真、标识标牌、门头招牌、印刷品
- 活动策划执行：活动策划、路演、发布会、展会、客户活动、校园营销
- 品牌宣传传播：品牌推广、整合营销、公关传播、媒体宣传、企业文化建设
- 视频内容制作：宣传片拍摄、视频制作、动画制作、微电影
- 新媒体运营：公众号运营、抖音运营、直播运营、H5制作
- 媒介资源投放：户外广告、社区广告、公交广告、信息流广告
- 渠道营销推广：网格营销、门店推广、地推、商圈推广
"""

SYSTEM_PROMPT = f"""你是一名广东移动招标项目分类专家。你的任务是判断招标公告是否属于"广告营销类"。

广告营销类包括以下赛道：
{AD_CATEGORIES}

不属于广告营销类的项目示例（应判定为非广告类）：
- 基站建设、光缆铺设、机房设备、铁塔维护
- 软件开发、系统集成、IT 运维
- 物业管理、食堂承包、保安保洁
- 空调消防、电力电源、综合布线
- 通信设备采购、网络技术支撑

请严格按以下 JSON 格式回复，不要包含其他内容：
{{"is_ad": true或false, "category": "赛道名称或空字符串", "reason": "一句话判断理由(不超过30字)"}}"""


def _build_user_prompt(title: str, content: str) -> str:
    """构建用户提示词，截取公告关键内容。"""
    # 截取前 3000 字符，足够 LLM 理解项目性质
    body = content[:3000] if content else ""
    return f"""请判断以下招标公告是否属于广告营销类：

【项目名称】
{title}

【公告正文】
{body}"""


def _parse_llm_response(text: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON，容错处理。"""
    # 尝试直接解析
    try:
        data = json.loads(text)
        return {
            "is_ad": bool(data.get("is_ad", False)),
            "category": str(data.get("category", "")),
            "reason": str(data.get("reason", ""))[:50],
        }
    except json.JSONDecodeError:
        pass

    # 尝试从文本中提取 JSON
    m = re.search(r'\{[^{}]*"is_ad"[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            return {
                "is_ad": bool(data.get("is_ad", False)),
                "category": str(data.get("category", "")),
                "reason": str(data.get("reason", ""))[:50],
            }
        except json.JSONDecodeError:
            pass

    # 最终回退：关键词兜底
    logger.warning(f"LLM 响应无法解析为 JSON，回退: {text[:100]}")
    return {"is_ad": False, "category": "", "reason": "LLM响应解析失败"}


def classify_by_llm(title: str, content: str = "") -> Dict[str, Any]:
    """
    使用 LLM 对公告进行广告类判定（同步接口）。

    Args:
        title: 公告标题
        content: 公告正文（original_content）

    Returns:
        {"is_ad": bool, "category": str, "reason": str}
    """
    if not settings.LLM_API_KEY:
        logger.debug("LLM API Key 未配置，跳过分类")
        return {"is_ad": False, "category": "", "reason": "LLM未配置"}

    if not settings.LLM_ENABLED:
        logger.debug("LLM 已禁用 (BZB_LLM_ENABLED=false)")
        return {"is_ad": False, "category": "", "reason": "LLM已禁用"}

    import asyncio

    async def _call():
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{settings.LLM_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": _build_user_prompt(title, content)},
                        ],
                        "temperature": 0.1,  # 低温度确保稳定输出
                        "max_tokens": 200,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM 分类调用失败: {e}")
            return None

    try:
        result_text = asyncio.run(_call())
    except RuntimeError:
        # 可能已在事件循环中
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            result_text = loop.run_until_complete(_call())
        except Exception as e:
            logger.warning(f"LLM 分类异步调用失败: {e}")
            return {"is_ad": False, "category": "", "reason": f"调用异常: {str(e)[:30]}"}
    except Exception as e:
        logger.warning(f"LLM 分类异常: {e}")
        return {"is_ad": False, "category": "", "reason": f"异常: {str(e)[:30]}"}

    if not result_text:
        return {"is_ad": False, "category": "", "reason": "LLM无响应"}

    result = _parse_llm_response(result_text)
    logger.info(
        f"LLM分类: is_ad={result['is_ad']}, "
        f"category={result['category']}, "
        f"reason={result['reason']}"
    )
    return result
