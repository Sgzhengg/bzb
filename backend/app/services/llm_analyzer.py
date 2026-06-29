"""
LLM 驱动的智能分析引擎

借鉴 OpenManus DataAnalysis Agent 的设计理念，
使用 LLM 进行动态数据分析和洞察生成。

核心能力：
  1. 自然语言竞品分析报告
  2. 动态权重调整（根据市场变化自适应）
  3. 异常模式检测（围标/陪标线索）
  4. 市场趋势洞察

依赖：
  httpx（已有）- 用于调用 LLM API
"""

import json
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)


# ============================================================
# LLM 配置
# ============================================================

@dataclass
class LLMConfig:
    """LLM API 配置"""
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 30


def _get_llm_config() -> LLMConfig:
    """从环境变量加载 LLM 配置。"""
    import os
    return LLMConfig(
        api_base=os.getenv("BZB_LLM_API_BASE", "https://api.openai.com/v1"),
        api_key=os.getenv("BZB_LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        model=os.getenv("BZB_LLM_MODEL", "gpt-4o-mini"),
        temperature=float(os.getenv("BZB_LLM_TEMPERATURE", "0.3")),
        max_tokens=int(os.getenv("BZB_LLM_MAX_TOKENS", "2000")),
        timeout=int(os.getenv("BZB_LLM_TIMEOUT", "30")),
    )


# ============================================================
# 分析结果数据结构
# ============================================================

@dataclass
class CompetitorInsight:
    """竞品洞察"""
    competitor_name: str
    strength: str           # 优势分析
    weakness: str           # 劣势分析
    threat_level: str       # 威胁等级：高/中/低
    strategy_advice: str    # 应对策略建议


@dataclass
class MarketTrend:
    """市场趋势"""
    trend_name: str
    direction: str          # 上升/下降/稳定
    confidence: float       # 置信度 0-1
    evidence: str           # 证据描述
    impact: str             # 对业务的影响


@dataclass
class AnomalyAlert:
    """异常检测"""
    alert_type: str         # 围标嫌疑/价格异常/中标模式异常
    severity: str           # 高/中/低
    description: str
    related_projects: List[str] = field(default_factory=list)


@dataclass
class LLMAnalysisReport:
    """LLM 分析报告"""
    title: str
    summary: str
    competitor_insights: List[CompetitorInsight] = field(default_factory=list)
    market_trends: List[MarketTrend] = field(default_factory=list)
    anomaly_alerts: List[AnomalyAlert] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    dynamic_weights: Dict[str, float] = field(default_factory=dict)
    generated_at: str = ""
    model_used: str = ""
    raw_response: str = ""


# ============================================================
# LLM 分析器
# ============================================================

class LLMAnalyzer:
    """
    LLM 驱动的招标数据分析器。

    使用 LLM API 对招标数据进行深度分析，
    生成竞品洞察、市场趋势、异常检测和策略建议。

    Usage:
        analyzer = LLMAnalyzer()
        report = await analyzer.analyze_competition(purchaser_data)
        print(report.summary)
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or _get_llm_config()
        self._available = bool(self.config.api_key)

    @property
    def is_available(self) -> bool:
        """检查 LLM 是否可用（已配置 API Key）。"""
        return self._available

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        """调用 LLM API。"""
        if not self._available:
            logger.warning("LLM 未配置 API Key，跳过分析")
            return None

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(
                    f"{self.config.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM API 调用失败: {e}")
            return None

    # ── 竞品分析 ──

    async def analyze_competition(
        self,
        purchaser_name: str,
        top_suppliers: List[Dict],
        historical_awards: List[Dict],
    ) -> LLMAnalysisReport:
        """
        竞品格局分析。

        Args:
            purchaser_name: 采购方名称
            top_suppliers: Top N 供应商列表 [{"name": "...", "win_count": N, "percentage": 0.X}, ...]
            historical_awards: 历史中标记录

        Returns:
            LLMAnalysisReport
        """
        report = LLMAnalysisReport(
            title=f"{purchaser_name} — 竞品格局分析",
            summary="",
            generated_at=datetime.now().isoformat(),
            model_used=self.config.model,
        )

        if not self._available:
            report.summary = "LLM 未配置，无法生成分析报告。"
            return report

        # 构建 prompt
        suppliers_text = "\n".join(
            f"- {s['name']}: 中标 {s.get('win_count', 0)} 次, "
            f"占比 {s.get('percentage', 0):.1%}"
            for s in top_suppliers[:10]
        )

        history_text = "\n".join(
            f"- {a.get('date', '')}: {a.get('winner', '')} 中标 "
            f"{a.get('project_name', '')} (金额: {a.get('amount', 'N/A')})"
            for a in historical_awards[:20]
        )

        system_prompt = """你是一位招标市场分析专家，专精于广告传媒行业的竞争格局分析。
请基于提供的供应商中标数据，生成一份专业的竞品分析报告。
使用 JSON 格式输出，包含 summary、insights、trends、recommendations 字段。
只输出 JSON，不要有其他内容。"""

        user_prompt = f"""请分析以下采购方的竞品格局：

采购方：{purchaser_name}

Top 供应商：
{suppliers_text}

近期中标记录：
{history_text}

请分析：
1. 竞争格局总结（3-5句话）
2. 主要竞争对手优劣势（3-5个）
3. 市场趋势判断
4. 策略建议（3条）
"""

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
        )

        if response:
            try:
                data = json.loads(response)
                report.summary = data.get("summary", "")
                report.raw_response = response

                for insight in data.get("insights", []):
                    report.competitor_insights.append(
                        CompetitorInsight(
                            competitor_name=insight.get("name", ""),
                            strength=insight.get("strength", ""),
                            weakness=insight.get("weakness", ""),
                            threat_level=insight.get("threat", "中"),
                            strategy_advice=insight.get("strategy", ""),
                        )
                    )

                for trend in data.get("trends", []):
                    report.market_trends.append(
                        MarketTrend(
                            trend_name=trend.get("name", ""),
                            direction=trend.get("direction", "稳定"),
                            confidence=float(trend.get("confidence", 0.5)),
                            evidence=trend.get("evidence", ""),
                            impact=trend.get("impact", ""),
                        )
                    )

                report.recommendations = data.get("recommendations", [])

            except json.JSONDecodeError:
                report.summary = response[:500]
                report.raw_response = response

        return report

    # ── 异常检测 ──

    async def detect_anomalies(
        self,
        purchaser_name: str,
        recent_awards: List[Dict],
    ) -> List[AnomalyAlert]:
        """
        异常模式检测：围标嫌疑、价格异常、中标模式异常等。

        Args:
            purchaser_name: 采购方名称
            recent_awards: 近期中标记录

        Returns:
            AnomalyAlert 列表
        """
        if not self._available or not recent_awards:
            return []

        awards_text = "\n".join(
            f"- {a.get('date', '')}: {a.get('winner', '')} 中标 "
            f"「{a.get('project_name', '')}」金额 {a.get('amount', 'N/A')} 万元"
            for a in recent_awards[:30]
        )

        system_prompt = """你是招标审计专家，擅长识别招标过程中的异常模式。
请基于中标数据分析是否存在围标、陪标、价格异常等可疑模式。
使用 JSON 格式输出 alerts 数组。只输出 JSON。"""

        user_prompt = f"""请分析以下采购方的中标数据，检测异常模式：

采购方：{purchaser_name}

中标记录：
{awards_text}

检测要点：
- 同一供应商连续中标是否异常频繁
- 中标金额是否异常（过高/过低）
- 是否有明显的围标/陪标模式
- 中标方轮换是否有规律
"""

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
        )

        alerts = []
        if response:
            try:
                data = json.loads(response)
                for a in data.get("alerts", []):
                    alerts.append(
                        AnomalyAlert(
                            alert_type=a.get("type", "未知"),
                            severity=a.get("severity", "低"),
                            description=a.get("description", ""),
                            related_projects=a.get("projects", []),
                        )
                    )
            except json.JSONDecodeError:
                pass

        return alerts

    # ── 动态权重调整 ──

    async def suggest_weights(
        self,
        market_context: str,
        current_weights: Dict[str, float],
    ) -> Dict[str, float]:
        """
        根据市场环境动态调整评分权重。

        Args:
            market_context: 市场环境描述
            current_weights: 当前权重配置

        Returns:
            建议的新权重（总和为 1.0）
        """
        if not self._available:
            return current_weights

        weights_text = "\n".join(
            f"- {k}: {v:.0%}" for k, v in current_weights.items()
        )

        system_prompt = """你是招标评估专家。根据市场环境变化，调整评分维度权重。
输出 JSON 格式的新权重，所有权重之和必须为 1.0。只输出 JSON。"""

        user_prompt = f"""当前市场环境：
{market_context}

当前权重配置：
{weights_text}

请根据市场环境建议新的权重分配，考虑：
- 市场是否处于激烈竞争期 → 提高 "客情关系强度" 和 "在位者优势" 权重
- 新政策是否要求更公开透明 → 提高 "采购方式公平性" 权重
- 是否有大量预算释放 → 提高 "预算健康度" 权重

输出新的权重 JSON，格式：{{"procurement_fairness": 0.2, ...}}
"""

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
        )

        if response:
            try:
                new_weights = json.loads(response)
                # 验证权重有效
                weights_dict = {
                    k: float(v)
                    for k, v in new_weights.items()
                    if isinstance(v, (int, float))
                }
                total = sum(weights_dict.values())
                if total > 0 and 0.9 < total < 1.1:
                    # 归一化
                    return {k: round(v / total, 4) for k, v in weights_dict.items()}
            except (json.JSONDecodeError, ValueError):
                pass

        return current_weights

    # ── 项目机会评估 ──

    async def evaluate_opportunity(
        self,
        project_info: Dict,
        competitor_context: str,
    ) -> Dict[str, Any]:
        """
        LLM 评估单个项目的投标机会。

        Args:
            project_info: 项目信息
            competitor_context: 竞争环境描述

        Returns:
            {"score": 0-100, "analysis": "...", "risks": [...], "advantages": [...]}
        """
        if not self._available:
            return {
                "score": 50,
                "analysis": "LLM 未配置，使用默认评分",
                "risks": [],
                "advantages": [],
            }

        system_prompt = """你是投标策略顾问。评估项目投标机会，给出 0-100 分及分析。
输出 JSON: {{"score": int, "analysis": str, "risks": [...], "advantages": [...]}}
只输出 JSON。"""

        user_prompt = f"""评估以下项目的投标机会：

项目信息：
- 名称：{project_info.get('title', '')}
- 采购方：{project_info.get('purchaser', '')}
- 预算：{project_info.get('budget', 'N/A')} 万元
- 采购方式：{project_info.get('procurement_method', '')}
- 项目类别：{project_info.get('project_category', '')}

竞争环境：
{competitor_context}

请给出：
1. 综合评分（0-100）
2. 简要分析
3. 主要风险（2-3条）
4. 我方优势（2-3条）
"""

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
        )

        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass

        return {
            "score": 50,
            "analysis": "分析失败",
            "risks": [],
            "advantages": [],
        }


# ============================================================
# 便捷函数
# ============================================================

# 全局单例
_llm_analyzer: Optional[LLMAnalyzer] = None


def get_llm_analyzer() -> LLMAnalyzer:
    """获取 LLM 分析器单例。"""
    global _llm_analyzer
    if _llm_analyzer is None:
        _llm_analyzer = LLMAnalyzer()
    return _llm_analyzer
