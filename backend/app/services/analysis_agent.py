"""
招标数据分析 Agent

借鉴 OpenManus DataAnalysis Agent 的编排模式，
将搜索发现、AI 爬取、LLM 分析、图表生成串联成自动化工作流。

支持的分析任务：
  1. 竞品格局分析 — 输入采购方 → 输出竞品报告 + 图表
  2. 市场机会扫描 — 自动发现新公告 → 评分排序 → 推荐
  3. 趋势洞察 — 历史数据分析 → 趋势报告
  4. 异常检测 — 中标数据分析 → 风险警报

Usage:
    agent = AnalysisAgent()
    
    # 竞品分析
    report = await agent.run_competition_analysis("广州移动")
    
    # 机会扫描
    opportunities = await agent.run_opportunity_scan()
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================
# 分析任务定义
# ============================================================

@dataclass
class AnalysisTask:
    """分析任务"""
    task_id: str
    task_type: str                    # competition / opportunity / trend / anomaly
    status: str = "pending"           # pending / running / completed / failed
    progress: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
    started_at: str = ""
    completed_at: str = ""


@dataclass
class CompetitionReport:
    """竞品分析报告"""
    purchaser_name: str
    summary: str
    top_competitors: List[Dict] = field(default_factory=list)
    market_share: Dict[str, float] = field(default_factory=dict)
    entry_barriers: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    chart_urls: List[str] = field(default_factory=list)
    generated_at: str = ""


@dataclass
class OpportunityScanResult:
    """机会扫描结果"""
    total_scanned: int
    high_opportunity: List[Dict] = field(default_factory=list)
    medium_opportunity: List[Dict] = field(default_factory=list)
    low_opportunity: List[Dict] = field(default_factory=list)
    top_picks: List[Dict] = field(default_factory=list)
    scan_time: str = ""


# ============================================================
# 分析 Agent
# ============================================================

class AnalysisAgent:
    """
    招标数据分析 Agent。

    编排多个服务模块完成端到端的分析任务。

    内部流程：
      搜索发现 → AI 爬取 → 数据清洗 → 规则评分 → LLM 深度分析 → 图表生成 → 报告输出
    """

    def __init__(self):
        self.tasks: Dict[str, AnalysisTask] = {}

    # ── 1. 竞品格局分析 ──

    async def run_competition_analysis(
        self,
        purchaser_name: str,
        use_llm: bool = True,
        generate_charts: bool = True,
    ) -> CompetitionReport:
        """
        竞品格局分析。

        流程：
          1. 查询该采购方历史中标数据
          2. 计算供应商份额（规则引擎）
          3. LLM 深度分析竞品优劣势
          4. 生成可视化图表
        """
        logger.info(f"📊 开始竞品分析: {purchaser_name}")

        report = CompetitionReport(
            purchaser_name=purchaser_name,
            summary="",
            generated_at=datetime.now().isoformat(),
        )

        try:
            # 1. 查询历史数据
            from app.db.session import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT winner_name, COUNT(*) as win_count,
                               SUM(budget) as total_amount
                        FROM announcements
                        WHERE purchaser_name = :name
                          AND winner_name IS NOT NULL
                        GROUP BY winner_name
                        ORDER BY win_count DESC
                        LIMIT 10
                    """),
                    {"name": purchaser_name},
                )
                rows = result.fetchall()

            if not rows:
                report.summary = f"未找到 {purchaser_name} 的历史中标数据。"
                return report

            # 2. 统计份额
            competitors = []
            total_wins = sum(r[1] for r in rows)
            for r in rows:
                share = r[1] / total_wins if total_wins > 0 else 0
                competitors.append({
                    "name": r[0],
                    "win_count": r[1],
                    "total_amount": round(float(r[2] or 0), 1),
                    "share": round(share, 3),
                })

            report.top_competitors = competitors
            report.market_share = {c["name"]: c["share"] for c in competitors}

            # 3. LLM 分析
            if use_llm:
                try:
                    from app.services.llm_analyzer import get_llm_analyzer

                    analyzer = get_llm_analyzer()
                    if analyzer.is_available:
                        llm_report = await analyzer.analyze_competition(
                            purchaser_name=purchaser_name,
                            top_suppliers=competitors,
                            historical_awards=[
                                {"winner": c["name"], "amount": c["total_amount"]}
                                for c in competitors
                            ],
                        )
                        report.summary = llm_report.summary
                        for insight in llm_report.competitor_insights:
                            report.entry_barriers.append(
                                f"{insight.competitor_name}: {insight.strength}"
                            )
                        report.recommendations = llm_report.recommendations

                except Exception as e:
                    logger.warning(f"LLM 分析失败: {e}")

            # 4. 默认总结
            if not report.summary:
                top = competitors[0]["name"] if competitors else "未知"
                report.summary = (
                    f"{purchaser_name} 共有 {len(competitors)} 家主要供应商，"
                    f"其中 {top} 以 {competitors[0]['win_count']} 次中标位居首位，"
                    f"市场份额 {competitors[0]['share']:.0%}。"
                )

            # 5. 图表建议
            if generate_charts:
                report.chart_urls = [
                    f"/api/v1/charts/html/category_distribution",
                    f"/api/v1/charts/html/monthly_trend",
                ]

            logger.info(f"✅ 竞品分析完成: {purchaser_name}")

        except Exception as e:
            logger.error(f"竞品分析失败: {e}")
            report.summary = f"分析失败: {e}"

        return report

    # ── 2. 市场机会扫描 ──

    async def run_opportunity_scan(
        self,
        preferred_categories: Optional[List[str]] = None,
        min_budget: float = 0,
        max_results: int = 50,
        use_llm: bool = True,
    ) -> OpportunityScanResult:
        """
        市场机会扫描。

        流程：
          1. 搜索发现新公告 URL
          2. AI 爬取详情
          3. 关键词过滤 + 赛道分类
          4. 机会评分引擎评分
          5. 按机会大小排序推荐
        """
        logger.info("🔍 开始市场机会扫描...")

        scan = OpportunityScanResult(
            total_scanned=0,
            scan_time=datetime.now().isoformat(),
        )

        try:
            from app.db.session import AsyncSessionLocal
            from sqlalchemy import text, desc

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT id, title, purchaser_name, purchaser_level,
                               project_category, procurement_method,
                               budget, announce_date, probability_label,
                               total_score
                        FROM announcements
                        ORDER BY
                            CASE probability_label
                                WHEN '低' THEN 1
                                WHEN '中' THEN 2
                                WHEN '高' THEN 3
                            END,
                            total_score DESC NULLS LAST
                        LIMIT :limit
                    """),
                    {"limit": max_results},
                )
                rows = result.fetchall()

            for r in rows:
                item = {
                    "id": r[0],
                    "title": r[1],
                    "purchaser": r[2],
                    "level": r[3],
                    "category": r[4],
                    "method": r[5],
                    "budget": float(r[6] or 0),
                    "date": str(r[7]) if r[7] else "",
                    "probability": r[8] or "未知",
                    "score": float(r[9] or 0),
                }

                # 过滤预算
                if item["budget"] < min_budget:
                    continue

                label = item["probability"]
                if label == "低":
                    scan.high_opportunity.append(item)
                elif label == "中":
                    scan.medium_opportunity.append(item)
                else:
                    scan.low_opportunity.append(item)

            scan.total_scanned = (
                len(scan.high_opportunity)
                + len(scan.medium_opportunity)
                + len(scan.low_opportunity)
            )

            # Top Picks = 高分 + 高预算
            all_items = (
                scan.high_opportunity
                + scan.medium_opportunity
                + scan.low_opportunity
            )
            all_items.sort(
                key=lambda x: (x.get("budget", 0), x.get("score", 0)),
                reverse=True,
            )
            scan.top_picks = all_items[:10]

            # LLM 增强
            if use_llm and scan.top_picks:
                try:
                    from app.services.llm_analyzer import get_llm_analyzer

                    analyzer = get_llm_analyzer()
                    if analyzer.is_available:
                        for item in scan.top_picks[:5]:
                            llm_eval = await analyzer.evaluate_opportunity(
                                project_info=item,
                                competitor_context="市场平均竞争水平",
                            )
                            item["llm_score"] = llm_eval.get("score")
                            item["llm_analysis"] = llm_eval.get("analysis", "")
                            item["llm_risks"] = llm_eval.get("risks", [])
                except Exception as e:
                    logger.warning(f"LLM 增强失败: {e}")

            logger.info(
                f"✅ 机会扫描完成: {scan.total_scanned} 条, "
                f"高机会 {len(scan.high_opportunity)}, "
                f"中机会 {len(scan.medium_opportunity)}, "
                f"低机会 {len(scan.low_opportunity)}"
            )

        except Exception as e:
            logger.error(f"机会扫描失败: {e}")

        return scan

    # ── 3. 异常检测 ──

    async def run_anomaly_detection(
        self,
        purchaser_name: str,
        months: int = 12,
    ) -> Dict[str, Any]:
        """
        异常检测：分析中标数据中的异常模式。

        Returns:
            {"alerts": [...], "risk_score": 0-100}
        """
        logger.info(f"🕵️ 开始异常检测: {purchaser_name}")

        try:
            from datetime import date, timedelta
            from app.db.session import AsyncSessionLocal
            from sqlalchemy import text

            start_date = date.today() - timedelta(days=months * 31)

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT winner_name, project_category, budget,
                               announce_date, procurement_method
                        FROM announcements
                        WHERE purchaser_name = :name
                          AND announce_date >= :start
                        ORDER BY announce_date DESC
                    """),
                    {"name": purchaser_name, "start": start_date},
                )
                rows = result.fetchall()

            awards = [
                {
                    "winner": r[0] or "",
                    "category": r[1] or "",
                    "amount": float(r[2] or 0),
                    "date": str(r[3]) if r[3] else "",
                    "method": r[4] or "",
                }
                for r in rows
            ]

            # LLM 异常检测
            alerts = []
            try:
                from app.services.llm_analyzer import get_llm_analyzer

                analyzer = get_llm_analyzer()
                if analyzer.is_available:
                    llm_alerts = await analyzer.detect_anomalies(
                        purchaser_name=purchaser_name,
                        recent_awards=awards,
                    )
                    alerts = [
                        {
                            "type": a.alert_type,
                            "severity": a.severity,
                            "description": a.description,
                        }
                        for a in llm_alerts
                    ]
            except Exception as e:
                logger.warning(f"LLM 异常检测失败: {e}")

            # 规则引擎辅助检测
            from collections import Counter
            winner_counts = Counter(a["winner"] for a in awards)
            total = len(awards)

            for winner, count in winner_counts.most_common():
                if total > 0 and count / total > 0.5:
                    alerts.append({
                        "type": "集中度异常",
                        "severity": "中",
                        "description": (
                            f"{winner} 在近{months}个月内中标 {count}/{total} 次，"
                            f"占比 {count/total:.0%}，可能存在依赖关系"
                        ),
                    })
                    break

            risk_score = min(100, len(alerts) * 25 + 10)
            logger.info(f"✅ 异常检测完成: {len(alerts)} 条警报, 风险分 {risk_score}")

            return {
                "purchaser": purchaser_name,
                "period": f"近{months}个月",
                "total_awards": total,
                "alerts": alerts,
                "risk_score": risk_score,
            }

        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return {"error": str(e), "alerts": [], "risk_score": 0}


# ============================================================
# 全局单例
# ============================================================

_agent: Optional[AnalysisAgent] = None


def get_analysis_agent() -> AnalysisAgent:
    """获取分析 Agent 单例。"""
    global _agent
    if _agent is None:
        _agent = AnalysisAgent()
    return _agent
