"""
Module de traitement et nettoyage des données
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Optional, Dict, Any


class SpendDataProcessor:
    """Classe pour le traitement des données de spends"""
    
    # Colonnes attendues
    NUMERIC_COLUMNS = ['CAPEX Spend', 'FI Spend', 'MM Spend', 'Total  spend', 'Order quantity']
    DATE_COLUMNS = ['Invoice Posting Date', 'Document date', 'Vendor Inv. Date']
    
    def __init__(self):
        self.original_df = None
        self.processed_df = None
    
    def load_and_process(self, uploaded_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Charge et traite le fichier Excel
        
        Args:
            uploaded_file: Fichier uploadé via Streamlit
            
        Returns:
            Tuple (DataFrame traité, message d'erreur ou None)
        """
        try:
            # Lecture du fichier
            df = pd.read_excel(uploaded_file,engine='calamine')
            self.original_df = df.copy()
            
            # Pipeline de nettoyage
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
    
    def _remove_empty_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Supprime les lignes entièrement vides"""
        return df.dropna(how='all')
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Supprime les doublons basés sur PO et PO Item"""
        if 'PO' in df.columns and 'PO Item' in df.columns:
            initial_count = len(df)
            df = df.drop_duplicates(subset=['PO', 'PO Item'], keep='first')
            removed = initial_count - len(df)
            if removed > 0:
                print(f"Doublons supprimés : {removed}")
        return df
    
    def _clean_text_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoie les colonnes textuelles"""
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', np.nan)
        return df
    
    def _convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convertit les colonnes numériques"""
        for col in self.NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    
    def _convert_date_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convertit les colonnes de dates"""
        for col in self.DATE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    
    def _fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remplit les valeurs manquantes"""
        default_values = {
            'Vendor Name': 'Non spécifié',
            'Requester': 'Non spécifié',
            'PSCS Cluster': 'Non classifié',
            'PSCS Category': 'Non classifié',
            'Purchasing Group Name': 'Non spécifié',
            'Company Code descr': 'Non spécifié'
        }
        
        for col, default in default_values.items():
            if col in df.columns:
                df[col] = df[col].fillna(default)
        
        return df
    
    def _create_derived_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée les colonnes dérivées"""
        # Utiliser Invoice Posting Date comme date principale
        if 'Invoice Posting Date' in df.columns:
            df['Date'] = df['Invoice Posting Date']
            df['Année'] = df['Date'].dt.year
            df['Mois'] = df['Date'].dt.month
            df['Nom_Mois'] = df['Date'].dt.strftime('%B')
            df['Année_Mois'] = df['Date'].dt.to_period('M').astype(str)
            df['Trimestre'] = df['Date'].dt.quarter
            df['Année_Trimestre'] = df['Année'].astype(str) + '-Q' + df['Trimestre'].astype(str)
            df['Semaine'] = df['Date'].dt.isocalendar().week
        
        # Calculer OPEX (FI + MM)
        if all(col in df.columns for col in ['FI Spend', 'MM Spend']):
            df['OPEX Spend'] = df['FI Spend'] + df['MM Spend']
        
        # Calculer le délai de facturation
        if 'Document date' in df.columns and 'Invoice Posting Date' in df.columns:
            df['Délai_Facturation_Jours'] = (
                df['Invoice Posting Date'] - df['Document date']
            ).dt.days
        
        # Calculer le prix unitaire
        if 'Total  spend' in df.columns and 'Order quantity' in df.columns:
            df['Prix_Unitaire'] = df.apply(
                lambda x: x['Total  spend'] / x['Order quantity'] 
                if x['Order quantity'] > 0 else 0,
                axis=1
            )
        
        return df
    
    def get_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcule les statistiques résumées
        
        Args:
            df: DataFrame à analyser
            
        Returns:
            Dictionnaire contenant les KPIs
        """
        stats = {
            'total_rows': len(df),
            'total_spend': df['Total  spend'].sum() if 'Total  spend' in df.columns else 0,
            'total_capex': df['CAPEX Spend'].sum() if 'CAPEX Spend' in df.columns else 0,
            'total_fi': df['FI Spend'].sum() if 'FI Spend' in df.columns else 0,
            'total_mm': df['MM Spend'].sum() if 'MM Spend' in df.columns else 0,
            'total_opex': df['OPEX Spend'].sum() if 'OPEX Spend' in df.columns else 0,
            'unique_vendors': df['Vendor Name'].nunique() if 'Vendor Name' in df.columns else 0,
            'unique_requesters': df['Requester'].nunique() if 'Requester' in df.columns else 0,
            'unique_categories': df['PSCS Category'].nunique() if 'PSCS Category' in df.columns else 0,
            'avg_order': df['Total  spend'].mean() if 'Total  spend' in df.columns else 0,
            'median_order': df['Total  spend'].median() if 'Total  spend' in df.columns else 0,
            'date_min': df['Date'].min() if 'Date' in df.columns and not df['Date'].isna().all() else None,
            'date_max': df['Date'].max() if 'Date' in df.columns and not df['Date'].isna().all() else None
        }
        
        return stats
    
    def apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Applique les filtres au DataFrame
        
        Args:
            df: DataFrame à filtrer
            filters: Dictionnaire de filtres
            
        Returns:
            DataFrame filtré
        """
        filtered_df = df.copy()
        
        # Filtre par date
        if 'date_range' in filters and filters['date_range'] and len(filters['date_range']) == 2:
            if 'Date' in filtered_df.columns:
                start_date, end_date = filters['date_range']
                filtered_df = filtered_df[
                    (filtered_df['Date'] >= pd.Timestamp(start_date)) & 
                    (filtered_df['Date'] <= pd.Timestamp(end_date))
                ]
        
        # Filtre par vendors
        if 'vendors' in filters and filters['vendors']:
            if 'Vendor Name' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Vendor Name'].isin(filters['vendors'])]
        
        # Filtre par catégories
        if 'categories' in filters and filters['categories']:
            if 'PSCS Category' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['PSCS Category'].isin(filters['categories'])]
        
        # Filtre par clusters
        if 'clusters' in filters and filters['clusters']:
            if 'PSCS Cluster' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['PSCS Cluster'].isin(filters['clusters'])]
        
        # Filtre par requesters
        if 'requesters' in filters and filters['requesters']:
            if 'Requester' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Requester'].isin(filters['requesters'])]
        
        # Filtre par montant minimum
        if 'min_spend' in filters and filters['min_spend'] > 0:
            if 'Total  spend' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Total  spend'] >= filters['min_spend']]
        
        # Filtre par montant maximum
        if 'max_spend' in filters and filters['max_spend'] > 0:
            if 'Total  spend' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Total  spend'] <= filters['max_spend']]
        
        # Filtre par période (année-mois)
        if 'period' in filters and filters['period']:
            if 'Année_Mois' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Année_Mois'] == filters['period']]
        
        return filtered_df