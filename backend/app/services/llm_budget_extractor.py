"""
LLM 预算金额提取服务

从公告正文中用 LLM（DeepSeek）智能提取预算金额。
b2b.10086.cn 公告正文中预算有多种表述方式：
  - "本项目不含税总价限价 5900000.00 元"
  - "采购预算金额为 50 万元"
  - "最高限价：85万元"
  - "预算总金额 300 万元（含税）"
  - 等等

LLM 负责理解语义并提取结构化数据。
"""
import json
import logging
import re
from typing import Optional, Dict, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def extract_budget_with_llm(
    title: str,
    content: str,
) -> Dict[str, Any]:
    """
    使用 LLM 从公告正文中提取预算金额。

    Args:
        title: 公告标题
        content: 公告正文（纯文本）

    Returns:
        {
            "budget_wan": float | None,      # 预算金额（万元）
            "budget_raw": str | None,         # 原始预算表述
            "registration_fee": float | None, # 报名费（元）
            "deposit": float | None,          # 保证金（元）
            "bid_date": str | None,           # 投标/开标日期
            "budget_note": str | None,        # 预算备注（含税/不含税等）
            "confidence": float,              # 置信度 0-1
        }
    """
    if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
        logger.warning("LLM 未配置，跳过预算提取")
        return _empty_result()

    # 裁剪内容：只取与预算相关的段落，减少 token 消耗
    focused_text = _extract_focused_sections(content, title)

    if not focused_text:
        logger.info(f"公告正文为空或太短: {title[:50]}")
        return _empty_result()

    prompt = _build_extraction_prompt(title, focused_text)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
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
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": settings.LLM_TEMPERATURE,
                    "max_tokens": settings.LLM_MAX_TOKENS,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            answer = data["choices"][0]["message"]["content"]
            result = _parse_llm_response(answer)
            logger.info(
                f"LLM 预算提取: title={title[:40]}... "
                f"budget={result.get('budget_wan')}万 "
                f"confidence={result.get('confidence')}"
            )
            return result

    except Exception as e:
        logger.error(f"LLM 预算提取失败: {e}")
        return _empty_result()


def _extract_focused_sections(content: str, title: str) -> str:
    """从公告正文中提取与预算相关的段落，减少 token"""
    lines = content.split("\n")
    budget_keywords = [
        "预算", "限价", "不含税", "含税", "总价", "金额",
        "万元", "报价", "最高限价", "采购预算", "标书",
        "报名费", "保证金", "投标", "开标", "截止",
        "总价", "费用", "价款", "价格",
    ]

    focused_lines = []
    # 保留标题行
    focused_lines.append(f"项目名称: {title}")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) < 3:
            continue

        # 保留含预算关键词的行及其上下文
        if any(kw in stripped for kw in budget_keywords):
            # 添加上下文（前1行 + 当前行 + 后1行）
            if i > 0:
                prev = lines[i - 1].strip()
                if prev and len(prev) > 3:
                    focused_lines.append(prev)
            focused_lines.append(stripped)
            if i < len(lines) - 1:
                nxt = lines[i + 1].strip()
                if nxt and len(nxt) > 3:
                    focused_lines.append(nxt)

    result = "\n".join(focused_lines[:80])  # 最多80行
    return result[:4000]  # 最多4000字符


def _build_extraction_prompt(title: str, content: str) -> str:
    return f"""请从以下招标公告正文中提取预算相关财务信息。

=== 公告标题 ===
{title}

=== 公告正文（节选） ===
{content}

请以 JSON 格式返回提取结果（只返回 JSON，不要其他内容）：
{{
    "budget_wan": 数字或null,  // 预算/限价金额，统一转为"万元"单位。如原文"590万元"→590，"850000元"→85
    "budget_raw": "原文中的预算表述",  // 如"本项目不含税总价限价5900000.00元"
    "registration_fee": 数字或null,  // 报名费/标书费（元），如原文"300元"→300
    "deposit": 数字或null,  // 保证金（元），如原文"5万元"→50000
    "bid_date": "YYYY-MM-DD"或null,  // 投标/开标日期
    "budget_note": "备注"或null,  // 如"不含税"、"含税"、"最高限价"等
    "confidence": 0-1之间的数字  // 你的置信度，0=不确定，1=非常确定
}}

注意:
- 如果找不到预算金额，budget_wan 填 null，confidence 填 0
- 金额转换: 1万元=10000元，保留2位小数
- 区分"预算金额"和"中标/中选金额"，只提取前者（公告中的预算/限价）"""


SYSTEM_PROMPT = """你是一个专业的招标公告数据提取助手。你的任务是从招标公告正文中精确提取预算金额、报名费、保证金等财务信息。

规则：
1. 金额统一转换：预算→万元，报名费→元，保证金→元
2. 只提取公告发布时的"预算"或"最高限价"，不要提取"中标金额"
3. 如果同一公告有"含税"和"不含税"两个金额，优先提取"不含税"的，并在 budget_note 中说明
4. 如果找不到某字段，填 null
5. 只返回 JSON，不要解释"""


def _parse_llm_response(answer: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON"""
    # 清理可能的 markdown 包裹
    answer = answer.strip()
    if answer.startswith("```"):
        answer = re.sub(r"^```\w*\n?", "", answer)
        answer = re.sub(r"\n?```$", "", answer)

    try:
        result = json.loads(answer)
    except json.JSONDecodeError:
        # 尝试提取 JSON 子串
        match = re.search(r"\{[^{}]*\}", answer, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                return _empty_result()
        else:
            return _empty_result()

    return {
        "budget_wan": _safe_float(result.get("budget_wan")),
        "budget_raw": result.get("budget_raw"),
        "registration_fee": _safe_float(result.get("registration_fee")),
        "deposit": _safe_float(result.get("deposit")),
        "bid_date": result.get("bid_date"),
        "budget_note": result.get("budget_note"),
        "confidence": _safe_float(result.get("confidence"), 0.0),
    }


def _safe_float(val, default=None):
    """安全转换为 float"""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _empty_result() -> Dict[str, Any]:
    return {
        "budget_wan": None,
        "budget_raw": None,
        "registration_fee": None,
        "deposit": None,
        "bid_date": None,
        "budget_note": None,
        "confidence": 0.0,
    }
