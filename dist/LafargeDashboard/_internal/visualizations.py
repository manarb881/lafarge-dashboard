"""
Visualizations - Lafarge Spend Analytics
High-contrast palette | increase=RED, decrease=GREEN (spend convention)

Year convention: comp_year selected → base_year = comp_year - 1
                 Selecting 2025 → shows 2024 vs 2025

═══════════════════════════════════════════════════════════════════
AUDIT NOTES — PARETO CALCULATION
═══════════════════════════════════════════════════════════════════
Standard Pareto (Loi de Pareto / 80-20):
  1. Group spend by dimension (Vendor, Requester, …)
  2. Sort descending by spend
  3. Compute cumulative % of TOTAL spend
  4. "80/20 cutoff" = fewest top entities whose cumulative spend ≥ 80%
     of the grand total

Formulas used:
  grand_total  = sum of ALL entity spends (before any cutoff)
  CumulPct[i]  = cumulative_spend[0..i] / grand_total × 100
  cutoff       = first index where CumulPct ≥ 80 (1-based count)

Hard-cap behaviour:
  When hard_cap (e.g. top-10) is applied AFTER finding the natural
  80% cutoff, the number of bars shown may be less than the true
  cutoff.  The chart title now shows the ACTUAL % covered by the
  bars displayed (not a hardcoded "80%").

Axis labels: all tick / title text forced to #111111 (near-black).
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import numpy as np

# ─── Palette ──────────────────────────────────────────────────────────────────
C_NAVY   = "#1B3A5C"
C_TEAL   = "#17A589"   # decrease (savings — good)
C_RED    = "#E74C3C"   # increase (more spend — bad)
C_ORANGE = "#E67E22"   # OPEX
C_BLUE   = "#2980B9"   # CAPEX
C_PURPLE = "#8E44AD"
C_GREY   = "#95A5A6"
C_DARK   = "#111111"   # all axis/tick text — forced dark
WHITE    = "#FFFFFF"
LIGHT_GREY = "#D5DBE1"
C_CUMUL  = "#F39C12"   # cumulative line on waterfalls

CLUSTER_PALETTE = [
    "#2980B9","#E74C3C","#27AE60","#E67E22","#8E44AD",
    "#17A589","#F39C12","#2C3E50","#C0392B","#1ABC9C",
    "#D35400","#7F8C8D",
]

MONTHS_ORDER = ['January','February','March','April','May','June',
                'July','August','September','October','November','December']
MONTHS_SHORT = ['Jan','Feb','Mar','Apr','May','Jun',
                'Jul','Aug','Sep','Oct','Nov','Dec']

LAYOUT = dict(
    font=dict(family="Segoe UI, Arial, sans-serif", size=12, color=C_DARK),
    paper_bgcolor=WHITE,
    plot_bgcolor="#FAFAFA",
    margin=dict(t=65, b=55, l=60, r=35),
    title_font=dict(color=C_DARK, size=14, family="Segoe UI, Arial, sans-serif"),
)

# Shared axis defaults — always dark ticks
_XAXIS = dict(tickfont=dict(size=11, color=C_DARK), title_font=dict(color=C_DARK))
_YAXIS = dict(tickfont=dict(size=11, color=C_DARK), title_font=dict(color=C_DARK),
              gridcolor=LIGHT_GREY)
_LEGEND = dict(font=dict(color=C_DARK, size=11), bgcolor="rgba(255,255,255,0.9)")


def _hex_to_rgba(hex_color, alpha=0.40):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{alpha})"

def _fmt(v):   return f"{round(v):,}"
def _fmt_d(v): return f"+{round(v):,}" if v >= 0 else f"{round(v):,}"


# ══════════════════════════════════════════════════════════════════════════════
# SHARED WATERFALL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def _build_waterfall(labels, values, base_val, end_val,
                     base_label, end_label, title,
                     total_delta=None, total_pct=None,
                     height=440, show_cumulative=True):
    """
    Waterfall with:
    • Zoomed y-axis (focuses on variation range, not absolute zero)
    • Cumulative-sum secondary-axis overlay line (orange dashes)
    • All values as rounded integers (kCHF)
    • ALL axis text forced to #111111
    """
    measure = ["absolute"] + ["relative"] * len(labels) + ["absolute"]
    x       = [base_label] + labels + [end_label]
    y_wf    = [base_val]   + values + [end_val]

    # Running totals for zoom range
    running = [base_val]
    acc = base_val
    for v in values:
        acc += v
        running.append(acc)
    running.append(end_val)

    y_min = min(running); y_max = max(running)
    span  = max(abs(y_max - y_min), 1.0)
    y_lo  = y_min - span * 0.20
    y_hi  = y_max + span * 0.42

    # Cumulative delta values for overlay line
    cum_vals = [0]
    acc_cum  = 0
    for v in values:
        acc_cum += v
        cum_vals.append(acc_cum)
    cum_vals.append(acc_cum)

    text_vals = [f"<b>{_fmt(v)}</b>" if m == "absolute" else _fmt_d(v)
                 for m, v in zip(measure, y_wf)]

    if show_cumulative:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    wf = go.Waterfall(
        orientation="v", measure=measure, x=x, y=y_wf,
        text=text_vals, textposition="outside",
        textfont=dict(size=11, color=C_DARK, family="Segoe UI, Arial"),
        connector=dict(line=dict(color="#BDC3C7", width=1, dash="dot")),
        decreasing=dict(marker_color=C_TEAL),
        increasing=dict(marker_color=C_RED),
        totals=dict(marker_color=C_NAVY),
        cliponaxis=False,
        name="Variation",
    )
    if show_cumulative:
        fig.add_trace(wf, secondary_y=False)
        fig.add_trace(go.Scatter(
            x=x, y=cum_vals, mode="lines+markers+text", name="Cumulé",
            line=dict(color=C_CUMUL, width=2.5, dash="dash"),
            marker=dict(size=7, color=C_CUMUL, symbol="diamond"),
            text=["" if (i == 0 or i == len(cum_vals)-1) else _fmt_d(v)
                  for i, v in enumerate(cum_vals)],
            textposition="top center",
            textfont=dict(size=9, color=C_CUMUL),
        ), secondary_y=True)
    else:
        fig.add_trace(wf)

    annotations = []
    if total_delta is not None:
        color = C_TEAL if total_delta <= 0 else C_RED
        sign  = "▼" if total_delta <= 0 else "▲"
        badge = f"{sign} {_fmt_d(total_delta)}"
        if total_pct is not None:
            badge += f"  ({total_pct:+.1f}%)"
        annotations.append(dict(
            x=0.5, y=1.14, xref="paper", yref="paper",
            text=(f'<span style="background:{color};color:white;padding:5px 14px;'
                  f'border-radius:20px;font-weight:bold;font-size:12px;">{badge}</span>'),
            showarrow=False, font=dict(size=12, color=C_DARK), align="center",
        ))

    fig.update_layout(
        **LAYOUT,
        title=dict(text=title, font=dict(size=14, color=C_DARK), x=0),
        yaxis=dict(**_YAXIS,
                   title="kCHF",
                   zeroline=True, zerolinecolor="#BDC3C7", zerolinewidth=1,
                   range=[y_lo, y_hi], rangemode="normal"),
        xaxis=dict(**_XAXIS, type="category"),
        showlegend=show_cumulative,
        legend=dict(**_LEGEND, orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        annotations=annotations,
        height=height,
    )
    if show_cumulative:
        cum_max = max(abs(v) for v in cum_vals) if cum_vals else 1
        fig.update_yaxes(
            title_text="Cumulé (kCHF)", secondary_y=True,
            gridcolor="rgba(0,0,0,0)",
            zeroline=True, zerolinecolor="#BDC3C7",
            range=[-(cum_max * 1.6), cum_max * 1.6],
            tickfont=dict(size=11, color=C_DARK),
            title_font=dict(color=C_DARK),
        )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# GENERIC STACKED CAPEX / OPEX BAR
# ══════════════════════════════════════════════════════════════════════════════
def _stacked_capex_opex(df, group_col, title, height=420):
    if group_col not in df.columns:
        return go.Figure()
    grp = df.groupby(group_col)[["CAPEX Spend","OPEX Spend"]].sum()
    grp = grp[grp.sum(axis=1) > 0].copy()
    grp["Total"] = grp["CAPEX Spend"] + grp["OPEX Spend"]
    grp = grp.sort_values("Total", ascending=False).reset_index()
    labels = grp[group_col].tolist()
    capex  = grp["CAPEX Spend"].tolist()
    opex   = grp["OPEX Spend"].tolist()
    totals = grp["Total"].tolist()
    fig = go.Figure()
    fig.add_trace(go.Bar(name="CAPEX", x=labels, y=capex, marker_color=C_BLUE,
                         text=[_fmt(v) for v in capex],
                         textposition="inside", textfont=dict(size=9, color=WHITE)))
    fig.add_trace(go.Bar(name="OPEX", x=labels, y=opex, marker_color=C_ORANGE,
                         text=[_fmt(v) for v in opex],
                         textposition="inside", textfont=dict(size=9, color=WHITE)))
    annotations = [dict(x=lbl, y=t, text=f"<b>{_fmt(t)}</b>",
                        showarrow=False, xanchor="center", yanchor="bottom", yshift=4,
                        font=dict(size=10, color=C_DARK))
                   for lbl, t in zip(labels, totals)]
    fig.update_layout(**LAYOUT,
        title=dict(text=title, font=dict(size=14, color=C_DARK), x=0),
        barmode="stack",
        xaxis=dict(**_XAXIS, tickangle=-30),
        yaxis=dict(**_YAXIS, title="kCHF"),
        legend=dict(**_LEGEND, orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        annotations=annotations, height=height)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# PARETO CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class ParetoCharts:
    """
    Pareto chart — 80/20 rule applied to procurement spend.

    CALCULATION (verified):
    ─────────────────────
    grand_total = sum of spend across ALL entities in the filtered df.

    Step 1 — Find the natural 80% cutoff:
      Sort entities descending by spend.
      Iterate; accumulate spend; stop when cumulative / grand_total >= 0.80.
      cutoff_natural = index of that entity (1-based).

    Step 2 — Apply hard_cap (optional display limit):
      cutoff_display = min(cutoff_natural, hard_cap)
      Note: if hard_cap < cutoff_natural, fewer bars are shown and the
      cumulative line may NOT reach 80%.  The chart title always shows
      the ACTUAL % covered by the displayed bars (not a hardcoded "80%").

    Step 3 — Cumulative % line:
      CumulPct[i] = sum(top-i spend) / grand_total × 100
      grand_total is the FULL total (all entities), so the line
      correctly shows what fraction of overall spend is covered.

    80% threshold line is always drawn on the secondary axis.
    """

    @staticmethod
    def _pareto_fig(df: pd.DataFrame, dim_col: str, spend_col: str,
                    title: str, hard_cap: int = None) -> go.Figure:
        if dim_col not in df.columns or spend_col not in df.columns:
            return go.Figure()

        # ── Step 1: aggregate and sort ────────────────────────────────────────
        all_data = (df.groupby(dim_col)[spend_col]
                      .sum()
                      .sort_values(ascending=False)
                      .reset_index())
        all_data.columns = ["Dimension", "Spend"]
        all_data = all_data[all_data["Spend"] > 0].reset_index(drop=True)
        if all_data.empty:
            return go.Figure()

        n_total     = len(all_data)
        grand_total = all_data["Spend"].sum()   # sum of ALL entities (denominator)

        # ── Step 2: find the natural 80% cutoff ──────────────────────────────
        cumsum          = 0.0
        cutoff_natural  = n_total   # default: all entities needed
        for i, v in enumerate(all_data["Spend"]):
            cumsum += v
            if cumsum / grand_total >= 0.80:
                cutoff_natural = i + 1   # 1-based count
                break

        # ── Step 3: apply hard_cap (display limit) ────────────────────────────
        cutoff_display = (min(cutoff_natural, hard_cap)
                          if hard_cap is not None
                          else cutoff_natural)

        # ── Step 4: slice to displayed entities ──────────────────────────────
        data = all_data.iloc[:cutoff_display].copy()

        # CumulPct: running sum / grand_total × 100
        # grand_total is the FULL total — so the line correctly shows
        # what fraction of ALL spend is concentrated in the top-N entities.
        data["CumulPct"] = data["Spend"].cumsum() / grand_total * 100

        # Actual % of total spend covered by the displayed bars
        actual_pct_covered = float(data["Spend"].sum() / grand_total * 100)
        pct_entities       = cutoff_display / n_total * 100

        # ── Build subtitle ────────────────────────────────────────────────────
        subtitle = (
            f"{cutoff_display} / {n_total} entités "
            f"({pct_entities:.0f}%) "
            f"→ {actual_pct_covered:.0f}% du spend total"
        )

        bar_colors = [CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)]
                      for i in range(len(data))]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(go.Bar(
            x=data["Dimension"], y=data["Spend"],
            name="Spend (kCHF)",
            marker_color=bar_colors,
            text=[_fmt(v) for v in data["Spend"]],
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

        # 80% reference line on the secondary axis
        fig.add_hline(
            y=80,
            line_dash="dash", line_color=C_TEAL, line_width=2,
            secondary_y=True,
            annotation_text="  80%",
            annotation_font=dict(color=C_TEAL, size=11),
        )

        fig.update_layout(**LAYOUT,
            title=dict(
                text=(f"<b>{title}</b><br>"
                      f"<sup style='color:{C_GREY}'>{subtitle}</sup>"),
                font=dict(size=13, color=C_DARK), x=0,
            ),
            xaxis=dict(**_XAXIS, tickangle=-35, type="category"),
            yaxis=dict(**_YAXIS, title="Spend (kCHF)"),
            legend=dict(**_LEGEND, orientation="h", yanchor="bottom",
                        y=1.02, xanchor="right", x=1),
            height=430, bargap=0.25,
        )
        fig.update_yaxes(
            title_text="Cumul %", secondary_y=True,
            range=[0, 105], ticksuffix="%",
            tickfont=dict(size=11, color=C_DARK),
            title_font=dict(color=C_DARK),
            gridcolor="rgba(0,0,0,0)",
        )
        return fig

    @staticmethod
    def vendor_pareto(df, hard_cap=10):
        return ParetoCharts._pareto_fig(df,"Vendor Name","Total  spend",
                                        "Pareto Fournisseurs",hard_cap=hard_cap)
    @staticmethod
    def requester_pareto(df, hard_cap=10):
        return ParetoCharts._pareto_fig(df,"Requester","Total  spend",
                                        "Pareto Requesters",hard_cap=hard_cap)
    @staticmethod
    def cost_center_pareto(df):
        return ParetoCharts._pareto_fig(df,"Cost Center ID","Total  spend",
                                        "Pareto Cost Center",hard_cap=10)
    @staticmethod
    def gl_account_pareto(df):
        return ParetoCharts._pareto_fig(df,"GL Account Name","Total  spend",
                                        "Pareto GL Account")
    @staticmethod
    def purchasing_group_pareto(df):
        return ParetoCharts._pareto_fig(df,"Purchasing Group Name","Total  spend",
                                        "Pareto Purchasing Group")


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class OverviewCharts:

    @staticmethod
    def cluster_variation_waterfall(df, comp_year):
        base_year = comp_year - 1
        if "Année" not in df.columns or "PSCS Cluster" not in df.columns:
            return go.Figure()
        y_base = df[df["Année"]==base_year].groupby("PSCS Cluster")["Total  spend"].sum()
        y_comp = df[df["Année"]==comp_year].groupby("PSCS Cluster")["Total  spend"].sum()
        clusters = sorted(set(y_base.index)|set(y_comp.index))
        deltas   = [float(y_comp.get(c,0)-y_base.get(c,0)) for c in clusters]
        bt=float(y_base.sum()); ct=float(y_comp.sum())
        td=ct-bt; pct=(td/bt*100) if bt else 0
        return _build_waterfall(labels=clusters, values=deltas,
            base_val=bt, end_val=ct,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation du Spend par Cluster — {base_year} vs {comp_year}",
            total_delta=td, total_pct=pct, height=480)

    @staticmethod
    def cluster_category_treemap(df):
        if "PSCS Cluster" not in df.columns or "PSCS Category" not in df.columns:
            return go.Figure()
        data = df.groupby(["PSCS Cluster","PSCS Category"])["Total  spend"].sum().reset_index()
        data.columns = ["Cluster","Category","Spend"]
        data = data[data["Spend"] > 0]
        if data.empty: return go.Figure()
        fig = px.treemap(data, path=["Cluster","Category"], values="Spend",
                         color="Cluster", color_discrete_sequence=CLUSTER_PALETTE)
        fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{value:,.0f} kCHF",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b><br>Spend: %{value:,.0f} kCHF<extra></extra>",
        )
        fig.update_layout(**LAYOUT,
            title=dict(text="Treemap Spend — Cluster → Catégorie (kCHF)",
                       font=dict(size=14,color=C_DARK),x=0), height=440)
        return fig

    @staticmethod
    def cluster_spend_bar(df):
        if "PSCS Cluster" not in df.columns: return go.Figure()
        data=(df.groupby("PSCS Cluster")["Total  spend"]
                .sum().sort_values(ascending=False).reset_index())
        data.columns=["Cluster","Spend"]
        colors=[CLUSTER_PALETTE[i%len(CLUSTER_PALETTE)] for i in range(len(data))]
        fig=go.Figure(go.Bar(x=data["Cluster"],y=data["Spend"],marker_color=colors,
                             text=[_fmt(v) for v in data["Spend"]],
                             textposition="outside",textfont=dict(size=10,color=C_DARK)))
        fig.update_layout(**LAYOUT,
            title=dict(text="Spend par Cluster (kCHF)",font=dict(size=14,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS,tickangle=-30),
            yaxis=dict(**_YAXIS,title="kCHF"),height=430)
        return fig

    @staticmethod
    def top10_company_codes(df):
        col="Company Code descr"
        if col not in df.columns: return go.Figure()
        data=(df.groupby(col)["Total  spend"]
                .sum().sort_values(ascending=False).head(10).reset_index())
        data.columns=["Company Code","Spend"]
        colors=[CLUSTER_PALETTE[i%len(CLUSTER_PALETTE)] for i in range(len(data))]
        fig=go.Figure(go.Bar(x=data["Spend"],y=data["Company Code"],orientation="h",
                             marker_color=colors[::-1],
                             text=[_fmt(v) for v in data["Spend"]],
                             textposition="outside",textfont=dict(size=10,color=C_DARK)))
        fig.update_layout(**LAYOUT,
            title=dict(text="Top 10 Company Code (kCHF)",font=dict(size=14,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS,title="kCHF"),
            yaxis=dict(**_YAXIS,autorange="reversed"),height=400)
        return fig


# ══════════════════════════════════════════════════════════════════════════════
# CAPEX / OPEX OVERVIEW CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class CapexOpexCharts:

    @classmethod
    def _monthly_variation(cls, df, spend_col, comp_year, title):
        base_year=comp_year-1
        if "Année" not in df.columns or "Nom_Mois" not in df.columns: return go.Figure()
        def _m(yr):
            s=df[df["Année"]==yr].groupby("Nom_Mois")[spend_col].sum()
            return {m: float(s.get(m,0)) for m in MONTHS_ORDER}
        bm=_m(base_year); cm=_m(comp_year)
        active=[m for m in MONTHS_ORDER if bm[m]!=0 or cm[m]!=0]
        if not active: return go.Figure()
        deltas=[cm[m]-bm[m] for m in active]
        bt=sum(bm[m] for m in active); ct=sum(cm[m] for m in active)
        td=ct-bt; pct=(td/bt*100) if bt else 0
        return _build_waterfall(labels=active, values=deltas, base_val=bt, end_val=ct,
            base_label=str(base_year), end_label=str(comp_year),
            title=title, total_delta=td, total_pct=pct)

    @classmethod
    def capex_monthly_variation(cls, df, comp_year):
        return cls._monthly_variation(df,"CAPEX Spend",comp_year,
            f"Variation CAPEX mensuelle — {comp_year-1} vs {comp_year}")

    @classmethod
    def opex_monthly_variation(cls, df, comp_year):
        return cls._monthly_variation(df,"OPEX Spend",comp_year,
            f"Variation OPEX mensuelle — {comp_year-1} vs {comp_year}")

    @staticmethod
    def total_spend_yearly_variation(df, comp_year):
        base_year=comp_year-1
        if "Année" not in df.columns: return go.Figure()
        by_year=df.groupby("Année")["Total  spend"].sum()
        base_val=float(by_year.get(base_year,0)); comp_val=float(by_year.get(comp_year,0))
        if base_val==0 and comp_val==0: return go.Figure()
        delta=comp_val-base_val; pct=(delta/base_val*100) if base_val else 0
        return _build_waterfall(
            labels=[f"Variation {base_year}→{comp_year}"], values=[delta],
            base_val=base_val, end_val=comp_val,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation du Total Spend — {base_year} vs {comp_year}",
            total_delta=delta, total_pct=pct, show_cumulative=False)

    @staticmethod
    def capex_opex_stacked_bar(df):
        if "Année" not in df.columns: return go.Figure()
        tmp=df.dropna(subset=["Année"]).copy()
        tmp["yr"]=tmp["Année"].astype(float).astype(int)
        grp=tmp.groupby("yr")[["CAPEX Spend","OPEX Spend"]].sum().sort_index()
        if grp.empty: return go.Figure()
        xlabels=["Y"+str(y) for y in grp.index]; xtitles=[str(y) for y in grp.index]
        capex=grp["CAPEX Spend"].tolist(); opex=grp["OPEX Spend"].tolist()
        totals=[c+o for c,o in zip(capex,opex)]
        fig=go.Figure()
        fig.add_trace(go.Bar(name="CAPEX",x=xlabels,y=capex,marker_color=C_BLUE,
                             text=[_fmt(v) for v in capex],
                             textposition="inside",textfont=dict(size=11,color=WHITE)))
        fig.add_trace(go.Bar(name="OPEX",x=xlabels,y=opex,marker_color=C_ORANGE,
                             text=[_fmt(v) for v in opex],
                             textposition="inside",textfont=dict(size=11,color=WHITE)))
        annotations=[dict(x=xl,y=t,text=f"<b>{_fmt(t)}</b>",
                          showarrow=False,xanchor="center",yanchor="bottom",yshift=5,
                          font=dict(size=10,color=C_DARK))
                     for xl,t in zip(xlabels,totals)]
        fig.update_layout(**LAYOUT,
            title=dict(text="CAPEX + OPEX par Année — Stacked (kCHF)",
                       font=dict(size=14,color=C_DARK),x=0),
            barmode="stack",
            xaxis=dict(**_XAXIS,tickmode="array",tickvals=xlabels,ticktext=xtitles),
            yaxis=dict(**_YAXIS,title="kCHF"),
            legend=dict(**_LEGEND,orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
            annotations=annotations, height=430)
        return fig


# ══════════════════════════════════════════════════════════════════════════════
# CLUSTER TAB CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class ClusterCharts:

    @staticmethod
    def _bar_colors_for(labels):
        unique=list(dict.fromkeys(labels))
        mapping={v:CLUSTER_PALETTE[i%len(CLUSTER_PALETTE)] for i,v in enumerate(unique)}
        return [mapping[l] for l in labels]

    # ── Generic filtered monthly variation ───────────────────────────────────
    @staticmethod
    def _filtered_monthly_var(df, spend_col, comp_year, title,
                               cluster=None, category=None, pscs_name=None):
        base_year=comp_year-1
        sub=df.copy()
        if cluster   and "PSCS Cluster"  in sub.columns: sub=sub[sub["PSCS Cluster"]  ==cluster]
        if category  and "PSCS Category" in sub.columns: sub=sub[sub["PSCS Category"] ==category]
        if pscs_name and "PSCS Name"     in sub.columns: sub=sub[sub["PSCS Name"]     ==pscs_name]
        if sub.empty or "Nom_Mois" not in sub.columns: return go.Figure()
        def _m(yr):
            s=sub[sub["Année"]==yr].groupby("Nom_Mois")[spend_col].sum()
            return {m: float(s.get(m,0)) for m in MONTHS_ORDER}
        bm=_m(base_year); cm=_m(comp_year)
        active=[m for m in MONTHS_ORDER if bm[m]!=0 or cm[m]!=0]
        if not active: return go.Figure()
        deltas=[cm[m]-bm[m] for m in active]
        bt=sum(bm[m] for m in active); ct=sum(cm[m] for m in active)
        td=ct-bt; pct=(td/bt*100) if bt else 0
        return _build_waterfall(labels=active, values=deltas, base_val=bt, end_val=ct,
            base_label=str(base_year), end_label=str(comp_year),
            title=title, total_delta=td, total_pct=pct)

    @staticmethod
    def capex_variation(df, comp_year, cluster=None, category=None, pscs_name=None):
        label=pscs_name or category or cluster or "All"
        return ClusterCharts._filtered_monthly_var(df,"CAPEX Spend",comp_year,
            f"Variation CAPEX Mensuelle — {label} — {comp_year-1} vs {comp_year}",
            cluster=cluster, category=category, pscs_name=pscs_name)

    @staticmethod
    def opex_variation(df, comp_year, cluster=None, category=None, pscs_name=None):
        label=pscs_name or category or cluster or "All"
        return ClusterCharts._filtered_monthly_var(df,"OPEX Spend",comp_year,
            f"Variation OPEX Mensuelle — {label} — {comp_year-1} vs {comp_year}",
            cluster=cluster, category=category, pscs_name=pscs_name)

    @staticmethod
    def stacked_capex_opex_cluster(df):
        return _stacked_capex_opex(df,"PSCS Cluster","CAPEX vs OPEX par Cluster (kCHF)")

    @staticmethod
    def stacked_capex_opex_category(df, cluster=None):
        sub=df[df["PSCS Cluster"]==cluster].copy() if cluster and "PSCS Cluster" in df.columns else df.copy()
        title=f"CAPEX vs OPEX par Catégorie — {cluster} (kCHF)" if cluster else "CAPEX vs OPEX par Catégorie (kCHF)"
        return _stacked_capex_opex(sub,"PSCS Category",title)

    @staticmethod
    def stacked_capex_opex_pscs_name(df, cluster=None, category=None):
        sub=df.copy()
        if cluster  and "PSCS Cluster"  in sub.columns: sub=sub[sub["PSCS Cluster"]  ==cluster]
        if category and "PSCS Category" in sub.columns: sub=sub[sub["PSCS Category"] ==category]
        title=f"CAPEX vs OPEX par PSCS Name — {category} (kCHF)" if category else "CAPEX vs OPEX par PSCS Name (kCHF)"
        return _stacked_capex_opex(sub,"PSCS Name",title)

    @staticmethod
    def spend_per_cluster(df):
        if "PSCS Cluster" not in df.columns: return go.Figure()
        data=df.groupby("PSCS Cluster")["Total  spend"].sum().sort_values(ascending=False).reset_index()
        data.columns=["Cluster","Spend"]
        colors=ClusterCharts._bar_colors_for(data["Cluster"].tolist())
        fig=go.Figure(go.Bar(x=data["Cluster"],y=data["Spend"],marker_color=colors,
                             text=[_fmt(v) for v in data["Spend"]],
                             textposition="outside",textfont=dict(size=10,color=C_DARK)))
        fig.update_layout(**LAYOUT,
            title=dict(text="Spend par Cluster (kCHF)",font=dict(size=14,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS,tickangle=-30),yaxis=dict(**_YAXIS,title="kCHF"),height=400)
        return fig

    @staticmethod
    def cluster_yoy_variation(df, comp_year):
        base_year=comp_year-1
        if "Année" not in df.columns or "PSCS Cluster" not in df.columns: return go.Figure()
        y_base=df[df["Année"]==base_year].groupby("PSCS Cluster")["Total  spend"].sum()
        y_comp=df[df["Année"]==comp_year].groupby("PSCS Cluster")["Total  spend"].sum()
        clusters=sorted(set(y_base.index)|set(y_comp.index))
        deltas=[float(y_comp.get(c,0)-y_base.get(c,0)) for c in clusters]
        bt=float(y_base.sum()); ct=float(y_comp.sum())
        td=ct-bt; pct=(td/bt*100) if bt else 0
        return _build_waterfall(labels=clusters, values=deltas, base_val=bt, end_val=ct,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation du Spend par Cluster — {base_year} vs {comp_year}",
            total_delta=td, total_pct=pct, height=480)

    @staticmethod
    def spend_per_category(df, cluster):
        sub=df[df["PSCS Cluster"]==cluster] if "PSCS Cluster" in df.columns else df
        if "PSCS Category" not in sub.columns or sub.empty: return go.Figure()
        data=sub.groupby("PSCS Category")["Total  spend"].sum().sort_values(ascending=False).reset_index()
        data.columns=["Category","Spend"]
        cluster_list=sorted(df["PSCS Cluster"].dropna().unique().tolist()) if "PSCS Cluster" in df.columns else []
        cidx=cluster_list.index(cluster) if cluster in cluster_list else 0
        color=CLUSTER_PALETTE[cidx%len(CLUSTER_PALETTE)]
        fig=go.Figure(go.Bar(x=data["Category"],y=data["Spend"],marker_color=color,
                             text=[_fmt(v) for v in data["Spend"]],
                             textposition="outside",textfont=dict(size=10,color=C_DARK)))
        fig.update_layout(**LAYOUT,
            title=dict(text=f"Spend par Catégorie — {cluster} (kCHF)",
                       font=dict(size=14,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS,tickangle=-30),yaxis=dict(**_YAXIS,title="kCHF"),height=400)
        return fig

    @staticmethod
    def cluster_monthly_variation(df, cluster, comp_year):
        return ClusterCharts._filtered_monthly_var(df,"Total  spend",comp_year,
            f"Variation Mensuelle — {cluster} — {comp_year-1} vs {comp_year}",cluster=cluster)

    @staticmethod
    def category_yoy_variation(df, cluster, comp_year):
        """Waterfall: variation par catégorie dans un cluster."""
        base_year=comp_year-1
        sub=df[df["PSCS Cluster"]==cluster] if "PSCS Cluster" in df.columns else df
        if "PSCS Category" not in sub.columns: return go.Figure()
        y_base=sub[sub["Année"]==base_year].groupby("PSCS Category")["Total  spend"].sum()
        y_comp=sub[sub["Année"]==comp_year].groupby("PSCS Category")["Total  spend"].sum()
        cats=sorted(set(y_base.index)|set(y_comp.index))
        deltas=[float(y_comp.get(c,0)-y_base.get(c,0)) for c in cats]
        bt=float(y_base.sum()); ct=float(y_comp.sum())
        td=ct-bt; pct=(td/bt*100) if bt else 0
        return _build_waterfall(labels=cats, values=deltas, base_val=bt, end_val=ct,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation par Catégorie — {cluster} — {base_year} vs {comp_year}",
            total_delta=td, total_pct=pct, height=460)

    @staticmethod
    def spend_per_pscs_name(df, cluster, category):
        sub=df.copy()
        if cluster  and "PSCS Cluster"  in sub.columns: sub=sub[sub["PSCS Cluster"]  ==cluster]
        if category and "PSCS Category" in sub.columns: sub=sub[sub["PSCS Category"] ==category]
        if "PSCS Name" not in sub.columns or sub.empty: return go.Figure()
        data=sub.groupby("PSCS Name")["Total  spend"].sum().sort_values(ascending=False).reset_index()
        data.columns=["PSCS Name","Spend"]
        data=data[data["Spend"]>0]
        if data.empty: return go.Figure()
        colors=[CLUSTER_PALETTE[i%len(CLUSTER_PALETTE)] for i in range(len(data))]
        fig=go.Figure(go.Bar(x=data["PSCS Name"],y=data["Spend"],marker_color=colors,
                             text=[_fmt(v) for v in data["Spend"]],
                             textposition="outside",textfont=dict(size=10,color=C_DARK)))
        fig.update_layout(**LAYOUT,
            title=dict(text=f"Spend par PSCS Name — {category} (kCHF)",
                       font=dict(size=14,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS,tickangle=-30),yaxis=dict(**_YAXIS,title="kCHF"),height=420)
        return fig

    @staticmethod
    def pscs_name_yoy_variation(df, cluster, category, comp_year):
        """Waterfall: variation par PSCS Name dans une catégorie."""
        base_year=comp_year-1
        sub=df.copy()
        if cluster  and "PSCS Cluster"  in sub.columns: sub=sub[sub["PSCS Cluster"]  ==cluster]
        if category and "PSCS Category" in sub.columns: sub=sub[sub["PSCS Category"] ==category]
        if "PSCS Name" not in sub.columns or sub.empty: return go.Figure()
        y_base=sub[sub["Année"]==base_year].groupby("PSCS Name")["Total  spend"].sum()
        y_comp=sub[sub["Année"]==comp_year].groupby("PSCS Name")["Total  spend"].sum()
        names=sorted(set(y_base.index)|set(y_comp.index))
        deltas=[float(y_comp.get(n,0)-y_base.get(n,0)) for n in names]
        bt=float(y_base.sum()); ct=float(y_comp.sum())
        td=ct-bt; pct=(td/bt*100) if bt else 0
        return _build_waterfall(labels=names, values=deltas, base_val=bt, end_val=ct,
            base_label=str(base_year), end_label=str(comp_year),
            title=f"Variation PSCS Name — {category} — {base_year} vs {comp_year}",
            total_delta=td, total_pct=pct, height=460)

    @staticmethod
    def pscs_name_monthly_variation(df, pscs_name, comp_year):
        return ClusterCharts._filtered_monthly_var(df,"Total  spend",comp_year,
            f"Variation Mensuelle — {pscs_name} — {comp_year-1} vs {comp_year}",
            pscs_name=pscs_name)

    @staticmethod
    def category_monthly_variation(df, category, comp_year, cluster=None):
        return ClusterCharts._filtered_monthly_var(df,"Total  spend",comp_year,
            f"Variation Mensuelle — {category} — {comp_year-1} vs {comp_year}",
            cluster=cluster, category=category)

    @staticmethod
    def category_pareto_by_cluster(df):
        if "PSCS Category" not in df.columns or "PSCS Cluster" not in df.columns:
            return go.Figure()
        data=(df.groupby(["PSCS Category","PSCS Cluster"])["Total  spend"].sum().reset_index())
        data.columns=["Category","Cluster","Spend"]
        data=(data.groupby("Category").agg(Spend=("Spend","sum"),Cluster=("Cluster","first")).reset_index())
        data=data[data["Spend"]>0].sort_values("Spend",ascending=False).reset_index(drop=True)
        n_total=len(data); gt=data["Spend"].sum()
        cumsum=0; cutoff=n_total
        for i,v in enumerate(data["Spend"]):
            cumsum+=v
            if cumsum/gt>=0.80: cutoff=i+1; break
        data=data.iloc[:cutoff].copy()
        data["CumulPct"]=data["Spend"].cumsum()/gt*100
        clusters=sorted(df["PSCS Cluster"].dropna().unique().tolist())
        cmap={c:CLUSTER_PALETTE[i%len(CLUSTER_PALETTE)] for i,c in enumerate(clusters)}
        bar_colors=[cmap.get(c,C_GREY) for c in data["Cluster"]]
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Bar(x=data["Category"],y=data["Spend"],marker_color=bar_colors,
                             name="Spend",text=[_fmt(v) for v in data["Spend"]],
                             textposition="outside",textfont=dict(size=9,color=C_DARK)),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=data["Category"],y=data["CumulPct"],name="Cumul %",
                                 mode="lines+markers",line=dict(color=C_RED,width=2),
                                 marker=dict(size=5)),secondary_y=True)
        fig.add_hline(y=80,line_dash="dash",line_color=C_TEAL,line_width=1.5,secondary_y=True,
                      annotation_text="  80%",annotation_font=dict(color=C_TEAL,size=11))
        for c,col in cmap.items():
            if c in data["Cluster"].values:
                fig.add_trace(go.Bar(x=[None],y=[None],name=c,marker_color=col,showlegend=True),
                              secondary_y=False)
        fig.update_layout(**LAYOUT,
            title=dict(text="Pareto Catégories → 80% du Spend (couleur = Cluster)",
                       font=dict(size=13,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS,tickangle=-35),yaxis=dict(**_YAXIS,title="kCHF"),
            barmode="stack",
            legend=dict(orientation="h",yanchor="top",y=-0.35,xanchor="center",x=0.5,
                        font=dict(size=9,color=C_DARK)),height=500)
        fig.update_layout(margin=dict(t=65,b=160,l=60,r=35))
        fig.update_yaxes(title_text="Cumul %",secondary_y=True,range=[0,105],ticksuffix="%",
                         tickfont=dict(size=11,color=C_DARK),title_font=dict(color=C_DARK),
                         gridcolor="rgba(0,0,0,0)")
        return fig

    @staticmethod
    def cluster_pareto(df):
        if "PSCS Cluster" not in df.columns: return go.Figure()
        data=df.groupby("PSCS Cluster")["Total  spend"].sum().sort_values(ascending=False).reset_index()
        data.columns=["Cluster","Spend"]
        data=data[data["Spend"]>0].reset_index(drop=True)
        n_total=len(data); gt=data["Spend"].sum()
        cumsum=0; cutoff=n_total
        for i,v in enumerate(data["Spend"]):
            cumsum+=v
            if cumsum/gt>=0.80: cutoff=i+1; break
        data=data.iloc[:cutoff].copy()
        data["CumulPct"]=data["Spend"].cumsum()/gt*100
        bar_colors=ClusterCharts._bar_colors_for(data["Cluster"].tolist())
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Bar(x=data["Cluster"],y=data["Spend"],marker_color=bar_colors,
                             name="Spend",text=[_fmt(v) for v in data["Spend"]],
                             textposition="outside",textfont=dict(size=9,color=C_DARK)),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=data["Cluster"],y=data["CumulPct"],name="Cumul %",
                                 mode="lines+markers",line=dict(color=C_RED,width=2),
                                 marker=dict(size=5)),secondary_y=True)
        fig.add_hline(y=80,line_dash="dash",line_color=C_TEAL,line_width=1.5,secondary_y=True,
                      annotation_text="  80%",annotation_font=dict(color=C_TEAL,size=11))
        fig.update_layout(**LAYOUT,
            title=dict(text="Pareto Clusters → 80% du Spend",font=dict(size=13,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS,tickangle=-30),yaxis=dict(**_YAXIS,title="kCHF"),
            legend=dict(**_LEGEND,orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
            height=400)
        fig.update_yaxes(title_text="Cumul %",secondary_y=True,range=[0,105],ticksuffix="%",
                         tickfont=dict(size=11,color=C_DARK),title_font=dict(color=C_DARK),
                         gridcolor="rgba(0,0,0,0)")
        return fig

    @staticmethod
    def capex_opex_per_category(df):
        return _stacked_capex_opex(df,"PSCS Category","CAPEX vs OPEX par Catégorie (kCHF)")

    @staticmethod
    def capex_opex_per_cluster(df):
        return _stacked_capex_opex(df,"PSCS Cluster","CAPEX vs OPEX par Cluster (kCHF)")


# ══════════════════════════════════════════════════════════════════════════════
# CAPEX / OPEX TAB CHARTS
# ══════════════════════════════════════════════════════════════════════════════
class CapexOpexTabCharts:

    @classmethod
    def _monthly_wf(cls, df, spend_col, comp_year, title):
        base_year=comp_year-1
        if "Année" not in df.columns or "Nom_Mois" not in df.columns: return go.Figure()
        def _m(yr):
            s=df[df["Année"]==yr].groupby("Nom_Mois")[spend_col].sum()
            return {m: float(s.get(m,0)) for m in MONTHS_ORDER}
        bm=_m(base_year); cm=_m(comp_year)
        active=[m for m in MONTHS_ORDER if bm[m]!=0 or cm[m]!=0]
        if not active: return go.Figure()
        deltas=[cm[m]-bm[m] for m in active]
        bt=sum(bm[m] for m in active); ct=sum(cm[m] for m in active)
        td=ct-bt; pct=(td/bt*100) if bt else 0
        return _build_waterfall(labels=active,values=deltas,base_val=bt,end_val=ct,
            base_label=str(base_year),end_label=str(comp_year),
            title=title,total_delta=td,total_pct=pct)

    @staticmethod
    def capex_opex_total_bar(df):
        capex=float(df["CAPEX Spend"].sum()) if "CAPEX Spend" in df.columns else 0
        opex =float(df["OPEX Spend"].sum())  if "OPEX Spend"  in df.columns else 0
        fig=go.Figure(go.Bar(x=["CAPEX","OPEX"],y=[capex,opex],marker_color=[C_BLUE,C_ORANGE],
                             text=[_fmt(capex),_fmt(opex)],textposition="outside",
                             textfont=dict(size=12,color=C_DARK),width=[0.4,0.4]))
        fig.update_layout(**LAYOUT,
            title=dict(text="Spend CAPEX vs OPEX (kCHF)",font=dict(size=14,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS),yaxis=dict(**_YAXIS,title="kCHF"),height=380)
        return fig

    @staticmethod
    def fi_mm_total_bar(df):
        fi=float(df["FI Spend"].sum()) if "FI Spend" in df.columns else 0
        mm=float(df["MM Spend"].sum()) if "MM Spend" in df.columns else 0
        fig=go.Figure(go.Bar(x=["FI Spend","MM Spend"],y=[fi,mm],marker_color=[C_PURPLE,C_TEAL],
                             text=[_fmt(fi),_fmt(mm)],textposition="outside",
                             textfont=dict(size=12,color=C_DARK),width=[0.4,0.4]))
        fig.update_layout(**LAYOUT,
            title=dict(text="Spend FI vs MM (kCHF)",font=dict(size=14,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS),yaxis=dict(**_YAXIS,title="kCHF"),height=380)
        return fig

    @staticmethod
    def stacked_spend_per_year(df):
        if "Année" not in df.columns: return go.Figure()
        tmp=df.dropna(subset=["Année"]).copy()
        tmp["yr"]=tmp["Année"].astype(float).astype(int)
        grp=tmp.groupby("yr")[["CAPEX Spend","OPEX Spend"]].sum().sort_index()
        if grp.empty: return go.Figure()
        xlabels=["Y"+str(y) for y in grp.index]; xtitles=[str(y) for y in grp.index]
        capex=grp["CAPEX Spend"].tolist(); opex=grp["OPEX Spend"].tolist()
        totals=[c+o for c,o in zip(capex,opex)]
        fig=go.Figure()
        fig.add_trace(go.Bar(name="CAPEX",x=xlabels,y=capex,marker_color=C_BLUE,
                             text=[_fmt(v) for v in capex],
                             textposition="inside",textfont=dict(size=10,color=WHITE)))
        fig.add_trace(go.Bar(name="OPEX",x=xlabels,y=opex,marker_color=C_ORANGE,
                             text=[_fmt(v) for v in opex],
                             textposition="inside",textfont=dict(size=10,color=WHITE)))
        annotations=[dict(x=xl,y=t,text=f"<b>{_fmt(t)}</b>",showarrow=False,
                          xanchor="center",yanchor="bottom",yshift=5,
                          font=dict(size=10,color=C_DARK))
                     for xl,t in zip(xlabels,totals)]
        fig.update_layout(**LAYOUT,
            title=dict(text="Spend par Année — CAPEX/OPEX Stacked (kCHF)",
                       font=dict(size=14,color=C_DARK),x=0),
            barmode="stack",
            xaxis=dict(**_XAXIS,tickmode="array",tickvals=xlabels,ticktext=xtitles),
            yaxis=dict(**_YAXIS,title="kCHF"),
            legend=dict(**_LEGEND,orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
            annotations=annotations,height=400)
        return fig

    @staticmethod
    def monthly_spend_by_year(df):
        if "Année" not in df.columns or "Nom_Mois" not in df.columns: return go.Figure()
        tmp=df.dropna(subset=["Année"]).copy()
        tmp["yr"]=tmp["Année"].astype(float).astype(int)
        years=sorted(tmp["yr"].unique().tolist())
        fig=go.Figure()
        for i,yr in enumerate(years):
            sub=tmp[tmp["yr"]==yr].groupby("Nom_Mois")["Total  spend"].sum()
            vals=[float(sub.get(m,0)) for m in MONTHS_ORDER]
            fig.add_trace(go.Bar(name=str(yr),x=MONTHS_SHORT,y=vals,
                                 marker_color=CLUSTER_PALETTE[i%len(CLUSTER_PALETTE)],
                                 text=[_fmt(v) if v>0 else "" for v in vals],
                                 textposition="outside",textfont=dict(size=8,color=C_DARK)))
        fig.update_layout(**LAYOUT,
            title=dict(text="Spend Mensuel par Année (kCHF)",font=dict(size=14,color=C_DARK),x=0),
            barmode="group",xaxis=dict(**_XAXIS),yaxis=dict(**_YAXIS,title="kCHF"),
            legend=dict(**_LEGEND,orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
            height=420)
        return fig

    @staticmethod
    def capex_opex_variation_bar(df, comp_year):
        base_year=comp_year-1
        cols={"CAPEX":"CAPEX Spend","OPEX":"OPEX Spend"}
        labels,base_vals,comp_vals,deltas,colors=[],[],[],[],[]
        for lbl,col in cols.items():
            if col not in df.columns: continue
            b=float(df[df["Année"]==base_year][col].sum()) if "Année" in df.columns else 0
            c=float(df[df["Année"]==comp_year][col].sum()) if "Année" in df.columns else 0
            d=c-b
            labels.append(lbl); base_vals.append(b); comp_vals.append(c)
            deltas.append(d); colors.append(C_RED if d>0 else C_TEAL)
        fig=go.Figure()
        fig.add_trace(go.Bar(name=str(base_year),x=labels,y=base_vals,
                             marker_color=_hex_to_rgba(C_NAVY,0.4),
                             text=[_fmt(v) for v in base_vals],
                             textposition="outside",textfont=dict(size=11,color=C_DARK)))
        fig.add_trace(go.Bar(name=str(comp_year),x=labels,y=comp_vals,
                             marker_color=[C_BLUE,C_ORANGE],
                             text=[_fmt(v) for v in comp_vals],
                             textposition="outside",textfont=dict(size=11,color=C_DARK)))
        annotations=[dict(x=l,y=max(b,c),text=f"<b>{_fmt_d(d)}</b>",showarrow=False,
                          yanchor="bottom",yshift=22,font=dict(size=11,color=col))
                     for l,b,c,d,col in zip(labels,base_vals,comp_vals,deltas,colors)]
        fig.update_layout(**LAYOUT,
            title=dict(text=f"Variation CAPEX/OPEX — {base_year} vs {comp_year} (kCHF)",
                       font=dict(size=14,color=C_DARK),x=0),
            barmode="group",xaxis=dict(**_XAXIS),yaxis=dict(**_YAXIS,title="kCHF"),
            legend=dict(**_LEGEND,orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
            annotations=annotations,height=400)
        return fig

    @classmethod
    def total_monthly_variation(cls,df,comp_year):
        return cls._monthly_wf(df,"Total  spend",comp_year,
            f"Variation Mensuelle Total Spend — {comp_year-1} vs {comp_year}")

    @staticmethod
    def spend_evolution_line(df):
        if "Date" not in df.columns: return go.Figure()
        tmp=df.dropna(subset=["Date"]).copy()
        tmp["YM"]=tmp["Date"].dt.to_period("M").astype(str)
        grp=tmp.groupby("YM")["Total  spend"].sum().reset_index().sort_values("YM")
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=grp["YM"],y=grp["Total  spend"],mode="lines+markers",
                                 line=dict(color=C_BLUE,width=2.5),marker=dict(size=5,color=C_BLUE),
                                 fill="tozeroy",fillcolor=_hex_to_rgba(C_BLUE,0.1),name="Total Spend"))
        fig.update_layout(**LAYOUT,
            title=dict(text="Évolution du Total Spend dans le temps (kCHF)",
                       font=dict(size=14,color=C_DARK),x=0),
            xaxis=dict(**_XAXIS,tickangle=-35,title="Période"),
            yaxis=dict(**_YAXIS,title="kCHF"),height=380)
        return fig

    @classmethod
    def capex_monthly_var(cls,df,comp_year):
        return cls._monthly_wf(df,"CAPEX Spend",comp_year,
            f"Variation CAPEX Mensuelle — {comp_year-1} vs {comp_year}")
    @classmethod
    def opex_monthly_var(cls,df,comp_year):
        return cls._monthly_wf(df,"OPEX Spend",comp_year,
            f"Variation OPEX Mensuelle — {comp_year-1} vs {comp_year}")
    @classmethod
    def mm_monthly_var(cls,df,comp_year):
        return cls._monthly_wf(df,"MM Spend",comp_year,
            f"Variation MM Mensuelle — {comp_year-1} vs {comp_year}")
    @classmethod
    def fi_monthly_var(cls,df,comp_year):
        return cls._monthly_wf(df,"FI Spend",comp_year,
            f"Variation FI Mensuelle — {comp_year-1} vs {comp_year}")


# ─── Legacy stubs ─────────────────────────────────────────────────────────────
class AdditionalCharts: pass
class OtherCharts:      pass