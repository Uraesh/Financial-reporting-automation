"""Domain-specific dashboard builders for financial monitoring."""

from __future__ import annotations
# pyright: reportUnknownArgumentType=warning, reportArgumentType=warning, reportAttributeAccessIssue=warning, reportCallIssue=warning
# pyright: reportUnknownLambdaType=warning, reportOperatorIssue=warning, reportReturnType=warning, reportGeneralTypeIssues=warning
# pylint: disable=too-many-return-statements,too-many-positional-arguments

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.express as px
from plotly.graph_objs import Figure

from scripts.aggregation import format_currency
from scripts.charts import create_distribution_figure, create_numeric_figure, style_figure
from scripts.types import ColumnMapping

DASHBOARD_OPTIONS: tuple[str, ...] = (
    "1. Dashboard de Performance Financiere",
    "2. Dashboard de Tresorerie",
    "3. Dashboard Budget vs Reel",
    "4. Dashboard de Risque Financier",
    "5. Dashboard de Portefeuille d'Investissement",
    "6. Dashboard Comptable",
    "7. Dashboard Rentabilite Produits/Services",
    "8. Dashboard KPI Financiers",
    "9. Dashboard de Prevision Financiere",
    "10. Dashboard Fraude & Conformite",
    "11. Dashboard Trading",
    "12. Dashboard de Performance Bancaire",
)

PRINCIPAL_DASHBOARDS: tuple[str, ...] = (
    "1) Financial Performance",
    "2) Risk Management",
    "3) Portfolio Management",
    "4) Treasury Management",
)

OPTIONAL_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("revenu", "revenues", "revenue", "chiffre_affaires", "ca"),
    "ebitda": ("ebitda",),
    "net_profit": ("profit_net", "net_profit", "benefice_net", "resultat_net"),
    "cash_flow": ("cash_flow", "flux_tresorerie", "flux_de_tresorerie"),
    "budget": ("budget", "budget_planifie", "planned_budget"),
    "cost": ("cout", "cost", "cout_production", "production_cost"),
    "product": ("produit", "product", "service", "segment", "categorie"),
    "equity": ("equity", "fonds_propres", "capitaux_propres"),
    "assets": ("assets", "actifs", "total_assets"),
    "debt": ("debt", "dette", "total_debt"),
    "investment": ("investment", "investissement"),
    "ar": ("accounts_receivable", "ar", "creances_clients"),
    "ap": ("accounts_payable", "ap", "dettes_fournisseurs"),
    "status": ("status", "statut", "invoice_status", "payment_status"),
    "default_flag": ("default", "defaut", "non_performing", "npl"),
    "volume": ("volume", "quantite"),
    "price": ("price", "prix", "cours"),
}


@dataclass(frozen=True)
class DashboardBundle:
    """Container rendered by Streamlit for one selected dashboard."""

    title: str
    description: str
    kpis: tuple[tuple[str, str], ...]
    figures: tuple[Figure, ...]


def build_dashboard_bundle(
    dataframe: pd.DataFrame,
    mapping: ColumnMapping,
    selected_dashboard: str,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Build the selected dashboard bundle."""
    prepared = _prepare_frame(dataframe, mapping)

    monthly_net = _monthly_sum(prepared, "amount_value").rename(columns={"amount_value": "value"})
    monthly_positive = _monthly_positive(prepared)
    direction_mix = _direction_mix(prepared)
    region_mix = _region_mix(prepared)
    product_mix = _product_mix(prepared)

    revenue = _estimate_revenue(prepared)
    ebitda = _optional_total(prepared, "ebitda", revenue * 0.27)
    net_profit = _optional_total(prepared, "net_profit", revenue * 0.14)
    cash_flow = _optional_total(prepared, "cash_flow", float(prepared["amount_value"].sum()))
    inflow = float(prepared.loc[prepared["direction"] == "Inflow", "amount_value"].clip(lower=0).sum())
    outflow = float(prepared.loc[prepared["direction"] == "Outflow", "abs_amount"].sum())
    cash_available = inflow - outflow

    growth = _latest_growth(monthly_positive["value"])
    gross_margin = _safe_ratio(revenue - prepared["abs_amount"].sum() * 0.65, revenue) * 100
    operating_margin = _safe_ratio(ebitda, revenue) * 100
    net_margin = _safe_ratio(net_profit, revenue) * 100

    returns = monthly_net["value"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    var_95 = float(np.percentile(returns, 5) * 100)
    market_risk = float(returns.std(ddof=0) * 100)
    stress_99 = float(np.percentile(returns, 1) * 100)

    burn_candidates = monthly_net.loc[monthly_net["value"] < 0, "value"].abs()
    burn_rate = float(burn_candidates.mean()) if not burn_candidates.empty else 0.0
    runway = _safe_ratio(max(cash_available, 0.0), burn_rate) if burn_rate > 0 else np.inf

    if selected_dashboard == DASHBOARD_OPTIONS[0]:
        cards = (
            ("Revenus / Chiffre d'affaires", format_currency(revenue)),
            ("EBITDA", format_currency(ebitda)),
            ("Profit net", format_currency(net_profit)),
            ("Marge nette", _format_percent(net_margin)),
            ("Croissance mensuelle", _format_percent(growth)),
            ("Cash flow", format_currency(cash_flow)),
        )
        margin_table = pd.DataFrame(
            {
                "metric": ["Marge brute", "Marge operationnelle", "Marge nette"],
                "value": [gross_margin, operating_margin, net_margin],
            }
        )
        figures = (
            create_numeric_figure(
                monthly_positive,
                x_column="month_label",
                y_column="value",
                chart_type=numeric_chart_type,
                title="Evolution du chiffre d'affaires",
            ),
            create_numeric_figure(
                margin_table,
                x_column="metric",
                y_column="value",
                chart_type="Barres",
                title="Marges (%)",
            ),
            create_distribution_figure(
                direction_mix,
                "direction",
                "value",
                distribution_chart_type,
                "Repartition des flux",
            ),
        )
        return DashboardBundle(
            title="Dashboard de Performance Financiere",
            description="Suivi global de la sante financiere (CFO/Direction).",
            kpis=cards,
            figures=figures,
        )

    if selected_dashboard == DASHBOARD_OPTIONS[1]:
        cumulative_cash = monthly_net.copy()
        cumulative_cash["value"] = cumulative_cash["value"].cumsum()
        cards = (
            ("Cash inflows", format_currency(inflow)),
            ("Cash outflows", format_currency(outflow)),
            ("Cash disponible", format_currency(cash_available)),
            ("Prevision tresorerie (3 mois)", format_currency(cash_available + float(monthly_net["value"].mean()) * 3.0)),
            ("Burn rate", format_currency(burn_rate)),
            ("Runway", _format_runway(runway)),
        )
        figures = (
            create_numeric_figure(
                monthly_net,
                x_column="month_label",
                y_column="value",
                chart_type=numeric_chart_type,
                title="Flux net de tresorerie",
            ),
            create_numeric_figure(
                cumulative_cash,
                x_column="month_label",
                y_column="value",
                chart_type="Ligne",
                title="Cash cumule",
            ),
            create_distribution_figure(
                direction_mix,
                "direction",
                "value",
                distribution_chart_type,
                "Repartition Inflows/Outflows",
            ),
        )
        return DashboardBundle(
            title="Dashboard de Tresorerie (Cash Flow)",
            description="Pilotage de liquidite, burn rate et runway.",
            kpis=cards,
            figures=figures,
        )

    if selected_dashboard == DASHBOARD_OPTIONS[2]:
        return _budget_bundle(prepared, numeric_chart_type, distribution_chart_type)

    if selected_dashboard == DASHBOARD_OPTIONS[3]:
        stress_table = pd.DataFrame(
            {"scenario": ["Base", "Adverse", "Severe"], "value": [0.0, var_95, stress_99]}
        )
        cards = (
            ("Value at Risk (95%)", _format_percent(var_95)),
            ("Exposition au risque", format_currency(float(prepared["abs_amount"].sum()))),
            ("Risque de credit", _format_percent(_credit_risk(prepared))),
            ("Risque de marche", _format_percent(market_risk)),
            ("Stress tests", _format_percent(stress_99)),
            ("Population suivie", str(int(len(prepared)))),
        )
        figures = (
            create_numeric_figure(
                monthly_net.assign(returns=returns),
                x_column="month_label",
                y_column="returns",
                chart_type="Histogramme",
                title="Distribution des rendements",
            ),
            create_numeric_figure(
                stress_table,
                x_column="scenario",
                y_column="value",
                chart_type=numeric_chart_type,
                title="Scenarios de stress",
            ),
            create_distribution_figure(region_mix, "region_label", "value", distribution_chart_type, "Exposition par region"),
        )
        return DashboardBundle(
            title="Dashboard de Risque Financier",
            description="VaR, risque credit/marche et stress tests.",
            kpis=cards,
            figures=figures,
        )

    if selected_dashboard == DASHBOARD_OPTIONS[4]:
        return _portfolio_bundle(prepared, product_mix, numeric_chart_type, distribution_chart_type)

    if selected_dashboard == DASHBOARD_OPTIONS[5]:
        return _accounting_bundle(prepared, numeric_chart_type, distribution_chart_type)

    if selected_dashboard == DASHBOARD_OPTIONS[6]:
        return _profitability_bundle(prepared, numeric_chart_type, distribution_chart_type)

    if selected_dashboard == DASHBOARD_OPTIONS[7]:
        return _kpi_bundle(prepared, revenue, ebitda, net_profit, numeric_chart_type, distribution_chart_type)

    if selected_dashboard == DASHBOARD_OPTIONS[8]:
        return _forecast_bundle(monthly_net, numeric_chart_type, distribution_chart_type)

    if selected_dashboard == DASHBOARD_OPTIONS[9]:
        return _fraud_bundle(prepared, numeric_chart_type, distribution_chart_type)

    if selected_dashboard == DASHBOARD_OPTIONS[10]:
        return _trading_bundle(prepared, numeric_chart_type, distribution_chart_type)

    return _banking_bundle(prepared, revenue, numeric_chart_type, distribution_chart_type)


def _budget_bundle(
    prepared: pd.DataFrame,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 3: Budget vs Reel."""
    actual = prepared.copy()
    actual["actual"] = np.where(actual["direction"] == "Outflow", actual["abs_amount"], 0.0)
    monthly_actual = _monthly_sum(actual, "actual")
    budget_col = _find_optional_column(prepared, OPTIONAL_ALIASES["budget"])
    if budget_col:
        source = prepared.copy()
        source["budget"] = pd.to_numeric(source[budget_col], errors="coerce").fillna(0.0).abs()
        monthly_budget = _monthly_sum(source, "budget")
    else:
        monthly_budget = monthly_actual.copy()
        monthly_budget["actual"] = monthly_budget["actual"].rolling(3, min_periods=1).mean() * 1.08
        monthly_budget = monthly_budget.rename(columns={"actual": "budget"})

    table = monthly_actual.merge(monthly_budget, on="month_label", how="left").fillna(0.0)
    table["variance"] = table["actual"] - table["budget"]
    table["variance_pct"] = table.apply(lambda row: _safe_ratio(row["variance"], row["budget"]) * 100, axis=1)
    cards = (
        ("Budget planifie", format_currency(float(table["budget"].sum()))),
        ("Depenses reelles", format_currency(float(table["actual"].sum()))),
        ("Variance totale", format_currency(float(table["variance"].sum()))),
        ("Variance moyenne", _format_percent(float(table["variance_pct"].mean()))),
        ("Analyse des ecarts", "Disponible"),
        ("Planification", "Active"),
    )
    melted = table.melt(id_vars="month_label", value_vars=["budget", "actual"], var_name="serie", value_name="value")
    figures = (
        create_numeric_figure(
            melted,
            x_column="month_label",
            y_column="value",
            chart_type=numeric_chart_type,
            title="Budget vs Reel",
            color_column="serie",
        ),
        create_numeric_figure(
            table,
            x_column="month_label",
            y_column="variance_pct",
            chart_type="Ligne",
            title="Variance (%)",
        ),
        create_distribution_figure(table.assign(weight=table["variance"].abs()), "month_label", "weight", distribution_chart_type, "Poids des ecarts"),
    )
    return DashboardBundle("Dashboard de Budget vs Reel", "Comparaison budget, reel et ecarts.", cards, figures)

def _portfolio_bundle(
    prepared: pd.DataFrame,
    product_mix: pd.DataFrame,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 5: Portefeuille."""
    asset_monthly = prepared.groupby(["month_label", "product_label"], as_index=False)["amount_value"].sum()
    volatility = (
        asset_monthly.groupby("product_label", as_index=False)["amount_value"]
        .std(ddof=0)
        .fillna(0.0)
        .rename(columns={"product_label": "product", "amount_value": "volatility"})
    )
    table = product_mix.merge(volatility, on="product", how="left").fillna(0.0)
    returns = _monthly_sum(prepared, "amount_value")["amount_value"].pct_change().fillna(0.0)
    sharpe = _safe_ratio(float(returns.mean()), float(returns.std(ddof=0) + 1e-9)) * np.sqrt(12.0)
    cards = (
        ("Performance portefeuille", format_currency(float(table["value"].sum()))),
        ("Allocation d'actifs", str(int(len(table)))),
        ("Rendement moyen", format_currency(float(table["value"].mean()))),
        ("Volatilite moyenne", _format_percent(float(table["volatility"].mean()))),
        ("Sharpe ratio", f"{sharpe:.2f}"),
        ("Top actif", str(table.sort_values("value", ascending=False)["product"].iloc[0])),
    )
    figures = (
        create_distribution_figure(table, "product", "allocation", distribution_chart_type, "Allocation d'actifs"),
        create_numeric_figure(
            table,
            x_column="product",
            y_column="value",
            chart_type=numeric_chart_type,
            title="Rendement par actif",
        ),
        create_numeric_figure(
            table,
            x_column="product",
            y_column="volatility",
            chart_type="Barres",
            title="Volatilite par actif",
        ),
    )
    return DashboardBundle(
        "Dashboard de Portefeuille d'Investissement",
        "Suivi performance, allocation, rendement et volatilite.",
        cards,
        figures,
    )


def _accounting_bundle(
    prepared: pd.DataFrame,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 6: Comptable."""
    inflow = float(prepared.loc[prepared["direction"] == "Inflow", "amount_value"].sum())
    outflow = float(prepared.loc[prepared["direction"] == "Outflow", "abs_amount"].sum())
    ar = _optional_total(prepared, "ar", inflow * 0.35)
    ap = _optional_total(prepared, "ap", outflow * 0.30)
    balance = ar - ap
    status_col = _find_optional_column(prepared, OPTIONAL_ALIASES["status"])
    if status_col:
        pending = int(
            prepared[status_col].astype("string").str.lower().str.contains(
                "pending|en_attente|late|retard",
                regex=True,
            ).sum()
        )
    else:
        pending = int((prepared["abs_amount"] >= prepared["abs_amount"].quantile(0.9)).sum())
    dso = _safe_ratio(ar, max(_estimate_revenue(prepared), 1.0) / 365.0)
    dpo = _safe_ratio(ap, max(outflow, 1.0) / 365.0)

    table = pd.DataFrame({"metric": ["AR", "AP", "Balance"], "value": [ar, ap, balance]})
    aging = prepared.copy()
    aging["days"] = (pd.Timestamp.today().normalize() - aging["date_value"]).dt.days.clip(lower=0)
    aging["bucket"] = pd.cut(aging["days"], bins=[-1, 30, 60, 90, 100000], labels=["0-30", "31-60", "61-90", "90+"])
    aging_table = aging.groupby("bucket", as_index=False, observed=False)["abs_amount"].sum()

    cards = (
        ("Comptes clients (AR)", format_currency(ar)),
        ("Comptes fournisseurs (AP)", format_currency(ap)),
        ("Balance generale", format_currency(balance)),
        ("Factures en attente", str(pending)),
        ("DSO", f"{dso:.1f} jours"),
        ("DPO", f"{dpo:.1f} jours"),
    )
    figures = (
        create_numeric_figure(
            table,
            x_column="metric",
            y_column="value",
            chart_type=numeric_chart_type,
            title="Vue comptable",
        ),
        create_distribution_figure(aging_table.rename(columns={"bucket": "age_bucket", "abs_amount": "value"}), "age_bucket", "value", distribution_chart_type, "Aging des montants"),
        create_numeric_figure(
            _monthly_sum(prepared, "abs_amount").rename(columns={"abs_amount": "value"}),
            x_column="month_label",
            y_column="value",
            chart_type="Ligne",
            title="Volume comptable mensuel",
        ),
    )
    return DashboardBundle("Dashboard Comptable", "Suivi AR/AP, balance et ageing.", cards, figures)


def _profitability_bundle(
    prepared: pd.DataFrame,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 7: Rentabilite."""
    revenue = (
        prepared.assign(rev=prepared["amount_value"].clip(lower=0))
        .groupby("product_label", as_index=False)["rev"]
        .sum()
        .rename(columns={"product_label": "product", "rev": "revenue"})
    )
    cost_col = _find_optional_column(prepared, OPTIONAL_ALIASES["cost"])
    if cost_col:
        costs = (
            prepared.assign(cost_value=pd.to_numeric(prepared[cost_col], errors="coerce").fillna(0.0).abs())
            .groupby("product_label", as_index=False)["cost_value"]
            .sum()
            .rename(columns={"product_label": "product", "cost_value": "cost"})
        )
    else:
        costs = revenue.copy()
        costs["cost"] = costs["revenue"] * 0.65
        costs = costs.drop(columns=["revenue"])

    table = revenue.merge(costs, on="product", how="left").fillna(0.0)
    table["profit"] = table["revenue"] - table["cost"]
    table["margin_pct"] = table.apply(lambda row: _safe_ratio(row["profit"], row["revenue"]) * 100, axis=1)
    table["roi_pct"] = table.apply(lambda row: _safe_ratio(row["profit"], row["cost"]) * 100, axis=1)
    total_revenue = float(table["revenue"].sum())
    table["contribution_pct"] = table["revenue"].apply(lambda value: _safe_ratio(value, total_revenue) * 100)

    cards = (
        ("Marge moyenne", _format_percent(float(table["margin_pct"].mean()))),
        ("Cout de production", format_currency(float(table["cost"].sum()))),
        ("ROI produit moyen", _format_percent(float(table["roi_pct"].mean()))),
        ("Contribution CA moyenne", _format_percent(float(table["contribution_pct"].mean()))),
        ("Produit le plus rentable", str(table.sort_values("margin_pct", ascending=False)["product"].iloc[0])),
        ("Produits/services suivis", str(int(len(table)))),
    )
    figures = (
        create_numeric_figure(
            table,
            x_column="product",
            y_column="margin_pct",
            chart_type=numeric_chart_type,
            title="Marge par produit/service",
        ),
        create_distribution_figure(table, "product", "contribution_pct", distribution_chart_type, "Contribution au CA"),
        create_numeric_figure(
            table,
            x_column="product",
            y_column="roi_pct",
            chart_type="Barres",
            title="ROI produit/service",
        ),
    )
    return DashboardBundle("Dashboard de Rentabilite Produits / Services", "Analyse marges, couts et ROI.", cards, figures)


def _kpi_bundle(
    prepared: pd.DataFrame,
    revenue: float,
    ebitda: float,
    net_profit: float,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 8: KPI financiers."""
    equity = max(_optional_total(prepared, "equity", revenue * 0.45), 1.0)
    assets = max(_optional_total(prepared, "assets", revenue * 1.4), 1.0)
    debt = max(_optional_total(prepared, "debt", prepared["abs_amount"].sum() * 0.5), 1.0)
    investment = max(_optional_total(prepared, "investment", prepared["abs_amount"].sum() * 0.4), 1.0)
    roe = _safe_ratio(net_profit, equity) * 100
    roi = _safe_ratio(net_profit, investment) * 100
    roa = _safe_ratio(net_profit, assets) * 100
    ebitda_margin = _safe_ratio(ebitda, revenue) * 100
    debt_to_equity = _safe_ratio(debt, equity)

    ratios = pd.DataFrame(
        {
            "ratio": ["ROE", "ROI", "ROA", "EBITDA margin", "Debt-to-equity"],
            "value": [roe, roi, roa, ebitda_margin, debt_to_equity * 100],
        }
    )
    cards = (
        ("ROE", _format_percent(roe)),
        ("ROI", _format_percent(roi)),
        ("ROA", _format_percent(roa)),
        ("EBITDA margin", _format_percent(ebitda_margin)),
        ("Debt-to-equity", f"{debt_to_equity:.2f}"),
        ("Profit net", format_currency(net_profit)),
    )
    figures = (
        create_numeric_figure(
            ratios,
            x_column="ratio",
            y_column="value",
            chart_type=numeric_chart_type,
            title="Ratios strategiques",
        ),
        create_numeric_figure(
            _monthly_sum(prepared, "amount_value").rename(columns={"amount_value": "value"}),
            x_column="month_label",
            y_column="value",
            chart_type="Ligne",
            title="Resultat mensuel",
        ),
        create_distribution_figure(pd.DataFrame({"category": ["Equity", "Debt", "Assets"], "value": [equity, debt, assets]}), "category", "value", distribution_chart_type, "Structure capital / dette / actifs"),
    )
    return DashboardBundle("Dashboard de KPI Financiers", "Vue rapide ROE/ROI/ROA/EBITDA/debt-to-equity.", cards, figures)

def _forecast_bundle(
    monthly_net: pd.DataFrame,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 9: Prevision financiere."""
    history = monthly_net.copy()
    if history.empty:
        history = pd.DataFrame({"month_label": [pd.Timestamp.today().strftime("%Y-%m")], "value": [0.0]})

    x_values = np.arange(len(history))
    y_values = history["value"].to_numpy(dtype=float)
    if len(history) >= 2:
        slope, intercept = np.polyfit(x_values, y_values, deg=1)
    else:
        slope, intercept = 0.0, float(y_values[0])

    horizon = 6
    future_x = np.arange(len(history), len(history) + horizon)
    future_values = slope * future_x + intercept
    last_month = pd.Period(history["month_label"].iloc[-1], freq="M")
    future_months = pd.period_range(last_month + 1, periods=horizon, freq="M").astype(str)
    forecast = pd.DataFrame({"month_label": future_months, "value": future_values, "serie": "Prevision"})
    trend = pd.concat([history.assign(serie="Historique"), forecast], ignore_index=True)

    returns = history["value"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    mean_return = float(returns.mean())
    std_return = float(returns.std(ddof=0))
    adjusted_std = std_return if std_return > 1e-9 else 0.02
    simulations = np.random.default_rng(42).normal(mean_return, adjusted_std, size=(500, horizon))
    base_value = float(history["value"].iloc[-1])
    monte_values = base_value * np.cumprod(1.0 + simulations, axis=1)[:, -1]

    scenario_central = float(forecast["value"].sum())
    scenarios = pd.DataFrame(
        {
            "scenario": ["Optimiste", "Central", "Pessimiste"],
            "value": [scenario_central * 1.1, scenario_central, scenario_central * 0.85],
        }
    )
    cards = (
        ("Prevision revenus (M+1)", format_currency(float(forecast["value"].iloc[0]))),
        ("Prevision cash flow (M+1)", format_currency(float(forecast["value"].iloc[0] * 0.9))),
        ("Scenario central (6 mois)", format_currency(scenario_central)),
        ("Scenario pessimiste", format_currency(float(scenarios.iloc[2]["value"]))),
        ("Monte Carlo P5", format_currency(float(np.percentile(monte_values, 5)))),
        ("Monte Carlo P95", format_currency(float(np.percentile(monte_values, 95)))),
    )
    figures = (
        create_numeric_figure(
            trend,
            x_column="month_label",
            y_column="value",
            chart_type=numeric_chart_type,
            title="Historique + prevision",
            color_column="serie",
        ),
        create_numeric_figure(
            pd.DataFrame({"bucket": "Simulation", "value": monte_values}),
            x_column="bucket",
            y_column="value",
            chart_type="Histogramme",
            title="Monte Carlo (valeurs finales)",
        ),
        create_distribution_figure(scenarios, "scenario", "value", distribution_chart_type, "Scenarios economiques"),
    )
    return DashboardBundle("Dashboard de Prevision Financiere", "Previsions, scenarios et simulation Monte Carlo.", cards, figures)


def _fraud_bundle(
    prepared: pd.DataFrame,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 10: fraude et conformite."""
    amounts = prepared["abs_amount"]
    mean_value = float(amounts.mean())
    std_value = float(amounts.std(ddof=0))
    adjusted_std = std_value if std_value > 1e-9 else 1.0
    anomalies = ((amounts - mean_value).abs() / adjusted_std) >= 3.0
    threshold = float(amounts.quantile(0.99)) if len(amounts) > 1 else float(amounts.max())
    suspicious = anomalies | (amounts >= threshold)
    aml_alerts = prepared["flow_label"].str.lower().str.contains("cash|crypto|offshore|sanction|aml", regex=True)
    compliance = 100.0 - _safe_ratio(float(anomalies.sum()), float(len(prepared))) * 100

    scatter = prepared.copy()
    scatter["status"] = np.where(suspicious, "Suspecte", "Normale")
    scatter_fig = px.scatter(
        scatter,
        x="date_value",
        y="amount_value",
        color="status",
        title="Transactions suspectes",
        labels={"date_value": "Date", "amount_value": "Montant"},
    )
    style_figure(scatter_fig)

    by_region = scatter.copy()
    by_region["alerts"] = np.where(suspicious | aml_alerts, 1, 0)
    by_region = by_region.groupby("region_label", as_index=False)["alerts"].sum()
    aml_table = pd.DataFrame(
        {"categorie": ["Alertes AML", "Anomalies"], "value": [int(aml_alerts.sum()), int(anomalies.sum())]}
    )
    cards = (
        ("Transactions suspectes", str(int(suspicious.sum()))),
        ("Anomalies", str(int(anomalies.sum()))),
        ("Alertes AML", str(int(aml_alerts.sum()))),
        ("Conformite", _format_percent(compliance)),
        ("Taux de fraude", _format_percent(_safe_ratio(float(suspicious.sum()), float(len(prepared))) * 100)),
        ("Seuil critique", format_currency(threshold)),
    )
    figures = (
        scatter_fig,
        create_numeric_figure(
            by_region.rename(columns={"region_label": "region", "alerts": "value"}),
            x_column="region",
            y_column="value",
            chart_type=numeric_chart_type,
            title="Alertes par region",
        ),
        create_distribution_figure(aml_table, "categorie", "value", distribution_chart_type, "Alertes AML vs anomalies"),
    )
    return DashboardBundle("Dashboard Fraude & Conformite", "Monitoring des anomalies et alertes AML.", cards, figures)


def _trading_bundle(
    prepared: pd.DataFrame,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 11: trading."""
    ordered = prepared.sort_values("date_value").reset_index(drop=True)
    ordered["pnl"] = ordered["amount_value"].cumsum()
    volume_col = _find_optional_column(ordered, OPTIONAL_ALIASES["volume"])
    if volume_col:
        ordered["volume_value"] = pd.to_numeric(ordered[volume_col], errors="coerce").fillna(0.0)
    else:
        ordered["volume_value"] = 1.0
    monthly_volume = _monthly_sum(ordered, "volume_value").rename(columns={"volume_value": "value"})
    monthly_pnl = _monthly_sum(ordered, "amount_value").rename(columns={"amount_value": "value"})
    price_col = _find_optional_column(ordered, OPTIONAL_ALIASES["price"])
    if price_col:
        prices = pd.to_numeric(ordered[price_col], errors="coerce").fillna(0.0)
    else:
        prices = ordered["abs_amount"]
    spreads = float(prices.diff().abs().fillna(0.0).mean())

    cards = (
        ("PnL", format_currency(float(ordered["pnl"].iloc[-1]))),
        ("Volume", format_currency(float(monthly_volume["value"].sum()))),
        ("Spreads", format_currency(spreads)),
        ("Positions ouvertes", str(int((ordered["amount_value"] > 0).sum()))),
        ("Transactions", str(int(len(ordered)))),
        ("Regions actives", str(int(ordered["region_label"].nunique()))),
    )
    figures = (
        create_numeric_figure(
            ordered,
            x_column="date_value",
            y_column="pnl",
            chart_type="Ligne",
            title="PnL cumule",
        ),
        create_numeric_figure(
            monthly_volume,
            x_column="month_label",
            y_column="value",
            chart_type=numeric_chart_type,
            title="Volume mensuel",
        ),
        create_distribution_figure(monthly_pnl.assign(month=monthly_pnl["month_label"]), "month", "value", distribution_chart_type, "Repartition du PnL"),
    )
    return DashboardBundle("Dashboard Trading", "Suivi PnL, volume, spreads et positions.", cards, figures)


def _banking_bundle(
    prepared: pd.DataFrame,
    revenue: float,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> DashboardBundle:
    """Dashboard 12: performance bancaire."""
    equity = max(_optional_total(prepared, "equity", revenue * 0.45), 1.0)
    assets = max(_optional_total(prepared, "assets", revenue * 1.4), 1.0)
    outflow = float(prepared.loc[prepared["direction"] == "Outflow", "abs_amount"].sum())
    liquidity_base = max(outflow * 0.30, 1.0)
    cash_available = float(prepared["amount_value"].sum())
    solvency = _safe_ratio(equity, assets) * 100
    liquidity = _safe_ratio(max(cash_available, 0.0), liquidity_base) * 100
    loan_mask = prepared["flow_label"].str.lower().str.contains("loan|pret|credit", regex=True)
    active_loans = int(loan_mask.sum())
    default_col = _find_optional_column(prepared, OPTIONAL_ALIASES["default_flag"])
    if default_col:
        defaults = int((pd.to_numeric(prepared[default_col], errors="coerce").fillna(0.0) > 0).sum())
    else:
        defaults = int((loan_mask & (prepared["amount_value"] < 0)).sum())
    default_rate = _safe_ratio(float(defaults), float(max(active_loans, 1))) * 100

    ratios = pd.DataFrame(
        {"metric": ["Ratio de solvabilite", "Ratio de liquidite", "Taux de defaut"], "value": [solvency, liquidity, default_rate]}
    )
    by_region = prepared.assign(active=np.where(loan_mask, 1, 0), default=np.where(loan_mask & (prepared["amount_value"] < 0), 1, 0))
    by_region = by_region.groupby("region_label", as_index=False)[["active", "default"]].sum()
    by_region = by_region.melt(id_vars="region_label", value_vars=["active", "default"], var_name="metric", value_name="value")

    cards = (
        ("Ratio de solvabilite", _format_percent(solvency)),
        ("Ratio de liquidite", _format_percent(liquidity)),
        ("Prets actifs", str(active_loans)),
        ("Taux de defaut", _format_percent(default_rate)),
        ("Cash disponible", format_currency(cash_available)),
        ("Defauts detectes", str(defaults)),
    )
    figures = (
        create_numeric_figure(
            ratios,
            x_column="metric",
            y_column="value",
            chart_type=numeric_chart_type,
            title="Ratios bancaires",
        ),
        create_numeric_figure(
            by_region,
            x_column="region_label",
            y_column="value",
            chart_type="Barres",
            title="Prets actifs vs defauts",
            color_column="metric",
        ),
        create_distribution_figure(pd.DataFrame({"categorie": ["Prets actifs", "Defauts"], "value": [active_loans, defaults]}), "categorie", "value", distribution_chart_type, "Repartition prets/defauts"),
    )
    return DashboardBundle("Dashboard de Performance Bancaire", "Suivi solvabilite, liquidite, prets et defauts.", cards, figures)


def _prepare_frame(dataframe: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Standard frame used by all dashboard variants."""
    prepared = dataframe.copy()
    prepared["amount_value"] = pd.to_numeric(prepared[mapping.amount], errors="coerce").fillna(0.0)
    prepared["date_value"] = pd.to_datetime(prepared[mapping.date], errors="coerce")
    if prepared["date_value"].notna().any():
        first_valid_date = prepared["date_value"].dropna().iloc[0]
    else:
        first_valid_date = pd.Timestamp.today().normalize()
    prepared["date_value"] = prepared["date_value"].fillna(first_valid_date)
    prepared["month_label"] = prepared["date_value"].dt.to_period("M").astype(str)
    prepared["flow_label"] = prepared[mapping.flow].astype("string").fillna("Flux non classe").astype(str)
    prepared["region_label"] = prepared[mapping.region].astype("string").fillna("Inconnue").astype(str)
    prepared["product_label"] = _get_dimension_column(prepared, "product", fallback="flow_label")
    prepared["abs_amount"] = prepared["amount_value"].abs()
    prepared["direction"] = _derive_direction(prepared["amount_value"], prepared["flow_label"])
    return prepared


def _find_optional_column(dataframe: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    """Find optional column by exact or fuzzy alias."""
    columns = list(dataframe.columns)
    for alias in aliases:
        if alias in columns:
            return alias
    for alias in aliases:
        for column_name in columns:
            if alias in column_name:
                return column_name
    return None


def _get_dimension_column(dataframe: pd.DataFrame, key: str, fallback: str) -> pd.Series:
    """Extract a text dimension column, with fallback."""
    optional_column = _find_optional_column(dataframe, OPTIONAL_ALIASES[key])
    if optional_column:
        return dataframe[optional_column].astype("string").fillna("Non classe").astype(str)
    return dataframe[fallback].astype("string").fillna("Non classe").astype(str)


def _optional_total(dataframe: pd.DataFrame, key: str, fallback: float) -> float:
    """Get numeric total from optional column or fallback value."""
    optional_column = _find_optional_column(dataframe, OPTIONAL_ALIASES[key])
    if optional_column is None:
        return float(fallback)
    values = pd.to_numeric(dataframe[optional_column], errors="coerce").fillna(0.0)
    return float(values.sum())


def _estimate_revenue(dataframe: pd.DataFrame) -> float:
    """Estimate revenue from dedicated column or positive amounts."""
    optional_column = _find_optional_column(dataframe, OPTIONAL_ALIASES["revenue"])
    if optional_column:
        values = pd.to_numeric(dataframe[optional_column], errors="coerce").fillna(0.0)
        return float(values.sum())
    positive_sum = float(dataframe.loc[dataframe["amount_value"] > 0, "amount_value"].sum())
    return positive_sum if positive_sum > 0 else float(dataframe["abs_amount"].sum())


def _derive_direction(amount_series: pd.Series, flow_series: pd.Series) -> pd.Series:
    """Infer Inflow/Outflow class from sign and flow labels."""
    outflow_pattern = "debit|sortie|outflow|expense|depense|paiement|withdraw|achat"
    flow_text = flow_series.astype("string").str.lower()
    is_outflow = (amount_series < 0) | flow_text.str.contains(outflow_pattern, regex=True)
    return pd.Series(np.where(is_outflow, "Outflow", "Inflow"), index=amount_series.index)


def _monthly_sum(dataframe: pd.DataFrame, value_column: str) -> pd.DataFrame:
    """Aggregate one numeric column by month."""
    return dataframe.groupby("month_label", as_index=False)[value_column].sum().sort_values("month_label").reset_index(drop=True)


def _monthly_positive(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate positive cash amounts by month."""
    source = dataframe.copy()
    source["value"] = source["amount_value"].clip(lower=0)
    return _monthly_sum(source, "value")


def _direction_mix(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate direction mix for composition charts."""
    return dataframe.groupby("direction", as_index=False)["abs_amount"].sum().rename(columns={"abs_amount": "value"})


def _region_mix(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate exposure by region."""
    return dataframe.groupby("region_label", as_index=False)["abs_amount"].sum().rename(columns={"abs_amount": "value"})


def _product_mix(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate performance by product/service."""
    table = dataframe.groupby("product_label", as_index=False)["amount_value"].sum().rename(columns={"product_label": "product", "amount_value": "value"})
    table["allocation"] = table["value"].abs()
    return table


def _credit_risk(dataframe: pd.DataFrame) -> float:
    """Estimate credit-risk share from flow labels."""
    ratio = _safe_ratio(float(dataframe["flow_label"].str.lower().str.contains("credit|loan|pret", regex=True).sum()), float(len(dataframe)))
    return ratio * 100


def _latest_growth(series: pd.Series) -> float:
    """Return latest percentage growth from an ordered series."""
    numeric_series = pd.Series(pd.to_numeric(series, errors="coerce"), dtype="float64")
    growth = numeric_series.fillna(0.0).pct_change().fillna(0.0) * 100.0
    return float(growth.iloc[-1]) if not growth.empty else 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    """Safe division helper for ratios."""
    if abs(denominator) < 1e-9:
        return 0.0
    return float(numerator / denominator)


def _format_percent(value: float) -> str:
    """Format percentage with one decimal."""
    return f"{value:.1f}%"


def _format_runway(value: float) -> str:
    """Format runway expressed in months."""
    if np.isinf(value):
        return "Stable (>12 mois)"
    return f"{value:.1f} mois"
