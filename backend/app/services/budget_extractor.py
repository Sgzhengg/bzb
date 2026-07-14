"""
LLM 驱动的公告信息提取器

使用 DeepSeek 对公告全文进行语义理解，提取"机会列表"所需的全部字段：
  预算金额 / 报名费 / 保证金 / 报名截止日期 / 投标日期 / 采购方式

设计原则:
  - 作为 Step 3（数据提取）的核心组件
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

SYSTEM_PROMPT = """你是一名招标项目信息提取专家。请从公告正文中提取以下字段，用于填入"机会列表"：

字段说明（对应列表列名）：
1. budget — 预算金额（万元）
   - "预算金额"可能是"采购预算""项目预算""控制价""最高限价""估算金额"等
   - 如果原文以"元"为单位，请转换为万元（除以10000）
2. registration_fee — 报名费（元）
   - 可能是"标书费""文件费""招标文件售价""报名费"
3. deposit — 投标保证金（万元）
   - 可能是"投标保证金""磋商保证金""谈判保证金"
4. deadline — 报名截止日期（格式 YYYY-MM-DD）
   - 可能是"报名截止时间""文件获取截止时间""标书发售截止时间"
   - 仅提取日期部分，忽略具体时分秒
5. bid_date — 投标/开标日期（格式 YYYY-MM-DD）
   - 可能是"开标时间""投标截止时间""递交截止时间""首轮应答截止时间"
   - 仅提取日期部分
6. procurement_method — 采购方式
   - 可选值: "公开招标" / "公开询比" / "竞争性谈判" / "单一来源" / "邀请招标" / "询价" / "比选"
   - 如果公告中提及"公开招标""公开询比""竞争性谈判"等字眼，直接返回对应值
   - 如果无法确定，返回"公开招标"作为默认值

注意:
- 如果某个字段在原文中未提及，对应值返回 null
- 日期统一格式为 YYYY-MM-DD（如 2026-07-15）
- 只回复 JSON，不包含其他内容

JSON 格式：
{"budget":数字或null, "registration_fee":数字或null, "deposit":数字或null, "deadline":"YYYY-MM-DD"或null, "bid_date":"YYYY-MM-DD"或null, "procurement_method":"公开招标"或其它, "budget_text":"原文中预算相关的原始文本片段", "confidence":"high/medium/low"}"""


def _build_user_prompt(title: str, content: str) -> str:
    """构建用户提示词。"""
    body = (content or "")[:4000]
    return f"""请从以下公告中提取财务信息：

【项目名称】
{title}

【公告正文】
{body}"""


def _parse_response(text: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON，提取全部6个字段。"""
    def _extract(data: dict) -> dict:
        return {
            "budget": _safe_float(data.get("budget")),
            "registration_fee": _safe_float(data.get("registration_fee")),
            "deposit": _safe_float(data.get("deposit")),
            "deadline": _safe_date(data.get("deadline")),
            "bid_date": _safe_date(data.get("bid_date")),
            "procurement_method": str(data.get("procurement_method", "")) or "公开招标",
            "budget_text": str(data.get("budget_text", ""))[:200],
            "confidence": str(data.get("confidence", "low")),
        }

    try:
        data = json.loads(text)
        return _extract(data)
    except json.JSONDecodeError:
        pass

    # 尝试从文本中提取 JSON 块
    m = re.search(r'\{[^{}]*"budget"[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            return _extract(data)
        except json.JSONDecodeError:
            pass

    logger.warning(f"LLM 响应解析失败: {text[:100]}")
    return _default_result()


def _default_result() -> Dict[str, Any]:
    return {
        "budget": None, "registration_fee": None, "deposit": None,
        "deadline": None, "bid_date": None,
        "procurement_method": "公开招标",
        "budget_text": "", "confidence": "low",
    }


def _safe_date(val) -> Optional[str]:
    """安全解析日期字符串为 YYYY-MM-DD 格式。"""
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    # 尝试匹配 YYYY-MM-DD 或 YYYY/MM/DD
    m = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return None


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
    使用 LLM 从公告全文中提取「机会列表」所需的全部字段。

    Returns:
        {budget, registration_fee, deposit, deadline, bid_date,
         procurement_method, budget_text, confidence}
    """
    if not settings.LLM_API_KEY or not settings.LLM_ENABLED:
        return _default_result()

    if not content or len(content.strip()) < 50:
        logger.debug("公告正文过短或为空，跳过 LLM 提取")
        return _default_result()

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
                        "max_tokens": 400,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM 提取调用失败: {e}")
            return None

    try:
        result_text = asyncio.run(_call())
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            result_text = loop.run_until_complete(_call())
        except Exception as e:
            logger.warning(f"LLM 提取异步异常: {e}")
            return _default_result()
    except Exception as e:
        logger.warning(f"LLM 提取异常: {e}")
        return _default_result()

    if not result_text:
        return _default_result()

    result = _parse_response(result_text)
    if result["budget"] is not None:
        logger.info(f"LLM 提取成功: 预算{result['budget']}万, 截止{result.get('deadline','?')}, 置信度:{result['confidence']}")
    return result


def extract_budget_hybrid(title: str, content: str = "", existing_budget: Optional[float] = None) -> Dict[str, Any]:
    """
    混合提取：正则先尝试预算 → LLM 提取全部字段。

    LLM 始终被调用（即使正则已提取到预算），因为 deadline / bid_date /
    procurement_method 也需要 LLM 从正文中提取。
    """
    # 正则优先提取预算（快速路径）
    regex_result = _default_result()
    regex_result["extractor"] = "regex"

    if existing_budget is not None and existing_budget > 0:
        regex_result["budget"] = existing_budget
        regex_result["confidence"] = "high"
    elif content:
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
                    regex_result["budget"] = budget
                    regex_result["budget_text"] = m.group(0)
                    regex_result["confidence"] = "high"
                    break

    # LLM 提取全部字段（始终调用，获取 deadline / bid_date / procurement_method）
    llm_result = extract_budget_by_llm(title, content)
    llm_result["extractor"] = "llm"

    # 合并：LLM 结果优先，但正则预算如果已有值则保留
    merged = dict(llm_result)
    if regex_result["budget"] and not llm_result["budget"]:
        merged["budget"] = regex_result["budget"]
        merged["budget_text"] = regex_result["budget_text"]
    if regex_result["confidence"] == "high":
        merged["confidence"] = "high"
    merged["extractor"] = "hybrid"

    return merged
