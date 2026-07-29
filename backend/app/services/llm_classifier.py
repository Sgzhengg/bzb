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
- 运营商: 广告创意设计/物料制作印刷/活动策划执行/品牌宣传传播/视频内容制作/新媒体运营/媒介资源投放/渠道营销推广/通信工程建设/ICT系统集成/设备采购/网络维护代维/行政物业
- 银行: IT设备采购/软件开发集成/网络安全/数据中心建设/网点装修/营销宣传/咨询服务
- 政府: 信息化建设/设备采购/工程建设/物业服务/咨询服务
- 保险: IT系统建设/宣传推广/咨询服务
- 能源: 设备采购/工程建设/IT系统/勘察设计
"""

SYSTEM_PROMPT = f"""你是一名招标项目分类专家。请对以下招标公告进行行业和类别判定。

各行业下的业务类别：
{AD_CATEGORIES}

请严格按以下 JSON 格式回复：
{{"industry_type": "行业名(运营商/银行/政府/保险/能源/其他)", "category": "业务类别", "reason": "判断理由(不超过30字)"}}"""


def _build_user_prompt(title: str, content: str) -> str:
    """构建用户提示词。"""
    body = content[:3000] if content else ""
    return f"""请对以下招标公告进行行业和类别判定：

【项目名称】
{title}

【公告正文】
{body}"""


def _parse_llm_response(text: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON，容错处理。"""
    try:
        data = json.loads(text)
        return {
            "industry_type": str(data.get("industry_type", "其他")),
            "category": str(data.get("category", "")),
            "reason": str(data.get("reason", ""))[:50],
            "is_ad": True,  # V3: 所有通过LLM判定的都是有效项目
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
    model_config = {"extra": "allow"}  # 允许LLM返回额外字段（如is_advertising），避免校验失败

    is_ad: bool = Field(default=False, description="是否属于广告营销类招标项目")
    is_advertising: Optional[bool] = Field(default=None, description="is_ad的别名兼容")
    category: Optional[str] = Field(default="", description="广告赛道: 广告创意设计/物料制作印刷/活动策划执行/品牌宣传传播/视频内容制作/新媒体运营/媒介资源投放/渠道营销推广，非广告则为空字符串")
    reason: Optional[str] = Field(default="", description="判断理由，30字以内")

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

    def model_post_init(self, __context):
        """兼容 LLM 返回 is_advertising 而非 is_ad 的情况"""
        if not self.is_ad and self.is_advertising is True:
            object.__setattr__(self, "is_ad", True)


UNIFIED_SYSTEM_PROMPT = """你是一名中国移动招标项目分析专家。请完成两项任务：

任务1 — 判断是否属于广告营销类：
- 广告营销类包括：广告创意设计、物料制作印刷、活动策划执行、品牌宣传传播、
  视频内容制作、新媒体运营、媒介资源投放、渠道营销推广
- 不属于广告营销类的示例：基站建设、光缆铺设、软件开发、系统集成、
  物业管理、食堂承包、保安保洁、通信设备采购、网络技术支撑、工程设计勘察

任务2 — 如果属于广告营销类，提取以下字段；如果不属于，数值字段返回 null。
必须使用以下精确字段名，不要修改或变体：
- "is_ad": true/false —— 是否广告营销类
- "category": "赛道名" —— 广告赛道分类
- "reason": "判断理由" —— 30字以内
- "budget": 数字或null —— 预算金额（万元，原文以"元"为单位请除以10000）
- "registration_fee": 数字或null —— 报名费/标书费（元）
- "deposit": 数字或null —— 投标保证金（万元）
- "deadline": "YYYY-MM-DD"或null —— 报名截止日期。对应"报名截止时间/日期"、"购买标书截止时间"。
  注意：询比/比选中只有单独写明的"报名截止时间"才映射到deadline，不要将"应答截止时间"映射到deadline
- "bid_date": "YYYY-MM-DD"或null —— 投标/开标日期。对应以下任一表述（按优先级）：
  1. 开标时间/开标日期（公开招标的投标日期即开标日）
  2. 应答截止时间/应答截止日期（询比/比选的投标日期）
  3. 递交截止时间/递交截止日期（文件递交截止即投标截止）
  4. 报价截止时间（询价的投标日期）
  5. 响应截止时间（竞争性谈判的投标日期）
  6. 申请截止时间
  注意：候选人公示中的"公示截止时间"不是投标日期，遇到此类请返回 null
- "procurement_method": "方式名"或null —— 采购方式（公开招标/公开询比/竞争性谈判/单一来源/邀请招标/询价/比选）

只回复 JSON，不包含其他内容。"""


def _parse_unified_response(text: str) -> Dict[str, Any]:
    """使用 Pydantic 解析 LLM 响应，自动验证和类型转换。"""
    def _extract_json(raw: str) -> Optional[dict]:
        # 直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # 提取 JSON 块（兼容 is_ad 和 is_advertising 两种写法）
        m = re.search(r'\{[^{}]*"is_ad(?:vertising)?"[^{}]*\}', raw, re.DOTALL)
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

    # 兼容 is_advertising → is_ad
    if "is_advertising" in data and "is_ad" not in data:
        data["is_ad"] = data.pop("is_advertising")

    try:
        extraction = AnnouncementExtraction.model_validate(data)
        result = extraction.model_dump()
        # 补全旧代码兼容字段
        result.setdefault("budget_text", data.get("budget_text", ""))
        result.setdefault("confidence", data.get("confidence", "low"))
        return result
    except Exception as e:
        logger.warning(f"Pydantic校验失败，回退手动解析: {e}")
        # 回退：手动提取已知字段（同时兼容 is_advertising）
        is_ad_val = data.get("is_ad") or data.get("is_advertising")
        return {
            "is_ad": bool(is_ad_val),
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
