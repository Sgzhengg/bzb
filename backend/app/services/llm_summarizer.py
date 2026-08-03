"""
智能公告摘要 + 资格预审分析服务

一次 LLM 调用完成：
  1. 一句话摘要
  2. 核心项目信息（预算/资质/时间/采购方式）
  3. 风险提示
  4. 资格预审建议 + 投标策略

设计原则:
  - Pydantic structured output，无需手写 JSON 解析
  - 结果存入 announcements.ai_summary 字段，避免重复调用
  - 同步接口（内部用 asyncio.run 桥接），适配现有采集流程
  - LLM 不可用时返回 None，不影响主流程
"""

import json
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# Pydantic 输出模型
# ============================================================

class QualificationCheck(BaseModel):
    """资格要求分析"""
    requirement: str = Field(default="", description="具体资质要求描述")
    is_hard_gate: bool = Field(default=False, description="是否为硬性门槛（如注册资本、行业资质）")
    our_advantage: Optional[str] = Field(default=None, description="我方是否满足/优势评估")


class RiskItem(BaseModel):
    """风险项"""
    risk_type: str = Field(default="", description="风险类型: 资质/资金/时间/竞争/其他")
    description: str = Field(default="", description="风险描述")
    severity: str = Field(default="低", description="严重程度: 高/中/低")


class StrategyAdvice(BaseModel):
    """策略建议"""
    advice: str = Field(default="", description="建议内容")
    priority: int = Field(default=0, description="优先级: 1高/2中/3低")


class AISummaryResult(BaseModel):
    """AI 完整分析结果"""
    model_config = {"extra": "ignore"}

    # 摘要
    one_liner: str = Field(default="", description="一句话摘要（30字以内）")
    brief: str = Field(default="", description="项目简报（3-5句话）")

    # 核心信息提取
    budget_analysis: Optional[str] = Field(default=None, description="预算分析（金额是否明确/资金是否充裕）")
    budget_health: Optional[str] = Field(default=None, description="资金健康度: 充裕/适中/偏低/未知")
    procurement_fairness: Optional[str] = Field(default=None, description="采购公平性: 高/中/低")

    # 资格要求
    qualifications: list[QualificationCheck] = Field(default_factory=list, description="资格要求清单")
    hard_gates: list[str] = Field(default_factory=list, description="硬性门槛摘要")

    # 时间节点
    key_dates: dict[str, str] = Field(default_factory=dict, description="关键时间节点")

    # 风险
    risks: list[RiskItem] = Field(default_factory=list, description="风险提示清单")
    risk_level: str = Field(default="低", description="综合风险等级: 高/中/低")

    # 策略建议
    should_bid: bool = Field(default=False, description="是否建议参与投标")
    bid_score: int = Field(default=0, ge=0, le=100, description="投标建议评分 0-100")
    strategy: list[StrategyAdvice] = Field(default_factory=list, description="策略建议清单")

    # 元信息
    generated_at: str = Field(default="", description="生成时间")
    content_length: int = Field(default=0, description="分析的内容长度（字符）")


# ============================================================
# Prompt 定义
# ============================================================

SYSTEM_PROMPT = """你是一名专业的运营商招标投标分析师。你的任务是对招标公告进行智能分析和资格预审。

请基于公告标题和正文，完成以下分析，输出 JSON 格式（只输出 JSON，不要其他内容）：

## 1. 一句话摘要 (one_liner)
用 30 字以内概括项目核心信息。

## 2. 项目简报 (brief)
用 3-5 句话描述项目概况：采购方、项目范围、核心需求。

## 3. 预算分析
- budget_analysis: 纯文本字符串，预算是否明确、资金是否充裕的简要分析（50字以内）。注意：这个字段必须是字符串，不能是对象！
- budget_health: "充裕" / "适中" / "偏低" / "未知"
- procurement_fairness: "高"(公开招标/公开询比) / "中"(竞争性谈判/邀请) / "低"(单一来源)

## 4. 资格要求提取 (qualifications)
逐条列出公告中明确的资格要求，每条包含:
- requirement: 具体要求
- is_hard_gate: true=硬性门槛(如注册资本≥500万/必须具有XX资质/提供N个案例)
  false=软性要求(如"优先考虑"、"具有相关经验")
- our_advantage: 在不知道我方具体情况时填 null，或基于常见情况给出客观判断

hard_gates: 硬性门槛的简短列表

## 5. 关键时间节点 (key_dates)
提取重要日期，如:
- "报名截止": "2026-08-10 17:00"
- "开标日期": "2026-08-20"
- "投标日期": "2026-08-20"

## 6. 风险提示 (risks)
识别 2-3 个主要风险:
- risk_type: "资质" / "资金" / "时间" / "竞争" / "其他"
- description: 风险描述
- severity: "高" / "中" / "低"

risk_level: 综合风险等级

## 7. 投标建议
- should_bid: true/false 是否建议参与
- bid_score: 0-100 建议评分
- strategy: 2-3 条策略建议，每条有 priority(1=高/2=中/3=低)"""


def _build_user_prompt(title: str, content: str) -> str:
    """构建用户 prompt，截取关键内容。"""
    body = content[:4000] if content else ""
    return f"""请分析以下招标公告：

【项目名称】
{title}

【公告正文】
{body}"""


# ============================================================
# LLM 调用
# ============================================================

async def _call_llm(title: str, content: str) -> Optional[str]:
    """调用 LLM API 生成摘要。"""
    if not settings.LLM_API_KEY or not settings.LLM_ENABLED:
        logger.debug("LLM 未配置，跳过智能摘要")
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
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
                    "temperature": 0.15,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"LLM 摘要调用失败: {e}")
        return None


# ============================================================
# 解析
# ============================================================

def _parse_response(text: str) -> Optional[Dict[str, Any]]:
    """使用 Pydantic 解析 LLM 响应。"""
    if not text:
        return None

    # 清理可能的 markdown 包裹
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    # 尝试直接解析 JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 提取 JSON 块
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
            except json.JSONDecodeError:
                logger.warning(f"LLM 响应无法解析为 JSON: {text[:100]}")
                return None
        else:
            logger.warning(f"LLM 响应中未找到 JSON: {text[:100]}")
            return None

    # 字段容错：LLM 有时会把 budget_analysis 返回为对象而非字符串
    if isinstance(data.get("budget_analysis"), dict):
        d = data["budget_analysis"]
        data["budget_analysis"] = d.get("budget_analysis") or str(d)
        if not data.get("budget_health"):
            data["budget_health"] = d.get("budget_health", "未知")
        if not data.get("procurement_fairness"):
            data["procurement_fairness"] = d.get("procurement_fairness", "未知")

    # 字段类型容错：确保字符串字段不会是 dict/list
    for str_field in ["one_liner", "brief", "budget_analysis", "budget_health", "procurement_fairness", "risk_level"]:
        if isinstance(data.get(str_field), (dict, list)):
            data[str_field] = str(data[str_field])[:100]

    try:
        result = AISummaryResult.model_validate(data)
        result.generated_at = datetime.now().isoformat(timespec="seconds")
        result.content_length = len(text)
        return result.model_dump()
    except Exception as e:
        logger.warning(f"Pydantic 校验失败: {e}")
        # Last resort: try manual field extraction
        try:
            fallback = AISummaryResult(
                one_liner=str(data.get("one_liner", ""))[:60] or "摘要生成失败",
                brief=str(data.get("brief", ""))[:200] or "请查看公告原文",
                budget_analysis=str(data.get("budget_analysis", ""))[:100] or None,
                budget_health=str(data.get("budget_health", "未知")),
                procurement_fairness=str(data.get("procurement_fairness", "未知")),
                risk_level=str(data.get("risk_level", "低")),
                should_bid=bool(data.get("should_bid", False)),
                bid_score=int(data.get("bid_score", 0)) if isinstance(data.get("bid_score"), (int, float)) else 0,
            )
            return fallback.model_dump()
        except Exception as e2:
            logger.error(f"手动回退也失败: {e2}")
            return None


# ============================================================
# 对外接口
# ============================================================

OPINION_JUDGE_SYSTEM_PROMPT = """你是招标情报分析师。用户会给你一条"征求意见公告"（正式招标前发布的征集意见稿），请判断该公告是否预示后续会发布真实招标机会。

判断依据（任一满足即判为"是"）：
1. 公告提到具体的采购内容、采购人或项目范围
2. 公告提到预算、投标、报名、应答等招标流程要素
3. 标题或正文包含项目名称且属于采购/服务/工程类

判为"否"的情况：
1. 纯技术咨询、标准讨论，无采购实体
2. 公告只是例行公示，内容为空泛模板
3. 与采购完全无关的通知

只输出 JSON：{"is_tender_lead": true或false, "reason": "一句话理由"}"""


def judge_opinion_value(title: str, content: str) -> Optional[bool]:
    """
    判断征求意见公告是否指向真实招标机会（招标前兆）。
    返回 True/False；LLM 不可用或调用失败时返回 None（调用方自行决定）。
    用于采集时区分"有价值的招标前兆"与"无关意见征询"。
    """
    if not settings.LLM_API_KEY or not settings.LLM_ENABLED:
        logger.debug("LLM 未配置，跳过意见征集判别")
        return None
    if not content or len(content.strip()) < 30:
        content = title

    user_prompt = f"标题：{title}\n\n正文（截取）：\n{content[:1500]}"
    try:
        import asyncio
        async def _call():
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.LLM_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": OPINION_JUDGE_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 200,
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        text = asyncio.run(_call())
        if not text:
            return None
        data = json.loads(text)
        v = data.get("is_tender_lead")
        if isinstance(v, bool):
            return v
        # 兼容字符串
        return str(v).lower() in ("true", "1", "yes", "是", "会")
    except Exception as e:
        logger.warning(f"意见征集判别失败: {e}")
        return None


def generate_summary(title: str, content: str) -> Optional[Dict[str, Any]]:
    """
    同步接口：生成公告智能摘要 + 资格预审分析。
    注意：在 FastAPI 异步上下文中请使用 await generate_summary_async()。
    """
    if not content or len(content.strip()) < 20:
        logger.debug("正文过短，跳过摘要生成")
        return None

    import asyncio

    try:
        result_text = asyncio.run(_call_llm(title, content))
    except RuntimeError:
        # 已在事件循环中 → 使用异步接口
        logger.debug("已在事件循环中，委托异步接口")
        return None
    except Exception as e:
        logger.warning(f"LLM 摘要异常: {e}")
        return None

    if not result_text:
        return None

    result = _parse_response(result_text)
    if result:
        logger.info(
            f"AI摘要生成成功: title={title[:40]}... "
            f"score={result.get('bid_score')}, "
            f"risk={result.get('risk_level')}"
        )
    return result


async def generate_summary_async(title: str, content: str) -> Optional[Dict[str, Any]]:
    """
    异步接口：在 FastAPI 请求处理器中直接 await 使用。
    """
    if not content or len(content.strip()) < 20:
        logger.debug("正文过短，跳过摘要生成")
        return None

    result_text = await _call_llm(title, content)
    if not result_text:
        return None

    result = _parse_response(result_text)
    if result:
        logger.info(
            f"AI摘要生成成功(异步): title={title[:40]}... "
            f"score={result.get('bid_score')}, "
            f"risk={result.get('risk_level')}"
        )
    return result
