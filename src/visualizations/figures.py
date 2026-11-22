"""Generate all publication-grade figures (PDF + PNG) directly from processed data and result tables."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.2,
    "figure.titlesize": 11.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
})

PALETTE = {
    "blue": "#0072B2",
    "orange": "#D55E00",
    "green": "#009E73",
    "purple": "#CC79A7",
    "amber": "#E69F00",
    "navy": "#1B365D",
    "slate": "#5C6B73",
}


def _save_fig(fig: plt.Figure, out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(out_dir / f"{name}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)


def plot_coverage_and_regimes(root: Path, out_dir: Path) -> None:
    cov = pd.read_csv(root / "data" / "source_coverage_matrix.csv")
    # Pick representative primary instruments
    keep = [
        ("Bank Indonesia", "JISDOR", "1d (business days)", "BI JISDOR (USD/IDR Official)"),
        ("Indodax", "BTCIDR", "5m", "Indodax BTC/IDR (5m & 1D)"),
        ("Indodax", "USDTIDR", "5m", "Indodax USDT/IDR (5m & 1D)"),
        ("Indodax", "ETHIDR", "5m", "Indodax ETH/IDR (5m & 1D)"),
        ("Indodax", "XRPIDR", "5m", "Indodax XRP/IDR (5m & 1D)"),
        ("Indodax", "BTCUSDT", "5m", "Indodax BTC/USDT (5m & 1D)"),
        ("Binance Spot", "BTCUSDT", "5m", "Binance BTC/USDT (5m & 1D)"),
        ("Binance Spot", "BTCBIDR", "5m", "Binance BTC/BIDR (Delisted May 2024)"),
        ("Binance Spot", "BTCIDR", "5m", "Binance BTC/IDR (Launched Nov 2025)"),
        ("Binance Spot", "USDCUSDT", "5m", "Binance USDC/USDT (Mar 2023 Suspension Gap)"),
        ("Coinbase", "USDT-USD", "1h", "Coinbase USDT/USD (1h & 1D)"),
        ("Kraken", "USDTUSD", "1d (720-bar cap)", "Kraken USDT/USD (720-bar API Cap)"),
    ]
    rows = []
    for ex, inst, freq_prefix, label in keep:
        m = cov[(cov["exchange"] == ex) & (cov["instrument"] == inst) & (cov["frequency"].str.startswith(freq_prefix[:2]))]
        if m.empty:
            continue
        r = m.iloc[0]
        rows.append({
            "label": label,
            "start": pd.to_datetime(str(r["first_timestamp"])[:10]),
            "end": pd.to_datetime(str(r["last_timestamp"])[:10]),
            "rows": int(r["rows_retrieved"]),
        })

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    y_pos = np.arange(len(rows))[::-1]
    for y, item in zip(y_pos, rows):
        width_days = (item["end"] - item["start"]).days
        color = PALETTE["orange"] if "Delisted" in item["label"] or "Cap" in item["label"] else PALETTE["blue"]
        ax.barh(y, width_days, left=mdates.date2num(item["start"]), height=0.58, color=color, alpha=0.85)
        ax.text(
            mdates.date2num(item["end"]) + 15, y,
            f"n={item['rows']:,}", va="center", fontsize=7.5, color="#222222"
        )

    events = [
        ("2022-05-01", "PMK 68/2022"),
        ("2024-11-01", "CFX Launch"),
        ("2025-01-10", "OJK Shift"),
        ("2025-08-01", "PMK 50/2025"),
        ("2026-04-01", "PADG 7/2026"),
    ]
    for dt_s, lbl in events:
        xval = mdates.date2num(pd.to_datetime(dt_s))
        ax.axvline(xval, color=PALETTE["slate"], linestyle=":", linewidth=1.0, alpha=0.75)
        ax.text(xval + 12, len(rows) - 0.25, lbl, rotation=22, fontsize=7.0, ha="left", va="bottom", color=PALETTE["navy"])

    ax.set_yticks(y_pos)
    ax.set_yticklabels([r["label"] for r in rows])
    ax.set_ylim(-0.6, len(rows) + 1.35)
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(mdates.date2num(pd.to_datetime("2020-11-01")), mdates.date2num(pd.to_datetime("2027-07-01")))
    ax.set_title("Historical Data Coverage Matrix and Indonesian Regulatory Milestones (2021-2026)", pad=10)
    ax.set_xlabel("Date (UTC)")
    _save_fig(fig, out_dir, "fig1_coverage_and_regimes")


def plot_synchronized_prices(root: Path, out_dir: Path) -> None:
    btc = pd.read_csv(root / "data" / "processed" / "btc_jisdor_sync_primary.csv")
    btc["dt"] = pd.to_datetime(btc["date"])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.2, 6.2), sharex=True)
    ax1.plot(btc["dt"], btc["indodax_close"] / 1e6, label="Indodax BTC/IDR (Million IDR)", color=PALETTE["blue"], lw=1.25)
    ax1.plot(btc["dt"], (btc["binance_close"] * btc["jisdor_idr_usd"]) / 1e6,
             label="Binance BTC/USDT x BI JISDOR (Million IDR)", color=PALETTE["orange"], lw=1.0, ls="--")
    ax1.set_ylabel("BTC Price (Million IDR)")
    ax1.set_title("(a) Synchronized Domestic BTC/IDR vs. JISDOR-Converted Global BTC/USDT (n = 1,414 Business Days)")
    ax1.legend(loc="upper left", frameon=False)

    ax2.plot(btc["dt"], btc["usdtidr_close"], label="Indodax USDT/IDR (Synced)", color=PALETTE["green"], lw=1.15)
    ax2.plot(btc["dt"], btc["jisdor_idr_usd"], label="Bank Indonesia JISDOR (USD/IDR)", color=PALETTE["navy"], lw=1.1, ls="--")
    ax2.set_ylabel("Exchange Rate (IDR per Unit)")
    ax2.set_title("(b) Local Stablecoin Exchange Rate (USDT/IDR) vs. Official BI JISDOR Benchmark (USD/IDR)")
    ax2.legend(loc="upper left", frameon=False)

    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.tight_layout()
    _save_fig(fig, out_dir, "fig2_synchronized_prices")


def plot_basis_decomposition(root: Path, out_dir: Path) -> None:
    btc = pd.read_csv(root / "data" / "processed" / "btc_jisdor_sync_primary.csv")
    btc["dt"] = pd.to_datetime(btc["date"])
    from src.fees.fee_schedule import lookup_costs_for_dates
    costs = lookup_costs_for_dates(btc["date"])
    taker_band = costs["route_a_domestic_2leg_taker_bps"].values
    maker_band = costs["route_a_domestic_2leg_maker_bps"].values

    var_info = json.loads((root / "results" / "models" / "variance_decomposition.json").read_text())["BTC"]

    fig = plt.figure(figsize=(9.5, 7.6))
    gs = fig.add_gridspec(4, 1, height_ratios=[1, 1, 1, 0.72], hspace=0.42)

    ax1 = fig.add_subplot(gs[0])
    ax1.plot(btc["dt"], btc["b_total_bps"], color=PALETTE["navy"], lw=0.85)
    ax1.axhline(0, color="black", lw=0.6)
    ax1.set_title(f"(a) Total BTC Basis vs. BI JISDOR ($B_t^{{total}}$): Mean = {btc['b_total_bps'].mean():.2f} bps, SD = {btc['b_total_bps'].std(ddof=1):.2f} bps")
    ax1.set_ylabel("bps")

    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.fill_between(btc["dt"], -taker_band, taker_band, color=PALETTE["amber"], alpha=0.18, label="Route A Taker Cost Band")
    ax2.fill_between(btc["dt"], -maker_band, maker_band, color=PALETTE["green"], alpha=0.16, label="Route A Maker Cost Band")
    ax2.plot(btc["dt"], btc["b_crypto_bps"], color=PALETTE["blue"], lw=0.75, label="$B_t^{crypto}$")
    ax2.axhline(0, color="black", lw=0.6)
    ax2.set_title(f"(b) Pure Crypto Basis ($B_t^{{crypto}}$) vs. Dynamic Statutory Cost Bands: Mean = {btc['b_crypto_bps'].mean():.2f} bps, SD = {btc['b_crypto_bps'].std(ddof=1):.2f} bps")
    ax2.set_ylabel("bps")
    ax2.legend(loc="upper right", ncol=3, frameon=False)

    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.plot(btc["dt"], btc["b_stablecoin_fx_bps"], color=PALETTE["orange"], lw=0.85)
    ax3.axhline(0, color="black", lw=0.6)
    ax3.set_title(f"(c) Stablecoin-FX Basis ($B_t^{{stablecoin-FX}}$ = USDT/IDR minus JISDOR): Mean = {btc['b_stablecoin_fx_bps'].mean():.2f} bps, SD = {btc['b_stablecoin_fx_bps'].std(ddof=1):.2f} bps")
    ax3.set_ylabel("bps")
    ax3.xaxis.set_major_locator(mdates.YearLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax4 = fig.add_subplot(gs[3])
    cov_share = 100.0 - var_info["gross_share_crypto_pct"] - var_info["gross_share_sf_pct"]
    labels = ["$Var(B^{crypto})$", "$Var(B^{stablecoin-FX})$", "$2\\,Cov(B^{crypto}, B^{stablecoin-FX})$"]
    vals = [var_info["gross_share_crypto_pct"], var_info["gross_share_sf_pct"], cov_share]
    colors = [PALETTE["blue"], PALETTE["orange"], PALETTE["purple"]]
    bars = ax4.barh(labels, vals, color=colors, height=0.55)
    for b, v in zip(bars, vals):
        ax4.text(v + 1.0, b.get_y() + b.get_height() / 2, f"{v:.2f}%", va="center", fontsize=8.5)
    ax4.set_xlim(0, 100)
    ax4.set_xlabel("Percentage of Total Variance ($Var(B^{total}) = 6,529.03\\text{ bps}^2$)")
    ax4.set_title("(d) Exact Algebraic Variance Decomposition of Total BTC Basis")

    _save_fig(fig, out_dir, "fig3_basis_decomposition")


def plot_basis_distributions(root: Path, out_dir: Path) -> None:
    btc = pd.read_csv(root / "data" / "processed" / "btc_jisdor_sync_primary.csv")
    eth = pd.read_csv(root / "data" / "processed" / "eth_jisdor_sync_primary.csv")
    xrp = pd.read_csv(root / "data" / "processed" / "xrp_jisdor_sync_primary.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 4.0))
    bins = np.linspace(-200, 350, 75)
    ax1.hist(btc["b_total_bps"].clip(-200, 350), bins=bins, density=True, alpha=0.45, color=PALETTE["navy"], label="$B^{total}$ (vs. JISDOR)")
    ax1.hist(btc["b_stablecoin_fx_bps"].clip(-200, 350), bins=bins, density=True, alpha=0.45, color=PALETTE["orange"], label="$B^{stablecoin-FX}$")
    ax1.hist(btc["b_crypto_bps"].clip(-200, 350), bins=bins, density=True, alpha=0.55, color=PALETTE["blue"], label="$B^{crypto}$ (USDT-Converted)")
    ax1.axvline(-62.11, color=PALETTE["green"], ls="--", lw=1.0, label="Oct 2026 Route A Taker Band (+/-62.1 bps)")
    ax1.axvline(62.11, color=PALETTE["green"], ls="--", lw=1.0)
    ax1.set_title("(a) BTC Basis Component Distributions")
    ax1.set_xlabel("Basis (bps)")
    ax1.set_ylabel("Density")
    ax1.legend(loc="upper right", frameon=False, fontsize=7.5)

    for lbl, df, col in [("BTC", btc, PALETTE["blue"]), ("ETH", eth, PALETTE["green"]), ("XRP", xrp, PALETTE["orange"])]:
        s = df["b_crypto_bps"].clip(-120, 120)
        ax2.hist(s, bins=60, density=True, histtype="step", lw=1.4, color=col, label=f"{lbl} (SD={df['b_crypto_bps'].std(ddof=1):.1f} bps)")
    ax2.axvline(-62.11, color=PALETTE["slate"], ls="--", lw=1.0, label="Route A Taker (+/-62.1 bps)")
    ax2.axvline(62.11, color=PALETTE["slate"], ls="--", lw=1.0)
    ax2.set_ylim(0, 0.0265)
    ax2.set_title("(b) Multi-Asset Pure Crypto Basis ($B^{crypto}$)")
    ax2.set_xlabel("Basis (bps)")
    ax2.legend(loc="upper right", frameon=True, facecolor="white", framealpha=0.92, edgecolor="none", fontsize=7.4)

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig4_basis_distributions")


def plot_rolling_dynamics(root: Path, out_dir: Path) -> None:
    btc = pd.read_csv(root / "data" / "processed" / "btc_jisdor_sync_primary.csv")
    btc["dt"] = pd.to_datetime(btc["date"])

    w = 60
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9.2, 6.8), sharex=True)
    ax1.plot(btc["dt"], btc["b_total_bps"].rolling(w).mean(), label="60d Rolling Mean: $B^{total}$", color=PALETTE["navy"], lw=1.2)
    ax1.plot(btc["dt"], btc["b_stablecoin_fx_bps"].rolling(w).mean(), label="60d Rolling Mean: $B^{stablecoin-FX}$", color=PALETTE["orange"], lw=1.1, ls="--")
    ax1.plot(btc["dt"], btc["b_crypto_bps"].rolling(w).mean(), label="60d Rolling Mean: $B^{crypto}$", color=PALETTE["blue"], lw=1.1)
    ax1.axhline(0, color="black", lw=0.6)
    ax1.set_ylabel("bps")
    ax1.set_title("(a) 60-Business-Day Rolling Mean of Basis Components")
    ax1.legend(loc="upper right", ncol=3, frameon=False, fontsize=7.8)

    ax2.plot(btc["dt"], btc["b_total_bps"].rolling(w).std(ddof=1), label="60d Rolling SD: $B^{total}$", color=PALETTE["navy"], lw=1.2)
    ax2.plot(btc["dt"], btc["b_stablecoin_fx_bps"].rolling(w).std(ddof=1), label="60d Rolling SD: $B^{stablecoin-FX}$", color=PALETTE["orange"], lw=1.1)
    ax2.plot(btc["dt"], btc["b_crypto_bps"].rolling(w).std(ddof=1), label="60d Rolling SD: $B^{crypto}$", color=PALETTE["blue"], lw=1.1)
    ax2.set_ylabel("bps")
    ax2.set_title("(b) 60-Business-Day Rolling Volatility (SD) of Basis Components")
    ax2.legend(loc="upper right", ncol=3, frameon=False, fontsize=7.8)

    rcorr = btc["b_crypto_bps"].rolling(w).corr(btc["b_stablecoin_fx_bps"])
    ax3.plot(btc["dt"], rcorr, color=PALETTE["purple"], lw=1.15)
    ax3.axhline(0, color="black", lw=0.6)
    ax3.axhline(btc["b_crypto_bps"].corr(btc["b_stablecoin_fx_bps"]), color=PALETTE["slate"], ls="--", lw=0.9,
                label=f"Full-Sample Correlation = {btc['b_crypto_bps'].corr(btc['b_stablecoin_fx_bps']):.3f}")
    ax3.set_ylim(-0.7, 0.7)
    ax3.set_ylabel("Corr")
    ax3.set_title("(c) 60-Business-Day Rolling Correlation Between $B^{crypto}$ and $B^{stablecoin-FX}$")
    ax3.legend(loc="upper right", frameon=False)
    ax3.xaxis.set_major_locator(mdates.YearLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig5_rolling_dynamics_and_corr")


def plot_cointegration_and_ec(root: Path, out_dir: Path) -> None:
    t3 = pd.read_csv(root / "results" / "tables" / "table3_cointegration_and_reconciliation.csv")
    t5 = pd.read_csv(root / "results" / "tables" / "table5_vecm_error_correction.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.8, 4.3))
    sub = t3[t3["specification"].str.contains("BTC_|ETH_|XRP_")].copy()
    short_names = [s.split(" (")[0].replace("_Converted", "").replace("_", " ") for s in sub["specification"]]
    y = np.arange(len(sub))[::-1]
    colors = [PALETTE["orange"] if "Unadjusted" in n else (PALETTE["blue"] if "JISDOR" in n or "SpotFX" in n else PALETTE["green"]) for n in short_names]
    ax1.barh(y, sub["trace_r0_ra"], color=colors, height=0.62, alpha=0.88)
    ax1.axvline(15.49, color="red", ls="--", lw=1.1, label="5% Critical Value (15.49)")
    ax1.set_xscale("log")
    ax1.set_yticks(y)
    ax1.set_yticklabels(short_names, fontsize=8)
    ax1.set_xlabel("Reinsel-Ahn Trace Statistic (Log Scale)")
    ax1.set_title("(a) Cointegration Rank ($H_0: r=0$) Across Conversion Specs")
    ax1.legend(loc="upper right", frameon=True, facecolor="white", framealpha=0.92, edgecolor="none", fontsize=8)

    systems = t5["system"].tolist()
    short_sys = [s.replace(" (Daily Bus. Days)", "").replace("vs ", "vs\n") for s in systems]
    x = np.arange(len(t5))
    w = 0.36
    ax2.bar(x - w/2, -t5["alpha_local_hac"], yerr=1.96 * t5["alpha_local_hac_se"], width=w,
            color=PALETTE["blue"], capsize=3, label="Local Speed $-\\alpha_{local}$ (HAC 95% CI)")
    ax2.bar(x + w/2, t5["alpha_global_hac"], yerr=1.96 * t5["alpha_global_hac_se"], width=w,
            color=PALETTE["orange"], capsize=3, label="Global Speed $\\alpha_{global}$ (HAC 95% CI)")
    ax2.axhline(0, color="black", lw=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(short_sys, rotation=28, ha="right", fontsize=7.2)
    ax2.set_ylim(-1.25, 2.35)
    ax2.set_ylabel("Error-Correction Coefficient")
    ax2.set_title("(b) Daily VECM Adjustment Speeds (Local vs. Global)")
    ax2.legend(loc="upper right", frameon=True, facecolor="white", framealpha=0.92, edgecolor="none", fontsize=7.8)

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig6_cointegration_and_ec")


def plot_regulatory_and_costs(root: Path, out_dir: Path) -> None:
    fee = pd.read_csv(root / "results" / "tables" / "historical_fee_reconstruction.csv")
    ev = pd.read_csv(root / "results" / "tables" / "table7_regulatory_event_windows.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.8, 4.4))
    # Build step series across fee regimes
    dates = []
    ra_t, ra_m, rb_t = [], [], []
    for _, r in fee.iterrows():
        dates.extend([pd.to_datetime(r["start_date"]), pd.to_datetime(r["end_date"])])
        ra_t.extend([r["route_a_domestic_2leg_taker_bps"], r["route_a_domestic_2leg_taker_bps"]])
        ra_m.extend([r["route_a_domestic_2leg_maker_bps"], r["route_a_domestic_2leg_maker_bps"]])
        rb_t.extend([r["route_b_cross_3leg_taker_bps"], r["route_b_cross_3leg_taker_bps"]])

    ax1.plot(dates, rb_t, color=PALETTE["orange"], lw=1.5, label="Route B Cross 3-Leg (Taker)")
    ax1.plot(dates, ra_t, color=PALETTE["blue"], lw=1.5, label="Route A Domestic 2-Leg (Taker)")
    ax1.plot(dates, ra_m, color=PALETTE["green"], lw=1.4, ls="--", label="Route A Domestic 2-Leg (Maker)")
    ax1.set_ylabel("Round-Trip Statutory Fee + Tax (bps)")
    ax1.set_title("(a) Reconstructed Indonesian Crypto Transaction-Cost Regimes")
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.set_ylim(-5, 100)
    ax1.legend(loc="lower right", frameon=True, framealpha=0.92, edgecolor="none", fontsize=7.6)

    ev_c = ev[ev["basis_leg"] == "B_crypto"].reset_index(drop=True)
    ev_s = ev[ev["basis_leg"] == "B_stablecoin_FX"].reset_index(drop=True)
    y = np.arange(len(ev_c))[::-1]
    h = 0.35
    ax2.barh(y + h/2, ev_c["diff_mean_bps"], height=h, color=PALETTE["blue"], alpha=0.88, label="$\\Delta \\bar{B}^{crypto}$ (Post - Pre)")
    ax2.barh(y - h/2, ev_s["diff_mean_bps"], height=h, color=PALETTE["orange"], alpha=0.88, label="$\\Delta \\bar{B}^{stablecoin-FX}$ (Post - Pre)")
    ax2.axvline(0, color="black", lw=0.7)
    ax2.set_yticks(y)
    ax2.set_yticklabels([f"{r['event_date']} {r['label'].split('(')[0].strip()}" for _, r in ev_c.iterrows()], fontsize=7.3)
    ax2.set_xlabel("30-Day Post minus Pre Mean Change (bps)")
    ax2.set_title("(b) Event-Window Basis Shifts Around Institutional Events")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.92, edgecolor="none", fontsize=7.6)

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig7_regulatory_and_costs")


def plot_robustness_and_orderbook(root: Path, out_dir: Path) -> None:
    t8 = pd.read_csv(root / "results" / "tables" / "table8_synchronization_sensitivity.csv")
    rc = pd.read_csv(root / "results" / "tables" / "route_specific_execution_costs.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.8, 4.3))
    y = np.arange(len(t8))[::-1]
    h = 0.36
    ax1.barh(y + h/2, t8["sd_b_total_bps"], height=h, color=PALETTE["navy"], label="$SD(B^{total})$")
    ax1.barh(y - h/2, t8["sd_b_crypto_bps"], height=h, color=PALETTE["blue"], label="$SD(B^{crypto})$")
    ax1.set_yticks(y)
    ax1.set_yticklabels([s.replace("_", " ") for s in t8["specification"]], fontsize=7.8)
    ax1.set_xlabel("Dispersion (SD in bps)")
    ax1.set_title("(a) Synchronization & FX Sensitivity", fontsize=9.5)
    ax1.legend(loc="lower right", frameon=True, facecolor="white", framealpha=0.92, edgecolor="none", fontsize=7.8)

    routes_short = {
        "Route A: Domestic 2-Leg (Sell BTC/IDR + Buy USDT/IDR on Indodax)": "Route A (Domestic 2-Leg)",
        "Route B: Cross-Exchange 3-Leg (Indodax BTC/IDR + USDT/IDR + Binance BTC/USDT)": "Route B (Cross 3-Leg)",
        "Route C: Same-Exchange Indodax (BTC/IDR + USDT/IDR + Indodax BTC/USDT)": "Route C (Indodax BTC/USDT)",
    }
    rc["rshort"] = rc["route"].map(routes_short)
    sizes = ["1k", "10k", "50k"]
    x = np.arange(3)
    w = 0.25
    for idx, sz in enumerate(sizes):
        sub = rc[rc["trade_size_usd"] == sz]
        ax2.bar(x + (idx - 1) * w, sub["all_in_taker_plus_slip_bps"], width=w,
                color=[PALETTE["blue"], PALETTE["orange"], PALETTE["purple"]][idx], label=f"Size ${sz}")
    ax2.set_xticks(x)
    ax2.set_xticklabels(["Route A\n(Domestic 2-Leg)", "Route B\n(Cross 3-Leg)", "Route C\n(Indodax BTC/USDT)"], fontsize=8.2)
    ax2.set_ylabel("All-In Taker Fee + Tax + Depth Slippage (bps)")
    ax2.set_title("(b) Live Execution Cost Thresholds (Nov 2026)", fontsize=9.5)
    ax2.legend(loc="upper left", frameon=False, fontsize=8)

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig8_robustness_and_orderbook")


def generate_all_figures(root: Path) -> List[str]:
    out_dir = root / "manuscript" / "figures"
    plot_coverage_and_regimes(root, out_dir)
    plot_synchronized_prices(root, out_dir)
    plot_basis_decomposition(root, out_dir)
    plot_basis_distributions(root, out_dir)
    plot_rolling_dynamics(root, out_dir)
    plot_cointegration_and_ec(root, out_dir)
    plot_regulatory_and_costs(root, out_dir)
    plot_robustness_and_orderbook(root, out_dir)
    return sorted(p.name for p in out_dir.glob("*.pdf"))
