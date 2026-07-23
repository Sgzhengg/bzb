"""
LLM 驱动的招标公告分类与数据提取器

使用 DeepSeek 对公告全文进行语义理解，一次调用完成：
  1. 判断是否属于广告营销类招标项目
  2. 提取「机会列表」所需的全部字段

设计原则:
  - Pydantic Structured Output，消除手写 JSON 解析
  - 同步接口（内部用 asyncio.run 桥接），适配现有采集流程
  - 超时 15s，失败时返回非广告类（宁可漏判也不错判）
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List

import httpx
from pydantic import BaseModel, Field

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


# ============================================================
# 统一 LLM 调用：分类 + 数据提取 合并为一次 API 调用
# 使用 Pydantic Structured Output，消除手写 JSON 解析
# ============================================================

class AnnouncementExtraction(BaseModel):
    """LLM 从公告中提取的完整结构化数据"""
    is_ad: bool = Field(description="是否属于广告营销类招标项目")
    category: str = Field(description="广告赛道: 广告创意设计/物料制作印刷/活动策划执行/品牌宣传传播/视频内容制作/新媒体运营/媒介资源投放/渠道营销推广，非广告则为空字符串")
    reason: str = Field(description="判断理由，30字以内")

    # 财务字段
    budget: Optional[float] = Field(default=None, description="预算金额（万元），原文以元为单位时除以10000")
    registration_fee: Optional[float] = Field(default=None, description="报名费/标书费（元）")
    deposit: Optional[float] = Field(default=None, description="投标保证金（万元）")

    # 日期字段
    deadline: Optional[str] = Field(default=None, description="报名截止日期 YYYY-MM-DD")
    bid_date: Optional[str] = Field(default=None, description="投标/开标日期 YYYY-MM-DD")

    # 其他
    procurement_method: Optional[str] = Field(default=None, description="采购方式: 公开招标/公开询比/竞争性谈判/单一来源/邀请招标/询价/比选")
    budget_text: str = Field(default="", description="原文中预算相关的原始文本片段")
    confidence: str = Field(default="low", description="提取置信度: high/medium/low")


UNIFIED_SYSTEM_PROMPT = """你是一名中国移动招标项目分析专家。请完成两项任务：

任务1 — 判断是否属于广告营销类：
- 广告营销类包括：广告创意设计、物料制作印刷、活动策划执行、品牌宣传传播、
  视频内容制作、新媒体运营、媒介资源投放、渠道营销推广
- 不属于广告营销类的示例：基站建设、光缆铺设、软件开发、系统集成、
  物业管理、食堂承包、保安保洁、通信设备采购、网络技术支撑、工程设计勘察

任务2 — 如果属于广告营销类，提取以下字段；如果不属于，数值字段返回 null：
- budget: 预算金额（万元，原文以"元"为单位请除以10000）
- registration_fee: 报名费/标书费（元）
- deposit: 投标保证金（万元）
- deadline: 报名截止日期（YYYY-MM-DD）。对应"报名截止时间/日期"、"购买标书截止时间"。
  注意：询比/比选中只有单独写明的"报名截止时间"才映射到deadline，不要将"应答截止时间"映射到deadline
- bid_date: 投标/开标日期（YYYY-MM-DD）。对应以下任一表述（按优先级）：
  1. 开标时间/开标日期（公开招标的投标日期即开标日）
  2. 应答截止时间/应答截止日期（询比/比选的投标日期）
  3. 递交截止时间/递交截止日期（文件递交截止即投标截止）
  4. 报价截止时间（询价的投标日期）
  5. 响应截止时间（竞争性谈判的投标日期）
  6. 申请截止时间
  注意：候选人公示中的"公示截止时间"不是投标日期，遇到此类请返回 null
- procurement_method: 采购方式（公开招标/公开询比/竞争性谈判/单一来源/邀请招标/询价/比选）

只回复 JSON，不包含其他内容。"""


def _parse_unified_response(text: str) -> Dict[str, Any]:
    """使用 Pydantic 解析 LLM 响应，自动验证和类型转换。"""
    def _extract_json(raw: str) -> Optional[dict]:
        # 直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # 提取 JSON 块
        m = re.search(r'\{[^{}]*"is_ad"[^{}]*\}', raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return None

    data = _extract_json(text)
    if not data:
        logger.warning(f"LLM响应无法解析: {text[:100]}")
        return _default_unified_result()

    try:
        extraction = AnnouncementExtraction.model_validate(data)
        result = extraction.model_dump()
        # 补全旧代码兼容字段
        result.setdefault("budget_text", data.get("budget_text", ""))
        result.setdefault("confidence", data.get("confidence", "low"))
        return result
    except Exception as e:
        logger.warning(f"Pydantic校验失败，回退手动解析: {e}")
        # 回退：手动提取已知字段
        return {
            "is_ad": bool(data.get("is_ad", False)),
            "category": str(data.get("category", "")),
            "reason": str(data.get("reason", ""))[:50],
            "budget": _safe_number(data.get("budget")),
            "registration_fee": _safe_number(data.get("registration_fee")),
            "deposit": _safe_number(data.get("deposit")),
            "deadline": _safe_date_str(data.get("deadline")),
            "bid_date": _safe_date_str(data.get("bid_date")),
            "procurement_method": str(data.get("procurement_method", "") or ""),
            "budget_text": str(data.get("budget_text", ""))[:200],
            "confidence": str(data.get("confidence", "low")),
        }


def _safe_number(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return None


def _safe_date_str(val) -> Optional[str]:
    if not val or not isinstance(val, str):
        return None
    m = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val.strip())
    return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}" if m else None


def _default_unified_result() -> Dict[str, Any]:
    return {
        "is_ad": False, "category": "", "reason": "",
        "budget": None, "registration_fee": None, "deposit": None,
        "deadline": None, "bid_date": None, "procurement_method": "",
        "budget_text": "", "confidence": "low",
    }


def classify_and_extract(title: str, content: str = "") -> Dict[str, Any]:
    """
    统一 LLM 调用：一次 API 完成「判定是否广告」+「提取全部字段」。

    使用 Pydantic Structured Output，自动验证和类型转换。
    """
    if not settings.LLM_API_KEY or not settings.LLM_ENABLED:
        return _default_unified_result()

    if not content or len(content.strip()) < 20:
        logger.debug("公告正文过短，跳过统一LLM调用")
        return _default_unified_result()

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
                            {"role": "system", "content": UNIFIED_SYSTEM_PROMPT},
                            {"role": "user", "content": _build_user_prompt(title, content)},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 500,
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"统一LLM调用失败: {e}")
            return None

    try:
        result_text = asyncio.run(_call())
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            result_text = loop.run_until_complete(_call())
        except Exception as e:
            logger.warning(f"统一LLM异步异常: {e}")
            return _default_unified_result()
    except Exception as e:
        logger.warning(f"统一LLM异常: {e}")
        return _default_unified_result()

    if not result_text:
        return _default_unified_result()

    result = _parse_unified_response(result_text)
    logger.info(
        f"统一LLM: is_ad={result['is_ad']}, "
        f"category={result['category']}, "
        f"budget={result.get('budget')}, "
        f"deadline={result.get('deadline')}"
    )
    return result
