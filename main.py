"""
Spend Analytics Dashboard — Page principale
Priorités d'affichage :
  1. Waterfall charts (avancement des dépenses)
  2. Pareto 80/20 par dimension (vendors, PSCS, requesters, groupes)
  3. Heatmap + évolution empilée
  4. Donuts / treemap / scatter complémentaires
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_processor import SpendDataProcessor
from visualizations import WaterfallCharts, ParetoCharts, TemporalCharts, StructureCharts

# ─── Config ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spend Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Titres d'onglets */
.stTabs [data-baseweb="tab"] { font-size: 14px; font-weight: 600; padding: 10px 18px; }
/* Bordure gauche sur les métriques */
[data-testid="metric-container"] {
    border-left: 4px solid #2563EB;
    padding-left: 12px;
    background: #F8FAFC;
    border-radius: 6px;
}
/* Bandeau section */
.section-banner {
    background: linear-gradient(90deg, #1E3A5F 0%, #2563EB 100%);
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ─── Session state ─────────────────────────────────────────────────────────────
def _init():
    if 'data_loaded'   not in st.session_state: st.session_state.data_loaded   = False
    if 'df'            not in st.session_state: st.session_state.df            = None
    if 'processor'     not in st.session_state: st.session_state.processor     = SpendDataProcessor()
    if 'drill_context' not in st.session_state: st.session_state.drill_context = {}


# ─── Sidebar filtres ──────────────────────────────────────────────────────────
def _sidebar_filters(df: pd.DataFrame) -> dict:
    st.sidebar.header("🔍 Filtres")
    f = {}

    if 'Date' in df.columns and not df['Date'].isna().all():
        st.sidebar.subheader("📅 Période")
        mn, mx = df['Date'].min().date(), df['Date'].max().date()
        dr = st.sidebar.date_input("Période", value=(mn, mx), min_value=mn, max_value=mx)
        f['date_range'] = dr

    st.sidebar.subheader("🏢 Fournisseurs")
    f['vendors'] = st.sidebar.multiselect(
        "Fournisseurs", sorted(df['Vendor Name'].unique()), default=None)

    st.sidebar.subheader("📦 PSCS")
    f['clusters'] = st.sidebar.multiselect(
        "Clusters", sorted(df['PSCS Cluster'].unique()), default=None)
    f['categories'] = st.sidebar.multiselect(
        "Catégories", sorted(df['PSCS Category'].unique()), default=None)

    st.sidebar.subheader("👥 Requesters")
    f['requesters'] = st.sidebar.multiselect(
        "Requesters", sorted(df['Requester'].unique()), default=None)

    st.sidebar.subheader("💰 Montants")
    c1, c2 = st.sidebar.columns(2)
    f['min_spend'] = c1.number_input("Min (€)", min_value=0.0, value=0.0, step=100.0)
    max_def = float(df['Total  spend'].max()) if 'Total  spend' in df.columns else 0.0
    f['max_spend'] = c2.number_input("Max (€)", min_value=0.0, value=max_def, step=1000.0)

    return f


# ─── KPIs ─────────────────────────────────────────────────────────────────────
def _kpis(stats: dict):
    st.markdown('<div class="section-banner">📈 Indicateurs Clés</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💶 Total Spend",  f"{stats['total_spend']:,.0f} €")
    c2.metric("📋 Commandes",    f"{stats['total_rows']:,}")
    c3.metric("🏢 Fournisseurs", f"{stats['unique_vendors']:,}")
    c4.metric("👥 Requesters",   f"{stats['unique_requesters']:,}")
    c5.metric("📦 Catégories",   f"{stats['unique_categories']:,}")

    st.markdown("<br>", unsafe_allow_html=True)
    c6, c7, c8, c9, c10 = st.columns(5)
    total = stats['total_spend'] or 1
    c6.metric("🟣 CAPEX",
              f"{stats['total_capex']:,.0f} €",
              f"{stats['total_capex']/total*100:.1f}%")
    c7.metric("🔵 OPEX",
              f"{stats['total_opex']:,.0f} €",
              f"{stats['total_opex']/total*100:.1f}%")
    c8.metric("🔷 FI Spend",
              f"{stats['total_fi']:,.0f} €",
              f"{stats['total_fi']/total*100:.1f}%")
    c9.metric("🔹 MM Spend",
              f"{stats['total_mm']:,.0f} €",
              f"{stats['total_mm']/total*100:.1f}%")
    if stats['date_min'] and stats['date_max']:
        c10.metric("📅 Période",
                   f"{stats['date_min'].strftime('%m/%Y')}",
                   f"→ {stats['date_max'].strftime('%m/%Y')}")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLETS PRINCIPAUX
# ══════════════════════════════════════════════════════════════════════════════

def _tab_waterfall(df: pd.DataFrame):
    """Onglet 1 — Waterfall (priorité absolue)"""
    st.markdown('<div class="section-banner">📊 Waterfall — Avancement & Variations des Dépenses</div>',
                unsafe_allow_html=True)
    st.caption("Les graphiques waterfall montrent mois par mois comment les dépenses s'accumulent "
               "et où les variations positives / négatives se produisent.")

    # ── Ligne 1 : mensuel simple + cumulatif ──────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        fig = WaterfallCharts.mensuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_1")
        else:
            st.info("Données temporelles insuffisantes (< 2 mois).")
    with c2:
        fig = WaterfallCharts.cumulatif_annuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_2")

    st.divider()

    # ── Ligne 2 : CAPEX/OPEX mensuel + contribution par cluster ──────────
    c3, c4 = st.columns(2)
    with c3:
        fig = WaterfallCharts.capex_opex_mensuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_3")
    with c4:
        fig = WaterfallCharts.par_cluster(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_4")

    st.divider()

    # ── Ligne 3 : empilé CAPEX/FI/MM ─────────────────────────────────────
    fig = TemporalCharts.capex_opex_stacked(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_5")


def _tab_pareto_vendors(df: pd.DataFrame):
    """Onglet 2 — Pareto Fournisseurs"""
    st.markdown('<div class="section-banner">📈 Pareto Fournisseurs — Loi 80/20</div>',
                unsafe_allow_html=True)
    st.caption("Les barres bleues représentent les fournisseurs qui génèrent 80% des dépenses. "
               "La zone grise = la « long tail ».")

    # Pareto principal
    fig = ParetoCharts.vendors(df, max_display=30)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_6")

    st.divider()

    c1, c2 = st.columns([1, 1])

    with c1:
        # Scatter volume vs montant moyen
        fig = StructureCharts.scatter_volume_spend(df, 'Vendor Name', 'Fournisseurs')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_7")

    with c2:
        # Évolution empilée top fournisseurs
        fig = TemporalCharts.evolution_stacked(df, 'Vendor Name', top_n=6,
                                               title_prefix='Top Fournisseurs')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_8")

    st.divider()

    # Table Pareto annotée
    st.markdown('<div class="section-banner">📋 Table Pareto — Classement complet Fournisseurs</div>',
                unsafe_allow_html=True)
    tbl = ParetoCharts.table_pareto(df, 'Vendor Name', 'Fournisseur')
    if tbl is not None:
        # Formater les montants
        tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
        st.dataframe(tbl, use_container_width=True, hide_index=True,
                     column_config={
                         'Rang':        st.column_config.NumberColumn(width='small'),
                         'Zone Pareto': st.column_config.TextColumn(width='medium'),
                         '% du Total':  st.column_config.NumberColumn(format="%.2f %%"),
                         '% Cumulé':    st.column_config.NumberColumn(format="%.2f %%"),
                     })

    st.divider()

    # ── Drill-down fournisseur ────────────────────────────────────────────
    st.markdown('<div class="section-banner">🔍 Drill-Down Fournisseur</div>',
                unsafe_allow_html=True)
    vendors_sorted = (df.groupby('Vendor Name')['Total  spend']
                        .sum().sort_values(ascending=False).index.tolist())
    sel = st.selectbox("Sélectionner un fournisseur", ["— Choisir —"] + vendors_sorted,
                       key="vendor_dd")
    if sel != "— Choisir —":
        if st.button(f"🔍 Analyser {sel}", key="btn_vendor_dd"):
            st.session_state.drill_context = {'type': 'vendor', 'vendor_name': sel}
            st.switch_page("pages/drill_down.py")


def _tab_pareto_pscs(df: pd.DataFrame):
    """Onglet 3 — Pareto PSCS"""
    st.markdown('<div class="section-banner">📈 Pareto PSCS — Catégories & Clusters</div>',
                unsafe_allow_html=True)

    # Pareto catégories
    fig = ParetoCharts.pscs_category(df, max_display=30)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_9")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        # Pareto clusters
        fig = ParetoCharts.pscs_cluster(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_10")
    with c2:
        # Treemap
        fig = StructureCharts.treemap_pscs(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_11")

    st.divider()

    # Heatmap mensuelle par catégorie
    fig = TemporalCharts.heatmap_categorie(df, top_n=15)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_12")

    st.divider()

    # Évolution empilée par catégorie
    fig = TemporalCharts.evolution_stacked(df, 'PSCS Category', top_n=8,
                                           title_prefix='Top Catégories PSCS')
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_13")

    st.divider()

    # Tables Pareto
    col_tab1, col_tab2 = st.columns(2)

    with col_tab1:
        st.markdown('<div class="section-banner">📋 Table — Catégories PSCS</div>',
                    unsafe_allow_html=True)
        tbl = ParetoCharts.table_pareto(df, 'PSCS Category', 'Catégorie')
        if tbl is not None:
            tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl, use_container_width=True, hide_index=True)

    with col_tab2:
        st.markdown('<div class="section-banner">📋 Table — Clusters PSCS</div>',
                    unsafe_allow_html=True)
        tbl2 = ParetoCharts.table_pareto(df, 'PSCS Cluster', 'Cluster')
        if tbl2 is not None:
            tbl2['Spend (€)'] = tbl2['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl2, use_container_width=True, hide_index=True)

    st.divider()

    # Drill-down catégorie
    st.markdown('<div class="section-banner">🔍 Drill-Down Catégorie</div>',
                unsafe_allow_html=True)
    cats_sorted = (df.groupby('PSCS Category')['Total  spend']
                     .sum().sort_values(ascending=False).index.tolist())
    sel = st.selectbox("Sélectionner une catégorie", ["— Choisir —"] + cats_sorted,
                       key="cat_dd")
    if sel != "— Choisir —":
        if st.button(f"🔍 Analyser {sel}", key="btn_cat_dd"):
            st.session_state.drill_context = {'type': 'category', 'category_name': sel}
            st.switch_page("pages/drill_down.py")


def _tab_pareto_requesters(df: pd.DataFrame):
    """Onglet 4 — Pareto Requesters & Groupes Achat"""
    st.markdown('<div class="section-banner">📈 Pareto Requesters & Groupes Achat</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = ParetoCharts.requesters(df, max_display=25)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_14")
    with c2:
        fig = ParetoCharts.purchasing_groups(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_15")

    st.divider()

    c3, c4 = st.columns(2)
    with c3:
        fig = StructureCharts.scatter_volume_spend(df, 'Requester', 'Requesters')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_16")
    with c4:
        fig = TemporalCharts.evolution_stacked(df, 'Requester', top_n=6,
                                               title_prefix='Top Requesters')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_17")

    st.divider()

    col_tab1, col_tab2 = st.columns(2)
    with col_tab1:
        st.markdown('<div class="section-banner">📋 Table — Requesters</div>',
                    unsafe_allow_html=True)
        tbl = ParetoCharts.table_pareto(df, 'Requester', 'Requester')
        if tbl is not None:
            tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl, use_container_width=True, hide_index=True)

    with col_tab2:
        st.markdown('<div class="section-banner">📋 Table — Groupes Achat</div>',
                    unsafe_allow_html=True)
        tbl2 = ParetoCharts.table_pareto(df, 'Purchasing Group Name', 'Groupe Achat')
        if tbl2 is not None:
            tbl2['Spend (€)'] = tbl2['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl2, use_container_width=True, hide_index=True)

    st.divider()

    # Drill-down requester
    st.markdown('<div class="section-banner">🔍 Drill-Down Requester</div>',
                unsafe_allow_html=True)
    req_sorted = (df.groupby('Requester')['Total  spend']
                    .sum().sort_values(ascending=False).index.tolist())
    sel = st.selectbox("Sélectionner un requester", ["— Choisir —"] + req_sorted,
                       key="req_dd")
    if sel != "— Choisir —":
        if st.button(f"🔍 Analyser {sel}", key="btn_req_dd"):
            st.session_state.drill_context = {'type': 'requester', 'requester_name': sel}
            st.switch_page("pages/drill_down.py")


def _tab_structure(df: pd.DataFrame):
    """Onglet 5 — Structure & Répartition (donuts, scatter, treemap)"""
    st.markdown('<div class="section-banner">🍩 Répartition CAPEX / OPEX / FI / MM</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = StructureCharts.donut_capex_opex(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_18")
    with c2:
        fig = StructureCharts.donut_fi_mm(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_19")

    st.divider()

    st.markdown('<div class="section-banner">🌳 Treemap PSCS</div>', unsafe_allow_html=True)
    fig = StructureCharts.treemap_pscs(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_20")


def _tab_explorer(df: pd.DataFrame):
    """Onglet 6 — Explorateur de données + export"""
    st.markdown('<div class="section-banner">🔎 Explorateur de Données Brutes</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    n_rows      = c1.slider("Lignes à afficher", 10, 1000, 100)
    all_cols    = df.columns.tolist()
    default_cols = [col for col in [
        'PO', 'Invoice Posting Date', 'Vendor Name', 'PSCS Cluster',
        'PSCS Category', 'Requester', 'Total  spend', 'CAPEX Spend',
        'FI Spend', 'MM Spend'
    ] if col in df.columns]
    cols_sel = c2.multiselect("Colonnes", all_cols, default=default_cols[:8])

    if cols_sel:
        st.dataframe(df[cols_sel].head(n_rows), use_container_width=True, hide_index=True)

    st.divider()
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Télécharger données filtrées (CSV)",
        csv,
        f"spend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "text/csv",
    )

# ══════════════════════════════════════════════════════════════════════════════
# ONGLETS PRINCIPAUX (CODE MANQUANT À RÉINSÉRER)
# ══════════════════════════════════════════════════════════════════════════════

def _tab_waterfall(df: pd.DataFrame):
    """Onglet 1 — Waterfall (priorité absolue)"""
    st.markdown('<div class="section-banner">📊 Waterfall — Avancement & Variations des Dépenses</div>',
                unsafe_allow_html=True)
    st.caption("Les graphiques waterfall montrent mois par mois comment les dépenses s'accumulent "
               "et où les variations positives / négatives se produisent.")

    # ── Ligne 1 : mensuel simple + cumulatif ──────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        fig = WaterfallCharts.mensuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_1")
        else:
            st.info("Données temporelles insuffisantes (< 2 mois).")
    with c2:
        fig = WaterfallCharts.cumulatif_annuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_2")

    st.divider()

    # ── Ligne 2 : CAPEX/OPEX mensuel + contribution par cluster ──────────
    c3, c4 = st.columns(2)
    with c3:
        fig = WaterfallCharts.capex_opex_mensuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_3")
    with c4:
        fig = WaterfallCharts.par_cluster(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_4")

    st.divider()

    # ── Ligne 3 : empilé CAPEX/FI/MM ─────────────────────────────────────
    fig = TemporalCharts.capex_opex_stacked(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_5")


def _tab_pareto_vendors(df: pd.DataFrame):
    """Onglet 2 — Pareto Fournisseurs"""
    st.markdown('<div class="section-banner">📈 Pareto Fournisseurs — Loi 80/20</div>',
                unsafe_allow_html=True)
    st.caption("Les barres bleues représentent les fournisseurs qui génèrent 80% des dépenses. "
               "La zone grise = la « long tail ».")

    # Pareto principal
    fig = ParetoCharts.vendors(df, max_display=30)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_6")

    st.divider()

    c1, c2 = st.columns([1, 1])

    with c1:
        # Scatter volume vs montant moyen
        fig = StructureCharts.scatter_volume_spend(df, 'Vendor Name', 'Fournisseurs')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_7")

    with c2:
        # Évolution empilée top fournisseurs
        fig = TemporalCharts.evolution_stacked(df, 'Vendor Name', top_n=6,
                                               title_prefix='Top Fournisseurs')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_8")

    st.divider()

    # Table Pareto annotée
    st.markdown('<div class="section-banner">📋 Table Pareto — Classement complet Fournisseurs</div>',
                unsafe_allow_html=True)
    tbl = ParetoCharts.table_pareto(df, 'Vendor Name', 'Fournisseur')
    if tbl is not None:
        # Formater les montants
        tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
        st.dataframe(tbl, use_container_width=True, hide_index=True,
                     column_config={
                         'Rang':        st.column_config.NumberColumn(width='small'),
                         'Zone Pareto': st.column_config.TextColumn(width='medium'),
                         '% du Total':  st.column_config.NumberColumn(format="%.2f %%"),
                         '% Cumulé':    st.column_config.NumberColumn(format="%.2f %%"),
                     })

    st.divider()

    # ── Drill-down fournisseur ────────────────────────────────────────────
    st.markdown('<div class="section-banner">🔍 Drill-Down Fournisseur</div>',
                unsafe_allow_html=True)
    vendors_sorted = (df.groupby('Vendor Name')['Total  spend']
                        .sum().sort_values(ascending=False).index.tolist())
    sel = st.selectbox("Sélectionner un fournisseur", ["— Choisir —"] + vendors_sorted,
                       key="vendor_dd")
    if sel != "— Choisir —":
        if st.button(f"🔍 Analyser {sel}", key="btn_vendor_dd"):
            st.session_state.drill_context = {'type': 'vendor', 'vendor_name': sel}
            st.switch_page("pages/drill_down.py")


def _tab_pareto_pscs(df: pd.DataFrame):
    """Onglet 3 — Pareto PSCS"""
    st.markdown('<div class="section-banner">📈 Pareto PSCS — Catégories & Clusters</div>',
                unsafe_allow_html=True)

    # Pareto catégories
    fig = ParetoCharts.pscs_category(df, max_display=30)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_9")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        # Pareto clusters
        fig = ParetoCharts.pscs_cluster(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_10")
    with c2:
        # Treemap
        fig = StructureCharts.treemap_pscs(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_11")

    st.divider()

    # Heatmap mensuelle par catégorie
    fig = TemporalCharts.heatmap_categorie(df, top_n=15)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_12")

    st.divider()

    # Évolution empilée par catégorie
    fig = TemporalCharts.evolution_stacked(df, 'PSCS Category', top_n=8,
                                           title_prefix='Top Catégories PSCS')
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_13")

    st.divider()

    # Tables Pareto
    col_tab1, col_tab2 = st.columns(2)

    with col_tab1:
        st.markdown('<div class="section-banner">📋 Table — Catégories PSCS</div>',
                    unsafe_allow_html=True)
        tbl = ParetoCharts.table_pareto(df, 'PSCS Category', 'Catégorie')
        if tbl is not None:
            tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl, use_container_width=True, hide_index=True)

    with col_tab2:
        st.markdown('<div class="section-banner">📋 Table — Clusters PSCS</div>',
                    unsafe_allow_html=True)
        tbl2 = ParetoCharts.table_pareto(df, 'PSCS Cluster', 'Cluster')
        if tbl2 is not None:
            tbl2['Spend (€)'] = tbl2['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl2, use_container_width=True, hide_index=True)

    st.divider()

    # Drill-down catégorie
    st.markdown('<div class="section-banner">🔍 Drill-Down Catégorie</div>',
                unsafe_allow_html=True)
    cats_sorted = (df.groupby('PSCS Category')['Total  spend']
                     .sum().sort_values(ascending=False).index.tolist())
    sel = st.selectbox("Sélectionner une catégorie", ["— Choisir —"] + cats_sorted,
                       key="cat_dd")
    if sel != "— Choisir —":
        if st.button(f"🔍 Analyser {sel}", key="btn_cat_dd"):
            st.session_state.drill_context = {'type': 'category', 'category_name': sel}
            st.switch_page("pages/drill_down.py")


def _tab_pareto_requesters(df: pd.DataFrame):
    """Onglet 4 — Pareto Requesters & Groupes Achat"""
    st.markdown('<div class="section-banner">📈 Pareto Requesters & Groupes Achat</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = ParetoCharts.requesters(df, max_display=25)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_14")
    with c2:
        fig = ParetoCharts.purchasing_groups(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_15")

    st.divider()

    c3, c4 = st.columns(2)
    with c3:
        fig = StructureCharts.scatter_volume_spend(df, 'Requester', 'Requesters')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_16")
    with c4:
        fig = TemporalCharts.evolution_stacked(df, 'Requester', top_n=6,
                                               title_prefix='Top Requesters')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_17")

    st.divider()

    col_tab1, col_tab2 = st.columns(2)
    with col_tab1:
        st.markdown('<div class="section-banner">📋 Table — Requesters</div>',
                    unsafe_allow_html=True)
        tbl = ParetoCharts.table_pareto(df, 'Requester', 'Requester')
        if tbl is not None:
            tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl, use_container_width=True, hide_index=True)

    with col_tab2:
        st.markdown('<div class="section-banner">📋 Table — Groupes Achat</div>',
                    unsafe_allow_html=True)
        tbl2 = ParetoCharts.table_pareto(df, 'Purchasing Group Name', 'Groupe Achat')
        if tbl2 is not None:
            tbl2['Spend (€)'] = tbl2['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl2, use_container_width=True, hide_index=True)

    st.divider()

    # Drill-down requester
    st.markdown('<div class="section-banner">🔍 Drill-Down Requester</div>',
                unsafe_allow_html=True)
    req_sorted = (df.groupby('Requester')['Total  spend']
                    .sum().sort_values(ascending=False).index.tolist())
    sel = st.selectbox("Sélectionner un requester", ["— Choisir —"] + req_sorted,
                       key="req_dd")
    if sel != "— Choisir —":
        if st.button(f"🔍 Analyser {sel}", key="btn_req_dd"):
            st.session_state.drill_context = {'type': 'requester', 'requester_name': sel}
            st.switch_page("pages/drill_down.py")


def _tab_structure(df: pd.DataFrame):
    """Onglet 5 — Structure & Répartition (donuts, scatter, treemap)"""
    st.markdown('<div class="section-banner">🍩 Répartition CAPEX / OPEX / FI / MM</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = StructureCharts.donut_capex_opex(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_18")
    with c2:
        fig = StructureCharts.donut_fi_mm(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="main_19")

    st.divider()

    st.markdown('<div class="section-banner">🌳 Treemap PSCS</div>', unsafe_allow_html=True)
    fig = StructureCharts.treemap_pscs(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="main_20")


def _tab_explorer(df: pd.DataFrame):
    """Onglet 6 — Explorateur de données + export"""
    st.markdown('<div class="section-banner">🔎 Explorateur de Données Brutes</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    n_rows      = c1.slider("Lignes à afficher", 10, 1000, 100)
    all_cols    = df.columns.tolist()
    default_cols = [col for col in [
        'PO', 'Invoice Posting Date', 'Vendor Name', 'PSCS Cluster',
        'PSCS Category', 'Requester', 'Total  spend', 'CAPEX Spend',
        'FI Spend', 'MM Spend'
    ] if col in df.columns]
    cols_sel = c2.multiselect("Colonnes", all_cols, default=default_cols[:8])

    if cols_sel:
        st.dataframe(df[cols_sel].head(n_rows), use_container_width=True, hide_index=True)

    st.divider()
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Télécharger données filtrées (CSV)",
        csv,
        f"spend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "text/csv",
    )

    
# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    _init()

    # Header
    col_t, col_anom, col_btn = st.columns([5, 1, 1])
    with col_t:
        st.title("📊 Spend Analytics Dashboard")
        st.caption("Waterfall · Pareto 80/20 · Drill-Down · Détection d'anomalies")
    with col_anom:
        if st.session_state.data_loaded:
            if st.button("🚨 Anomalies", use_container_width=True, key="btn_anomalies",
                         help="Ouvrir la page de détection d'anomalies"):
                st.switch_page("pages/anomaly_detection.py")
    with col_btn:
        if st.session_state.data_loaded:
            if st.button("🔄 Recharger", use_container_width=True):
                st.session_state.update(data_loaded=False, df=None, drill_context={})
                st.rerun()

    st.divider()

    # Upload
    if not st.session_state.data_loaded:
        st.subheader("📁 Chargement des données")
        uploaded = st.file_uploader(
            "Choisissez votre fichier Excel de spends",
            type=['xlsx', 'xls'],
            help="Colonnes attendues : PO, Vendor Name, Total  spend, CAPEX Spend, "
                 "FI Spend, MM Spend, Invoice Posting Date, PSCS Cluster, PSCS Category, …",
        )
        if uploaded:
            with st.spinner("🔄 Traitement en cours…"):
                df, err = st.session_state.processor.load_and_process(uploaded)
            if err:
                st.error(f"❌ {err}")
            else:
                st.session_state.df = df
                st.session_state.data_loaded = True
                st.success(f"✅ {len(df):,} lignes chargées")
                st.rerun()
        return

    # Filtres
    filters     = _sidebar_filters(st.session_state.df)
    filtered_df = st.session_state.processor.apply_filters(st.session_state.df, filters)
    st.sidebar.divider()
    st.sidebar.success(f"📊 **{len(filtered_df):,}** lignes")

    if len(filtered_df) == 0:
        st.warning("⚠️ Aucune donnée après filtrage — réduisez les filtres.")
        return

    # KPIs
    stats = st.session_state.processor.get_summary_stats(filtered_df)
    _kpis(stats)
    st.divider()

    # Onglets
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Waterfall",
        "🏢 Pareto Vendors",
        "📦 Pareto PSCS",
        "👥 Pareto Requesters",
        "🍩 Structure",
        "🔎 Données",
    ])

    with tab1: _tab_waterfall(filtered_df)
    with tab2: _tab_pareto_vendors(filtered_df)
    with tab3: _tab_pareto_pscs(filtered_df)
    with tab4: _tab_pareto_requesters(filtered_df)
    with tab5: _tab_structure(filtered_df)
    with tab6: _tab_explorer(filtered_df)


if __name__ == "__main__":
    main()