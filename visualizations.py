"""
Visualizations - Lafarge Spend Analytics
Clean high-contrast palette | increase=RED, decrease=GREEN
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ─── High-contrast palette (readable on white) ────────────────────────────────
C_NAVY      = "#1B3A5C"   # main bars / totals
C_TEAL      = "#17A589"   # decrease (good — spend down)
C_RED       = "#E74C3C"   # increase (bad — spend up)
C_ORANGE    = "#E67E22"   # OPEX
C_BLUE      = "#2980B9"   # CAPEX
C_PURPLE    = "#8E44AD"   # accent
C_GREEN     = "#27AE60"   # cumul line
C_GREY      = "#95A5A6"   # beyond-80% bars
C_YELLOW    = "#F1C40F"
C_DARK      = "#2C3E50"   # text / axis

CLUSTER_PALETTE = [
    "#2980B9","#E74C3C","#27AE60","#E67E22","#8E44AD",
    "#17A589","#F39C12","#2C3E50","#C0392B","#1ABC9C",
    "#D35400","#7F8C8D",
]

def _hex_to_rgba(hex_color, alpha=0.45):
    """Convert #RRGGBB to rgba(r,g,b,alpha) for Plotly transparency."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{alpha})"


LAYOUT = dict(
    font_family="Segoe UI, Arial, sans-serif",
    font_color=C_DARK,
    paper_bgcolor="white",
    plot_bgcolor="#FAFAFA",
    margin=dict(t=55, b=45, l=45, r=25),
    title_font=dict(color=C_DARK, size=14, family="Segoe UI, Arial, sans-serif"),
)

# Standard legend style — merge into update_layout calls that define a legend
LEGEND = dict(
    font=dict(color=C_DARK, size=11, family="Segoe UI, Arial, sans-serif"),
    bgcolor="rgba(255,255,255,0.9)",
    bordercolor="#D5E8F5",
    borderwidth=1,
)


# ══════════════════════════════════════════════════════════════════════════════
# SHARED WATERFALL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def _build_waterfall(labels, values, base_val, end_val,
                     base_label, end_label, title,
                     total_delta=None, total_pct=None):
    measure = ["absolute"] + ["relative"] * len(labels) + ["absolute"]
    x       = [base_label] + labels + [end_label]
    y       = [base_val]   + values  + [end_val]

    text_vals = []
    for m, v in zip(measure, y):
        text_vals.append(f"<b>{v:,.1f}</b>" if m == "absolute" else f"{v:+,.1f}")

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measure,
        x=x, y=y,
        text=text_vals,
        textposition="outside",
        textfont=dict(size=11, color=C_DARK, family="Segoe UI, Arial"),
        connector=dict(line=dict(color="#BDC3C7", width=1, dash="dot")),
        decreasing=dict(marker_color=C_TEAL),
        increasing=dict(marker_color=C_RED),
        totals=dict(marker_color=C_NAVY),
    ))

    annotations = []
    if total_delta is not None:
        color  = C_TEAL if total_delta <= 0 else C_RED
        badge  = f"{total_delta:+,.1f}"
        if total_pct is not None:
            badge += f"<br>({total_pct:+.1f}%)"
        annotations.append(dict(
            x=0.5, y=1.13, xref="paper", yref="paper",
            text=f'<span style="background:{color};color:white;padding:4px 12px;'
                 f'border-radius:20px;font-weight:bold;font-size:12px;">{badge}</span>',
            showarrow=False, font=dict(size=12), align="center",
        ))

    fig.update_layout(
        **LAYOUT,
        title=dict(text=title, font=dict(size=14, color=C_DARK), x=0),
        yaxis=dict(title="kCHF", gridcolor="#ECF0F1", zeroline=True,
                   zerolinecolor="#BDC3C7", zerolinewidth=1),
        xaxis=dict(
            type="category",  # prevent numeric interpolation of year labels
            tickfont=dict(size=11, color=C_DARK),
        ),
        showlegend=False,
        annotations=annotations,
        height=430,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class OverviewCharts:

    # ── 1. Waterfall – Variation per Cluster ─────────────────────────────────
    @staticmethod
    def cluster_variation_waterfall(df: pd.DataFrame, base_year: int) -> go.Figure:
        comp_year = base_year + 1
        if "Année" not in df.columns or "PSCS Cluster" not in df.columns:
            return go.Figure()

        y_base = df[df["Année"] == base_year].groupby("PSCS Cluster")["Total  spend"].sum()
        y_comp = df[df["Année"] == comp_year].groupby("PSCS Cluster")["Total  spend"].sum()

        clusters = sorted(set(y_base.index) | set(y_comp.index))
        deltas   = [float(y_comp.get(c, 0) - y_base.get(c, 0)) for c in clusters]

        base_total  = float(y_base.sum())
        comp_total  = float(y_comp.sum())
        total_delta = comp_total - base_total
        total_pct   = (total_delta / base_total * 100) if base_total else 0

        return _build_waterfall(
            labels=clusters, values=deltas,
            base_val=base_total, end_val=comp_total,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation du Spend par Cluster — {base_year} vs {comp_year}",
            total_delta=total_delta, total_pct=total_pct,
        )

    # ── 2. Treemap – Categories inside Clusters ───────────────────────────────
    @staticmethod
    def cluster_category_treemap(df: pd.DataFrame) -> go.Figure:
        if "PSCS Cluster" not in df.columns or "PSCS Category" not in df.columns:
            return go.Figure()

        data = (
            df.groupby(["PSCS Cluster", "PSCS Category"])["Total  spend"]
            .sum()
            .reset_index()
        )
        data.columns = ["Cluster", "Category", "Spend"]
        data = data[data["Spend"] > 0]

        if data.empty:
            return go.Figure()

        fig = px.treemap(
            data,
            path=["Cluster", "Category"],
            values="Spend",
            color="Cluster",
            color_discrete_sequence=CLUSTER_PALETTE,
            custom_data=["Spend"],
        )
        fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{value:,.1f} kCHF",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b><br>Spend: %{value:,.1f} kCHF<extra></extra>",
        )
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Treemap Spend — Cluster → Catégorie (kCHF)",
                       font=dict(size=14, color=C_DARK), x=0),
            height=430,
        )
        return fig

    # ── 3. Bar Chart – Spend by Cluster ──────────────────────────────────────
    @staticmethod
    def cluster_spend_bar(df: pd.DataFrame) -> go.Figure:
        if "PSCS Cluster" not in df.columns:
            return go.Figure()

        data = (
            df.groupby("PSCS Cluster")["Total  spend"]
            .sum().sort_values(ascending=False).reset_index()
        )
        data.columns = ["Cluster", "Spend"]
        colors = [CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)] for i in range(len(data))]

        fig = go.Figure(go.Bar(
            x=data["Cluster"], y=data["Spend"],
            marker_color=colors,
            text=[f"{v:,.1f}" for v in data["Spend"]],
            textposition="outside",
            textfont=dict(size=10, color=C_DARK),
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Spend par Cluster (kCHF)", font=dict(size=14, color=C_DARK), x=0),
            xaxis=dict(tickangle=-30, tickfont=dict(size=10, color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            height=430,
        )
        return fig

    # ── 4. Bar Chart – Top 10 Company Codes ──────────────────────────────────
    @staticmethod
    def top10_company_codes(df: pd.DataFrame) -> go.Figure:
        col = "Company Code descr"
        if col not in df.columns:
            return go.Figure()

        data = (
            df.groupby(col)["Total  spend"]
            .sum().sort_values(ascending=False).head(10).reset_index()
        )
        data.columns = ["Company Code", "Spend"]
        
        # Use a gradient or the cluster palette
        colors = [CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)] for i in range(len(data))]

        fig = go.Figure(go.Bar(
            x=data["Spend"], y=data["Company Code"],
            orientation="h",
            marker_color=colors[::-1], # reverse for visual hierarchy in horizontal bar
            text=[f"{v:,.1f}" for v in data["Spend"]],
            textposition="outside",
            textfont=dict(size=10, color=C_DARK),
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Top 10 Company Code (kCHF)", font=dict(size=14, color=C_DARK), x=0),
            xaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            yaxis=dict(autorange="reversed", tickfont=dict(size=10, color=C_DARK)),
            height=400,
        )
        return fig


# ══════════════════════════════════════════════════════════════════════════════
# CAPEX / OPEX CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class CapexOpexCharts:

    MONTHS_ORDER = ['January','February','March','April','May','June',
                    'July','August','September','October','November','December']

    @classmethod
    def _monthly_variation(cls, df, spend_col, base_year, title):
        comp_year = base_year + 1
        if "Année" not in df.columns or "Nom_Mois" not in df.columns:
            return go.Figure()

        def _monthly(yr):
            sub = df[df["Année"] == yr].groupby("Nom_Mois")[spend_col].sum()
            return {m: float(sub.get(m, 0)) for m in cls.MONTHS_ORDER}

        base_m = _monthly(base_year)
        comp_m = _monthly(comp_year)
        active = [m for m in cls.MONTHS_ORDER if base_m[m] != 0 or comp_m[m] != 0]
        if not active:
            return go.Figure()

        deltas      = [comp_m[m] - base_m[m] for m in active]
        base_total  = sum(base_m[m] for m in active)
        comp_total  = sum(comp_m[m] for m in active)
        total_delta = comp_total - base_total
        total_pct   = (total_delta / base_total * 100) if base_total else 0

        return _build_waterfall(
            labels=active, values=deltas,
            base_val=base_total, end_val=comp_total,
            base_label=str(base_year), end_label=str(comp_year),
            title=title, total_delta=total_delta, total_pct=total_pct,
        )

    @classmethod
    def capex_monthly_variation(cls, df, base_year):
        return cls._monthly_variation(df, "CAPEX Spend", base_year,
            f"Variation CAPEX mensuelle — {base_year} vs {base_year+1}")

    @classmethod
    def opex_monthly_variation(cls, df, base_year):
        return cls._monthly_variation(df, "OPEX Spend", base_year,
            f"Variation OPEX mensuelle — {base_year} vs {base_year+1}")

    @staticmethod
    def total_spend_yearly_variation(df, base_year):
        """Simple Y vs Y+1 waterfall: base bar, one delta bar, end bar."""
        comp_year = base_year + 1
        if "Année" not in df.columns:
            return go.Figure()

        by_year = df.groupby("Année")["Total  spend"].sum()

        base_val = float(by_year.get(base_year, 0))
        comp_val = float(by_year.get(comp_year, 0))

        if base_val == 0 and comp_val == 0:
            return go.Figure()

        delta       = comp_val - base_val
        total_pct   = (delta / base_val * 100) if base_val else 0

        return _build_waterfall(
            labels=[f"Variation {base_year}→{comp_year}"],
            values=[delta],
            base_val=base_val,
            end_val=comp_val,
            base_label=str(base_year),
            end_label=str(comp_year),
            title=f"Variation du Total Spend — {base_year} vs {comp_year}",
            total_delta=delta,
            total_pct=total_pct,
        )

    # ── 7. Stacked bar CAPEX + OPEX by year ──────────────────────────────────
    @staticmethod
    def capex_opex_stacked_bar(df: pd.DataFrame) -> go.Figure:
        if "Année" not in df.columns:
            return go.Figure()

        # Step 1: clean year column → plain integers
        tmp = df.dropna(subset=["Année"]).copy()
        tmp["yr"] = tmp["Année"].astype(float).astype(int)

        # Step 2: aggregate per year
        grp = tmp.groupby("yr")[["CAPEX Spend", "OPEX Spend"]].sum().sort_index()
        capex  = grp["CAPEX Spend"].tolist()
        opex   = grp["OPEX Spend"].tolist()
        totals = [c + o for c, o in zip(capex, opex)]
        # Step 3: x labels — use px.bar-style string so plotly never tries to parse as number
        xlabels = ["Y" + str(y) for y in grp.index.tolist()]   # "Y2024", "Y2025", "Y2026"
        xtitles = [str(y) for y in grp.index.tolist()]         # shown as tick text

        if not xlabels or sum(totals) == 0:
            return go.Figure()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="CAPEX", x=xlabels, y=capex,
            marker_color=C_BLUE,
            text=[f"{v:,.1f}" for v in capex],
            textposition="inside",
            textfont=dict(size=12, color="white"),
        ))
        fig.add_trace(go.Bar(
            name="OPEX", x=xlabels, y=opex,
            marker_color=C_ORANGE,
            text=[f"{v:,.1f}" for v in opex],
            textposition="inside",
            textfont=dict(size=12, color="white"),
        ))

        fig.update_layout(
            font_family=LAYOUT["font_family"],
            font_color=LAYOUT["font_color"],
            paper_bgcolor=LAYOUT["paper_bgcolor"],
            plot_bgcolor=LAYOUT["plot_bgcolor"],
            margin=LAYOUT["margin"],
            title=dict(text="CAPEX + OPEX par Année — Stacked (kCHF)",
                       font=dict(size=14, color=C_DARK), x=0),
            barmode="stack",
            xaxis=dict(
                tickmode="array",
                tickvals=xlabels,
                ticktext=xtitles,          # display clean "2024" not "Y2024"
                tickfont=dict(size=13, color=C_DARK),
                tickangle=0,
                title="",
            ),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1", tickfont=dict(color=C_DARK)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=11, color=C_DARK)),
            height=430,
        )
        return fig


# ══════════════════════════════════════════════════════════════════════════════
# PARETO CHARTS  — show ONLY the 20% of entities that drive 80% of spend
# ══════════════════════════════════════════════════════════════════════════════
class ParetoCharts:

    @staticmethod
    def _pareto_fig(df: pd.DataFrame, dim_col: str, spend_col: str,
                    title: str, hard_cap: int = None) -> go.Figure:
        if dim_col not in df.columns or spend_col not in df.columns:
            return go.Figure()

        all_data = (
            df.groupby(dim_col)[spend_col]
            .sum().sort_values(ascending=False).reset_index()
        )
        all_data.columns = ["Dimension", "Spend"]
        all_data = all_data[all_data["Spend"] > 0].reset_index(drop=True)

        if all_data.empty:
            return go.Figure()

        grand_total = all_data["Spend"].sum()

        # ── Find cutoff: fewest top entities whose cumulative spend >= 80% ───
        cumsum = 0
        cutoff = len(all_data)
        for i, v in enumerate(all_data["Spend"]):
            cumsum += v
            if cumsum / grand_total >= 0.80:
                cutoff = i + 1
                break

        # Apply hard cap if specified (e.g. top 10 only)
        if hard_cap is not None:
            cutoff = min(cutoff, hard_cap)

        data = all_data.iloc[:cutoff].copy()
        data["CumulPct"] = data["Spend"].cumsum() / grand_total * 100

        n_total = len(all_data)
        pct_entities = cutoff / n_total * 100

        # Color gradient: darker for higher spend
        bar_colors = [CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)] for i in range(len(data))]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(go.Bar(
            x=data["Dimension"], y=data["Spend"],
            name="Spend (kCHF)",
            marker_color=bar_colors,
            text=[f"{v:,.1f}" for v in data["Spend"]],
            textposition="outside",
            textfont=dict(size=9, color=C_DARK),
        ), secondary_y=False)

        fig.add_trace(go.Scatter(
            x=data["Dimension"], y=data["CumulPct"],
            name="Cumul %",
            mode="lines+markers",
            line=dict(color=C_RED, width=2.5),
            marker=dict(size=6, color=C_RED),
        ), secondary_y=True)

        fig.add_hline(
            y=80, line_dash="dash", line_color=C_TEAL, line_width=2,
            secondary_y=True,
            annotation_text="  80%", annotation_position="right",
            annotation_font=dict(color=C_TEAL, size=11),
        )

        fig.update_layout(
            **LAYOUT,
            title=dict(
                text=f"{title}<br><sup style='color:{C_GREY}'>"
                     f"{cutoff} / {n_total} entités ({pct_entities:.0f}%) → 80% du spend</sup>",
                font=dict(size=13, color=C_DARK), x=0,
            ),
            xaxis=dict(tickangle=-35, tickfont=dict(size=9, color=C_DARK)),
            yaxis=dict(title="Spend (kCHF)", gridcolor="#ECF0F1",
                       tickfont=dict(color=C_DARK)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=10, color=C_DARK)),
            height=420,
            bargap=0.25,
        )
        fig.update_yaxes(
            title_text="Cumul %", secondary_y=True,
            range=[0, 105], ticksuffix="%",
            gridcolor="#ECF0F1", tickfont=dict(color=C_DARK),
        )
        return fig

    @staticmethod
    def vendor_pareto(df):
        return ParetoCharts._pareto_fig(df, "Vendor Name", "Total  spend", "Pareto Fournisseurs — Top 10", hard_cap=10)

    @staticmethod
    def requester_pareto(df):
        return ParetoCharts._pareto_fig(df, "Requester", "Total  spend", "Pareto Requesters — Top 10", hard_cap=10)

    @staticmethod
    def cost_center_pareto(df):
        return ParetoCharts._pareto_fig(df, "Cost Center ID", "Total  spend", "Pareto Cost Center — Top 10", hard_cap=10)

    @staticmethod
    def gl_account_pareto(df):
        return ParetoCharts._pareto_fig(df, "GL Account Name", "Total  spend", "Pareto GL Account")

    @staticmethod
    def purchasing_group_pareto(df):
        return ParetoCharts._pareto_fig(df, "Purchasing Group Name", "Total  spend", "Pareto Purchasing Group")




# ══════════════════════════════════════════════════════════════════════════════
# CLUSTER TAB CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class ClusterCharts:

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _bar_colors_for(labels):
        """Assign a consistent palette color per unique label."""
        unique = list(dict.fromkeys(labels))
        mapping = {v: CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)] for i, v in enumerate(unique)}
        return [mapping[l] for l in labels]

    @staticmethod
    def _yoy_grouped_bar(df, group_col, base_year, title, color_by_group=True):
        """
        Generic grouped bar: for each entity in group_col show
        spend in base_year (lighter) and base_year+1 (solid).
        A delta label sits above each pair.
        """
        comp_year = base_year + 1
        if "Année" not in df.columns or group_col not in df.columns:
            return go.Figure()

        y_base = df[df["Année"] == base_year].groupby(group_col)["Total  spend"].sum()
        y_comp = df[df["Année"] == comp_year].groupby(group_col)["Total  spend"].sum()
        entities = sorted(set(y_base.index) | set(y_comp.index))

        base_vals = [float(y_base.get(e, 0)) for e in entities]
        comp_vals = [float(y_comp.get(e, 0)) for e in entities]
        deltas    = [c - b for b, c in zip(base_vals, comp_vals)]

        if color_by_group:
            solid_colors  = ClusterCharts._bar_colors_for(entities)
            light_colors  = [_hex_to_rgba(c, 0.40) for c in solid_colors]
        else:
            solid_colors  = [C_NAVY] * len(entities)
            light_colors  = [_hex_to_rgba(C_NAVY, 0.35)] * len(entities)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name=str(base_year),
            x=entities, y=base_vals,
            marker_color=light_colors,
            text=[f"{v:,.1f}" for v in base_vals],
            textposition="outside",
            textfont=dict(size=9, color=C_DARK),
        ))
        fig.add_trace(go.Bar(
            name=str(comp_year),
            x=entities, y=comp_vals,
            marker_color=solid_colors,
            text=[f"{v:,.1f}" for v in comp_vals],
            textposition="outside",
            textfont=dict(size=9, color=C_DARK),
        ))

        # Delta annotations between the two bars
        annotations = []
        for e, d in zip(entities, deltas):
            color = C_RED if d > 0 else C_TEAL
            annotations.append(dict(
                x=e, y=max(y_base.get(e, 0), y_comp.get(e, 0)),
                text=f"<b>{d:+,.1f}</b>",
                showarrow=False, yanchor="bottom", yshift=22,
                font=dict(size=10, color=color),
            ))

        fig.update_layout(
            **LAYOUT,
            title=dict(text=title, font=dict(size=14, color=C_DARK), x=0),
            barmode="group",
            xaxis=dict(tickangle=-30, tickfont=dict(size=10, color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11, color=C_DARK, family="Segoe UI, Arial, sans-serif"),
                        bgcolor="rgba(255,255,255,0.9)"),
            annotations=annotations,
            height=430,
        )
        return fig

    # ── 1. Bar chart: spend per cluster ───────────────────────────────────────
    @staticmethod
    def spend_per_cluster(df):
        if "PSCS Cluster" not in df.columns:
            return go.Figure()
        data = (df.groupby("PSCS Cluster")["Total  spend"]
                .sum().sort_values(ascending=False).reset_index())
        data.columns = ["Cluster", "Spend"]
        colors = ClusterCharts._bar_colors_for(data["Cluster"].tolist())
        fig = go.Figure(go.Bar(
            x=data["Cluster"], y=data["Spend"],
            marker_color=colors,
            text=[f"{v:,.1f}" for v in data["Spend"]],
            textposition="outside",
            textfont=dict(size=10, color=C_DARK),
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Spend par Cluster (kCHF)", font=dict(size=14, color=C_DARK), x=0),
            xaxis=dict(tickangle=-30, tickfont=dict(size=10, color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            height=400,
        )
        return fig

    # ── 2. YoY variation per cluster (waterfall) ────────────────────────────────
    @staticmethod
    def cluster_yoy_variation(df, base_year):
        comp_year = base_year + 1
        if "Année" not in df.columns or "PSCS Cluster" not in df.columns:
            return go.Figure()

        y_base = df[df["Année"] == base_year].groupby("PSCS Cluster")["Total  spend"].sum()
        y_comp = df[df["Année"] == comp_year].groupby("PSCS Cluster")["Total  spend"].sum()
        clusters    = sorted(set(y_base.index) | set(y_comp.index))
        deltas      = [float(y_comp.get(c, 0) - y_base.get(c, 0)) for c in clusters]
        base_total  = float(y_base.sum())
        comp_total  = float(y_comp.sum())
        total_delta = comp_total - base_total
        total_pct   = (total_delta / base_total * 100) if base_total else 0

        return _build_waterfall(
            labels=clusters, values=deltas,
            base_val=base_total, end_val=comp_total,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation du Spend par Cluster — {base_year} vs {comp_year}",
            total_delta=total_delta, total_pct=total_pct,
        )

    # ── 3. Spend per category for chosen cluster ──────────────────────────────
    @staticmethod
    def spend_per_category(df, cluster):
        sub = df[df["PSCS Cluster"] == cluster] if "PSCS Cluster" in df.columns else df
        if "PSCS Category" not in sub.columns or sub.empty:
            return go.Figure()
        data = (sub.groupby("PSCS Category")["Total  spend"]
                .sum().sort_values(ascending=False).reset_index())
        data.columns = ["Category", "Spend"]
        # All bars same cluster color
        cluster_list = df["PSCS Cluster"].dropna().unique().tolist() if "PSCS Cluster" in df.columns else []
        cidx = sorted(cluster_list).index(cluster) if cluster in sorted(cluster_list) else 0
        color = CLUSTER_PALETTE[cidx % len(CLUSTER_PALETTE)]
        fig = go.Figure(go.Bar(
            x=data["Category"], y=data["Spend"],
            marker_color=color,
            text=[f"{v:,.1f}" for v in data["Spend"]],
            textposition="outside",
            textfont=dict(size=10, color=C_DARK),
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text=f"Spend par Catégorie — {cluster} (kCHF)",
                       font=dict(size=14, color=C_DARK), x=0),
            xaxis=dict(tickangle=-30, tickfont=dict(size=10, color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            height=400,
        )
        return fig

    # ── 4. Monthly YoY variation for chosen cluster (waterfall) ───────────────
    @staticmethod
    def cluster_monthly_variation(df, cluster, base_year):
        MONTHS = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"]
        comp_year = base_year + 1
        if "PSCS Cluster" not in df.columns or "Nom_Mois" not in df.columns:
            return go.Figure()
        sub = df[df["PSCS Cluster"] == cluster]
        def _m(yr):
            s = sub[sub["Année"] == yr].groupby("Nom_Mois")["Total  spend"].sum()
            return {m: float(s.get(m, 0)) for m in MONTHS}
        bm = _m(base_year); cm = _m(comp_year)
        active = [m for m in MONTHS if bm[m] != 0 or cm[m] != 0]
        if not active:
            return go.Figure()
        deltas     = [cm[m] - bm[m] for m in active]
        base_total = sum(bm[m] for m in active)
        comp_total = sum(cm[m] for m in active)
        td  = comp_total - base_total
        pct = (td / base_total * 100) if base_total else 0
        return _build_waterfall(
            labels=active, values=deltas,
            base_val=base_total, end_val=comp_total,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation mensuelle — {cluster} — {base_year} vs {comp_year}",
            total_delta=td, total_pct=pct,
        )

    # ── 5. YoY variation per category in chosen cluster (grouped bar) ─────────
    @staticmethod
    def category_yoy_variation(df, cluster, base_year):
        sub = df[df["PSCS Cluster"] == cluster] if "PSCS Cluster" in df.columns else df
        return ClusterCharts._yoy_grouped_bar(
            sub, "PSCS Category", base_year,
            f"Variation par Catégorie — {cluster} — {base_year} vs {base_year+1}",
            color_by_group=False,
        )

    # ── 6. Monthly variation waterfall for a chosen CATEGORY ──────────────────
    @staticmethod
    def category_monthly_variation(df, category, base_year):
        """Waterfall of monthly spend deltas for a specific PSCS Category (Y vs Y+1)."""
        MONTHS = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"]
        comp_year = base_year + 1
        if "PSCS Category" not in df.columns or "Nom_Mois" not in df.columns:
            return go.Figure()
        sub = df[df["PSCS Category"] == category]
        if sub.empty:
            return go.Figure()
        def _m(yr):
            s = sub[sub["Année"] == yr].groupby("Nom_Mois")["Total  spend"].sum()
            return {m: float(s.get(m, 0)) for m in MONTHS}
        bm = _m(base_year); cm = _m(comp_year)
        active = [m for m in MONTHS if bm[m] != 0 or cm[m] != 0]
        if not active:
            return go.Figure()
        deltas     = [cm[m] - bm[m] for m in active]
        base_total = sum(bm[m] for m in active)
        comp_total = sum(cm[m] for m in active)
        td  = comp_total - base_total
        pct = (td / base_total * 100) if base_total else 0
        return _build_waterfall(
            labels=active, values=deltas,
            base_val=base_total, end_val=comp_total,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation mensuelle — {category} — {base_year} vs {comp_year}",
            total_delta=td, total_pct=pct,
        )

    # ── 6. Pareto: categories → 80% spend (colored by cluster) ───────────────
    @staticmethod
    def category_pareto_by_cluster(df):
        if "PSCS Category" not in df.columns or "PSCS Cluster" not in df.columns:
            return go.Figure()
        data = (df.groupby(["PSCS Category","PSCS Cluster"])["Total  spend"]
                .sum().reset_index())
        data.columns = ["Category","Cluster","Spend"]
        data = data.groupby("Category").agg(Spend=("Spend","sum"), Cluster=("Cluster","first")).reset_index()
        data = data[data["Spend"] > 0].sort_values("Spend", ascending=False).reset_index(drop=True)
        grand_total = data["Spend"].sum()
        cumsum = 0; cutoff = len(data)
        for i, v in enumerate(data["Spend"]):
            cumsum += v
            if cumsum / grand_total >= 0.80:
                cutoff = i + 1; break
        data = data.iloc[:cutoff].copy()
        data["CumulPct"] = data["Spend"].cumsum() / grand_total * 100

        clusters = sorted(df["PSCS Cluster"].dropna().unique().tolist())
        cmap = {c: CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)] for i, c in enumerate(clusters)}
        bar_colors = [cmap.get(c, C_GREY) for c in data["Cluster"]]

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(
            x=data["Category"], y=data["Spend"],
            marker_color=bar_colors,
            name="Spend",
            text=[f"{v:,.1f}" for v in data["Spend"]],
            textposition="outside", textfont=dict(size=9, color=C_DARK),
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=data["Category"], y=data["CumulPct"],
            name="Cumul %", mode="lines+markers",
            line=dict(color=C_RED, width=2),
            marker=dict(size=5),
        ), secondary_y=True)
        fig.add_hline(y=80, line_dash="dash", line_color=C_TEAL, line_width=1.5,
                      secondary_y=True,
                      annotation_text="  80%", annotation_font=dict(color=C_TEAL, size=11))
        # Legend for clusters
        for c, col in cmap.items():
            if c in data["Cluster"].values:
                fig.add_trace(go.Bar(x=[None], y=[None], name=c,
                                     marker_color=col, showlegend=True), secondary_y=False)
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Pareto Catégories → 80% du Spend (couleur = Cluster)",
                       font=dict(size=13, color=C_DARK), x=0),
            xaxis=dict(tickangle=-35, tickfont=dict(size=9, color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            barmode="stack",
            legend=dict(
                orientation="h",
                yanchor="top", y=-0.35,
                xanchor="center", x=0.5,
                font=dict(size=9, color=C_DARK),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#D5E8F5", borderwidth=1,
            ),
            height=500,
        )
        # Extra bottom margin for the legend — set separately to avoid conflict with **LAYOUT
        fig.update_layout(margin=dict(t=55, b=160, l=45, r=25))
        fig.update_yaxes(title_text="Cumul %", secondary_y=True,
                         range=[0,105], ticksuffix="%", gridcolor="#ECF0F1")
        return fig

    # ── 7. Pareto: clusters → 80% spend ──────────────────────────────────────
    @staticmethod
    def cluster_pareto(df):
        if "PSCS Cluster" not in df.columns:
            return go.Figure()
        data = (df.groupby("PSCS Cluster")["Total  spend"]
                .sum().sort_values(ascending=False).reset_index())
        data.columns = ["Cluster","Spend"]
        data = data[data["Spend"] > 0].reset_index(drop=True)
        grand_total = data["Spend"].sum()
        cumsum = 0; cutoff = len(data)
        for i, v in enumerate(data["Spend"]):
            cumsum += v
            if cumsum / grand_total >= 0.80:
                cutoff = i + 1; break
        data = data.iloc[:cutoff].copy()
        data["CumulPct"] = data["Spend"].cumsum() / grand_total * 100
        bar_colors = ClusterCharts._bar_colors_for(data["Cluster"].tolist())

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(
            x=data["Cluster"], y=data["Spend"],
            marker_color=bar_colors, name="Spend",
            text=[f"{v:,.1f}" for v in data["Spend"]],
            textposition="outside", textfont=dict(size=9, color=C_DARK),
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=data["Cluster"], y=data["CumulPct"],
            name="Cumul %", mode="lines+markers",
            line=dict(color=C_RED, width=2), marker=dict(size=5),
        ), secondary_y=True)
        fig.add_hline(y=80, line_dash="dash", line_color=C_TEAL, line_width=1.5,
                      secondary_y=True,
                      annotation_text="  80%", annotation_font=dict(color=C_TEAL, size=11))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Pareto Clusters → 80% du Spend",
                       font=dict(size=13, color=C_DARK), x=0),
            xaxis=dict(tickangle=-30, tickfont=dict(size=10, color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11, color=C_DARK, family="Segoe UI, Arial, sans-serif"),
                        bgcolor="rgba(255,255,255,0.9)"),
            height=400,
        )
        fig.update_yaxes(title_text="Cumul %", secondary_y=True,
                         range=[0,105], ticksuffix="%", gridcolor="#ECF0F1")
        return fig

    # ── 8. Top-10 vendors (cluster tab) ──────────────────────────────────────
    @staticmethod
    def top10_vendors(df):
        return ParetoCharts._pareto_fig(df, "Vendor Name", "Total  spend",
                                        "Top 10 Fournisseurs", hard_cap=10)

    # ── 9. Top-10 requesters (cluster tab) ───────────────────────────────────
    @staticmethod
    def top10_requesters(df):
        return ParetoCharts._pareto_fig(df, "Requester", "Total  spend",
                                        "Top 10 Requesters", hard_cap=10)

    # ── 10. Stacked CAPEX/OPEX per category ──────────────────────────────────
    @staticmethod
    def capex_opex_per_category(df):
        if "PSCS Category" not in df.columns:
            return go.Figure()
        grp = df.groupby("PSCS Category")[["CAPEX Spend","OPEX Spend"]].sum()
        grp = grp[grp.sum(axis=1) > 0].sort_values("CAPEX Spend", ascending=False).reset_index()
        cats = grp["PSCS Category"].tolist()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="CAPEX", x=cats, y=grp["CAPEX Spend"].tolist(),
            marker_color=C_BLUE,
            text=[f"{v:,.1f}" for v in grp["CAPEX Spend"]],
            textposition="inside", textfont=dict(size=9, color="white"),
        ))
        fig.add_trace(go.Bar(
            name="OPEX", x=cats, y=grp["OPEX Spend"].tolist(),
            marker_color=C_ORANGE,
            text=[f"{v:,.1f}" for v in grp["OPEX Spend"]],
            textposition="inside", textfont=dict(size=9, color="white"),
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="CAPEX vs OPEX par Catégorie — Stacked (kCHF)",
                       font=dict(size=14, color=C_DARK), x=0),
            barmode="stack",
            xaxis=dict(tickangle=-35, tickfont=dict(size=9, color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11, color=C_DARK, family="Segoe UI, Arial, sans-serif"),
                        bgcolor="rgba(255,255,255,0.9)"),
            height=420,
        )
        return fig

    # ── 11. Stacked CAPEX/OPEX per cluster ───────────────────────────────────
    @staticmethod
    def capex_opex_per_cluster(df):
        if "PSCS Cluster" not in df.columns:
            return go.Figure()
        grp = df.groupby("PSCS Cluster")[["CAPEX Spend","OPEX Spend"]].sum()
        grp = grp[grp.sum(axis=1) > 0].sort_values("CAPEX Spend", ascending=False).reset_index()
        clusters = grp["PSCS Cluster"].tolist()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="CAPEX", x=clusters, y=grp["CAPEX Spend"].tolist(),
            marker_color=C_BLUE,
            text=[f"{v:,.1f}" for v in grp["CAPEX Spend"]],
            textposition="inside", textfont=dict(size=9, color="white"),
        ))
        fig.add_trace(go.Bar(
            name="OPEX", x=clusters, y=grp["OPEX Spend"].tolist(),
            marker_color=C_ORANGE,
            text=[f"{v:,.1f}" for v in grp["OPEX Spend"]],
            textposition="inside", textfont=dict(size=9, color="white"),
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="CAPEX vs OPEX par Cluster — Stacked (kCHF)",
                       font=dict(size=14, color=C_DARK), x=0),
            barmode="stack",
            xaxis=dict(tickangle=-30, tickfont=dict(size=10, color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11, color=C_DARK, family="Segoe UI, Arial, sans-serif"),
                        bgcolor="rgba(255,255,255,0.9)"),
            height=400,
        )
        return fig

# ─── Legacy stubs ─────────────────────────────────────────────────────────────
class AdditionalCharts: pass
class OtherCharts:      pass


# ══════════════════════════════════════════════════════════════════════════════
# CAPEX / OPEX TAB CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class CapexOpexTabCharts:

    MONTHS_ORDER = ['January','February','March','April','May','June',
                    'July','August','September','October','November','December']
    MONTHS_SHORT = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec']

    # ── helper: month waterfall ───────────────────────────────────────────────
    @classmethod
    def _monthly_wf(cls, df, spend_col, base_year, title):
        comp_year = base_year + 1
        if "Année" not in df.columns or "Nom_Mois" not in df.columns:
            return go.Figure()
        def _m(yr):
            s = df[df["Année"]==yr].groupby("Nom_Mois")[spend_col].sum()
            return {m: float(s.get(m,0)) for m in cls.MONTHS_ORDER}
        bm = _m(base_year); cm = _m(comp_year)
        active = [m for m in cls.MONTHS_ORDER if bm[m]!=0 or cm[m]!=0]
        if not active:
            return go.Figure()
        deltas = [cm[m]-bm[m] for m in active]
        bt = sum(bm[m] for m in active); ct = sum(cm[m] for m in active)
        td = ct-bt; pct=(td/bt*100) if bt else 0
        return _build_waterfall(
            labels=active, values=deltas,
            base_val=bt, end_val=ct,
            base_label=str(base_year), end_label=str(comp_year),
            title=title, total_delta=td, total_pct=pct,
        )

    # ══ SECTION 1 — BAR PLOTS ════════════════════════════════════════════════

    # ── 1a. CAPEX vs OPEX total bar ───────────────────────────────────────────
    @staticmethod
    def capex_opex_total_bar(df):
        capex = float(df["CAPEX Spend"].sum()) if "CAPEX Spend" in df.columns else 0
        opex  = float(df["OPEX Spend"].sum())  if "OPEX Spend"  in df.columns else 0
        fig = go.Figure(go.Bar(
            x=["CAPEX","OPEX"], y=[capex, opex],
            marker_color=[C_BLUE, C_ORANGE],
            text=[f"{capex:,.1f}", f"{opex:,.1f}"],
            textposition="outside",
            textfont=dict(size=12, color=C_DARK),
            width=[0.4, 0.4],
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Spend CAPEX vs OPEX (kCHF)", font=dict(size=14,color=C_DARK), x=0),
            xaxis=dict(tickfont=dict(size=13,color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            height=380,
        )
        return fig

    # ── 1b. FI vs MM total bar ────────────────────────────────────────────────
    @staticmethod
    def fi_mm_total_bar(df):
        fi = float(df["FI Spend"].sum()) if "FI Spend" in df.columns else 0
        mm = float(df["MM Spend"].sum()) if "MM Spend" in df.columns else 0
        fig = go.Figure(go.Bar(
            x=["FI Spend","MM Spend"], y=[fi, mm],
            marker_color=[C_PURPLE, C_TEAL],
            text=[f"{fi:,.1f}", f"{mm:,.1f}"],
            textposition="outside",
            textfont=dict(size=12, color=C_DARK),
            width=[0.4, 0.4],
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Spend FI vs MM (kCHF)", font=dict(size=14,color=C_DARK), x=0),
            xaxis=dict(tickfont=dict(size=13,color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            height=380,
        )
        return fig

    # ── 1c. Stacked spend per year (CAPEX / OPEX stacks) ─────────────────────
    @staticmethod
    def stacked_spend_per_year(df):
        if "Année" not in df.columns:
            return go.Figure()
        tmp = df.dropna(subset=["Année"]).copy()
        tmp["yr"] = tmp["Année"].astype(float).astype(int)
        grp = tmp.groupby("yr")[["CAPEX Spend","OPEX Spend"]].sum().sort_index()
        xlabels = ["Y"+str(y) for y in grp.index]
        xtitles = [str(y) for y in grp.index]
        totals  = (grp["CAPEX Spend"] + grp["OPEX Spend"]).tolist()

        fig = go.Figure()
        fig.add_trace(go.Bar(name="CAPEX", x=xlabels, y=grp["CAPEX Spend"].tolist(),
                             marker_color=C_BLUE,
                             text=[f"{v:,.1f}" for v in grp["CAPEX Spend"]],
                             textposition="inside", textfont=dict(size=10,color="white")))
        fig.add_trace(go.Bar(name="OPEX",  x=xlabels, y=grp["OPEX Spend"].tolist(),
                             marker_color=C_ORANGE,
                             text=[f"{v:,.1f}" for v in grp["OPEX Spend"]],
                             textposition="inside", textfont=dict(size=10,color="white")))
        annotations = [dict(x=xl, y=t, text=f"<b>{t:,.1f}</b>",
                            showarrow=False, xanchor="center", yanchor="bottom", yshift=5,
                            font=dict(size=10,color=C_DARK))
                       for xl,t in zip(xlabels,totals)]
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Spend par Année — CAPEX/OPEX Stacked (kCHF)",
                       font=dict(size=14,color=C_DARK), x=0),
            barmode="stack",
            xaxis=dict(tickmode="array", tickvals=xlabels, ticktext=xtitles,
                       tickfont=dict(size=12,color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11, color=C_DARK, family="Segoe UI, Arial, sans-serif"),
                        bgcolor="rgba(255,255,255,0.9)"),
            annotations=annotations, height=400,
        )
        return fig

    # ── 1d. Spend across months — one bar group per month, one bar per year ───
    @staticmethod
    def monthly_spend_by_year(df):
        if "Année" not in df.columns or "Nom_Mois" not in df.columns:
            return go.Figure()
        tmp = df.dropna(subset=["Année"]).copy()
        tmp["yr"] = tmp["Année"].astype(float).astype(int)
        years = sorted(tmp["yr"].unique().tolist())
        MONTHS = CapexOpexTabCharts.MONTHS_ORDER
        SHORT  = CapexOpexTabCharts.MONTHS_SHORT

        fig = go.Figure()
        for i, yr in enumerate(years):
            sub = tmp[tmp["yr"]==yr].groupby("Nom_Mois")["Total  spend"].sum()
            vals = [float(sub.get(m,0)) for m in MONTHS]
            fig.add_trace(go.Bar(
                name=str(yr), x=SHORT, y=vals,
                marker_color=CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)],
                text=[f"{v:,.1f}" if v>0 else "" for v in vals],
                textposition="outside", textfont=dict(size=8,color=C_DARK),
            ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Spend Mensuel par Année (kCHF)",
                       font=dict(size=14,color=C_DARK), x=0),
            barmode="group",
            xaxis=dict(tickfont=dict(size=11,color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11, color=C_DARK, family="Segoe UI, Arial, sans-serif"),
                        bgcolor="rgba(255,255,255,0.9)"),
            height=420,
        )
        return fig

    # ══ SECTION 2 — VARIATION PLOTS (all driven by same base_year) ══════════

    # ── 2a. CAPEX/OPEX variation bar (Y vs Y+1) ───────────────────────────────
    @staticmethod
    def capex_opex_variation_bar(df, base_year):
        comp_year = base_year + 1
        cols = {"CAPEX": "CAPEX Spend", "OPEX": "OPEX Spend"}
        labels, base_vals, comp_vals, deltas, colors = [], [], [], [], []
        for lbl, col in cols.items():
            if col not in df.columns: continue
            b = float(df[df["Année"]==base_year][col].sum()) if "Année" in df.columns else 0
            c = float(df[df["Année"]==comp_year][col].sum()) if "Année" in df.columns else 0
            d = c - b
            labels.append(lbl); base_vals.append(b); comp_vals.append(c)
            deltas.append(d); colors.append(C_RED if d>0 else C_TEAL)

        fig = go.Figure()
        fig.add_trace(go.Bar(name=str(base_year), x=labels, y=base_vals,
                             marker_color=_hex_to_rgba(C_NAVY, 0.4),
                             text=[f"{v:,.1f}" for v in base_vals],
                             textposition="outside", textfont=dict(size=11,color=C_DARK)))
        fig.add_trace(go.Bar(name=str(comp_year), x=labels, y=comp_vals,
                             marker_color=[C_BLUE, C_ORANGE],
                             text=[f"{v:,.1f}" for v in comp_vals],
                             textposition="outside", textfont=dict(size=11,color=C_DARK)))
        annotations = [dict(x=l, y=max(b,c), text=f"<b>{d:+,.1f}</b>",
                            showarrow=False, yanchor="bottom", yshift=22,
                            font=dict(size=11, color=col))
                       for l,b,c,d,col in zip(labels,base_vals,comp_vals,deltas,colors)]
        fig.update_layout(
            **LAYOUT,
            title=dict(text=f"Variation CAPEX/OPEX — {base_year} vs {comp_year} (kCHF)",
                       font=dict(size=14,color=C_DARK), x=0),
            barmode="group",
            xaxis=dict(tickfont=dict(size=13,color=C_DARK)),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11, color=C_DARK, family="Segoe UI, Arial, sans-serif"),
                        bgcolor="rgba(255,255,255,0.9)"),
            annotations=annotations, height=400,
        )
        return fig

    # ── 2b. Total spend monthly variation waterfall ───────────────────────────
    @classmethod
    def total_monthly_variation(cls, df, base_year):
        return cls._monthly_wf(df, "Total  spend", base_year,
                               f"Variation Mensuelle Total Spend — {base_year} vs {base_year+1}")

    # ── 2c. Line chart — total spend evolution across all time ────────────────
    @staticmethod
    def spend_evolution_line(df):
        if "Année_Mois" not in df.columns and "Date" not in df.columns:
            return go.Figure()
        tmp = df.dropna(subset=["Date"]).copy()
        tmp["YM"] = tmp["Date"].dt.to_period("M").astype(str)
        grp = tmp.groupby("YM")["Total  spend"].sum().reset_index().sort_values("YM")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=grp["YM"], y=grp["Total  spend"],
            mode="lines+markers",
            line=dict(color=C_BLUE, width=2.5),
            marker=dict(size=5, color=C_BLUE),
            fill="tozeroy", fillcolor=_hex_to_rgba(C_BLUE, 0.1),
            name="Total Spend",
        ))
        fig.update_layout(
            **LAYOUT,
            title=dict(text="Évolution du Total Spend dans le temps (kCHF)",
                       font=dict(size=14,color=C_DARK), x=0),
            xaxis=dict(tickangle=-35, tickfont=dict(size=9,color=C_DARK),
                       title="Période"),
            yaxis=dict(title="kCHF", gridcolor="#ECF0F1"),
            height=380,
        )
        return fig

    # ── 2d. CAPEX monthly variation waterfall ────────────────────────────────
    @classmethod
    def capex_monthly_var(cls, df, base_year):
        return cls._monthly_wf(df, "CAPEX Spend", base_year,
                               f"Variation CAPEX Mensuelle — {base_year} vs {base_year+1}")

    # ── 2e. OPEX monthly variation waterfall ─────────────────────────────────
    @classmethod
    def opex_monthly_var(cls, df, base_year):
        return cls._monthly_wf(df, "OPEX Spend", base_year,
                               f"Variation OPEX Mensuelle — {base_year} vs {base_year+1}")

    # ── 2f. MM monthly variation waterfall ───────────────────────────────────
    @classmethod
    def mm_monthly_var(cls, df, base_year):
        return cls._monthly_wf(df, "MM Spend", base_year,
                               f"Variation MM Mensuelle — {base_year} vs {base_year+1}")

    # ── 2g. FI monthly variation waterfall ───────────────────────────────────
    @classmethod
    def fi_monthly_var(cls, df, base_year):
        return cls._monthly_wf(df, "FI Spend", base_year,
                               f"Variation FI Mensuelle — {base_year} vs {base_year+1}")