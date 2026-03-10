import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_processor import SpendDataProcessor
from visualizations import OverviewCharts, CapexOpexCharts, ParetoCharts, ClusterCharts, CapexOpexTabCharts

st.set_page_config(page_title="Spend Analytics – Lafarge", page_icon="📊", layout="wide")

# ─── High-contrast CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Base ── */
  html, body,
  [data-testid="stAppViewContainer"],
  .main, .block-container {
    background-color: #F4F6F9 !important;
    color: #1A1A2E !important;
  }
  * { font-family: 'Segoe UI', Arial, sans-serif; }

  /* ── Sidebar background ── */
  [data-testid="stSidebar"] {
    background-color: #1B3A5C !important;
  }

  /* White text for sidebar labels, headers, markdown */
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] .stRadio label,
  [data-testid="stSidebar"] .stCheckbox label {
    color: #FFFFFF !important;
  }

  /* Selectbox + multiselect: white bg, dark text so selected value is readable */
  [data-testid="stSidebar"] [data-baseweb="select"] {
    background-color: #FFFFFF !important;
  }
  [data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    color: #1A1A2E !important;
  }
  [data-testid="stSidebar"] [data-baseweb="select"] span,
  [data-testid="stSidebar"] [data-baseweb="select"] div {
    color: #1A1A2E !important;
  }
  /* Multiselect tags */
  [data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: #2980B9 !important;
  }
  [data-testid="stSidebar"] [data-baseweb="tag"] span {
    color: #FFFFFF !important;
  }
  /* Date input */
  [data-testid="stSidebar"] [data-baseweb="input"] > div {
    background-color: #FFFFFF !important;
  }
  [data-testid="stSidebar"] input {
    color: #1A1A2E !important;
    background-color: #FFFFFF !important;
  }
  /* Dropdown options panel */
  [data-baseweb="popover"] [data-baseweb="menu"] {
    background-color: #FFFFFF !important;
  }
  [data-baseweb="popover"] [data-baseweb="menu"] li {
    color: #1A1A2E !important;
  }
  [data-baseweb="popover"] [data-baseweb="menu"] li:hover {
    background-color: #EBF2FA !important;
  }

  /* ── Page titles ── */
  h1,h2,h3,h4,h5,h6 {
    color: #1B3A5C !important;
    font-family: 'Segoe UI', Arial, sans-serif !important;
  }

  /* ── Section banners ── */
  .section-banner {
    background: linear-gradient(90deg, #1B3A5C 0%, #2980B9 100%);
    color: #FFFFFF !important;
    padding: 11px 20px; border-radius: 7px;
    font-weight: 700; font-size: 15px;
    margin: 20px 0 10px 0; letter-spacing: 0.3px;
  }
  .section-banner * { color: #FFFFFF !important; }

  .section-sub {
    background: #FFFFFF;
    color: #1B3A5C !important;
    padding: 7px 16px;
    border-left: 4px solid #2980B9;
    border-radius: 0 6px 6px 0;
    font-weight: 700; font-size: 14px;
    margin: 12px 0 6px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab"] {
    font-size: 14px; font-weight: 700;
    color: #1B3A5C !important;
  }
  .stTabs [aria-selected="true"] {
    border-bottom: 3px solid #E74C3C !important;
    color: #E74C3C !important;
  }

  /* ── KPI metrics ── */
  [data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #D5E8F5;
    border-radius: 10px;
    padding: 14px 18px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.07);
  }
  [data-testid="stMetricLabel"] {
    font-weight: 700;
    color: #1B3A5C !important;
    font-size: 0.82rem !important;
  }
  [data-testid="stMetricValue"] {
    color: #1A1A2E !important;
    font-size: 1.3rem !important;
    font-weight: 800 !important;
  }
  [data-testid="stMetricDelta"] svg { display: none; }
  [data-testid="stMetricDelta"][data-direction="increase"] > div { color: #E74C3C !important; }
  [data-testid="stMetricDelta"][data-direction="decrease"] > div { color: #27AE60 !important; }

  /* ── Plotly chart text ── */
  .js-plotly-plot .plotly .gtitle,
  .js-plotly-plot .plotly .xtitle,
  .js-plotly-plot .plotly .ytitle,
  .js-plotly-plot .plotly .g-xtitle text,
  .js-plotly-plot .plotly .g-ytitle text,
  .js-plotly-plot .plotly .xtick text,
  .js-plotly-plot .plotly .ytick text,
  .js-plotly-plot .plotly .legendtext,
  .js-plotly-plot .plotly .annotation-text {
    fill: #2C3E50 !important;
    color: #2C3E50 !important;
  }
  
  /* Treemap labels - force white for contrast on colored blocks */
  .js-plotly-plot .treemap .treetext,
  .js-plotly-plot .treemap .treetext text,
  .js-plotly-plot .treemap tspan {
    fill: white !important;
    color: white !important;
  }
  
  /* Generic text fallback (not important to allow chart-specific overrides) */
  .js-plotly-plot text {
    fill: #2C3E50;
  }

  /* ── Dividers ── */
  hr { border-color: #D5E8F5; margin: 14px 0; }
  
  /* ── Buttons ── */
  .stButton > button {
    background-color: #E74C3C !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
  }
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df'          not in st.session_state: st.session_state.df          = None

processor   = SpendDataProcessor()
MONTHS_FULL = ['January','February','March','April','May','June',
               'July','August','September','October','November','December']


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def _sidebar_filters(df):
    st.sidebar.header("🔍 Filtres")
    if st.sidebar.button("🔄 Reset"):
        st.session_state.clear(); st.rerun()
    st.sidebar.divider()
    f = {}

    st.sidebar.markdown('**📅 Période**')
    years = sorted(df['Année'].dropna().unique().astype(int).tolist(), reverse=True)
    f['year'] = st.sidebar.selectbox('Année', years, index=0)
    col_ytd, col_mtd = st.sidebar.columns(2)
    f['year_to_date']  = col_ytd.checkbox('YTD', value=False)
    f['month_to_date'] = col_mtd.checkbox('MTD', value=False)
    available_months = ([m for m in MONTHS_FULL if m in df['Nom_Mois'].unique()]
                        if 'Nom_Mois' in df.columns else [])
    f['months'] = st.sidebar.multiselect('Mois', available_months)
    if 'Date' in df.columns:
        mn, mx = df['Date'].min().date(), df['Date'].max().date()
        f['date_range'] = st.sidebar.date_input('Plage personnalisée', value=(mn,mx), min_value=mn, max_value=mx)
    else:
        f['date_range'] = ()

    st.sidebar.divider()
    st.sidebar.markdown('**🏷️ Dimensions**')
    dim_map = [
        ('company_code',     'Company Code descr',   'Company Code'),
        ('vendor',           'Vendor Name',           'Vendor'),
        ('requestor',        'Requester',             'Requestor'),
        ('wbs',              'WBS Element ID',        'WBS Element ID'),
        ('purchasing_group', 'Purchasing Group Name', 'Purchasing Group'),
        ('cost_center',      'Cost Center ID',        'Cost Center ID'),
        ('gl_account',       'GL Account Name',       'GL Account Name'),
        ('cluster',          'PSCS Cluster',          'Cluster'),
        ('category',         'PSCS Category',         'Category'),
    ]
    for key, col, label in dim_map:
        if col in df.columns:
            opts = sorted(df[col].dropna().unique().tolist())
            f[key] = st.sidebar.multiselect(label, opts, key=f'filter_{key}')
        else:
            f[key] = []

    st.sidebar.divider()
    st.sidebar.markdown('**💰 Type de Dépense**')
    f['capex_opex'] = st.sidebar.radio('Type', ['All','CAPEX only','OPEX only'], horizontal=True, index=0)
    return f


# ══════════════════════════════════════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════════════════════════════════════
def _kpis(comp, year):
    s, d, has = comp['current'], comp['deltas'], comp['has_comparison']
    prev = year - 1 if year else None
    st.markdown('<div class="section-banner">📈 Indicateurs Clés</div>', unsafe_allow_html=True)
    if has and prev:
        st.caption(
            f'Δ = {year} vs {prev} &nbsp;|&nbsp; '
            f'<span style="color:#E74C3C;font-weight:700">▲ hausse</span> &nbsp; '
            f'<span style="color:#27AE60;font-weight:700">▼ baisse</span>',
            unsafe_allow_html=True)

    _fmt     = lambda k: f"{d[k]:+,.1f} kCHF" if has else None
    _fmt_pct = lambda k: f"{d[k]:+.1f} pp"   if has else None

    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    c1.metric('💰 Total Spend', f"{s['total_spend']:,.1f} kCHF", _fmt('total_spend'))
    c2.metric('🏗️ CAPEX',       f"{s['total_capex']:,.1f} kCHF", _fmt('total_capex'))
    c3.metric('📋 OPEX',        f"{s['total_opex']:,.1f} kCHF",  _fmt('total_opex'))
    c4.metric('📑 FI Spend',    f"{s['total_fi']:,.1f} kCHF",    _fmt('total_fi'))
    c5.metric('📦 MM Spend',    f"{s['total_mm']:,.1f} kCHF",    _fmt('total_mm'))
    c6.metric('🏗️ CAPEX %',     f"{s['capex_pct']:.1f} %",       _fmt_pct('capex_pct'))
    c7.metric('📋 OPEX %',      f"{s['opex_pct']:.1f} %",        _fmt_pct('opex_pct'))
    st.write('')
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric('📑 Commandes',    f"{s['total_rows']:,}")
    c2.metric('🏢 Fournisseurs', f"{s['unique_vendors']:,}")
    c3.metric('👥 Requesters',   f"{s['unique_requesters']:,}")
    c4.metric('📦 Catégories',   f"{s['unique_categories']:,}")
    c5.metric('🏷️ Clusters',     f"{s.get('unique_clusters',0):,}")


# ══════════════════════════════════════════════════════════════════════════════
# HELPER – year picker
# ══════════════════════════════════════════════════════════════════════════════
def _variation_year_picker(df, key):
    all_years  = sorted(df['Année'].dropna().unique().astype(int).tolist())
    selectable = [y for y in all_years if y + 1 in all_years] or all_years
    desc       = sorted(selectable, reverse=True)
    default    = min(1, len(desc) - 1)
    col, _     = st.columns([2, 5])
    with col:
        chosen = st.selectbox("📅 Année de référence (Y vs Y+1)", desc, index=default, key=key)
    return int(chosen)


# ══════════════════════════════════════════════════════════════════════════════
# TAB – OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
def _tab_overview(filtered_df):

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — VARIATION CHARTS  (one shared year picker for all 4)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>📉 Analyses de Variation (Y vs Y+1)</div>",
                unsafe_allow_html=True)

    # Single year picker drives ALL variation charts below
    yr   = _variation_year_picker(filtered_df, key="yr_variation")
    yr1  = yr + 1

    # Row 1 — Cluster variation (full width)
    st.markdown("<div class='section-sub'>📊 Variation du Spend par Cluster</div>",
                unsafe_allow_html=True)
    st.plotly_chart(OverviewCharts.cluster_variation_waterfall(filtered_df, yr),
                    use_container_width=True)

    st.write("")

    # Row 2 — CAPEX monthly | OPEX monthly
    col_c, col_o = st.columns(2)
    with col_c:
        st.markdown(f"<div class='section-sub'>🏗️ Variation CAPEX mensuelle — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexCharts.capex_monthly_variation(filtered_df, yr),
                        use_container_width=True)
    with col_o:
        st.markdown(f"<div class='section-sub'>📋 Variation OPEX mensuelle — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexCharts.opex_monthly_variation(filtered_df, yr),
                        use_container_width=True)

    st.write("")

    # Row 3 — Total Spend variation (full width)
    st.markdown(f"<div class='section-sub'>📈 Variation Total Spend — {yr} vs {yr1}</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexCharts.total_spend_yearly_variation(filtered_df, yr),
                    use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — CLUSTER & SPEND  (no year picker — reflects sidebar filters)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🗺️ Vue d'ensemble par Cluster & CAPEX/OPEX</div>",
                unsafe_allow_html=True)

    # Row 1 — Treemap | Cluster bar
    col_tree, col_bar = st.columns([3, 2])
    with col_tree:
        st.markdown("<div class='section-sub'>🌳 Treemap Cluster → Catégorie</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(OverviewCharts.cluster_category_treemap(filtered_df),
                        use_container_width=True)
    with col_bar:
        st.markdown("<div class='section-sub'>📊 Spend par Cluster</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(OverviewCharts.cluster_spend_bar(filtered_df),
                        use_container_width=True)

    st.write("")

    # Row 2 — Top 10 Company Codes (full width)
    st.markdown("<div class='section-sub'>🏢 Top 10 Company Code</div>",
                unsafe_allow_html=True)
    st.plotly_chart(OverviewCharts.top10_company_codes(filtered_df),
                    use_container_width=True)

    st.write("")

    # Row 3 — Stacked CAPEX/OPEX by year (full width)
    st.markdown("<div class='section-sub'>📊 CAPEX + OPEX par Année — Stacked</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexCharts.capex_opex_stacked_bar(filtered_df),
                    use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — PARETO
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🎯 Analyses Pareto — Top entités générant 80% du Spend</div>",
                unsafe_allow_html=True)

    col_v, col_r = st.columns(2)
    with col_v:
        st.markdown("<div class='section-sub'>🏢 Pareto Fournisseurs</div>", unsafe_allow_html=True)
        st.plotly_chart(ParetoCharts.vendor_pareto(filtered_df), use_container_width=True)
    with col_r:
        st.markdown("<div class='section-sub'>👥 Pareto Requesters</div>", unsafe_allow_html=True)
        st.plotly_chart(ParetoCharts.requester_pareto(filtered_df), use_container_width=True)

    st.write("")
    col_cc, col_gl = st.columns(2)
    with col_cc:
        st.markdown("<div class='section-sub'>🏦 Pareto Cost Center</div>", unsafe_allow_html=True)
        st.plotly_chart(ParetoCharts.cost_center_pareto(filtered_df), use_container_width=True)
    with col_gl:
        st.markdown("<div class='section-sub'>📒 Pareto GL Account</div>", unsafe_allow_html=True)
        st.plotly_chart(ParetoCharts.gl_account_pareto(filtered_df), use_container_width=True)

    st.write("")
    _, col_pg, _ = st.columns([1, 3, 1])
    with col_pg:
        st.markdown("<div class='section-sub'>🛒 Pareto Purchasing Group</div>", unsafe_allow_html=True)
        st.plotly_chart(ParetoCharts.purchasing_group_pareto(filtered_df), use_container_width=True)



# ══════════════════════════════════════════════════════════════════════════════
# TAB – CLUSTER
# ══════════════════════════════════════════════════════════════════════════════
def _tab_cluster(filtered_df):

    # ── shared year picker (used by ALL variation charts in this tab) ─────────
    yr  = _variation_year_picker(filtered_df, key="yr_cluster_tab")
    yr1 = yr + 1

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — GLOBAL CLUSTER VIEW
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🗺️ Vue Globale par Cluster</div>",
                unsafe_allow_html=True)

    # Row 1: spend bar (full width)
    st.markdown("<div class='section-sub'>📊 Spend par Cluster</div>",
                unsafe_allow_html=True)
    st.plotly_chart(ClusterCharts.spend_per_cluster(filtered_df),
                    use_container_width=True)

    st.write("")

    # Row 2: cluster variation waterfall (full width — needs space for many clusters)
    st.markdown(f"<div class='section-sub'>📉 Variation Spend par Cluster — {yr} vs {yr1}</div>",
                unsafe_allow_html=True)
    st.plotly_chart(ClusterCharts.cluster_yoy_variation(filtered_df, yr),
                    use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — FOCUS CLUSTER  (inline cluster picker)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🔍 Focus Cluster</div>",
                unsafe_allow_html=True)

    clusters = sorted(filtered_df["PSCS Cluster"].dropna().unique().tolist())                if "PSCS Cluster" in filtered_df.columns else []

    # Default to Packaging if present, else first cluster
    default_cluster = "Packaging" if "Packaging" in clusters else (clusters[0] if clusters else None)
    default_idx     = clusters.index(default_cluster) if default_cluster in clusters else 0

    col_pick, _ = st.columns([2, 5])
    with col_pick:
        chosen_cluster = st.selectbox("🏷️ Choisir un Cluster", clusters,
                                      index=default_idx, key="cluster_focus_pick")

    if chosen_cluster:
        # Row 1: spend per category | monthly variation
        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown(f"<div class='section-sub'>📊 Spend par Catégorie — {chosen_cluster}</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(ClusterCharts.spend_per_category(filtered_df, chosen_cluster),
                            use_container_width=True)
        with col_d:
            st.markdown(f"<div class='section-sub'>📅 Variation Mensuelle — {chosen_cluster} — {yr} vs {yr1}</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(ClusterCharts.cluster_monthly_variation(filtered_df, chosen_cluster, yr),
                            use_container_width=True)

        st.write("")

        # Row 2: category YoY variation (full width)
        st.markdown(f"<div class='section-sub'>📉 Variation par Catégorie — {chosen_cluster} — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.category_yoy_variation(filtered_df, chosen_cluster, yr),
                        use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2b — FOCUS CATÉGORIE  (category picker driven by chosen_cluster)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🔬 Focus Catégorie — Variation Mensuelle</div>",
                unsafe_allow_html=True)

    if chosen_cluster:
        # Categories available in the chosen cluster
        categories = sorted(
            filtered_df[filtered_df["PSCS Cluster"] == chosen_cluster]["PSCS Category"]
            .dropna().unique().tolist()
        ) if "PSCS Category" in filtered_df.columns else []

        if categories:
            col_cat, _ = st.columns([2, 5])
            with col_cat:
                chosen_category = st.selectbox(
                    "📦 Choisir une Catégorie",
                    categories,
                    index=0,
                    key="category_focus_pick",
                )

            st.markdown(
                f"<div class='section-sub'>📅 Variation Mensuelle — {chosen_category} — {yr} vs {yr1}</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                ClusterCharts.category_monthly_variation(filtered_df, chosen_category, yr),
                use_container_width=True,
            )
        else:
            st.info("Aucune catégorie disponible pour ce cluster.")
    else:
        st.info("Sélectionnez un cluster ci-dessus pour voir les catégories.")

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — PARETO
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🎯 Analyses Pareto</div>",
                unsafe_allow_html=True)

    # Row 1: category pareto | cluster pareto
    col_e, col_f = st.columns(2)
    with col_e:
        st.markdown("<div class='section-sub'>📦 Pareto Catégories → 80% du Spend</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.category_pareto_by_cluster(filtered_df),
                        use_container_width=True)
    with col_f:
        st.markdown("<div class='section-sub'>🗺️ Pareto Clusters → 80% du Spend</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.cluster_pareto(filtered_df),
                        use_container_width=True)

    st.write("")

    # Row 2: top 10 vendors | top 10 requesters
    col_g, col_h = st.columns(2)
    with col_g:
        st.markdown("<div class='section-sub'>🏢 Top 10 Fournisseurs</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.top10_vendors(filtered_df),
                        use_container_width=True)
    with col_h:
        st.markdown("<div class='section-sub'>👥 Top 10 Requesters</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.top10_requesters(filtered_df),
                        use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4 — CAPEX / OPEX
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>💰 CAPEX / OPEX par Catégorie & Cluster</div>",
                unsafe_allow_html=True)

    col_i, col_j = st.columns(2)
    with col_i:
        st.markdown("<div class='section-sub'>📊 CAPEX vs OPEX par Catégorie</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.capex_opex_per_category(filtered_df),
                        use_container_width=True)
    with col_j:
        st.markdown("<div class='section-sub'>📊 CAPEX vs OPEX par Cluster</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.capex_opex_per_cluster(filtered_df),
                        use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB – CAPEX / OPEX
# ══════════════════════════════════════════════════════════════════════════════
def _tab_capex_opex(filtered_df):

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — BAR PLOTS  (no year filter — reflect sidebar selection)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>📊 Vue Globale — Répartition du Spend</div>",
                unsafe_allow_html=True)

    # Row 1 — CAPEX/OPEX total | FI/MM total
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='section-sub'>💰 Spend CAPEX vs OPEX</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.capex_opex_total_bar(filtered_df),
                        use_container_width=True)
    with col_b:
        st.markdown("<div class='section-sub'>📑 Spend FI vs MM</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.fi_mm_total_bar(filtered_df),
                        use_container_width=True)

    st.write("")

    # Row 2 — Stacked per year (full width)
    st.markdown("<div class='section-sub'>📅 Spend par Année — CAPEX/OPEX Stacked</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexTabCharts.stacked_spend_per_year(filtered_df),
                    use_container_width=True)

    st.write("")

    # Row 3 — Monthly grouped by year (full width)
    st.markdown("<div class='section-sub'>🗓️ Spend Mensuel — comparaison par Année</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexTabCharts.monthly_spend_by_year(filtered_df),
                    use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — VARIATION PLOTS  (single shared year picker)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>📉 Analyses de Variation (Y vs Y+1)</div>",
                unsafe_allow_html=True)

    yr  = _variation_year_picker(filtered_df, key="yr_capex_opex_tab")
    yr1 = yr + 1

    # Row 1 — CAPEX/OPEX variation bar | Total monthly variation waterfall
    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown(f"<div class='section-sub'>💰 Variation CAPEX/OPEX — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.capex_opex_variation_bar(filtered_df, yr),
                        use_container_width=True)
    with col_d:
        st.markdown(f"<div class='section-sub'>📅 Variation Total Spend Mensuelle — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.total_monthly_variation(filtered_df, yr),
                        use_container_width=True)

    st.write("")

    # Row 2 — Line chart evolution (full width)
    st.markdown("<div class='section-sub'>📈 Évolution du Spend sur toute la période</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexTabCharts.spend_evolution_line(filtered_df),
                    use_container_width=True)

    st.write("")

    # Row 3 — CAPEX monthly wf | OPEX monthly wf
    col_e, col_f = st.columns(2)
    with col_e:
        st.markdown(f"<div class='section-sub'>🏗️ Variation CAPEX Mensuelle — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.capex_monthly_var(filtered_df, yr),
                        use_container_width=True)
    with col_f:
        st.markdown(f"<div class='section-sub'>📋 Variation OPEX Mensuelle — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.opex_monthly_var(filtered_df, yr),
                        use_container_width=True)

    st.write("")

    # Row 4 — MM monthly wf | FI monthly wf
    col_g, col_h = st.columns(2)
    with col_g:
        st.markdown(f"<div class='section-sub'>📦 Variation MM Mensuelle — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.mm_monthly_var(filtered_df, yr),
                        use_container_width=True)
    with col_h:
        st.markdown(f"<div class='section-sub'>📑 Variation FI Mensuelle — {yr} vs {yr1}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.fi_monthly_var(filtered_df, yr),
                        use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # ── Logo & Header ─────────────────────────────────────────────────────────
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("lafarge.png", width=140)
    with col_title:
        st.markdown(
            '<h2 style="color:#1B3A5C;font-family:Segoe UI,Arial,sans-serif;'
            'font-weight:800;margin-bottom:0;">Spend Analytics Dashboard</h2>'
            '<p style="color:#E74C3C;font-family:Segoe UI,Arial,sans-serif;'
            'font-weight:600;margin-top:2px;">Holcim Lafarge – Procurement Intelligence</p>',
            unsafe_allow_html=True,
        )

    if not st.session_state.data_loaded:
        uploaded = st.file_uploader('Choisissez votre fichier Excel', type=['xlsx', 'xls'])
        if uploaded:
            with st.spinner('Traitement en cours…'):
                df, err = processor.load_and_process(uploaded)
            if err:
                st.error(err)
            else:
                st.session_state.df          = df
                st.session_state.data_loaded = True
                st.success(f'✅ {len(df):,} lignes chargées avec succès')
                st.rerun()
        return

    filters     = _sidebar_filters(st.session_state.df)
    filtered_df = processor.apply_filters(st.session_state.df, filters)

    if len(filtered_df) == 0:
        st.warning("Aucune donnée après filtrage")
        return

    comp_stats = processor.get_comparative_stats(st.session_state.df, filters)
    _kpis(comp_stats, filters.get('year'))
    st.divider()

    tab_overview, tab_cluster, tab_co = st.tabs(['🗺️ Overview', '🏷️ Clusters', '💰 CAPEX/OPEX'])
    with tab_overview:
        _tab_overview(filtered_df=filtered_df)
    with tab_cluster:
        _tab_cluster(filtered_df=filtered_df)
    with tab_co:
        _tab_capex_opex(filtered_df=filtered_df)


if __name__ == '__main__':
    main()