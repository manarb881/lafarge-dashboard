"""
Page Détection d'Anomalies
4 modules indépendants, tous basés sur des méthodes statistiques robustes :
  1. Commandes outliers     — IQR + Z-score par vendor/catégorie
  2. Ruptures temporelles   — variation mois/mois hors intervalle de confiance
  3. Requesters suspects    — Z-score sur montant total et volume de commandes
  4. Doublons suspects      — même vendor + montant proche + dates proches
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os
from typing import Optional

# Import des styles depuis visualization (si disponible)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from visualizations import C, LAYOUT_BASE, LAYOUT_NO_AXES
except ImportError:
    # Fallback si visualizations n'est pas trouvé
    C = {'red': '#DC2626', 'blue': '#2563EB', 'pareto': '#F59E0B', 'grey': '#94A3B8', 'green': '#16A34A'}
    LAYOUT_BASE = {}
    LAYOUT_NO_AXES = {}

st.set_page_config(page_title="Détection d'Anomalies", page_icon="🚨", layout="wide")

# ─── Styles CSS ───
st.markdown("""
<style>
.section-banner { background: linear-gradient(90deg, #7C1D1D 0%, #DC2626 100%); color: white; padding: 8px 16px; border-radius: 6px; font-weight: 700; margin-bottom: 8px; }
.banner-warn { background: linear-gradient(90deg, #78350F 0%, #D97706 100%); color: white; padding: 8px 16px; border-radius: 6px; font-weight: 700; margin-bottom: 8px; }
.banner-ok { background: linear-gradient(90deg, #14532D 0%, #16A34A 100%); color: white; padding: 8px 16px; border-radius: 6px; font-weight: 700; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

def _banner(txt, style="red"):
    cls = {"red": "section-banner", "warn": "banner-warn", "ok": "banner-ok"}.get(style, "section-banner")
    st.markdown(f'<div class="{cls}">{txt}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 1 — COMMANDES OUTLIERS
# ══════════════════════════════════════════════════════════════════════════════

def _detect_outliers(df: pd.DataFrame) -> pd.DataFrame:
    if 'Total  spend' not in df.columns: return pd.DataFrame()

    # Calcul Z-score par groupe
    for group_col in ['Vendor Name', 'PSCS Category']:
        if group_col not in df.columns: continue
        try:
            grp = df.groupby(group_col)['Total  spend']
            df[f'mean_{group_col}'] = grp.transform('mean')
            df[f'std_{group_col}']  = grp.transform('std').fillna(0)
            df[f'z_{group_col}'] = np.where(
                df[f'std_{group_col}'] > 0.01,
                (df['Total  spend'] - df[f'mean_{group_col}']) / df[f'std_{group_col}'], 0
            )
        except: continue

    z_cols = [c for c in ['z_Vendor Name', 'z_PSCS Category'] if c in df.columns]
    if not z_cols: return pd.DataFrame()

    df['z_max'] = df[z_cols].abs().max(axis=1)
    df['Anomalie_Score'] = df['z_max'].apply(lambda z: "🔴 Critique" if z > 4 else ("🟡 Suspecte" if z > 2.5 else "🟢 Normale"))

    def _explain(row):
        parts = []
        if 'z_Vendor Name' in row and abs(row['z_Vendor Name']) > 2.5:
            parts.append(f"Z-score vendor = {row['z_Vendor Name']:+.2f}")
        if 'z_PSCS Category' in row and abs(row['z_PSCS Category']) > 2.5:
            parts.append(f"Z-score cat. = {row['z_PSCS Category']:+.2f}")
        return " | ".join(parts) if parts else "RAS"

    df['Explication'] = df.apply(_explain, axis=1)
    
    keep = [c for c in ['PO', 'Invoice Posting Date', 'Vendor Name', 'Total  spend', 'Anomalie_Score', 'z_max', 'Explication'] if c in df.columns]
    return df[keep][df['Anomalie_Score'] != '🟢 Normale'].sort_values('z_max', ascending=False)

def _tab_outliers(df: pd.DataFrame):
    _banner("🔍 Commandes anormalement chères (Z-score > 2.5)", "red")
    out = _detect_outliers(df.copy())
    if out.empty:
        _banner("✅ Aucune anomalie détectée", "ok")
        return

    n_crit = (out['Anomalie_Score'] == '🔴 Critique').sum()
    n_susp = (out['Anomalie_Score'] == '🟡 Suspecte').sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 Critiques", f"{n_crit}")
    c2.metric("🟡 Suspectes", f"{n_susp}")
    c3.metric("💶 Montant concerné", f"{out['Total  spend'].sum():,.0f} €")

    # Scatter Plot
    fig = px.scatter(out, x="Total  spend", y="z_max", color="Anomalie_Score",
                     hover_data=['PO', 'Vendor Name'],
                     color_discrete_map={"🔴 Critique": C['red'], "🟡 Suspecte": C['pareto']})
    fig.add_hline(y=2.5, line_dash="dash", line_color="grey")
    fig.update_layout(height=400, title="Z-Score vs Montant", **LAYOUT_BASE)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(out, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 2 — RUPTURES TEMPORELLES
# ══════════════════════════════════════════════════════════════════════════════

def _tab_temporal(df: pd.DataFrame):
    _banner("📅 Ruptures temporelles (Variation hors ±2σ)", "red")
    if 'Année_Mois' not in df.columns:
        st.warning("Données temporelles insuffisantes.")
        return

    monthly = df.groupby('Année_Mois')['Total  spend'].sum().reset_index().sort_values('Année_Mois')
    if len(monthly) < 3: return

    monthly['roll_mean'] = monthly['Total  spend'].diff().rolling(3, min_periods=2).mean()
    monthly['roll_std'] = monthly['Total  spend'].diff().rolling(3, min_periods=2).std().fillna(0)
    monthly['diff'] = monthly['Total  spend'].diff()
    
    # Détection
    def _score(r):
        if pd.isna(r['diff']): return '🟢'
        z_score = abs((r['diff'] - r['roll_mean']) / r['roll_std']) if r['roll_std'] > 0 else 0
        return '🔴' if z_score > 3 else ('🟡' if z_score > 2 else '🟢')

    monthly['Score'] = monthly.apply(_score, axis=1)
    
    anomalies = monthly[monthly['Score'] != '🟢']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly['Année_Mois'], y=monthly['Total  spend'], name='Spend', line=dict(color=C['blue'])))
    if not anomalies.empty:
        fig.add_trace(go.Scatter(x=anomalies['Année_Mois'], y=anomalies['Total  spend'], mode='markers', 
                                 marker=dict(color=C['red'], size=10), name='Anomalie'))
    
    fig.update_layout(height=400, title="Évolution Mensuelle", **LAYOUT_BASE)
    st.plotly_chart(fig, use_container_width=True)
    
    if not anomalies.empty:
        st.dataframe(anomalies, use_container_width=True)
    else:
        _banner("✅ Aucune rupture détectée", "ok")

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 3 & 4 (Requesters & Doublons - Versions simplifiées)
# ══════════════════════════════════════════════════════════════════════════════

def _tab_requesters(df: pd.DataFrame):
    _banner("👥 Requesters Suspects (Volume ou Montant atypique)", "red")
    if 'Requester' not in df.columns: return
    
    req = df.groupby('Requester').agg(Total=('Total  spend', 'sum'), Nb=('Total  spend', 'count')).reset_index()
    req['z_total'] = (req['Total'] - req['Total'].mean()) / req['Total'].std()
    
    suspects = req[req['z_total'].abs() > 3].sort_values('z_total', ascending=False)
    
    if not suspects.empty:
        st.metric("👥 Requesters signalés", len(suspects))
        fig = px.scatter(req, x="Nb", y="Total", color=req['Requester'].isin(suspects['Requester']),
                         color_discrete_map={True: C['red'], False: C['grey']}, log_x=True, log_y=True)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(suspects, use_container_width=True)
    else:
        _banner("✅ Aucun requester suspect", "ok")

def _tab_duplicates(df: pd.DataFrame):
    _banner("📋 Doublons Potentiels (Même Vendor, Montant et Date proches)", "red")
    # Pour la performance, on ne garde que les colonnes utiles
    sub = df[['Vendor Name', 'Total  spend', 'Invoice Posting Date', 'PO']].copy()
    sub = sub[sub['Total  spend'] > 0]
    
    # On cherche les doublons exacts sur (Vendor, Spend, Date)
    dups = sub[sub.duplicated(subset=['Vendor Name', 'Total  spend', 'Invoice Posting Date'], keep=False)]
    
    if not dups.empty:
        st.warning(f"⚠️ {len(dups)} lignes semblent être des doublons exacts (Même Vendor, Date et Montant).")
        st.dataframe(dups.sort_values(['Vendor Name', 'Total  spend']), use_container_width=True)
    else:
        _banner("✅ Aucun doublon strict détecté", "ok")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if 'df' not in st.session_state or st.session_state.df is None:
        st.error("❌ Données non chargées.")
        return

    # 🛑 NETTOYAGE LOCAL (Spécifique à cette page, sans toucher au data_processor)
    # On travaille sur une copie pour ne pas casser les autres pages
    df = st.session_state.df.copy()

    # 1. Nettoyage du NOM de la colonne (Gérer le double espace "Total  spend")
    # On renomme tout ce qui ressemble à "total spend" vers "Total  spend" pour standardiser
    cols_map = {c: 'Total  spend' for c in df.columns if c.lower().replace(' ', '') == 'totalspend'}
    df = df.rename(columns=cols_map)

    # 2. Vérification existence colonne Spend
    if 'Total  spend' not in df.columns:
        st.error(f"Erreur : Colonne 'Total  spend' introuvable. Colonnes dispos : {list(df.columns)}")
        st.stop()

    # 3. Conversion Montants (ex: "3 256,67" -> 3256.67)
    if df['Total  spend'].dtype == 'object':
        try:
            df['Total  spend'] = (df['Total  spend'].astype(str)
                                  .str.replace(r'\s+', '', regex=True) # Enlever espaces
                                  .str.replace(',', '.')               # Virgule -> Point
                                  )
            df['Total  spend'] = pd.to_numeric(df['Total  spend'], errors='coerce').fillna(0)
        except Exception as e:
            st.error(f"Erreur conversion montant : {e}")

    # 4. Conversion Dates (ex: 20240226 -> Datetime)
    if 'Invoice Posting Date' in df.columns:
        # Si c'est un nombre (20240226) ou texte
        if df['Invoice Posting Date'].dtype != 'datetime64[ns]':
            df['Invoice Posting Date'] = pd.to_datetime(
                df['Invoice Posting Date'].astype(str), 
                format='%Y%m%d', 
                errors='coerce'
            )
        # Création de Année_Mois locale
        df['Année_Mois'] = df['Invoice Posting Date'].dt.strftime('%Y-%m')

    # ─────────────────────────────────────────────────────────────

    # Header
    c1, c2 = st.columns([6, 1])
    c1.title("🚨 Détection d'Anomalies")
    if c2.button("← Retour"): st.switch_page("main.py")

    tab0,tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Synthèse","🔍 Commandes Outliers", "📅 Ruptures", "👥 Requesters", "📋 Doublons"
    ])
    with tab0: _tab_synthese(df)
    with tab1: _tab_outliers(df)
    with tab2: _tab_temporal(df)
    with tab3: _tab_requesters(df)
    with tab4: _tab_duplicates(df)
def _tab_synthese(df: pd.DataFrame):
    _banner("🎯 Synthèse Globale des Risques", "red")
    
    # --- Calculs silencieux pour la synthèse ---
    
    # 1. Outliers
    outliers = _detect_outliers(df)
    n_out = len(outliers)
    m_out = outliers['Total  spend'].sum() if not outliers.empty else 0
    
    # 2. Requesters (Logique simplifiée reprise du module)
    req = df.groupby('Requester')['Total  spend'].sum().reset_index()
    if len(req) > 2:
        req['z'] = (req['Total  spend'] - req['Total  spend'].mean()) / req['Total  spend'].std()
        susp_req = req[req['z'].abs() > 3]
        n_req = len(susp_req)
        m_req = susp_req['Total  spend'].sum()
    else:
        n_req, m_req = 0, 0

    # 3. Duplicates
    sub = df[['Vendor Name', 'Total  spend', 'Invoice Posting Date']].copy()
    sub = sub[sub['Total  spend'] > 0]
    dups = sub[sub.duplicated(subset=['Vendor Name', 'Total  spend', 'Invoice Posting Date'], keep=False)]
    n_dup = len(dups)
    m_dup = dups['Total  spend'].sum()

    # 4. Temporal (On compte les mois en alerte rouge)
    monthly = df.groupby('Année_Mois')['Total  spend'].sum().reset_index()
    n_temp = 0
    if len(monthly) >= 3:
        monthly['roll_std'] = monthly['Total  spend'].diff().rolling(3).std().fillna(0)
        monthly['z'] = (monthly['Total  spend'].diff() - monthly['Total  spend'].diff().rolling(3).mean()) / monthly['roll_std']
        n_temp = len(monthly[monthly['z'].abs() > 3])
    
    # --- Affichage des KPIs ---
    
    # Total à risque (On ne compte pas le temporel car c'est une tendance, pas des factures précises)
    total_risk_amount = m_out + m_dup
    total_alerts = n_out + n_req + n_dup + n_temp
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 Total Alertes", f"{total_alerts}", help="Somme des anomalies détectées sur tous les modules")
    c2.metric("💶 Montant 'À Risque'", f"{total_risk_amount:,.0f} €", help="Cumul Outliers + Doublons")
    
    # Jauge de risque visuelle
    risk_level = "FAIBLE"
    risk_color = "green"
    if total_alerts > 5: risk_level, risk_color = "MODÉRÉ", "orange"
    if total_alerts > 20: risk_level, risk_color = "CRITIQUE", "red"
    
    c3.markdown(f"""
    <div style="background-color:#F8FAFC; border-left: 5px solid {risk_color}; padding: 10px; border-radius: 5px;">
        <h4 style="margin:0; color:black;">Niveau de Risque</h4>
        <h2 style="margin:0; color:{risk_color};">{risk_level}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Tableau récapitulatif
    summary_data = {
        "Type d'Anomalie": ["🔍 Commandes Outliers", "👥 Requesters Suspects", "📋 Doublons Stricts", "📅 Ruptures Mensuelles"],
        "Nombre de Cas": [n_out, n_req, n_dup, n_temp],
        "Impact Financier (€)": [m_out, m_req, m_dup, 0], # 0 pour temporel car difficile à chiffrer
        "Priorité": ["🔴 Haute" if x > 0 else "🟢 Basse" for x in [n_out, n_req, n_dup, n_temp]]
    }
    df_sum = pd.DataFrame(summary_data)
    
    # Affichage propre
    st.dataframe(
        df_sum, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Impact Financier (€)": st.column_config.NumberColumn(format="%.0f €"),
        }
    )
    
    if total_alerts == 0:
        st.success("✅ Aucune anomalie majeure détectée dans les données actuelles.")

if __name__ == "__main__":
    main()