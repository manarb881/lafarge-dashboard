"""
Page Analyse Comparative — Waterfall et Pareto côte-à-côte
Compare 2 à N éléments sur la même dimension (vendors, catégories, périodes)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualizations import WaterfallCharts, ParetoCharts, TemporalCharts, C, LAYOUT_BASE, LAYOUT_NO_AXES

st.set_page_config(page_title="Analyse Comparative", page_icon="📊", layout="wide")

st.markdown("""
<style>
.section-banner {
    background: linear-gradient(90deg, #1E3A5F 0%, #2563EB 100%);
    color: white; padding: 8px 16px; border-radius: 6px;
    font-weight: 700; font-size: 14px; margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


def _banner(txt):
    st.markdown(f'<div class="section-banner">{txt}</div>', unsafe_allow_html=True)


# ─── Waterfall comparatif ──────────────────────────────────────────────────────

def waterfall_compare(df: pd.DataFrame, group_col: str, items: list,
                      title: str) -> go.Figure:
    """Waterfall mensuel côte-à-côte pour N éléments."""
    if 'Année_Mois' not in df.columns:
        return None

    colors = px.colors.qualitative.Bold
    fig = go.Figure()

    for i, item in enumerate(items):
        sub = df[df[group_col] == item]
        monthly = (sub.groupby('Année_Mois')['Total  spend']
                      .sum().reset_index().sort_values('Année_Mois'))
        if len(monthly) < 2:
            continue
        vals   = list(monthly['Total  spend'])
        deltas = [vals[0]] + [vals[j] - vals[j-1] for j in range(1, len(vals))]
        measures = ['absolute'] + ['relative'] * (len(vals) - 1)
        color = colors[i % len(colors)]

        fig.add_trace(go.Waterfall(
            name=item,
            orientation='v',
            measure=measures,
            x=list(monthly['Année_Mois']),
            y=deltas,
            connector=dict(line=dict(color='#CBD5E1', width=1, dash='dot')),
            increasing=dict(marker=dict(color=color)),
            decreasing=dict(marker=dict(color='#DC2626')),
            totals=dict(marker=dict(color=color)),
            visible=True,
        ))

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=f'📊 Waterfall Comparatif — {title}', font_size=15),
        barmode='group',
        xaxis_title='Période',
        yaxis_title='Spend (€)',
        height=480,
        showlegend=True,
    )
    return fig


def cumul_compare(df: pd.DataFrame, group_col: str, items: list,
                  title: str) -> go.Figure:
    """Courbes cumulatives comparatives."""
    if 'Année_Mois' not in df.columns:
        return None

    colors = px.colors.qualitative.Bold
    fig = go.Figure()

    for i, item in enumerate(items):
        sub = df[df[group_col] == item]
        monthly = (sub.groupby('Année_Mois')['Total  spend']
                      .sum().reset_index().sort_values('Année_Mois'))
        cumul = list(np.cumsum(monthly['Total  spend']))
        fig.add_trace(go.Scatter(
            x=list(monthly['Année_Mois']),
            y=cumul,
            mode='lines+markers',
            name=item,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=7),
            hovertemplate=f'<b>{item}</b><br>%{{x}}<br>Cumul: %{{y:,.0f}} €<extra></extra>',
        ))

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=f'📈 Cumul Comparatif — {title}', font_size=15),
        xaxis_title='Période',
        yaxis_title='Cumul (€)',
        height=430,
        showlegend=True,
    )
    return fig


def bar_compare(df: pd.DataFrame, group_col: str, items: list,
                title: str) -> go.Figure:
    """Barres CAPEX vs OPEX par élément."""
    agg = (df[df[group_col].isin(items)]
           .groupby(group_col)
           .agg(CAPEX=('CAPEX Spend', 'sum'), OPEX=('OPEX Spend', 'sum'))
           .reindex(items))

    fig = go.Figure()
    fig.add_trace(go.Bar(x=agg.index, y=agg['CAPEX'], name='CAPEX',
                         marker_color=C['capex']))
    fig.add_trace(go.Bar(x=agg.index, y=agg['OPEX'],  name='OPEX',
                         marker_color=C['opex']))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=f'📊 CAPEX vs OPEX — {title}', font_size=15),
        barmode='group',
        xaxis_title=group_col,
        yaxis_title='Montant (€)',
        height=400,
    )
    fig.update_xaxes(tickangle=-35)
    return fig


def stats_table(df: pd.DataFrame, group_col: str, items: list) -> pd.DataFrame:
    sub = df[df[group_col].isin(items)]
    agg = sub.groupby(group_col).agg(
        Total=('Total  spend', 'sum'),
        NbCmds=('Total  spend', 'count'),
        Moy=('Total  spend', 'mean'),
        CAPEX=('CAPEX Spend', 'sum'),
        OPEX=('OPEX Spend', 'sum'),
    ).reindex(items)
    total_global = agg['Total'].sum() or 1
    agg['% Total'] = (agg['Total'] / total_global * 100).round(1)
    agg = agg.reset_index()
    agg.columns = [group_col, 'Total (€)', 'Commandes', 'Moy. (€)',
                   'CAPEX (€)', 'OPEX (€)', '% Total']
    for col in ['Total (€)', 'Moy. (€)', 'CAPEX (€)', 'OPEX (€)']:
        agg[col] = agg[col].apply(lambda x: f"{x:,.0f} €")
    agg['% Total'] = agg['% Total'].apply(lambda x: f"{x:.1f}%")
    return agg


# ══════════════════════════════════════════════════════════════════════════════
# SECTIONS PAR TYPE
# ══════════════════════════════════════════════════════════════════════════════

def _compare_vendors(df, selected):
    _banner("📊 Waterfall Comparatif — Fournisseurs")
    fig = waterfall_compare(df, 'Vendor Name', selected, 'Fournisseurs')
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="ca_1")

    c1, c2 = st.columns(2)
    with c1:
        fig = cumul_compare(df, 'Vendor Name', selected, 'Fournisseurs')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="ca_2")
    with c2:
        fig = bar_compare(df, 'Vendor Name', selected, 'Fournisseurs')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="ca_3")

    st.divider()
    _banner("📋 Tableau Comparatif")
    st.dataframe(stats_table(df, 'Vendor Name', selected),
                 use_container_width=True, hide_index=True)


def _compare_categories(df, selected):
    _banner("📊 Waterfall Comparatif — Catégories PSCS")
    fig = waterfall_compare(df, 'PSCS Category', selected, 'Catégories')
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="ca_4")

    c1, c2 = st.columns(2)
    with c1:
        fig = cumul_compare(df, 'PSCS Category', selected, 'Catégories')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="ca_5")
    with c2:
        fig = bar_compare(df, 'PSCS Category', selected, 'Catégories')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="ca_6")

    st.divider()
    _banner("📋 Tableau Comparatif")
    st.dataframe(stats_table(df, 'PSCS Category', selected),
                 use_container_width=True, hide_index=True)


def _compare_periods(df, selected):
    if 'Année_Mois' not in df.columns:
        st.warning("Colonne de période indisponible.")
        return

    _banner("📊 Dépenses par Période sélectionnée")
    sub = df[df['Année_Mois'].isin(selected)]

    period_stats = sub.groupby('Année_Mois').agg(
        Total=('Total  spend', 'sum'),
        NbCmds=('Total  spend', 'count'),
        CAPEX=('CAPEX Spend', 'sum'),
        OPEX=('OPEX Spend', 'sum'),
    ).reindex(sorted(selected)).reset_index()

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=period_stats['Année_Mois'],
                             y=period_stats['Total'],
                             marker_color=C['blue']))
        fig.update_layout(**LAYOUT_BASE,
                          title=dict(text='📊 Total Spend par Période', font_size=15),
                          height=380)
        st.plotly_chart(fig, use_container_width=True, key="ca_7")
    with c2:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=period_stats['Année_Mois'], y=period_stats['CAPEX'],
                             name='CAPEX', marker_color=C['capex']))
        fig.add_trace(go.Bar(x=period_stats['Année_Mois'], y=period_stats['OPEX'],
                             name='OPEX', marker_color=C['opex']))
        fig.update_layout(**LAYOUT_BASE,
                          title=dict(text='📊 CAPEX vs OPEX par Période', font_size=15),
                          barmode='stack', height=380)
        st.plotly_chart(fig, use_container_width=True, key="ca_8")

    st.divider()

    # Pour chaque période : pareto vendors
    _banner("📈 Pareto Fournisseurs — par période")
    for period in sorted(selected):
        with st.expander(f"📅 {period}", expanded=False):
            df_p = sub[sub['Année_Mois'] == period]
            col1, col2 = st.columns(2)
            with col1:
                fig = ParetoCharts.vendors(df_p, max_display=20)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="ca_9")
            with col2:
                fig = ParetoCharts.pscs_category(df_p, max_display=20)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="ca_10")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if 'df' not in st.session_state or st.session_state.df is None:
        st.error("❌ Aucune donnée chargée.")
        if st.button("← Accueil"):
            st.switch_page("main.py")
        return

    df = st.session_state.df

    col_t, col_b = st.columns([5, 1])
    with col_t:
        st.title("📊 Analyse Comparative")
        st.caption("Comparez vendors, catégories ou périodes sur waterfall, cumul et CAPEX/OPEX")
    with col_b:
        if st.button("← Retour Dashboard", use_container_width=True):
            st.switch_page("main.py")

    st.divider()

    comp_type = st.radio(
        "Dimension à comparer",
        ["Fournisseurs", "Catégories PSCS", "Périodes"],
        horizontal=True,
    )

    st.divider()

    if comp_type == "Fournisseurs":
        vendors_list = (df.groupby('Vendor Name')['Total  spend']
                          .sum().sort_values(ascending=False).index.tolist())
        selected = st.multiselect(
            "Sélectionner les fournisseurs (2–8)",
            vendors_list,
            default=vendors_list[:3] if len(vendors_list) >= 3 else vendors_list,
            max_selections=8,
        )
        if len(selected) >= 2:
            _compare_vendors(df, selected)
        else:
            st.info("Sélectionnez au moins 2 fournisseurs.")

    elif comp_type == "Catégories PSCS":
        cats_list = (df.groupby('PSCS Category')['Total  spend']
                       .sum().sort_values(ascending=False).index.tolist())
        selected = st.multiselect(
            "Sélectionner les catégories (2–8)",
            cats_list,
            default=cats_list[:3] if len(cats_list) >= 3 else cats_list,
            max_selections=8,
        )
        if len(selected) >= 2:
            _compare_categories(df, selected)
        else:
            st.info("Sélectionnez au moins 2 catégories.")

    elif comp_type == "Périodes":
        if 'Année_Mois' in df.columns:
            periods_list = sorted(df['Année_Mois'].unique())
            selected = st.multiselect(
                "Sélectionner les périodes (2–12)",
                periods_list,
                default=periods_list[-4:] if len(periods_list) >= 4 else periods_list,
                max_selections=12,
            )
            if len(selected) >= 2:
                _compare_periods(df, selected)
            else:
                st.info("Sélectionnez au moins 2 périodes.")
        else:
            st.warning("Colonne de période indisponible.")


if __name__ == "__main__":
    main()