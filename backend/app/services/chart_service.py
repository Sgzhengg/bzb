"""
交互式图表服务

借鉴 OpenManus chart_visualization 的设计，
为招标数据分析生成 Plotly 交互式 HTML 图表。

支持图表类型：
  - 采购方中标分布 (Treemap/Sunburst)
  - 供应商竞争矩阵 (Heatmap)
  - 月度中标趋势 (Line/Area)
  - 预算-中标对比 (Scatter/Bubble)
  - 赛道分布 (Pie/Doughnut)
  - 地市对比 (Bar/Rader)

依赖：
  plotly (需安装: pip install plotly)
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# 尝试导入 plotly
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    from plotly.utils import PlotlyJSONEncoder
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly 未安装。请执行: pip install plotly")


# ============================================================
# 图表配置
# ============================================================

# 标中宝品牌色
BRAND_COLORS = {
    "primary": "#1677FF",      # 主色 (Antd Blue)
    "success": "#52C41A",
    "warning": "#FAAD14",
    "danger": "#FF4D4F",
    "purple": "#722ED1",
    "cyan": "#13C2C2",
}

# 图表主题
CHART_TEMPLATE = "plotly_white"
CHART_HEIGHT = 500
CHART_WIDTH = None  # 自适应


def _check_plotly():
    """检查 plotly 是否可用。"""
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly 未安装。请执行: pip install plotly")


# ============================================================
# 图表生成器
# ============================================================

class ChartService:
    """
    招标数据可视化图表服务。

    Usage:
        service = ChartService()
        html = service.competition_heatmap(purchaser_data)
        # 返回可嵌入 iframe 的独立 HTML
    """

    @staticmethod
    def _to_html(fig: go.Figure) -> str:
        """将 Plotly Figure 转为独立 HTML 字符串。"""
        return fig.to_html(
            full_html=True,
            include_plotlyjs="cdn",
            config={
                "displayModeBar": True,
                "responsive": True,
                "displaylogo": False,
            },
        )

    # ── 1. 采购方中标分布 ──

    def purchaser_winner_treemap(
        self,
        data: List[Dict],
        title: str = "采购方中标分布",
    ) -> str:
        """
        采购方-中标方 Treemap 图。

        Args:
            data: [{"purchaser": "广州移动", "winner": "省广", "amount": 500}, ...]
        """
        _check_plotly()

        if not data:
            return "<p>无数据</p>"

        df_data = {
            "purchaser": [],
            "winner": [],
            "amount": [],
            "count": [],
        }

        # 聚合
        key_counts: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for item in data:
            purchaser = item.get("purchaser", "未知")
            winner = item.get("winner", "未知")
            amount = float(item.get("amount", 0) or 0)
            key_counts[purchaser][winner] += amount

        for purchaser, winners in key_counts.items():
            for winner, total in winners.items():
                df_data["purchaser"].append(purchaser)
                df_data["winner"].append(winner)
                df_data["amount"].append(round(total, 1))
                df_data["count"].append(1)

        import pandas as pd
        df = pd.DataFrame(df_data)

        fig = px.treemap(
            df,
            path=["purchaser", "winner"],
            values="amount",
            color="amount",
            color_continuous_scale="Blues",
            title=title,
        )
        fig.update_layout(
            template=CHART_TEMPLATE,
            height=CHART_HEIGHT,
            margin=dict(t=50, l=10, r=10, b=10),
        )
        return self._to_html(fig)

    # ── 2. 供应商竞争矩阵 ──

    def competition_heatmap(
        self,
        data: List[Dict],
        title: str = "供应商竞争矩阵",
    ) -> str:
        """
        供应商 x 采购方 竞争矩阵 Heatmap。

        Args:
            data: [{"purchaser": "广州移动", "winner": "省广", "win_count": 3}, ...]
        """
        _check_plotly()

        if not data:
            return "<p>无数据</p>"

        # 构建矩阵
        purchasers = sorted(set(d.get("purchaser", "") for d in data))
        winners = sorted(set(d.get("winner", "") for d in data))

        matrix = {}
        for d in data:
            key = (d.get("purchaser", ""), d.get("winner", ""))
            matrix[key] = matrix.get(key, 0) + d.get("win_count", 1)

        z = [[matrix.get((p, w), 0) for w in winners] for p in purchasers]

        fig = go.Figure(
            data=go.Heatmap(
                z=z,
                x=winners,
                y=purchasers,
                colorscale="Blues",
                text=[[str(v) if v > 0 else "" for v in row] for row in z],
                texttemplate="%{text}",
                textfont={"size": 12},
            )
        )
        fig.update_layout(
            title=title,
            template=CHART_TEMPLATE,
            height=max(CHART_HEIGHT, len(purchasers) * 60 + 100),
            xaxis_title="供应商",
            yaxis_title="采购方",
        )
        return self._to_html(fig)

    # ── 3. 月度中标趋势 ──

    def monthly_trend(
        self,
        data: List[Dict],
        title: str = "月度中标趋势",
    ) -> str:
        """
        月度中标金额/数量趋势图。

        Args:
            data: [{"month": "2024-01", "total_amount": 500, "count": 10}, ...]
        """
        _check_plotly()

        if not data:
            return "<p>无数据</p>"

        months = [d.get("month", "") for d in data]
        amounts = [float(d.get("total_amount", 0) or 0) for d in data]
        counts = [int(d.get("count", 0) or 0) for d in data]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Bar(
                x=months, y=amounts,
                name="中标金额(万元)",
                marker_color=BRAND_COLORS["primary"],
                opacity=0.7,
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=months, y=counts,
                name="中标数量",
                mode="lines+markers",
                marker_color=BRAND_COLORS["warning"],
                line=dict(width=3),
            ),
            secondary_y=True,
        )

        fig.update_layout(
            title=title,
            template=CHART_TEMPLATE,
            height=CHART_HEIGHT,
            hovermode="x unified",
        )
        fig.update_yaxes(title_text="金额(万元)", secondary_y=False)
        fig.update_yaxes(title_text="数量", secondary_y=True)

        return self._to_html(fig)

    # ── 4. 预算中标对比 ──

    def budget_vs_award_scatter(
        self,
        data: List[Dict],
        title: str = "预算 vs 中标金额",
    ) -> str:
        """
        预算与中标金额散点图（气泡大小=项目数量）。

        Args:
            data: [{"purchaser": "...", "avg_budget": 100, "avg_award": 90, "count": 5}, ...]
        """
        _check_plotly()

        if not data:
            return "<p>无数据</p>"

        purchasers = [d.get("purchaser", "") for d in data]
        budgets = [float(d.get("avg_budget", 0) or 0) for d in data]
        awards = [float(d.get("avg_award", 0) or 0) for d in data]
        counts = [int(d.get("count", 1) or 1) for d in data]

        # 添加 y=x 参考线
        max_val = max(max(budgets), max(awards)) * 1.1

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=[0, max_val], y=[0, max_val],
                mode="lines",
                name="预算=中标",
                line=dict(dash="dash", color="gray", width=1),
                showlegend=True,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=budgets, y=awards,
                mode="markers+text",
                name="采购方",
                text=purchasers,
                textposition="top center",
                marker=dict(
                    size=[max(10, min(60, c * 5)) for c in counts],
                    color=BRAND_COLORS["primary"],
                    opacity=0.6,
                ),
            )
        )

        fig.update_layout(
            title=title,
            template=CHART_TEMPLATE,
            height=CHART_HEIGHT,
            xaxis_title="平均预算(万元)",
            yaxis_title="平均中标金额(万元)",
        )
        return self._to_html(fig)

    # ── 5. 赛道分布 ──

    def category_distribution(
        self,
        data: List[Dict],
        title: str = "项目赛道分布",
        chart_type: str = "pie",
    ) -> str:
        """
        项目赛道分布图。

        Args:
            data: [{"category": "媒介投放类", "count": 15, "total_amount": 3000}, ...]
            chart_type: "pie" | "doughnut" | "bar"
        """
        _check_plotly()

        if not data:
            return "<p>无数据</p>"

        categories = [d.get("category", "未知") for d in data]
        values = [d.get("count", 0) for d in data]
        amounts = [float(d.get("total_amount", 0) or 0) for d in data]

        colors = [
            BRAND_COLORS["primary"],
            BRAND_COLORS["success"],
            BRAND_COLORS["warning"],
            BRAND_COLORS["danger"],
            BRAND_COLORS["purple"],
            BRAND_COLORS["cyan"],
        ]

        if chart_type in ("pie", "doughnut"):
            fig = go.Figure(
                data=go.Pie(
                    labels=categories,
                    values=values,
                    hole=0.4 if chart_type == "doughnut" else 0,
                    marker=dict(colors=colors[:len(categories)]),
                    textinfo="label+percent",
                    hovertemplate=(
                        "%{label}<br>数量: %{value} 个<br>"
                        "金额: %{customdata} 万元<extra></extra>"
                    ),
                    customdata=amounts,
                )
            )
        else:
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=categories,
                        y=values,
                        marker_color=colors[:len(categories)],
                        text=values,
                        textposition="outside",
                    )
                ]
            )

        fig.update_layout(
            title=title,
            template=CHART_TEMPLATE,
            height=CHART_HEIGHT,
        )
        return self._to_html(fig)

    # ── 6. 地市对比雷达图 ──

    def city_radar(
        self,
        data: List[Dict],
        title: str = "地市综合对比",
    ) -> str:
        """
        广东21地市雷达对比图。

        Args:
            data: [
                {"city": "广州", "项目数": 50, "平均预算": 200, "竞争度": 0.7, "透明度": 0.9},
                ...
            ]
        """
        _check_plotly()

        if not data:
            return "<p>无数据</p>"

        dimensions = [k for k in data[0].keys() if k != "city"]
        cities = [d["city"] for d in data]

        fig = go.Figure()

        for d in data:
            fig.add_trace(
                go.Scatterpolar(
                    r=[d.get(dim, 0) for dim in dimensions],
                    theta=dimensions,
                    name=d["city"],
                    fill="toself",
                    opacity=0.3,
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            title=title,
            template=CHART_TEMPLATE,
            height=CHART_HEIGHT + 100,
            showlegend=True,
        )
        return self._to_html(fig)


# ============================================================
# JSON 图表数据（供前端 Antd Charts 使用）
# ============================================================

def prepare_chart_data(
    data: List[Dict],
    chart_type: str,
) -> Dict[str, Any]:
    """
    准备前端 Antd Charts 可用的 JSON 格式图表数据。

    图表类型：
      - "category_pie": 赛道饼图数据
      - "monthly_line": 月度趋势数据
      - "city_bar": 地市柱状图数据
      - "competition_heatmap": 竞争矩阵数据
    """
    if chart_type == "category_pie":
        counter = Counter(d.get("project_category", "未知") for d in data)
        return {
            "type": "pie",
            "data": [
                {"category": k, "count": v}
                for k, v in counter.most_common(10)
            ],
        }

    elif chart_type == "monthly_line":
        monthly = defaultdict(lambda: {"count": 0, "amount": 0})
        for d in data:
            date_str = d.get("announce_date", "") or d.get("award_date", "")
            if len(date_str) >= 7:
                month = date_str[:7]
                monthly[month]["count"] += 1
                monthly[month]["amount"] += float(d.get("budget", 0) or 0)

        sorted_months = sorted(monthly.keys())[-12:]  # 最近12个月
        return {
            "type": "line",
            "data": [
                {
                    "month": m,
                    "count": monthly[m]["count"],
                    "amount": round(monthly[m]["amount"], 1),
                }
                for m in sorted_months
            ],
        }

    elif chart_type == "city_bar":
        city_counter = Counter(
            d.get("purchaser_level", "未知") for d in data
        )
        return {
            "type": "bar",
            "data": [
                {"city": k, "count": v}
                for k, v in city_counter.most_common(21)
            ],
        }

    elif chart_type == "competition_heatmap":
        purchaser_winners = defaultdict(lambda: defaultdict(int))
        for d in data:
            purchaser = d.get("purchaser", "未知")
            winner = d.get("winner_name", "") or d.get("winner", "未知")
            purchaser_winners[purchaser][winner] += 1

        purchasers = sorted(purchaser_winners.keys())
        # 只取 Top 10 采购方 × Top 5 中标方
        top_purchasers = sorted(
            purchasers,
            key=lambda p: sum(purchaser_winners[p].values()),
            reverse=True,
        )[:10]

        return {
            "type": "heatmap",
            "purchasers": top_purchasers,
            "data": [
                {
                    "purchaser": p,
                    "winners": dict(purchaser_winners[p].most_common(5)),
                }
                for p in top_purchasers
            ],
        }

    return {"type": "unknown", "data": []}
