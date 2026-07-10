"""
LLM 驱动的预算金额提取器

当正则表达式无法从公告中提取预算时，使用 DeepSeek 对全文进行语义理解，
精准提取预算金额、报名费、保证金等财务信息。

设计原则:
  - 仅作为正则提取的兜底
  - 同步接口，适配现有采集流程
  - 返回结构化 JSON，包含置信度
"""

import json
import logging
import re
from typing import Dict, Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一名招标项目财务信息提取专家。请从公告正文中提取以下金额（单位：万元）：

注意:
- 如果原文以"元"为单位，请转换为万元（除以10000）
- 如果某个字段在原文中未提及，返回 null
- "预算金额"可能是"采购预算""项目预算""控制价""最高限价"等
- "报名费"可能是"标书费""文件费""招标文件售价"
- "保证金"可能是"投标保证金""磋商保证金"

只回复 JSON，不包含其他内容：
{"budget": 数字或null, "registration_fee": 数字或null, "deposit": 数字或null, "budget_text": "原文中预算相关的原始文本片段", "confidence": "high/medium/low"}"""


def _build_user_prompt(title: str, content: str) -> str:
    """构建用户提示词。"""
    body = (content or "")[:4000]
    return f"""请从以下公告中提取财务信息：

【项目名称】
{title}

【公告正文】
{body}"""


def _parse_response(text: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON。"""
    try:
        data = json.loads(text)
        return {
            "budget": _safe_float(data.get("budget")),
            "registration_fee": _safe_float(data.get("registration_fee")),
            "deposit": _safe_float(data.get("deposit")),
            "budget_text": str(data.get("budget_text", ""))[:200],
            "confidence": str(data.get("confidence", "low")),
        }
    except json.JSONDecodeError:
        pass

    m = re.search(r'\{[^{}]*"budget"[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            return {
                "budget": _safe_float(data.get("budget")),
                "registration_fee": _safe_float(data.get("registration_fee")),
                "deposit": _safe_float(data.get("deposit")),
                "budget_text": str(data.get("budget_text", ""))[:200],
                "confidence": str(data.get("confidence", "low")),
            }
        except json.JSONDecodeError:
            pass

    logger.warning(f"LLM 预算响应解析失败: {text[:100]}")
    return {"budget": None, "registration_fee": None, "deposit": None, "budget_text": "", "confidence": "low"}


def _safe_float(val) -> Optional[float]:
    """安全转换为 float。"""
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return None


def extract_budget_by_llm(title: str, content: str = "") -> Dict[str, Any]:
    """
    使用 LLM 从公告全文中提取预算等财务信息。

    Args:
        title: 公告标题
        content: 公告正文（original_content）

    Returns:
        {"budget": float|None, "registration_fee": float|None,
         "deposit": float|None, "budget_text": str, "confidence": str}
    """
    if not settings.LLM_API_KEY or not settings.LLM_ENABLED:
        return {"budget": None, "registration_fee": None, "deposit": None, "budget_text": "", "confidence": "low"}

    if not content or len(content.strip()) < 50:
        logger.debug("公告正文过短或为空，跳过 LLM 预算提取")
        return {"budget": None, "registration_fee": None, "deposit": None, "budget_text": "", "confidence": "low"}

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
                        "temperature": 0.1,
                        "max_tokens": 300,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM 预算提取调用失败: {e}")
            return None

    try:
        result_text = asyncio.run(_call())
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            result_text = loop.run_until_complete(_call())
        except Exception as e:
            logger.warning(f"LLM 预算提取异步异常: {e}")
            return {"budget": None, "registration_fee": None, "deposit": None, "budget_text": "", "confidence": "low"}
    except Exception as e:
        logger.warning(f"LLM 预算提取异常: {e}")
        return {"budget": None, "registration_fee": None, "deposit": None, "budget_text": "", "confidence": "low"}

    if not result_text:
        return {"budget": None, "registration_fee": None, "deposit": None, "budget_text": "", "confidence": "low"}

    result = _parse_response(result_text)
    if result["budget"] is not None:
        logger.info(f"LLM 预算提取成功: {result['budget']}万元 (置信度:{result['confidence']})")
    return result


def extract_budget_hybrid(title: str, content: str = "", existing_budget: Optional[float] = None) -> Dict[str, Any]:
    """
    混合预算提取：正则优先 → LLM 兜底。

    如果 existing_budget 已有值（正则提取成功），直接返回。
    否则尝试用 LLM 从全文提取。
    """
    if existing_budget is not None and existing_budget > 0:
        return {
            "budget": existing_budget,
            "registration_fee": None,
            "deposit": None,
            "budget_text": "",
            "confidence": "regex",
            "extractor": "regex",
        }

    # 尝试正则（复用现有逻辑的简化版）
    if content:
        for pat in [
            r"(?:预算|采购预算|项目预算|预算金额|控制价|最高限价)[：:是为]?\s*[¥￥]?\s*(\d[\d,.]*)\s*万",
            r"(?:预算|采购预算|项目预算|预算金额|控制价|最高限价)[：:是为]?\s*[¥￥]?\s*(\d{4,})\s*元",
        ]:
            m = re.search(pat, content)
            if m:
                val = float(m.group(1).replace(",", ""))
                if "元" in m.group(0) and "万" not in m.group(0):
                    val = val / 10000
                budget = round(val, 2)
                if 0.1 <= budget <= 100000:
                    return {
                        "budget": budget,
                        "registration_fee": None,
                        "deposit": None,
                        "budget_text": m.group(0),
                        "confidence": "high",
                        "extractor": "regex",
                    }

    # 全文正则失败 → LLM 兜底
    llm_result = extract_budget_by_llm(title, content)
    llm_result["extractor"] = "llm"
    return llm_result
