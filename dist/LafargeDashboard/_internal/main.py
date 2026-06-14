import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_processor import SpendDataProcessor
from visualizations import (OverviewCharts, CapexOpexCharts, ParetoCharts,
                             ClusterCharts, CapexOpexTabCharts)

st.set_page_config(page_title="Spend Analytics – Lafarge", page_icon="📊", layout="wide")
import sys, os

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  html,body,[data-testid="stAppViewContainer"],.main,.block-container{
    background-color:#F4F6F9 !important;color:#1A1A2E !important;}
  *{font-family:'Segoe UI',Arial,sans-serif;}
  [data-testid="stSidebar"]{background-color:#1B3A5C !important;}
  [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3,[data-testid="stSidebar"] p,
  [data-testid="stSidebar"] label,[data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] .stRadio label,
  [data-testid="stSidebar"] .stCheckbox label{color:#FFFFFF !important;}
  [data-testid="stSidebar"] [data-baseweb="select"]{background-color:#FFFFFF !important;}
  [data-testid="stSidebar"] [data-baseweb="select"]>div{background-color:#FFFFFF !important;color:#1A1A2E !important;}
  [data-testid="stSidebar"] [data-baseweb="tag"]{background-color:#2980B9 !important;}
  [data-testid="stSidebar"] [data-baseweb="tag"] span{color:#FFFFFF !important;}
  [data-testid="stSidebar"] [data-baseweb="input"]>div{background-color:#FFFFFF !important;}
  [data-testid="stSidebar"] input{color:#1A1A2E !important;background-color:#FFFFFF !important;}
  [data-baseweb="popover"] [data-baseweb="menu"]{background-color:#FFFFFF !important;}
  [data-baseweb="popover"] [data-baseweb="menu"] li{color:#1A1A2E !important;}
  [data-baseweb="popover"] [data-baseweb="menu"] li:hover{background-color:#EBF2FA !important;}
  h1,h2,h3,h4,h5,h6{color:#1B3A5C !important;font-family:'Segoe UI',Arial,sans-serif !important;}
  .section-banner{
    background:linear-gradient(90deg,#1B3A5C 0%,#2980B9 100%);
    color:#FFFFFF !important;padding:11px 20px;border-radius:7px;
    font-weight:700;font-size:15px;margin:20px 0 10px 0;letter-spacing:0.3px;}
  .section-banner *{color:#FFFFFF !important;}
  .section-sub{
    background:#FFFFFF;color:#1B3A5C !important;padding:7px 16px;
    border-left:4px solid #2980B9;border-radius:0 6px 6px 0;
    font-weight:700;font-size:14px;margin:12px 0 6px 0;
    box-shadow:0 1px 3px rgba(0,0,0,0.08);}
  .section-sub-orange{
    background:#FFF8F0;color:#A04000 !important;padding:7px 16px;
    border-left:4px solid #E67E22;border-radius:0 6px 6px 0;
    font-weight:700;font-size:14px;margin:12px 0 6px 0;}
  .section-sub-purple{
    background:#F8F0FF;color:#5B2C8E !important;padding:7px 16px;
    border-left:4px solid #8E44AD;border-radius:0 6px 6px 0;
    font-weight:700;font-size:14px;margin:12px 0 6px 0;}
  .stTabs [data-baseweb="tab"]{font-size:14px;font-weight:700;color:#1B3A5C !important;}
  .stTabs [aria-selected="true"]{border-bottom:3px solid #E74C3C !important;color:#E74C3C !important;}
  [data-testid="stMetric"]{
    background:#FFFFFF;border:1px solid #D5E8F5;border-radius:10px;
    padding:25px 32px !important;box-shadow:0 4px 10px rgba(0,0,0,0.1);}
  [data-testid="stMetricLabel"]{font-weight:700;color:#1B3A5C !important;font-size:1.0rem !important;}
  [data-testid="stMetricValue"]{color:#1A1A2E !important;font-size:1.7rem !important;font-weight:800 !important;}
  [data-testid="stMetricDelta"] svg{display:none;}
  [data-testid="stMetricDelta"][data-direction="increase"]>div{color:#E74C3C !important;}
  [data-testid="stMetricDelta"][data-direction="decrease"]>div{color:#27AE60 !important;}
  hr{border-color:#D5E8F5;margin:14px 0;}
  .stButton>button{background-color:#E74C3C !important;color:white !important;
    border:none !important;border-radius:6px !important;font-weight:600 !important;}
  /* Force Plotly axis text dark */
  .js-plotly-plot .plotly .xtick text,
  .js-plotly-plot .plotly .ytick text,
  .js-plotly-plot .plotly .g-xtitle text,
  .js-plotly-plot .plotly .g-ytitle text,
  .js-plotly-plot .plotly .gtitle,
  .js-plotly-plot .plotly .legendtext {
    fill: #111111 !important;
    color: #111111 !important;
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
    years     = sorted(df['Année'].dropna().unique().astype(int).tolist(), reverse=True)
    year_opts = ["Toutes"] + [str(y) for y in years]
    sel_year  = st.sidebar.selectbox('Année', year_opts, index=1)
    f['year'] = int(sel_year) if sel_year != "Toutes" else None

    col_ytd, col_mtd = st.sidebar.columns(2)
    f['year_to_date']  = col_ytd.checkbox('YTD', value=False,
        help="YTD: mois sélectionné → Jan→mois choisi. Sans mois → toute l'année.")
    f['month_to_date'] = col_mtd.checkbox('MTD', value=False,
        help="MTD: affiche uniquement le(s) mois sélectionné(s).")

    available_months = ([m for m in MONTHS_FULL if m in df['Nom_Mois'].unique()]
                        if 'Nom_Mois' in df.columns else [])
    f['months'] = st.sidebar.multiselect('Mois', available_months)

    if 'Date' in df.columns:
        mn, mx = df['Date'].min().date(), df['Date'].max().date()
        f['date_range'] = st.sidebar.date_input(
            'Plage personnalisée', value=(mn,mx), min_value=mn, max_value=mx)
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
        ("PSCS Name", "PSCS Name", "PSCS Name")
    ]
    for key, col, label in dim_map:
        if col in df.columns:
            series = df[col]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            opts = sorted(series.dropna().unique().tolist())
            f[key] = st.sidebar.multiselect(label, opts, key=f'filter_{key}')
        else:
            f[key] = []

    st.sidebar.divider()

    return f


def _strip_date_filters(filters: dict) -> dict:
    """
    Return a copy of filters with ALL date-related keys neutralised.
    Used to feed the variation/waterfall charts so they always have
    access to both years (current and previous) regardless of what the
    user selected in the sidebar date section.

    Keys neutralised:
      year           → None   (no year restriction)
      months         → []     (no month restriction)
      year_to_date   → False
      month_to_date  → False
      date_range     → ()     (no custom range)
    """
    stripped = dict(filters)
    stripped['year']           = None
    stripped['months']         = []
    stripped['year_to_date']   = False
    stripped['month_to_date']  = False
    stripped['date_range']     = ()
    return stripped


# ══════════════════════════════════════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════════════════════════════════════
def _kpis(comp, year):
    s, d, has = comp['current'], comp['deltas'], comp['has_comparison']
    current_year  = comp.get('current_year',  year)
    previous_year = comp.get('previous_year', (current_year - 1 if current_year else None))

    st.markdown('<div class="section-banner">📈 Indicateurs Clés</div>', unsafe_allow_html=True)
    if has and current_year and previous_year:
        st.caption(
            f'Δ = {current_year} vs {previous_year} &nbsp;|&nbsp; '
            f'<span style="color:#E74C3C;font-weight:700">▲ hausse</span> &nbsp; '
            f'<span style="color:#27AE60;font-weight:700">▼ baisse</span>',
            unsafe_allow_html=True)

    def _fmt(k):
        if not has: return None
        return f"{d[k]:+,.0f} kCHF"
    def _fmt_pct(k):
        if not has: return None
        return f"{d[k]:+.1f} pp"

    c1,c2,c3 = st.columns(3)
    c1.metric('💰 Total Spend', f"{s['total_spend']:,.0f} kCHF", _fmt('total_spend'), delta_color="inverse")
    c2.metric('🏗️ CAPEX',        f"{s['total_capex']:,.0f} kCHF", _fmt('total_capex'), delta_color="inverse")
    c3.metric('📋 OPEX',         f"{s['total_opex']:,.0f} kCHF",  _fmt('total_opex'),  delta_color="inverse")
    st.write('')
    c4,c5,c6,c7 = st.columns(4)
    c4.metric('📑 FI Spend', f"{s['total_fi']:,.0f} kCHF",  _fmt('total_fi'),  delta_color="inverse")
    c5.metric('📦 MM Spend', f"{s['total_mm']:,.0f} kCHF",  _fmt('total_mm'),  delta_color="inverse")
    c6.metric('🏗️ CAPEX %',  f"{s['capex_pct']:.1f} %",     _fmt_pct('capex_pct'), delta_color="inverse")
    c7.metric('📋 OPEX %',   f"{s['opex_pct']:.1f} %",      _fmt_pct('opex_pct'),  delta_color="inverse")
    st.write('')
    c1,c2,c5 = st.columns(3)
    c1.metric('📑 Commandes',    f"{s['total_rows']:,}")
    c2.metric('🏢 Fournisseurs', f"{s['unique_vendors']:,}")
    c5.metric('🏷️ Clusters',     f"{s.get('unique_clusters',0):,}")


# ══════════════════════════════════════════════════════════════════════════════
# YEAR PICKER  (returns comp_year: select 2025 → shows 2024 vs 2025)
# ══════════════════════════════════════════════════════════════════════════════
def _comp_year_picker(df, key):
    """
    Uses the FULL (date-unfiltered) dataframe to build the year list,
    so the picker always offers all available years.
    """
    all_years  = sorted(df['Année'].dropna().unique().astype(int).tolist())
    selectable = [y for y in all_years if (y-1) in all_years] or all_years
    desc       = sorted(selectable, reverse=True)
    col, _     = st.columns([2, 5])
    with col:
        chosen = st.selectbox("📅 Année de comparaison (affiche Y-1 vs Y)",
                              desc, index=0, key=key)
    return int(chosen)


# ══════════════════════════════════════════════════════════════════════════════
# TAB – OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
def _tab_overview(filtered_df, variation_df):
    """
    filtered_df  : date + dimension filters applied  → used for non-variation charts
    variation_df : only dimension filters applied    → used for all variation/waterfall charts
    """
    st.markdown("<div class='section-banner'>📉 Analyses de Variation (Y-1 vs Y)</div>",
                unsafe_allow_html=True)
    # Year picker uses variation_df so all years are available
    comp_yr = _comp_year_picker(variation_df, key="yr_overview")
    base_yr = comp_yr - 1

    st.markdown(f"<div class='section-sub'>📊 Variation du Spend par Cluster — {base_yr} vs {comp_yr}</div>",
                unsafe_allow_html=True)
    st.plotly_chart(OverviewCharts.cluster_variation_waterfall(variation_df, comp_yr),
                    use_container_width=True)
    st.write("")

    col_c, col_o = st.columns(2)
    with col_c:
        st.markdown(f"<div class='section-sub'>🏗️ Variation CAPEX mensuelle — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexCharts.capex_monthly_variation(variation_df, comp_yr),
                        use_container_width=True)
    with col_o:
        st.markdown(f"<div class='section-sub'>📋 Variation OPEX mensuelle — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexCharts.opex_monthly_variation(variation_df, comp_yr),
                        use_container_width=True)

    st.write("")
    st.markdown(f"<div class='section-sub'>📈 Variation Total Spend — {base_yr} vs {comp_yr}</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexCharts.total_spend_yearly_variation(variation_df, comp_yr),
                    use_container_width=True)

    st.divider()
    st.markdown("<div class='section-banner'>🗺️ Vue d'ensemble — Cluster & CAPEX/OPEX</div>",
                unsafe_allow_html=True)
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
    st.markdown("<div class='section-sub'>🏢 Top 10 Company Code</div>", unsafe_allow_html=True)
    st.plotly_chart(OverviewCharts.top10_company_codes(filtered_df), use_container_width=True)

    st.write("")
    st.markdown("<div class='section-sub'>📊 CAPEX + OPEX par Année — Stacked</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexCharts.capex_opex_stacked_bar(filtered_df),
                    use_container_width=True)

    st.divider()
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
    _, col_pg, _ = st.columns([1,3,1])
    with col_pg:
        st.markdown("<div class='section-sub'>🛒 Pareto Purchasing Group</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ParetoCharts.purchasing_group_pareto(filtered_df),
                        use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB – CLUSTER  (hierarchy: Cluster → Category → PSCS Name)
# ══════════════════════════════════════════════════════════════════════════════
def _tab_cluster(filtered_df, variation_df):
    """
    filtered_df  : date + dimension filters applied  → used for non-variation charts
    variation_df : only dimension filters applied    → used for all variation/waterfall charts
    """
    comp_yr = _comp_year_picker(variation_df, key="yr_cluster_tab")
    base_yr = comp_yr - 1

    # ════════════════════════════════════════════════════════════════════
    # A — GLOBAL VIEW
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🗺️ Vue Globale par Cluster</div>",
                unsafe_allow_html=True)

    st.markdown("<div class='section-sub'>📊 Spend par Cluster</div>", unsafe_allow_html=True)
    st.plotly_chart(ClusterCharts.spend_per_cluster(filtered_df), use_container_width=True)

    st.markdown(f"<div class='section-sub'>📉 Variation Spend par Cluster — {base_yr} vs {comp_yr}</div>",
                unsafe_allow_html=True)
    st.plotly_chart(ClusterCharts.cluster_yoy_variation(variation_df, comp_yr),
                    use_container_width=True)
    st.markdown("<div class='section-sub'>📊 CAPEX vs OPEX par Cluster</div>",
                unsafe_allow_html=True)
    st.plotly_chart(ClusterCharts.capex_opex_per_cluster(filtered_df),
                    use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════
    # B — FOCUS CLUSTER
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🔍 Focus Cluster</div>", unsafe_allow_html=True)

    clusters = sorted(filtered_df["PSCS Cluster"].dropna().unique().tolist()) \
               if "PSCS Cluster" in filtered_df.columns else []
    default_cluster = "Packaging" if "Packaging" in clusters else (clusters[0] if clusters else None)
    default_idx     = clusters.index(default_cluster) if default_cluster in clusters else 0

    col_pick, _ = st.columns([2, 5])
    with col_pick:
        chosen_cluster = st.selectbox("🏷️ Choisir un Cluster", clusters,
                                      index=default_idx, key="cluster_focus_pick")

    if chosen_cluster:
        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown(f"<div class='section-sub'>📊 Spend par Catégorie — {chosen_cluster}</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(ClusterCharts.spend_per_category(filtered_df, chosen_cluster),
                            use_container_width=True)
        with col_d:
            st.markdown(f"<div class='section-sub'>📅 Variation Mensuelle — {chosen_cluster} — {base_yr} vs {comp_yr}</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(ClusterCharts.cluster_monthly_variation(
                                variation_df, chosen_cluster, comp_yr),
                            use_container_width=True)

        st.write("")

        st.markdown(f"<div class='section-sub'>📉 Variation par Catégorie — {chosen_cluster} — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.category_yoy_variation(variation_df, chosen_cluster, comp_yr),
                        use_container_width=True)

        st.write("")

        st.markdown(f"<div class='section-sub-orange'>💰 CAPEX vs OPEX par Catégorie — {chosen_cluster}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.stacked_capex_opex_category(filtered_df, chosen_cluster),
                        use_container_width=True)

        st.write("")

        st.markdown(f"<div class='section-sub-orange'>📊 Variation CAPEX & OPEX — {chosen_cluster} — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        col_cx, col_ox = st.columns(2)
        with col_cx:
            st.plotly_chart(ClusterCharts.capex_variation(
                                variation_df, comp_yr, cluster=chosen_cluster),
                            use_container_width=True)
        with col_ox:
            st.plotly_chart(ClusterCharts.opex_variation(
                                variation_df, comp_yr, cluster=chosen_cluster),
                            use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════
    # C — FOCUS CATEGORY
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner' style='background:linear-gradient(90deg,#1B6CA8 0%,#2ECC71 100%);'>📦 Focus Catégorie</div>",
                unsafe_allow_html=True)

    if chosen_cluster and "PSCS Category" in filtered_df.columns:
        cat_df     = filtered_df[filtered_df["PSCS Cluster"] == chosen_cluster]
        categories = sorted(cat_df["PSCS Category"].dropna().unique().tolist())
    else:
        cat_df     = filtered_df
        categories = sorted(filtered_df["PSCS Category"].dropna().unique().tolist()) \
                     if "PSCS Category" in filtered_df.columns else []

    chosen_category = None
    if categories:
        col_pick2, _ = st.columns([2, 5])
        with col_pick2:
            chosen_category = st.selectbox("📦 Choisir une Catégorie", categories,
                                           index=0, key="category_focus_pick")

        if chosen_category:
            col_e, col_f = st.columns(2)
            with col_e:
                st.markdown(f"<div class='section-sub'>📊 Spend par PSCS Name — {chosen_category}</div>",
                            unsafe_allow_html=True)
                st.plotly_chart(ClusterCharts.spend_per_pscs_name(
                                    filtered_df, chosen_cluster, chosen_category),
                                use_container_width=True)
            with col_f:
                st.markdown(f"<div class='section-sub'>📅 Variation Mensuelle — {chosen_category} — {base_yr} vs {comp_yr}</div>",
                            unsafe_allow_html=True)
                st.plotly_chart(ClusterCharts.category_monthly_variation(
                                    variation_df, chosen_category, comp_yr,
                                    cluster=chosen_cluster),
                                use_container_width=True)

            st.write("")

            st.markdown(f"<div class='section-sub'>📉 Variation PSCS Name — {chosen_category} — {base_yr} vs {comp_yr}</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(ClusterCharts.pscs_name_yoy_variation(
                                variation_df, chosen_cluster, chosen_category, comp_yr),
                            use_container_width=True)

            st.write("")

            st.markdown(f"<div class='section-sub-orange'>💰 CAPEX vs OPEX par PSCS Name — {chosen_category}</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(ClusterCharts.stacked_capex_opex_pscs_name(
                                filtered_df, chosen_cluster, chosen_category),
                            use_container_width=True)

            st.write("")

            st.markdown(f"<div class='section-sub-orange'>📊 Variation CAPEX & OPEX — {chosen_category} — {base_yr} vs {comp_yr}</div>",
                        unsafe_allow_html=True)
            col_cx2, col_ox2 = st.columns(2)
            with col_cx2:
                st.plotly_chart(ClusterCharts.capex_variation(
                                    variation_df, comp_yr,
                                    cluster=chosen_cluster, category=chosen_category),
                                use_container_width=True)
            with col_ox2:
                st.plotly_chart(ClusterCharts.opex_variation(
                                    variation_df, comp_yr,
                                    cluster=chosen_cluster, category=chosen_category),
                                use_container_width=True)
    else:
        st.info("Aucune catégorie disponible pour ce cluster.")

    st.divider()

    # ════════════════════════════════════════════════════════════════════
    # D — FOCUS PSCS NAME
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner' style='background:linear-gradient(90deg,#5B2C8E 0%,#8E44AD 100%);'>🔬 Focus PSCS Name</div>",
                unsafe_allow_html=True)

    if chosen_cluster and chosen_category and "PSCS Name" in filtered_df.columns:
        pscs_sub   = filtered_df.copy()
        pscs_sub   = pscs_sub[pscs_sub["PSCS Cluster"]  == chosen_cluster]
        pscs_sub   = pscs_sub[pscs_sub["PSCS Category"] == chosen_category]
        pscs_names = sorted(pscs_sub["PSCS Name"].dropna().unique().tolist())
    else:
        pscs_names = []

    chosen_pscs = None
    if pscs_names:
        col_pick3, _ = st.columns([2, 5])
        with col_pick3:
            chosen_pscs = st.selectbox("🔬 Choisir un PSCS Name", pscs_names,
                                       index=0, key="pscs_name_focus_pick")

        if chosen_pscs:
            sub_pscs = filtered_df[filtered_df["PSCS Name"] == chosen_pscs] \
                       if "PSCS Name" in filtered_df.columns else filtered_df
            by_yr = sub_pscs.groupby("Année")["Total  spend"].sum().reset_index()

            col_g, col_h = st.columns(2)
            with col_g:
                if not by_yr.empty:
                    from visualizations import C_PURPLE as _CP, LAYOUT as _L, LIGHT_GREY as _LG, _fmt as _f
                    import plotly.graph_objects as _go
                    _fig = _go.Figure(_go.Bar(
                        x=by_yr["Année"].astype(str), y=by_yr["Total  spend"],
                        marker_color=_CP,
                        text=[_f(v) for v in by_yr["Total  spend"]],
                        textposition="outside", textfont=dict(size=10, color="#111111"),
                    ))
                    _fig.update_layout(**_L,
                        title=dict(text=f"Spend par Année — {chosen_pscs} (kCHF)",
                                   font=dict(size=14,color="#111111"),x=0),
                        xaxis=dict(tickfont=dict(size=11,color="#111111")),
                        yaxis=dict(title="kCHF",gridcolor=_LG,
                                   tickfont=dict(size=11,color="#111111")),
                        height=400)
                    st.markdown(f"<div class='section-sub-purple'>📊 Spend par Année — {chosen_pscs}</div>",
                                unsafe_allow_html=True)
                    st.plotly_chart(_fig, use_container_width=True)

            with col_h:
                st.markdown(f"<div class='section-sub-purple'>📅 Variation Mensuelle — {chosen_pscs} — {base_yr} vs {comp_yr}</div>",
                            unsafe_allow_html=True)
                st.plotly_chart(ClusterCharts.pscs_name_monthly_variation(
                                    variation_df, chosen_pscs, comp_yr),
                                use_container_width=True)

            st.write("")

            st.markdown(f"<div class='section-sub-orange'>📊 Variation CAPEX & OPEX — {chosen_pscs} — {base_yr} vs {comp_yr}</div>",
                        unsafe_allow_html=True)
            col_cx3, col_ox3 = st.columns(2)
            with col_cx3:
                st.plotly_chart(ClusterCharts.capex_variation(
                                    variation_df, comp_yr,
                                    cluster=chosen_cluster, category=chosen_category,
                                    pscs_name=chosen_pscs),
                                use_container_width=True)
            with col_ox3:
                st.plotly_chart(ClusterCharts.opex_variation(
                                    variation_df, comp_yr,
                                    cluster=chosen_cluster, category=chosen_category,
                                    pscs_name=chosen_pscs),
                                use_container_width=True)
    else:
        st.info("Sélectionnez un cluster et une catégorie pour explorer le niveau PSCS Name.")

    st.divider()

    # ════════════════════════════════════════════════════════════════════
    # E — TOP 10 (follow all active filters)
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🏆 Top 10 — filtré par sélections actives</div>",
                unsafe_allow_html=True)

    top_df = filtered_df.copy()
    if chosen_cluster  and "PSCS Cluster"  in top_df.columns:
        top_df = top_df[top_df["PSCS Cluster"]  == chosen_cluster]
    if chosen_category and "PSCS Category" in top_df.columns:
        top_df = top_df[top_df["PSCS Category"] == chosen_category]
    if chosen_pscs     and "PSCS Name"     in top_df.columns:
        top_df = top_df[top_df["PSCS Name"]     == chosen_pscs]

    parts = []
    if chosen_cluster:  parts.append(f"Cluster={chosen_cluster}")
    if chosen_category: parts.append(f"Catégorie={chosen_category}")
    if chosen_pscs:     parts.append(f"PSCS={chosen_pscs}")
    st.caption(f"Périmètre actif : **{' | '.join(parts) if parts else 'Toutes données'}**")

    col_g2, col_h2 = st.columns(2)
    with col_g2:
        st.markdown("<div class='section-sub'>🏢 Top 10 Fournisseurs</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ParetoCharts.vendor_pareto(top_df, hard_cap=10),
                        use_container_width=True)
    with col_h2:
        st.markdown("<div class='section-sub'>👥 Top 10 Requesters</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ParetoCharts.requester_pareto(top_df, hard_cap=10),
                        use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════════
    # F — PARETO & GLOBAL CAPEX/OPEX
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section-banner'>🎯 Pareto Global & CAPEX/OPEX</div>",
                unsafe_allow_html=True)

    col_e2, col_f2 = st.columns(2)
    with col_e2:
        st.markdown("<div class='section-sub'>📦 Pareto Catégories → 80% du Spend</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.category_pareto_by_cluster(filtered_df),
                        use_container_width=True)
    with col_f2:
        st.markdown("<div class='section-sub'>🗺️ Pareto Clusters → 80% du Spend</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.cluster_pareto(filtered_df), use_container_width=True)

    st.write("")
    col_i, col_j = st.columns(2)

    with col_i:
        st.markdown("<div class='section-sub'>📊 Top 10 CAPEX vs OPEX par Catégorie</div>",
                    unsafe_allow_html=True)
        top_10_cats = filtered_df.groupby("PSCS Category")["Total  spend"].sum().nlargest(10).index
        st.plotly_chart(ClusterCharts.capex_opex_per_category(
                            filtered_df[filtered_df["PSCS Category"].isin(top_10_cats)]),
                        use_container_width=True)

    with col_j:
        st.markdown("<div class='section-sub'>📊 CAPEX vs OPEX par Cluster</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(ClusterCharts.capex_opex_per_cluster(filtered_df),
                        use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB – CAPEX / OPEX
# ══════════════════════════════════════════════════════════════════════════════
def _tab_capex_opex(filtered_df, variation_df):
    """
    filtered_df  : date + dimension filters applied  → used for non-variation charts
    variation_df : only dimension filters applied    → used for all variation/waterfall charts
    """
    st.markdown("<div class='section-banner'>📊 Vue Globale — Répartition du Spend</div>",
                unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='section-sub'>💰 Spend CAPEX vs OPEX</div>", unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.capex_opex_total_bar(filtered_df), use_container_width=True)
    with col_b:
        st.markdown("<div class='section-sub'>📑 Spend FI vs MM</div>", unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.fi_mm_total_bar(filtered_df), use_container_width=True)

    st.write("")
    st.markdown("<div class='section-sub'>📅 Spend par Année — CAPEX/OPEX Stacked</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexTabCharts.stacked_spend_per_year(filtered_df), use_container_width=True)

    st.write("")
    st.markdown("<div class='section-sub'>🗓️ Spend Mensuel — comparaison par Année</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexTabCharts.monthly_spend_by_year(filtered_df), use_container_width=True)

    st.divider()
    st.markdown("<div class='section-banner'>📉 Analyses de Variation (Y-1 vs Y)</div>",
                unsafe_allow_html=True)
    comp_yr = _comp_year_picker(variation_df, key="yr_capex_opex_tab")
    base_yr = comp_yr - 1

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown(f"<div class='section-sub'>💰 Variation CAPEX/OPEX — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.capex_opex_variation_bar(variation_df, comp_yr),
                        use_container_width=True)
    with col_d:
        st.markdown(f"<div class='section-sub'>📅 Variation Total Spend Mensuelle — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.total_monthly_variation(variation_df, comp_yr),
                        use_container_width=True)

    st.write("")
    st.markdown("<div class='section-sub'>📈 Évolution du Spend sur toute la période</div>",
                unsafe_allow_html=True)
    st.plotly_chart(CapexOpexTabCharts.spend_evolution_line(filtered_df), use_container_width=True)

    st.write("")
    col_e, col_f = st.columns(2)
    with col_e:
        st.markdown(f"<div class='section-sub'>🏗️ Variation CAPEX Mensuelle — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.capex_monthly_var(variation_df, comp_yr),
                        use_container_width=True)
    with col_f:
        st.markdown(f"<div class='section-sub'>📋 Variation OPEX Mensuelle — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.opex_monthly_var(variation_df, comp_yr),
                        use_container_width=True)

    st.write("")
    col_g, col_h = st.columns(2)
    with col_g:
        st.markdown(f"<div class='section-sub'>📦 Variation MM Mensuelle — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.mm_monthly_var(variation_df, comp_yr),
                        use_container_width=True)
    with col_h:
        st.markdown(f"<div class='section-sub'>📑 Variation FI Mensuelle — {base_yr} vs {comp_yr}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(CapexOpexTabCharts.fi_monthly_var(variation_df, comp_yr),
                        use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        try:
            st.image(resource_path("holcim_logo_color.svg"), width=140)
        except Exception:
            st.markdown("<h3>🏗️ Lafarge</h3>", unsafe_allow_html=True)
    with col_title:
        st.markdown(
            '<h2 style="color:#1B3A5C;font-family:Segoe UI,Arial,sans-serif;'
            'font-weight:800;margin-bottom:0;">Spend Analytics Dashboard</h2>'
            '<p style="color:#E74C3C;font-family:Segoe UI,Arial,sans-serif;'
            'font-weight:600;margin-top:2px;">Holcim Lafarge – Procurement Intelligence</p>',
            unsafe_allow_html=True)

    if not st.session_state.data_loaded:
        uploaded = st.file_uploader('Choisissez votre fichier Excel', type=['xlsx','xls'])
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

    # Self-heal session state if it contains duplicated columns from prior runs
    if st.session_state.df.columns.duplicated().any():
        st.session_state.df = st.session_state.df.loc[:, ~st.session_state.df.columns.duplicated()]

    filters     = _sidebar_filters(st.session_state.df)

    # ── filtered_df : full sidebar filters (date + dimensions) ───────────────
    # Used for KPIs, snapshot charts, pareto, treemaps, stacked bars, etc.
    filtered_df = processor.apply_filters(st.session_state.df, filters)

    # ── variation_df : dimension filters ONLY (date filters stripped) ─────────
    # Used exclusively for Y-1 vs Y variation / waterfall charts.
    # This ensures both years are always present regardless of what the user
    # selected in the sidebar date section (year, month, YTD, MTD, date range).
    variation_filters = _strip_date_filters(filters)
    variation_df      = processor.apply_filters(st.session_state.df, variation_filters)

    if len(filtered_df) == 0:
        st.warning("Aucune donnée après filtrage")
        return

    comp_stats = processor.get_comparative_stats(st.session_state.df, filters)
    _kpis(comp_stats, filters.get('year'))
    st.divider()

    tab_ov, tab_cl, tab_co = st.tabs(['🗺️ Overview', '🏷️ Clusters', '💰 CAPEX/OPEX'])
    with tab_ov: _tab_overview(filtered_df, variation_df)
    with tab_cl: _tab_cluster(filtered_df, variation_df)
    with tab_co: _tab_capex_opex(filtered_df, variation_df)


if __name__ == '__main__':
    main()