"""
Page Drill-Down — Analyse contextuelle détaillée
Chaque vue (vendor / catégorie / requester / période) affiche :
  1. KPIs contextuels
  2. Waterfall mensuel spécifique
  3. Pareto de la dimension complémentaire
  4. Heatmap + tableaux
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualizations import WaterfallCharts, ParetoCharts, TemporalCharts, StructureCharts

st.set_page_config(page_title="Analyse Détaillée", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.section-banner {
    background: linear-gradient(90deg, #1E3A5F 0%, #2563EB 100%);
    color: white; padding: 8px 16px; border-radius: 6px;
    font-weight: 700; font-size: 14px; margin-bottom: 8px;
}
[data-testid="metric-container"] {
    border-left: 4px solid #2563EB;
    padding-left: 12px;
    background: #F8FAFC;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _banner(txt):
    st.markdown(f'<div class="section-banner">{txt}</div>', unsafe_allow_html=True)


def _kpis_row(df: pd.DataFrame, extra_col: str = None, extra_label: str = ''):
    total  = df['Total  spend'].sum()
    capex  = df['CAPEX Spend'].sum()
    opex   = df['OPEX Spend'].sum()
    n_cmds = len(df)
    avg    = df['Total  spend'].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💶 Total",    f"{total:,.0f} €")
    c2.metric("📋 Commandes",f"{n_cmds:,}")
    c3.metric("🟣 CAPEX",    f"{capex:,.0f} €",
              f"{capex/total*100:.1f}%" if total else "0%")
    c4.metric("🔵 OPEX",     f"{opex:,.0f} €",
              f"{opex/total*100:.1f}%"  if total else "0%")
    c5.metric("📊 Moy.",     f"{avg:,.0f} €")

    if extra_col and extra_col in df.columns:
        st.metric(f"🔢 {extra_label}", f"{df[extra_col].nunique():,}")


def _back_button():
    if st.button("← Retour Dashboard", key="back_btn"):
        st.session_state.drill_context = {}
        st.switch_page("main.py")


# ══════════════════════════════════════════════════════════════════════════════
# VUE FOURNISSEUR
# ══════════════════════════════════════════════════════════════════════════════

def _view_vendor(df_full: pd.DataFrame, vendor_name: str):
    df = df_full[df_full['Vendor Name'] == vendor_name]
    st.title(f"🏢 {vendor_name}")
    st.caption(f"Analyse complète du fournisseur — {len(df):,} commandes")

    _kpis_row(df, 'PSCS Category', 'Catégories')
    st.divider()

    # ── 1. Waterfall mensuel ──────────────────────────────────────────────
    _banner("📊 Waterfall — Avancement mensuel")
    c1, c2 = st.columns(2)
    with c1:
        fig = WaterfallCharts.mensuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_1")
        else:
            st.info("Données insuffisantes pour le waterfall.")
    with c2:
        fig = WaterfallCharts.cumulatif_annuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_2")

    st.divider()

    # ── 2. Waterfall CAPEX/OPEX ───────────────────────────────────────────
    fig = WaterfallCharts.capex_opex_mensuel(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="dd_3")
        st.divider()

    # ── 3. Pareto catégories pour ce vendor ───────────────────────────────
    _banner("📈 Pareto Catégories PSCS — pour ce fournisseur")
    fig = ParetoCharts.pscs_category(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="dd_4")

    c3, c4 = st.columns(2)
    with c3:
        fig = TemporalCharts.heatmap_categorie(df, top_n=10)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_5")
    with c4:
        fig = TemporalCharts.evolution_stacked(df, 'PSCS Category', top_n=6,
                                               title_prefix='Catégories')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_6")

    st.divider()

    # ── 4. Table Pareto ───────────────────────────────────────────────────
    _banner("📋 Table Pareto — Catégories pour ce fournisseur")
    tbl = ParetoCharts.table_pareto(df, 'PSCS Category', 'Catégorie')
    if tbl is not None:
        tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
        st.dataframe(tbl, use_container_width=True, hide_index=True)

    st.divider()

    # ── 5. Détail commandes ───────────────────────────────────────────────
    _banner("📋 Détail des commandes")
    keep = [c for c in ['PO', 'Invoice Posting Date', 'PSCS Category',
                        'Requester', 'Total  spend', 'CAPEX Spend', 'OPEX Spend']
            if c in df.columns]
    detail = df[keep].sort_values('Invoice Posting Date', ascending=False)
    if 'Invoice Posting Date' in detail.columns:
        detail = detail.copy()
        detail['Invoice Posting Date'] = detail['Invoice Posting Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(detail.head(200), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# VUE CATÉGORIE
# ══════════════════════════════════════════════════════════════════════════════

def _view_category(df_full: pd.DataFrame, category_name: str):
    df = df_full[df_full['PSCS Category'] == category_name]
    st.title(f"📦 {category_name}")
    st.caption(f"Analyse complète de la catégorie — {len(df):,} commandes")

    _kpis_row(df, 'Vendor Name', 'Fournisseurs')
    st.divider()

    # ── 1. Waterfall mensuel ──────────────────────────────────────────────
    _banner("📊 Waterfall — Avancement mensuel")
    c1, c2 = st.columns(2)
    with c1:
        fig = WaterfallCharts.mensuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_7")
        else:
            st.info("Données insuffisantes.")
    with c2:
        fig = WaterfallCharts.cumulatif_annuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_8")

    st.divider()

    fig = WaterfallCharts.capex_opex_mensuel(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="dd_9")
        st.divider()

    # ── 2. Pareto fournisseurs pour cette catégorie ───────────────────────
    _banner("📈 Pareto Fournisseurs — pour cette catégorie")
    fig = ParetoCharts.vendors(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="dd_10")

    c3, c4 = st.columns(2)
    with c3:
        fig = ParetoCharts.requesters(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_11")
    with c4:
        fig = TemporalCharts.evolution_stacked(df, 'Vendor Name', top_n=6,
                                               title_prefix='Fournisseurs')
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_12")

    st.divider()

    # ── 3. Tables Pareto ──────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        _banner("📋 Table Pareto — Fournisseurs")
        tbl = ParetoCharts.table_pareto(df, 'Vendor Name', 'Fournisseur')
        if tbl is not None:
            tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl, use_container_width=True, hide_index=True)
    with col_b:
        _banner("📋 Table Pareto — Requesters")
        tbl2 = ParetoCharts.table_pareto(df, 'Requester', 'Requester')
        if tbl2 is not None:
            tbl2['Spend (€)'] = tbl2['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl2, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# VUE REQUESTER
# ══════════════════════════════════════════════════════════════════════════════

def _view_requester(df_full: pd.DataFrame, requester_name: str):
    df = df_full[df_full['Requester'] == requester_name]
    st.title(f"👥 {requester_name}")
    st.caption(f"Analyse complète du requester — {len(df):,} commandes")

    _kpis_row(df, 'Vendor Name', 'Fournisseurs')
    st.divider()

    # ── 1. Waterfall mensuel ──────────────────────────────────────────────
    _banner("📊 Waterfall — Avancement mensuel")
    c1, c2 = st.columns(2)
    with c1:
        fig = WaterfallCharts.mensuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_13")
        else:
            st.info("Données insuffisantes.")
    with c2:
        fig = WaterfallCharts.cumulatif_annuel(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_14")

    st.divider()

    fig = WaterfallCharts.capex_opex_mensuel(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="dd_15")
        st.divider()

    # ── 2. Pareto vendors + catégories ───────────────────────────────────
    _banner("📈 Pareto Fournisseurs & Catégories utilisés")
    c3, c4 = st.columns(2)
    with c3:
        fig = ParetoCharts.vendors(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_16")
    with c4:
        fig = ParetoCharts.pscs_category(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_17")

    st.divider()

    # Waterfall par cluster pour ce requester
    fig = WaterfallCharts.par_cluster(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="dd_18")

    st.divider()

    # ── 3. Tables ─────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        _banner("📋 Table Pareto — Fournisseurs")
        tbl = ParetoCharts.table_pareto(df, 'Vendor Name', 'Fournisseur')
        if tbl is not None:
            tbl['Spend (€)'] = tbl['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl, use_container_width=True, hide_index=True)
    with col_b:
        _banner("📋 Table Pareto — Catégories PSCS")
        tbl2 = ParetoCharts.table_pareto(df, 'PSCS Category', 'Catégorie')
        if tbl2 is not None:
            tbl2['Spend (€)'] = tbl2['Spend (€)'].apply(lambda x: f"{x:,.0f} €")
            st.dataframe(tbl2, use_container_width=True, hide_index=True)

    st.divider()

    # ── 4. Détail de toutes les commandes, du plus cher au moins cher ─────
    _banner("🧾 Toutes les commandes — du plus cher au moins cher")

    # Colonnes disponibles à afficher (ordre de priorité)
    detail_cols = [c for c in [
        'PO', 'PO Item', 'Invoice Posting Date', 'Vendor Name',
        'PSCS Cluster', 'PSCS Category', 'Item Text',
        'Total  spend', 'CAPEX Spend', 'FI Spend', 'MM Spend',
        'Order quantity', 'Prix_Unitaire',
        'Purchasing Group Name', 'Reference',
    ] if c in df.columns]

    detail = (df[detail_cols]
              .sort_values('Total  spend', ascending=False)
              .reset_index(drop=True))

    # Formatage lisible
    detail_display = detail.copy()
    if 'Invoice Posting Date' in detail_display.columns:
        detail_display['Invoice Posting Date'] = (
            detail_display['Invoice Posting Date'].dt.strftime('%Y-%m-%d')
        )

    # Rang global
    detail_display.insert(0, '#', range(1, len(detail_display) + 1))

    # Calcul du % cumulé du spend pour ce requester
    total_req = detail['Total  spend'].sum()
    if total_req > 0:
        detail_display['% Cumulé'] = (
            detail['Total  spend'].cumsum() / total_req * 100
        ).round(1).astype(str) + ' %'

    # Mise en forme des colonnes numériques
    for col in ['Total  spend', 'CAPEX Spend', 'FI Spend', 'MM Spend', 'Prix_Unitaire']:
        if col in detail_display.columns:
            detail_display[col] = detail_display[col].apply(lambda x: f"{x:,.0f} €")
    if 'Order quantity' in detail_display.columns:
        detail_display['Order quantity'] = detail_display['Order quantity'].apply(
            lambda x: f"{x:,.2f}")

    # Résumé rapide au-dessus du tableau
    n_total   = len(detail)
    top5_pct  = (detail.head(5)['Total  spend'].sum() / total_req * 100) if total_req > 0 else 0
    top10_pct = (detail.head(10)['Total  spend'].sum() / total_req * 100) if total_req > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📋 Total commandes",    f"{n_total:,}")
    m2.metric("💶 Spend total",        f"{total_req:,.0f} €")
    m3.metric("🔝 Top 5 → % du total", f"{top5_pct:.1f}%")
    m4.metric("🔝 Top 10 → % total",   f"{top10_pct:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # Filtre rapide sur le tableau
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        search_vendor = st.text_input("🔎 Filtrer par fournisseur", key="req_tbl_vendor")
    with col_f2:
        search_cat = st.text_input("🔎 Filtrer par catégorie", key="req_tbl_cat")
    with col_f3:
        show_n = st.selectbox("Afficher", [50, 100, 250, 500, "Tout"],
                              index=1, key="req_tbl_n")

    # Appliquer les filtres texte
    mask = pd.Series(True, index=detail.index)
    if search_vendor and 'Vendor Name' in detail.columns:
        mask &= detail['Vendor Name'].astype(str).str.contains(
            search_vendor, case=False, na=False)
    if search_cat and 'PSCS Category' in detail.columns:
        mask &= detail['PSCS Category'].astype(str).str.contains(
            search_cat, case=False, na=False)

    filtered_detail = detail_display.loc[mask]
    if show_n != "Tout":
        filtered_detail = filtered_detail.head(int(show_n))

    st.dataframe(
        filtered_detail,
        use_container_width=True,
        hide_index=True,
        column_config={
            '#':              st.column_config.NumberColumn(width='small'),
            'Total  spend':   st.column_config.TextColumn('Total (€)',   width='medium'),
            'CAPEX Spend':    st.column_config.TextColumn('CAPEX (€)',   width='medium'),
            'FI Spend':       st.column_config.TextColumn('FI (€)',      width='medium'),
            'MM Spend':       st.column_config.TextColumn('MM (€)',      width='medium'),
            'Prix_Unitaire':  st.column_config.TextColumn('Prix unit.',  width='medium'),
            '% Cumulé':       st.column_config.TextColumn('% Cumulé',   width='small'),
            'Invoice Posting Date': st.column_config.TextColumn('Date',  width='small'),
        }
    )

    # Export CSV du détail
    csv = detail.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Exporter toutes les commandes (CSV)",
        csv,
        f"commandes_{requester_name.replace(' ', '_')}.csv",
        "text/csv",
        key="req_detail_csv",
    )


# ══════════════════════════════════════════════════════════════════════════════
# VUE PÉRIODE
# ══════════════════════════════════════════════════════════════════════════════

def _view_period(df_full: pd.DataFrame):
    st.title("📅 Analyse par Période")

    if 'Année_Mois' not in df_full.columns:
        st.warning("Colonne de période indisponible.")
        return

    periods = sorted(df_full['Année_Mois'].unique())
    sel_period = st.selectbox("Sélectionner la période", periods,
                              index=len(periods) - 1 if periods else 0)
    df = df_full[df_full['Année_Mois'] == sel_period]

    st.caption(f"Période : **{sel_period}** — {len(df):,} commandes")
    _kpis_row(df, 'Vendor Name', 'Fournisseurs')
    st.divider()

    # Waterfall de toutes les périodes (en contexte) + période sélectionnée mise en avant
    _banner("📊 Waterfall Global + focus période")
    c1, c2 = st.columns(2)
    with c1:
        # Waterfall global toutes périodes
        fig = WaterfallCharts.mensuel(df_full)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_19")
    with c2:
        # Pareto vendors pour la période sélectionnée
        fig = ParetoCharts.vendors(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_20")

    st.divider()

    c3, c4 = st.columns(2)
    with c3:
        fig = ParetoCharts.pscs_category(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_21")
    with c4:
        fig = StructureCharts.treemap_pscs(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="dd_22")

    st.divider()
    fig = WaterfallCharts.par_cluster(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key="dd_23")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if 'df' not in st.session_state or st.session_state.df is None:
        st.error("❌ Aucune donnée chargée — retournez à la page principale.")
        if st.button("← Accueil"):
            st.switch_page("main.py")
        return

    context = st.session_state.get('drill_context', {})

    # Bouton retour toujours visible en haut à droite
    col_spacer, col_back = st.columns([6, 1])
    with col_back:
        _back_button()

    st.divider()

    df_full = st.session_state.df

    ctype = context.get('type')
    if ctype == 'vendor':
        _view_vendor(df_full, context['vendor_name'])
    elif ctype == 'category':
        _view_category(df_full, context['category_name'])
    elif ctype == 'requester':
        _view_requester(df_full, context['requester_name'])
    elif ctype == 'period':
        _view_period(df_full)
    else:
        st.info("ℹ️ Aucun contexte sélectionné. Retournez au dashboard et choisissez un élément.")


if __name__ == "__main__":
    main()