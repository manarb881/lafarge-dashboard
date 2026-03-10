"""
Module de traitement et nettoyage des données - VERSION LAFARGE3
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Optional, Dict, Any


class SpendDataProcessor:
    """Classe pour le traitement des données de spends"""

    NUMERIC_COLUMNS = ['CAPEX Spend', 'FI Spend', 'MM Spend', 'Total  spend', 'Order quantity']
    DATE_COLUMNS = ['Invoice Posting Date', 'Document date', 'Vendor Inv. Date']

    def __init__(self):
        self.original_df = None
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
    def _remove_empty_rows(self, df):
        return df.dropna(how='all')

    def _remove_duplicates(self, df):
        return df

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
        default_mapping = {
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
        for target, default in default_mapping.items():
            actual = self._find_column(df, target)
            if actual:
                df[actual] = df[actual].astype(str).fillna(default).replace('nan', default)
        return df

    def _find_column(self, df, target):
        if target in df.columns:
            return target
        # Normalize: lowercase, strip spaces, strip dots, strip trailing spaces
        def _norm(s):
            return s.lower().replace(" ", "").replace(".", "").strip()
        target_norm = _norm(target)
        for col in df.columns:
            if _norm(col) == target_norm:
                return col
        return None

    def _create_derived_columns(self, df):
        # ── Normalize column names that may have dots/extra spaces ───────────
        rename_map = {}
        for raw_variant, canonical in [
            ('GL. Account Name ', 'GL Account Name'),
            ('GL. Account Name',  'GL Account Name'),
            ('GL Account Name ',  'GL Account Name'),
            ('GL. Account ID',    'GL Account ID'),
        ]:
            actual = self._find_column(df, raw_variant)
            if actual and actual != canonical:
                rename_map[actual] = canonical
        if rename_map:
            df = df.rename(columns=rename_map)

        date_col = self._find_column(df, 'Invoice Posting Date')
        if date_col:
            df['Date']      = pd.to_datetime(df[date_col], errors='coerce')
            df['Année']     = df['Date'].dt.year
            df['Month_num'] = df['Date'].dt.month
            df['Nom_Mois']  = df['Date'].dt.strftime('%B')
            df['Année_Mois']= df['Date'].dt.to_period('M').astype(str)

        # Convert to kCHF
        for col in ['CAPEX Spend', 'FI Spend', 'MM Spend', 'Total  spend']:
            actual = self._find_column(df, col)
            if actual:
                df[col] = pd.to_numeric(df[actual], errors='coerce').fillna(0) / 1000

        df['OPEX Spend']   = df.get('FI Spend', 0) + df.get('MM Spend', 0)
        df['Total  spend'] = df.get('CAPEX Spend', 0) + df['OPEX Spend']
        return df

    # ─── Stats ────────────────────────────────────────────────────────────────
    def get_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        total_spend = float(df['Total  spend'].sum()) if 'Total  spend' in df.columns else 0.0
        total_capex = float(df['CAPEX Spend'].sum())  if 'CAPEX Spend'  in df.columns else 0.0
        total_opex  = float(df['OPEX Spend'].sum())   if 'OPEX Spend'   in df.columns else 0.0

        stats = {
            'total_rows':        len(df),
            'total_spend':       total_spend,
            'total_capex':       total_capex,
            'total_fi':          float(df['FI Spend'].sum())  if 'FI Spend'  in df.columns else 0.0,
            'total_mm':          float(df['MM Spend'].sum())  if 'MM Spend'  in df.columns else 0.0,
            'total_opex':        total_opex,
            'unique_vendors':    df['Vendor Name'].nunique()        if 'Vendor Name'    in df.columns else 0,
            'unique_requesters': df['Requester'].nunique()          if 'Requester'      in df.columns else 0,
            'unique_categories': df['PSCS Category'].nunique()      if 'PSCS Category'  in df.columns else 0,
            'unique_clusters':   df['PSCS Cluster'].nunique()       if 'PSCS Cluster'   in df.columns else 0,
            'date_min':          df['Date'].min() if 'Date' in df.columns else None,
            'date_max':          df['Date'].max() if 'Date' in df.columns else None,
        }
        stats['capex_pct'] = (total_capex / total_spend * 100) if total_spend > 0 else 0.0
        stats['opex_pct']  = (total_opex  / total_spend * 100) if total_spend > 0 else 0.0
        return stats

    # ─── Filters ──────────────────────────────────────────────────────────────
    def apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        fdf = df.copy()
        year   = filters.get('year')
        months = filters.get('months', [])

        # ── Year to Date ──────────────────────────────────────────────────────
        if filters.get('year_to_date') and year and 'Année' in fdf.columns:
            fdf = fdf[fdf['Année'] <= year]

        # ── Single year ───────────────────────────────────────────────────────
        elif year and 'Année' in fdf.columns:
            fdf = fdf[fdf['Année'] == year]

        # ── Month to Date ─────────────────────────────────────────────────────
        if filters.get('month_to_date') and 'Date' in fdf.columns:
            current_month = pd.Timestamp.now().month
            fdf = fdf[fdf['Date'].dt.month <= current_month]

        # ── Month filter ──────────────────────────────────────────────────────
        if months and 'Nom_Mois' in fdf.columns:
            fdf = fdf[fdf['Nom_Mois'].isin(months)]

        # ── Custom date range (only when no year filter) ──────────────────────
        date_range = filters.get('date_range', ())
        if len(date_range) == 2 and not year and not filters.get('year_to_date'):
            if 'Date' in fdf.columns:
                start, end = date_range
                fdf = fdf[
                    (fdf['Date'] >= pd.Timestamp(start)) &
                    (fdf['Date'] <= pd.Timestamp(end))
                ]

        # ── Dimension filters ─────────────────────────────────────────────────
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

        # ── CAPEX / OPEX ──────────────────────────────────────────────────────
        capex_opex = filters.get('capex_opex', 'All')
        if capex_opex == 'CAPEX only' and 'CAPEX Spend' in fdf.columns:
            fdf = fdf[fdf['CAPEX Spend'] > 0]
        elif capex_opex == 'OPEX only' and 'OPEX Spend' in fdf.columns:
            fdf = fdf[fdf['OPEX Spend'] > 0]

        return fdf

    # ─── Comparative stats ────────────────────────────────────────────────────
    def get_comparative_stats(self, df: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        _zero_deltas = {k: 0.0 for k in
                        ['total_spend', 'total_capex', 'total_fi', 'total_mm', 'total_opex',
                         'capex_pct', 'opex_pct']}

        current_df    = self.apply_filters(df, filters)
        current_stats = self.get_summary_stats(current_df)

        year = filters.get('year')
        if not year:
            return {'current': current_stats, 'deltas': _zero_deltas, 'has_comparison': False}

        prev_filters = {**filters, 'year': year - 1, 'year_to_date': False}
        prev_df      = self.apply_filters(df, prev_filters)

        if prev_df.empty:
            return {'current': current_stats, 'deltas': _zero_deltas, 'has_comparison': False}

        prev_stats = self.get_summary_stats(prev_df)
        deltas = {k: current_stats[k] - prev_stats[k]
                  for k in ['total_spend', 'total_capex', 'total_fi', 'total_mm', 'total_opex',
                             'capex_pct', 'opex_pct']}

        return {'current': current_stats, 'deltas': deltas, 'has_comparison': True}

    # ─── Helper: default base year for variation charts ───────────────────────
    @staticmethod
    def get_default_base_year(df: pd.DataFrame) -> int:
        """
        Returns second-to-last year so that the variation chart shows
        (second-to-last) vs (last) by default.
        """
        if 'Année' not in df.columns:
            return 0
        years = sorted(df['Année'].dropna().unique().astype(int).tolist())
        if len(years) >= 2:
            return years[-2]
        return years[0] if years else 0