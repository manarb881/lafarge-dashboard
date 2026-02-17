"""
Module de visualisations Plotly
Priorités :
  1. Waterfall charts (avancement cumulatif des dépenses)
  2. Pareto 80/20 (vendors, PSCS Category, PSCS Cluster, Requester)
  3. Heatmap temporelle + évolution empilée
  4. Treemap / donut complémentaires
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Optional


# ─── Palette globale ──────────────────────────────────────────────────────────
C = {
    'blue':   '#2563EB',
    'lblue':  '#93C5FD',
    'green':  '#16A34A',
    'lgreen': '#86EFAC',
    'red':    '#DC2626',
    'orange': '#EA580C',
    'grey':   '#94A3B8',
    'dgrey':  '#475569',
    'pareto': '#F59E0B',
    'capex':  '#7C3AED',
    'opex':   '#0EA5E9',
    'fi':     '#06B6D4',
    'mm':     '#6366F1',
    'up':     '#16A34A',
    'down':   '#DC2626',
    'total':  '#1E3A5F',
}

LAYOUT_BASE = dict(
    font=dict(family='Inter, sans-serif', size=13),
    paper_bgcolor='rgba(0,0,0,0)',   # transparent → suit le thème Streamlit
    plot_bgcolor='rgba(0,0,0,0)',    # idem
    margin=dict(t=60, b=50, l=65, r=35),
    hoverlabel=dict(font_size=13),
    xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', zeroline=False),
    yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', zeroline=False),
)

# Pour les graphiques sans axes cartésiens (pie, treemap, sunburst…)
LAYOUT_NO_AXES = dict(
    font=dict(family='Inter, sans-serif', size=13),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(t=60, b=30, l=30, r=30),
    hoverlabel=dict(font_size=13),
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. WATERFALL CHARTS
# ══════════════════════════════════════════════════════════════════════════════

class WaterfallCharts:
    """Waterfall charts : montrent mois par mois comment les dépenses s'accumulent
    et les variations positives / négatives par rapport à la période précédente."""

    @staticmethod
    def mensuel(df: pd.DataFrame) -> Optional[go.Figure]:
        """Waterfall mensuel : variation mois sur mois du spend total."""
        if 'Année_Mois' not in df.columns:
            return None

        monthly = (df.groupby('Année_Mois')['Total  spend']
                     .sum()
                     .reset_index()
                     .sort_values('Année_Mois'))

        if len(monthly) < 2:
            return None

        labels   = list(monthly['Année_Mois'])
        values   = list(monthly['Total  spend'])
        deltas   = [values[0]] + [values[i] - values[i-1] for i in range(1, len(values))]
        measures = ['absolute'] + ['relative'] * (len(values) - 1)

        fig = go.Figure(go.Waterfall(
            orientation='v',
            measure=measures,
            x=labels,
            y=deltas,
            text=[f"{v:+,.0f} €" if i > 0 else f"{v:,.0f} €" for i, v in enumerate(deltas)],
            textposition='outside',
            connector=dict(line=dict(color=C['grey'], width=1, dash='dot')),
            increasing=dict(marker=dict(color=C['up'])),
            decreasing=dict(marker=dict(color=C['down'])),
            totals=dict(marker=dict(color=C['total'])),
            hovertemplate='<b>%{x}</b><br>Variation: %{y:+,.0f} €<extra></extra>',
        ))

        # Ligne de la valeur mensuelle réelle
        fig.add_trace(go.Scatter(
            x=labels, y=values,
            mode='lines+markers',
            name='Spend réel',
            line=dict(color=C['orange'], width=2, dash='dash'),
            marker=dict(size=7),
            hovertemplate='<b>%{x}</b><br>Spend: %{y:,.0f} €<extra></extra>',
        ))

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text='📊 Waterfall — Avancement mensuel des dépenses', font_size=15),
            xaxis_title='Période',
            yaxis_title='Montant (€)',
            height=470,
            showlegend=True,
        )
        return fig

    @staticmethod
    def capex_opex_mensuel(df: pd.DataFrame) -> Optional[go.Figure]:
        """Waterfall CAPEX et OPEX sur deux sous-graphiques."""
        if 'Année_Mois' not in df.columns:
            return None

        monthly = (df.groupby('Année_Mois')
                     .agg({'CAPEX Spend': 'sum', 'OPEX Spend': 'sum'})
                     .reset_index()
                     .sort_values('Année_Mois'))

        if len(monthly) < 2:
            return None

        labels = list(monthly['Année_Mois'])

        def _wf_trace(vals, name, col_up, col_down, col_total):
            deltas   = [vals[0]] + [vals[i] - vals[i-1] for i in range(1, len(vals))]
            measures = ['absolute'] + ['relative'] * (len(vals) - 1)
            return go.Waterfall(
                name=name, orientation='v', measure=measures,
                x=labels, y=deltas,
                connector=dict(line=dict(color=C['grey'], width=1, dash='dot')),
                increasing=dict(marker=dict(color=col_up)),
                decreasing=dict(marker=dict(color=col_down)),
                totals=dict(marker=dict(color=col_total)),
                hovertemplate=f'<b>{name}</b><br>%{{x}}<br>Δ: %{{y:+,.0f}} €<extra></extra>',
            )

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            subplot_titles=['CAPEX', 'OPEX'],
                            vertical_spacing=0.13)

        fig.add_trace(_wf_trace(list(monthly['CAPEX Spend']),
                                'CAPEX', C['capex'], C['red'], C['total']), row=1, col=1)
        fig.add_trace(_wf_trace(list(monthly['OPEX Spend']),
                                'OPEX',  C['opex'],  C['red'], C['total']), row=2, col=1)

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text='📊 Waterfall CAPEX / OPEX — variations mensuelles', font_size=15),
            height=620,
        )
        return fig

    @staticmethod
    def cumulatif_annuel(df: pd.DataFrame) -> Optional[go.Figure]:
        """Waterfall cumulatif : construction du total sur la période."""
        if 'Année_Mois' not in df.columns:
            return None

        monthly = (df.groupby('Année_Mois')['Total  spend']
                     .sum()
                     .reset_index()
                     .sort_values('Année_Mois'))

        if len(monthly) < 2:
            return None

        labels = list(monthly['Année_Mois'])
        vals   = list(monthly['Total  spend'])
        cumul  = list(np.cumsum(vals))

        fig = go.Figure(go.Waterfall(
            orientation='v',
            measure=['relative'] * len(vals),
            x=labels,
            y=vals,
            text=[f"{v:,.0f} €" for v in vals],
            textposition='outside',
            connector=dict(line=dict(color=C['grey'], width=1, dash='dot')),
            increasing=dict(marker=dict(color=C['blue'])),
            decreasing=dict(marker=dict(color=C['red'])),
            hovertemplate='<b>%{x}</b><br>Ajout: %{y:,.0f} €<extra></extra>',
        ))

        fig.add_trace(go.Scatter(
            x=labels, y=cumul,
            mode='lines+markers',
            name='Cumul',
            line=dict(color=C['orange'], width=3),
            marker=dict(size=9, symbol='circle-open',
                        line=dict(width=2, color=C['orange'])),
            yaxis='y2',
            hovertemplate='<b>%{x}</b><br>Cumul: %{y:,.0f} €<extra></extra>',
        ))

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text='📊 Waterfall Cumulatif — construction du total sur la période', font_size=15),
            xaxis_title='Période',
            yaxis_title='Spend mensuel (€)',
            yaxis2=dict(title='Cumul (€)', overlaying='y', side='right', showgrid=False),
            height=470,
            showlegend=True,
        )
        return fig

    @staticmethod
    def par_cluster(df: pd.DataFrame) -> Optional[go.Figure]:
        """Waterfall : contribution de chaque cluster PSCS au total."""
        if 'PSCS Cluster' not in df.columns:
            return None

        agg   = (df.groupby('PSCS Cluster')['Total  spend']
                   .sum().sort_values(ascending=False).reset_index())
        labels = list(agg['PSCS Cluster'])
        vals   = list(agg['Total  spend'])
        total  = sum(vals)

        fig = go.Figure(go.Waterfall(
            orientation='v',
            measure=['relative'] * len(vals) + ['total'],
            x=labels + ['TOTAL'],
            y=vals + [0],
            text=[f"{v:,.0f} €" for v in vals] + [f"{total:,.0f} €"],
            textposition='outside',
            connector=dict(line=dict(color=C['grey'], width=1, dash='dot')),
            increasing=dict(marker=dict(color=C['blue'])),
            decreasing=dict(marker=dict(color=C['red'])),
            totals=dict(marker=dict(color=C['total'])),
            hovertemplate='<b>%{x}</b><br>Montant: %{y:,.0f} €<extra></extra>',
        ))

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text='📊 Waterfall — Contribution de chaque Cluster PSCS', font_size=15),
            xaxis_title='Cluster PSCS',
            yaxis_title='Montant (€)',
            height=450,
        )
        return fig


# ══════════════════════════════════════════════════════════════════════════════
# 2. PARETO 80/20
# ══════════════════════════════════════════════════════════════════════════════

class ParetoCharts:
    """Graphiques Pareto : barres décroissantes + courbe de cumul %."""

    @staticmethod
    def _build(labels, values, title, x_label, seuil: float = 0.80) -> go.Figure:
        # Filtrer les valeurs <= 0 (avoirs, remboursements) qui fausseraient le cumul
        pairs = [(l, v) for l, v in zip(labels, values) if v > 0]
        if not pairs:
            return None
        labels, values = zip(*pairs)
        labels, values = list(labels), list(values)

        total  = sum(values)
        cumuls = list(np.cumsum(values) / total * 100)

        idx_seuil  = next((i for i, c in enumerate(cumuls) if c >= seuil * 100),
                          len(labels) - 1)
        bar_colors = [C['blue'] if i <= idx_seuil else C['grey']
                      for i in range(len(labels))]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(go.Bar(
            x=labels, y=values,
            name='Spend (€)',
            marker_color=bar_colors,
            hovertemplate='<b>%{x}</b><br>Spend: %{y:,.0f} €<extra></extra>',
        ), secondary_y=False)

        fig.add_trace(go.Scatter(
            x=labels, y=cumuls,
            mode='lines+markers',
            name='% Cumulé',
            line=dict(color=C['pareto'], width=3),
            marker=dict(size=7),
            hovertemplate='<b>%{x}</b><br>Cumul: %{y:.1f}%<extra></extra>',
        ), secondary_y=True)

        # Ligne 80 %
        fig.add_hline(y=seuil * 100, line_dash='dash', line_color=C['red'],
                      secondary_y=True, line_width=2,
                      annotation_text=f'{seuil*100:.0f} %',
                      annotation_position='right',
                      annotation_font_color=C['red'])

        # Zone bleue jusqu'au seuil
        if idx_seuil < len(labels) - 1:
            fig.add_vrect(x0=-0.5, x1=idx_seuil + 0.5,
                          fillcolor='rgba(37,99,235,0.07)',
                          layer='below', line_width=0)

        n_pareto  = idx_seuil + 1
        pct_items = n_pareto / len(labels) * 100

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(
                text=(f'📈 Pareto — {title}  '
                      f'<span style="font-size:12px;color:{C["red"]}">'
                      f'{n_pareto} éléments ({pct_items:.0f}%) → 80% du spend'
                      f'</span>'),
                font_size=14,
            ),
            xaxis_title=x_label,
            height=480,
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02,
                        xanchor='right', x=1),
        )
        fig.update_xaxes(tickangle=-40)
        fig.update_yaxes(title_text='Spend (€)',  secondary_y=False)
        fig.update_yaxes(title_text='% Cumulé',   secondary_y=True, range=[0, 105])
        return fig

    @staticmethod
    def vendors(df: pd.DataFrame, max_display: int = 30) -> Optional[go.Figure]:
        if 'Vendor Name' not in df.columns:
            return None
        agg = (df.groupby('Vendor Name')['Total  spend']
                 .sum().sort_values(ascending=False).head(max_display))
        return ParetoCharts._build(list(agg.index), list(agg.values),
                                   'Fournisseurs', 'Fournisseur')

    @staticmethod
    def pscs_category(df: pd.DataFrame, max_display: int = 30) -> Optional[go.Figure]:
        if 'PSCS Category' not in df.columns:
            return None
        agg = (df.groupby('PSCS Category')['Total  spend']
                 .sum().sort_values(ascending=False).head(max_display))
        return ParetoCharts._build(list(agg.index), list(agg.values),
                                   'Catégories PSCS', 'Catégorie')

    @staticmethod
    def pscs_cluster(df: pd.DataFrame) -> Optional[go.Figure]:
        if 'PSCS Cluster' not in df.columns:
            return None
        agg = (df.groupby('PSCS Cluster')['Total  spend']
                 .sum().sort_values(ascending=False))
        return ParetoCharts._build(list(agg.index), list(agg.values),
                                   'Clusters PSCS', 'Cluster')

    @staticmethod
    def requesters(df: pd.DataFrame, max_display: int = 25) -> Optional[go.Figure]:
        if 'Requester' not in df.columns:
            return None
        agg = (df.groupby('Requester')['Total  spend']
                 .sum().sort_values(ascending=False).head(max_display))
        return ParetoCharts._build(list(agg.index), list(agg.values),
                                   'Requesters', 'Requester')

    @staticmethod
    def purchasing_groups(df: pd.DataFrame) -> Optional[go.Figure]:
        if 'Purchasing Group Name' not in df.columns:
            return None
        agg = (df.groupby('Purchasing Group Name')['Total  spend']
                 .sum().sort_values(ascending=False))
        return ParetoCharts._build(list(agg.index), list(agg.values),
                                   'Groupes Achat', 'Groupe')

    @staticmethod
    def table_pareto(df: pd.DataFrame, col: str, label: str) -> Optional[pd.DataFrame]:
        """DataFrame annoté Pareto (rang, %, cumulé, zone)."""
        if col not in df.columns:
            return None
        agg = (df.groupby(col)['Total  spend']
                 .sum().sort_values(ascending=False).reset_index())
        agg.columns = [label, 'Spend (€)']
        # Exclure avoirs/négatifs du calcul Pareto
        agg = agg[agg['Spend (€)'] > 0].copy()
        if agg.empty:
            return None
        total = agg['Spend (€)'].sum()
        agg['% du Total'] = (agg['Spend (€)'] / total * 100).round(2)
        agg['% Cumulé']   = agg['% du Total'].cumsum().round(2)
        agg['Rang']       = range(1, len(agg) + 1)
        agg['Zone Pareto'] = agg['% Cumulé'].apply(
            lambda x: '🔴 Top 80%' if x <= 80 else '⚪ Long tail'
        )
        return agg[['Rang', label, 'Spend (€)', '% du Total', '% Cumulé', 'Zone Pareto']]


# ══════════════════════════════════════════════════════════════════════════════
# 3. CHARTS TEMPORELS COMPLÉMENTAIRES
# ══════════════════════════════════════════════════════════════════════════════

class TemporalCharts:

    @staticmethod
    def heatmap_categorie(df: pd.DataFrame, top_n: int = 15) -> Optional[go.Figure]:
        if 'Année_Mois' not in df.columns or 'PSCS Category' not in df.columns:
            return None

        top_cats = (df.groupby('PSCS Category')['Total  spend']
                      .sum().nlargest(top_n).index)
        sub = df[df['PSCS Category'].isin(top_cats)]
        pivot = (sub.groupby(['PSCS Category', 'Année_Mois'])['Total  spend']
                    .sum().unstack(fill_value=0))
        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale='YlOrRd',
            hoverongaps=False,
            hovertemplate='<b>%{y}</b><br>%{x}<br>Spend: %{z:,.0f} €<extra></extra>',
        ))
        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text=f'🗓️ Heatmap — Spend mensuel Top {top_n} catégories', font_size=15),
            xaxis_title='Période',
            yaxis_title='Catégorie',
            height=max(380, top_n * 28),
        )
        return fig

    @staticmethod
    def evolution_stacked(df: pd.DataFrame, group_col: str, top_n: int = 8,
                          title_prefix: str = '') -> Optional[go.Figure]:
        if 'Année_Mois' not in df.columns or group_col not in df.columns:
            return None

        top_items = (df.groupby(group_col)['Total  spend']
                       .sum().nlargest(top_n).index)
        sub   = df[df[group_col].isin(top_items)]
        pivot = (sub.groupby(['Année_Mois', group_col])['Total  spend']
                    .sum().unstack(fill_value=0).sort_index())

        colors = px.colors.qualitative.Set2
        fig = go.Figure()
        for i, col in enumerate(pivot.columns):
            fig.add_trace(go.Scatter(
                x=pivot.index, y=pivot[col],
                name=col, mode='lines',
                stackgroup='one',
                fillcolor=colors[i % len(colors)],
                line=dict(width=0.5),
                hovertemplate=f'<b>{col}</b><br>%{{x}}: %{{y:,.0f}} €<extra></extra>',
            ))

        label = group_col.replace('PSCS ', '').replace('Vendor Name', 'Fournisseur')
        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text=f'📈 Évolution empilée — {title_prefix or label} (Top {top_n})',
                       font_size=15),
            xaxis_title='Période',
            yaxis_title='Spend (€)',
            height=440,
            showlegend=True,
        )
        return fig

    @staticmethod
    def capex_opex_stacked(df: pd.DataFrame) -> Optional[go.Figure]:
        if 'Année_Mois' not in df.columns:
            return None

        monthly = (df.groupby('Année_Mois')
                     .agg({'CAPEX Spend': 'sum', 'FI Spend': 'sum', 'MM Spend': 'sum'})
                     .reset_index().sort_values('Année_Mois'))

        fig = go.Figure()
        for col, color, name in [
            ('CAPEX Spend', C['capex'], 'CAPEX'),
            ('FI Spend',    C['fi'],    'FI Spend'),
            ('MM Spend',    C['mm'],    'MM Spend'),
        ]:
            fig.add_trace(go.Bar(
                x=monthly['Année_Mois'], y=monthly[col],
                name=name, marker_color=color,
                hovertemplate=f'{name}<br>%{{x}}: %{{y:,.0f}} €<extra></extra>',
            ))

        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text='📊 CAPEX / FI / MM — Évolution mensuelle empilée', font_size=15),
            barmode='stack',
            xaxis_title='Période',
            yaxis_title='Montant (€)',
            height=430,
        )
        return fig


# ══════════════════════════════════════════════════════════════════════════════
# 4. CHARTS DE STRUCTURE / RÉPARTITION
# ══════════════════════════════════════════════════════════════════════════════

class StructureCharts:

    @staticmethod
    def treemap_pscs(df: pd.DataFrame) -> Optional[go.Figure]:
        if 'PSCS Cluster' not in df.columns or 'PSCS Category' not in df.columns:
            return None

        cat_data = (df.groupby(['PSCS Cluster', 'PSCS Category'])['Total  spend']
                      .sum().reset_index())
        cat_data = cat_data[cat_data['Total  spend'] > 0]

        fig = px.treemap(
            cat_data,
            path=['PSCS Cluster', 'PSCS Category'],
            values='Total  spend',
            color='Total  spend',
            color_continuous_scale='Blues',
        )
        fig.update_traces(
            hovertemplate='<b>%{label}</b><br>Spend: %{value:,.0f} €'
                          '<br>Part: %{percentRoot:.1%}<extra></extra>'
        )
        fig.update_layout(
            **LAYOUT_NO_AXES,
            title=dict(text='🌳 Treemap — Répartition PSCS Cluster / Catégorie', font_size=15),
            height=500,
        )
        return fig

    @staticmethod
    def donut_capex_opex(df: pd.DataFrame) -> go.Figure:
        vals   = [df['CAPEX Spend'].sum(), df['OPEX Spend'].sum()]
        labels = ['CAPEX', 'OPEX']
        fig = go.Figure(go.Pie(
            labels=labels, values=vals, hole=0.52,
            marker=dict(colors=[C['capex'], C['opex']]),
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>%{value:,.0f} €<br>(%{percent})<extra></extra>',
        ))
        fig.update_layout(**LAYOUT_NO_AXES,
                          title=dict(text='🍩 CAPEX vs OPEX', font_size=15),
                          height=380)
        return fig

    @staticmethod
    def donut_fi_mm(df: pd.DataFrame) -> go.Figure:
        vals   = [df['FI Spend'].sum(), df['MM Spend'].sum()]
        labels = ['FI Spend', 'MM Spend']
        fig = go.Figure(go.Pie(
            labels=labels, values=vals, hole=0.52,
            marker=dict(colors=[C['fi'], C['mm']]),
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>%{value:,.0f} €<br>(%{percent})<extra></extra>',
        ))
        fig.update_layout(**LAYOUT_NO_AXES,
                          title=dict(text='🍩 Détail OPEX — FI vs MM', font_size=15),
                          height=380)
        return fig

    @staticmethod
    def scatter_volume_spend(df: pd.DataFrame, group_col: str,
                             title: str = '') -> Optional[go.Figure]:
        if group_col not in df.columns:
            return None
        agg = df.groupby(group_col).agg(
            Total=('Total  spend', 'sum'),
            NbCmds=('Total  spend', 'count'),
            Moy=('Total  spend', 'mean'),
        ).reset_index()

        # px.scatter n'accepte que des tailles >= 0 → valeur absolue, min à 1
        agg['BubbleSize'] = agg['Total'].abs().clip(lower=1)
        # Exclure les lignes avec moyenne négative pour l'axe Y (avoirs purs)
        agg = agg[agg['Moy'] > 0].copy()

        if agg.empty:
            return None

        fig = px.scatter(
            agg, x='NbCmds', y='Moy',
            size='BubbleSize', color='Total',
            hover_name=group_col,
            color_continuous_scale='Blues',
            labels={
                'NbCmds': 'Nombre de commandes',
                'Moy':    'Montant moyen (€)',
                'Total':  'Total (€)',
            },
            size_max=55,
            hover_data={'BubbleSize': False, 'Total': ':,.0f'},
        )
        fig.update_layout(
            **LAYOUT_BASE,
            title=dict(text=f'🔵 Volume vs Montant moyen — {title or group_col}',
                       font_size=15),
            height=430,
        )
        return fig