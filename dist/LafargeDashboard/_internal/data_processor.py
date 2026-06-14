"""
Module de traitement et nettoyage des données - VERSION LAFARGE3

═══════════════════════════════════════════════════════════════════
AUDIT NOTES
═══════════════════════════════════════════════════════════════════

1. YTD / MTD logic (apply_filters)
   ─────────────────────────────────
   Year filter is ALWAYS applied first (exact year), then the
   temporal scope (YTD / MTD / plain month) is applied on top.

   YTD (Year-to-Date):
     • months selected   → keep rows where Month_num ≤ max(selected months)
       e.g. year=2026, month=February, YTD → Jan 2026 + Feb 2026
     • no months         → keep entire selected year (no further filter)

   MTD (Month-to-Date):
     • months selected   → keep ONLY the exact selected month(s)
       e.g. year=2026, month=February, MTD → Feb 2026 only
     • no months         → keep only the current calendar month

2. CAPEX / OPEX filter (apply_filters Step 5)
   ─────────────────────────────────────────
   Row-level filter: keeps rows where the relevant spend column > 0.
   • "CAPEX only"  → fdf[fdf['CAPEX Spend'] > 0]
   • "OPEX only"   → fdf[fdf['OPEX Spend']  > 0]   (OPEX = FI + MM)
   • "All"         → no filter
   Each row represents one invoice line; a line is either CAPEX or
   OPEX-typed in practice. Filtering by >0 isolates the correct subset.
   Total  spend for filtered rows still equals CAPEX + OPEX for that
   row (not re-zeroed), which is correct because it represents the
   true cost of that transaction.

3. KPI delta logic (get_comparative_stats)
   ─────────────────────────────────────
   Delta = current period − SAME period one year back.
   "Same period" means: identical YTD/MTD flags AND identical month
   selection, but year shifted by −1.
   Examples:
     year=2026, Feb, YTD  → current=Jan+Feb 2026, prev=Jan+Feb 2025
     year=2026, Feb, MTD  → current=Feb 2026,     prev=Feb 2025
     year=2026, no month  → current=all 2026,      prev=all 2025
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any

MONTHS_ORDER = ['January','February','March','April','May','June',
                'July','August','September','October','November','December']
import sys, os

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class SpendDataProcessor:

    NUMERIC_COLUMNS = ['CAPEX Spend', 'FI Spend', 'MM Spend', 'Total  spend', 'Order quantity']
    DATE_COLUMNS    = ['Invoice Posting Date', 'Document date', 'Vendor Inv. Date']

    def __init__(self):
        self.original_df  = None
        self.processed_df = None

    # ─── Load & Process ───────────────────────────────────────────────────────
    def load_and_process(self, uploaded_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            df = pd.read_excel(uploaded_file, engine='calamine')
            self.original_df = df.copy()
            df = self._remove_empty_rows(df)
            df = self._remove_duplicates(df)
            df = self._clean_text_columns(df)
            df = self._convert_numeric_columns(df)
            df = self._convert_date_columns(df)
            df = self._fill_missing_values(df)
            df = self._create_derived_columns(df)
            self.processed_df = df
            return df, None
        except Exception as e:
            return None, f"Erreur lors du chargement du fichier : {str(e)}"

    # ─── Cleaning helpers ─────────────────────────────────────────────────────
    def _remove_empty_rows(self, df): return df.dropna(how='all')
    def _remove_duplicates(self, df): return df

    def _clean_text_columns(self, df):
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip().replace('nan', np.nan)
        return df

    def _convert_numeric_columns(self, df):
        for col in self.NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df

    def _convert_date_columns(self, df):
        for col in self.DATE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
        return df

    def _fill_missing_values(self, df):
        defaults = {
            'Vendor Name':          'Non spécifié',
            'Requester':            'Non spécifié',
            'PSCS Cluster':         'Non classifié',
            'PSCS Category':        'Non classifié',
            'PSCS Name':            'Non classifié',
            'Purchasing Group Name':'Non spécifié',
            'Company Code descr':   'Non spécifié',
            'WBS Element ID':       'Hors Projet',
            'Cost Center ID':       'Non spécifié',
            'GL Account Name':      'Non spécifié',
        }
        for target, default in defaults.items():
            actual = self._find_column(df, target)
            if actual:
                df[actual] = df[actual].astype(str).fillna(default).replace('nan', default)
        return df

    def _find_column(self, df, target):
        if target in df.columns:
            return target
        def _norm(s):
            return s.lower().replace(" ","").replace(".","").strip()
        tn = _norm(target)
        for col in df.columns:
            if _norm(col) == tn:
                return col
        return None

    def _create_derived_columns(self, df):
        # Normalize GL Account column name
        for variant in ['GL. Account Name ', 'GL. Account Name',
                        'GL Account Name ', 'GL. Account ID']:
            actual = self._find_column(df, variant)
            if actual and actual != 'GL Account Name':
                if 'GL Account Name' not in df.columns:
                    df = df.rename(columns={actual: 'GL Account Name'})
                else:
                    df['GL Account Name'] = df['GL Account Name'].fillna(df[actual])
                    df = df.drop(columns=[actual])

        date_col = self._find_column(df, 'Invoice Posting Date')
        if date_col:
            df['Date']       = pd.to_datetime(df[date_col], errors='coerce')
            df['Année']      = df['Date'].dt.year
            df['Month_num']  = df['Date'].dt.month
            df['Nom_Mois']   = df['Date'].dt.strftime('%B')
            df['Année_Mois'] = df['Date'].dt.to_period('M').astype(str)

        # Convert raw amounts to kCHF
        for col in ['CAPEX Spend', 'FI Spend', 'MM Spend', 'Total  spend']:
            actual = self._find_column(df, col)
            if actual:
                df[col] = pd.to_numeric(df[actual], errors='coerce').fillna(0) / 1000

        # OPEX = FI + MM  (derived after kCHF conversion)
        df['OPEX Spend']   = df.get('FI Spend', 0) + df.get('MM Spend', 0)
        # Recalculate Total to ensure consistency: Total = CAPEX + OPEX
        df['Total  spend'] = df.get('CAPEX Spend', 0) + df['OPEX Spend']
        return df

    # ─── Stats ────────────────────────────────────────────────────────────────
    def get_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        total_spend = float(df['Total  spend'].sum()) if 'Total  spend' in df.columns else 0.0
        total_capex = float(df['CAPEX Spend'].sum())  if 'CAPEX Spend'  in df.columns else 0.0
        total_opex  = float(df['OPEX Spend'].sum())   if 'OPEX Spend'   in df.columns else 0.0
        return {
            'total_rows':        len(df),
            'total_spend':       total_spend,
            'total_capex':       total_capex,
            'total_fi':          float(df['FI Spend'].sum()) if 'FI Spend' in df.columns else 0.0,
            'total_mm':          float(df['MM Spend'].sum()) if 'MM Spend' in df.columns else 0.0,
            'total_opex':        total_opex,
            # CAPEX % and OPEX % of Total Spend
            'capex_pct':         (total_capex / total_spend * 100) if total_spend > 0 else 0.0,
            'opex_pct':          (total_opex  / total_spend * 100) if total_spend > 0 else 0.0,
            'unique_vendors':    df['Vendor Name'].nunique()   if 'Vendor Name'   in df.columns else 0,
            'unique_requesters': df['Requester'].nunique()     if 'Requester'     in df.columns else 0,
            'unique_categories': df['PSCS Category'].nunique() if 'PSCS Category' in df.columns else 0,
            'unique_clusters':   df['PSCS Cluster'].nunique()  if 'PSCS Cluster'  in df.columns else 0,
            'date_min':          df['Date'].min() if 'Date' in df.columns else None,
            'date_max':          df['Date'].max() if 'Date' in df.columns else None,
        }

    # ─── Filters ──────────────────────────────────────────────────────────────
    def apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        fdf    = df.copy()
        year   = filters.get('year')
        months = filters.get('months', [])
        ytd    = filters.get('year_to_date',  False)
        mtd    = filters.get('month_to_date', False)

        # ── Step 1: ALWAYS restrict to the selected year first ────────────────
        # This is a hard filter: all subsequent steps operate within this year.
        if year and 'Année' in fdf.columns:
            fdf = fdf[fdf['Année'] == year]

        # ── Step 2: temporal scope (YTD / MTD / plain month) ─────────────────
        if ytd:
            # Year-to-Date: accumulate from Jan to the selected month.
            # If no month is selected → keep the entire year (no further filter).
            if months and 'Month_num' in fdf.columns:
                # Convert month names → numbers, take the maximum selected month
                max_month = max(
                    (MONTHS_ORDER.index(m) + 1 for m in months if m in MONTHS_ORDER),
                    default=12,
                )
                fdf = fdf[fdf['Month_num'] <= max_month]
            # else: no month selected → whole year, nothing more to do

        elif mtd:
            # Month-to-Date: keep only the exact selected month(s).
            # If no month is selected → fallback to current calendar month.
            if months and 'Nom_Mois' in fdf.columns:
                fdf = fdf[fdf['Nom_Mois'].isin(months)]
            elif 'Date' in fdf.columns:
                current_month = pd.Timestamp.now().month
                fdf = fdf[fdf['Date'].dt.month == current_month]

        else:
            # No toggle: plain month filter (or whole year if no month chosen)
            if months and 'Nom_Mois' in fdf.columns:
                fdf = fdf[fdf['Nom_Mois'].isin(months)]

        # ── Step 3: custom date range (only when NO year filter) ──────────────
        date_range = filters.get('date_range', ())
        if len(date_range) == 2 and not year:
            if 'Date' in fdf.columns:
                start, end = date_range
                fdf = fdf[
                    (fdf['Date'] >= pd.Timestamp(start)) &
                    (fdf['Date'] <= pd.Timestamp(end))
                ]

        # ── Step 4: dimension filters ─────────────────────────────────────────
        dim_mappings = {
            'company_code':     'Company Code descr',
            'vendor':           'Vendor Name',
            'requestor':        'Requester',
            'wbs':              'WBS Element ID',
            'purchasing_group': 'Purchasing Group Name',
            'cost_center':      'Cost Center ID',
            'gl_account':       'GL Account Name',
            'cluster':          'PSCS Cluster',
            'category':         'PSCS Category',
        }
        for key, col in dim_mappings.items():
            vals = filters.get(key, [])
            if vals:
                actual = self._find_column(fdf, col)
                if actual:
                    fdf = fdf[fdf[actual].isin(vals)]

        # ── Step 5: CAPEX / OPEX radio filter ────────────────────────────────
        # Row-level filter: an invoice line is "CAPEX" if CAPEX Spend > 0,
        # "OPEX" if OPEX Spend (= FI + MM) > 0.
        # "All" keeps every row regardless.
        # Note: in practice most rows are either CAPEX or OPEX (rarely both),
        # so this correctly partitions the data.
        capex_opex = filters.get('capex_opex', 'All')
        if capex_opex == 'CAPEX only':
            if 'CAPEX Spend' in fdf.columns:
                fdf = fdf[fdf['CAPEX Spend'] > 0]
        elif capex_opex == 'OPEX only':
            if 'OPEX Spend' in fdf.columns:
                fdf = fdf[fdf['OPEX Spend'] > 0]
        # 'All' → no filter applied

        return fdf

    # ─── Comparative stats ────────────────────────────────────────────────────
    def get_comparative_stats(self, df: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute KPI deltas: current period vs SAME period one year back.

        "Same period" = identical YTD/MTD flags and month selection,
        but year shifted by −1. Examples:
          year=2026, Feb, YTD  → current: Jan+Feb 2026  prev: Jan+Feb 2025
          year=2026, Feb, MTD  → current: Feb 2026      prev: Feb 2025
          year=2026, no month  → current: all 2026      prev: all 2025
        """
        _zero = {k: 0.0 for k in ['total_spend','total_capex','total_fi','total_mm',
                                   'total_opex','capex_pct','opex_pct',
                                   'total_rows','unique_vendors',
                                   'unique_requesters','unique_categories']}

        year_val = filters.get('year')

        # ── Resolve current year and previous year ────────────────────────────
        if not year_val or str(year_val).lower() in ('toutes','all','none',''):
            years = sorted(df['Année'].dropna().unique().astype(int).tolist()) \
                    if 'Année' in df.columns else []
            if len(years) < 2:
                current_df = self.apply_filters(df, filters)
                return {'current': self.get_summary_stats(current_df),
                        'deltas': _zero, 'has_comparison': False}
            current_year  = years[-1]   # most recent year
            previous_year = years[-2]   # one year back
        else:
            current_year  = int(year_val)
            previous_year = current_year - 1   # always exactly one year back

        # ── Current period ────────────────────────────────────────────────────
        # Override the year in filters to the resolved current_year,
        # keeping all other settings (YTD, MTD, months, dimensions) intact.
        current_filters = {**filters, 'year': current_year}
        current_df      = self.apply_filters(df, current_filters)
        current_stats   = self.get_summary_stats(current_df)

        # ── Previous period (one year back, SAME scope) ───────────────────────
        # We keep YTD, MTD, months, dimensions UNCHANGED so that we compare
        # apple-to-apple: e.g. Jan+Feb 2025 vs Jan+Feb 2026.
        prev_filters = {**filters, 'year': previous_year}
        prev_df      = self.apply_filters(df, prev_filters)

        if prev_df.empty:
            return {'current': current_stats, 'deltas': _zero, 'has_comparison': False,
                    'current_year': current_year, 'previous_year': previous_year}

        prev_stats = self.get_summary_stats(prev_df)

        # Delta = current − previous (positive = more spend = RED)
        deltas = {k: current_stats[k] - prev_stats.get(k, 0)
                  for k in ['total_spend','total_capex','total_fi','total_mm',
                             'total_opex','capex_pct','opex_pct',
                             'total_rows','unique_vendors',
                             'unique_requesters','unique_categories']}

        return {
            'current':       current_stats,
            'deltas':        deltas,
            'has_comparison': True,
            'current_year':  current_year,
            'previous_year': previous_year,
        }

    @staticmethod
    def get_default_base_year(df: pd.DataFrame) -> int:
        if 'Année' not in df.columns:
            return 0
        years = sorted(df['Année'].dropna().unique().astype(int).tolist())
        return years[-2] if len(years) >= 2 else (years[0] if years else 0)