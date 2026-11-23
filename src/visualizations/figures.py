"""Generate all publication-grade figures (PDF + PNG) directly from processed data and result tables.

All figures are designed at 6.8 in width with >=10 pt source fonts, generous
padding, grayscale-safe line styles/hatching, and non-overlapping legends.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10.5,
    "axes.titlesize": 10.8,
    "axes.labelsize": 10.5,
    "xtick.labelsize": 9.8,
    "ytick.labelsize": 9.8,
    "legend.fontsize": 9.5,
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
    fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight", pad_inches=0.16, dpi=300)
    fig.savefig(out_dir / f"{name}.png", bbox_inches="tight", pad_inches=0.16, dpi=300)
    plt.close(fig)


def plot_coverage_and_regimes(root: Path, out_dir: Path) -> None:
    cov = pd.read_csv(root / "data" / "source_coverage_matrix.csv")
    keep = [
        ("Bank Indonesia", "JISDOR", "1d", "BI JISDOR (USD/IDR)"),
        ("Indodax", "BTCIDR", "5m", "Indodax BTC/IDR (5m)"),
        ("Indodax", "USDTIDR", "5m", "Indodax USDT/IDR (5m)"),
        ("Indodax", "ETHIDR", "5m", "Indodax ETH/IDR (5m)"),
        ("Indodax", "XRPIDR", "5m", "Indodax XRP/IDR (5m)"),
        ("Indodax", "BTCUSDT", "5m", "Indodax BTC/USDT (5m)"),
        ("Binance Spot", "BTCUSDT", "5m", "Binance BTC/USDT (5m)"),
        ("Binance Spot", "BTCBIDR", "5m", "Binance BTC/BIDR (delisted)"),
        ("Binance Spot", "BTCIDR", "5m", "Binance BTC/IDR (Nov 2025+)"),
        ("Binance Spot", "USDCUSDT", "5m", "Binance USDC/USDT (5m)"),
        ("Coinbase", "USDT-USD", "1h", "Coinbase USDT/USD (1h)"),
        ("Kraken", "USDTUSD", "1d", "Kraken USDT/USD (1d cap)"),
    ]
    rows = []
    for ex, inst, freq_prefix, label in keep:
        m = cov[(cov["exchange"] == ex) & (cov["instrument"] == inst) & (cov["frequency"].astype(str).str.lower().str.startswith(freq_prefix.lower()))]
        if m.empty:
            m = cov[(cov["exchange"] == ex) & (cov["instrument"] == inst)]
        if m.empty:
            continue
        r = m.iloc[0]
        rows.append({
            "label": label,
            "start": pd.to_datetime(str(r["first_timestamp"])[:10]),
            "end": pd.to_datetime(str(r["last_timestamp"])[:10]),
            "rows": int(r["rows_retrieved"]),
        })

    fig, ax = plt.subplots(figsize=(6.8, 5.8))
    y_pos = np.arange(len(rows))[::-1]
    for y, item in zip(y_pos, rows):
        width_days = (item["end"] - item["start"]).days
        is_partial = ("delisted" in item["label"] or "cap" in item["label"] or "Nov 2025" in item["label"])
        color = PALETTE["orange"] if is_partial else PALETTE["blue"]
        hatch = "///" if is_partial else None
        ax.barh(y, width_days, left=mdates.date2num(item["start"]), height=0.60,
                color=color, hatch=hatch, edgecolor="white" if not is_partial else "#7A3000", linewidth=0.5, alpha=0.88)
        ax.text(
            mdates.date2num(item["end"]) + 28, y,
            f"n={item['rows']:,}", va="center", fontsize=9.2, color="#222222"
        )

    events = [
        ("2022-05-01", "PMK 68", 0.0, "center", 0),
        ("2024-11-01", "CFX", 0.0, "right", -22),
        ("2025-01-10", "OJK", 0.92, "center", 0),
        ("2025-08-01", "PMK 50", 0.0, "left", 18),
        ("2026-04-01", "PADG 7", 0.92, "center", 0),
    ]
    for dt_s, lbl, y_off, ha, x_off in events:
        xval = mdates.date2num(pd.to_datetime(dt_s))
        ax.axvline(xval, color=PALETTE["slate"], linestyle=":", linewidth=1.1, alpha=0.8)
        ax.text(xval + x_off, len(rows) - 0.15 + y_off, lbl, fontsize=9.2, ha=ha, va="bottom", color=PALETTE["navy"], fontweight="bold")

    ax.set_yticks(y_pos)
    ax.set_yticklabels([r["label"] for r in rows], fontsize=9.5)
    ax.set_ylim(-0.6, len(rows) + 1.8)
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(mdates.date2num(pd.to_datetime("2020-11-01")), mdates.date2num(pd.to_datetime("2028-02-01")))
    ax.set_title("Historical Data Coverage & Milestones (2021\u20132026)", fontsize=10.5, pad=10)
    ax.set_xlabel("Date (UTC)")
    p_full = mpatches.Patch(facecolor=PALETTE["blue"], alpha=0.88, label="Full / Active Span")
    p_part = mpatches.Patch(facecolor=PALETTE["orange"], hatch="///", edgecolor="#7A3000", alpha=0.88, label="Delisted / Late Launch / Capped")
    ax.legend(handles=[p_full, p_part], loc="lower left", ncol=2, frameon=True, facecolor="white", framealpha=0.95, edgecolor="none", fontsize=9.0)
    fig.tight_layout()
    _save_fig(fig, out_dir, "fig1_coverage_and_regimes")


def plot_synchronized_prices(root: Path, out_dir: Path) -> None:
    btc = pd.read_csv(root / "data" / "processed" / "btc_jisdor_sync_primary.csv")
    btc["dt"] = pd.to_datetime(btc["date"])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.8, 5.6), sharex=True)
    ax1.plot(btc["dt"], btc["indodax_close"] / 1e6, label="Indodax BTC/IDR", color=PALETTE["blue"], lw=1.6, alpha=0.85)
    ax1.plot(btc["dt"], (btc["binance_close"] * btc["jisdor_idr_usd"]) / 1e6,
             label="Binance BTC/USDT $\\times$ JISDOR", color=PALETTE["orange"], lw=1.1, ls="--")
    ax1.set_ylabel("BTC (Million IDR)")
    ax1.set_title("(a) Domestic BTC/IDR vs. JISDOR-Converted Global BTC", fontsize=10.2)
    ax1.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.9, edgecolor="none")

    ax2.plot(btc["dt"], btc["usdtidr_close"], label="Indodax USDT/IDR", color=PALETTE["green"], lw=1.4)
    ax2.plot(btc["dt"], btc["jisdor_idr_usd"], label="BI JISDOR (USD/IDR)", color=PALETTE["navy"], lw=1.1, ls="--")
    ax2.set_ylabel("IDR per Unit")
    ax2.set_title("(b) Local USDT/IDR vs. Official BI JISDOR", fontsize=10.2)
    ax2.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.9, edgecolor="none")

    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
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

    fig = plt.figure(figsize=(6.8, 8.0))
    gs = fig.add_gridspec(4, 1, height_ratios=[1, 1.15, 1, 0.85], hspace=0.58)

    ax1 = fig.add_subplot(gs[0])
    ax1.plot(btc["dt"], btc["b_total_bps"], color=PALETTE["navy"], lw=0.9)
    ax1.axhline(0, color="black", lw=0.6)
    ax1.set_title(f"(a) Total BTC Basis ($B_t^{{total}}$): Mean {btc['b_total_bps'].mean():.2f}, SD {btc['b_total_bps'].std(ddof=1):.2f} bps", fontsize=10.2)
    ax1.set_ylabel("bps")

    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.fill_between(btc["dt"], -taker_band, taker_band, color=PALETTE["amber"], alpha=0.22, label="Route A Taker")
    ax2.fill_between(btc["dt"], -maker_band, maker_band, color=PALETTE["green"], alpha=0.18, label="Route A Maker")
    ax2.plot(btc["dt"], btc["b_crypto_bps"], color=PALETTE["blue"], lw=0.8, label="$B_t^{crypto}$")
    ax2.axhline(0, color="black", lw=0.6)
    ax2.set_ylim(-270, 290)
    ax2.set_title(f"(b) Pure Crypto Basis ($B_t^{{crypto}}$): Mean {btc['b_crypto_bps'].mean():.2f}, SD {btc['b_crypto_bps'].std(ddof=1):.2f} bps", fontsize=10.2)
    ax2.set_ylabel("bps")
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=3, frameon=True, facecolor="white", framealpha=0.95, edgecolor="none", fontsize=9.2)

    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.plot(btc["dt"], btc["b_stablecoin_fx_bps"], color=PALETTE["orange"], lw=0.9)
    ax3.axhline(0, color="black", lw=0.6)
    ax3.set_title(f"(c) Stablecoin\u2013FX Basis ($B_t^{{s\\text{{-}}FX}}$): Mean {btc['b_stablecoin_fx_bps'].mean():.2f}, SD {btc['b_stablecoin_fx_bps'].std(ddof=1):.2f} bps", fontsize=10.2)
    ax3.set_ylabel("bps")
    ax3.xaxis.set_major_locator(mdates.YearLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax4 = fig.add_subplot(gs[3])
    cov_share = 100.0 - var_info["gross_share_crypto_pct"] - var_info["gross_share_sf_pct"]
    labels = ["$Var(B^{cry})$", "$Var(B^{s\\text{-}FX})$", "$2\\,Cov$"]
    vals = [var_info["gross_share_crypto_pct"], var_info["gross_share_sf_pct"], cov_share]
    colors = [PALETTE["blue"], PALETTE["orange"], PALETTE["purple"]]
    bars = ax4.barh(labels, vals, color=colors, height=0.58)
    for b, v in zip(bars, vals):
        ax4.text(v + 1.4, b.get_y() + b.get_height() / 2, f"{v:.2f}%", va="center", fontsize=9.8)
    ax4.set_xlim(0, 102)
    ax4.set_xlabel("Share of $\\mathrm{Var}(B^{total}) = 6,529.03\\text{ bps}^2$ (%)")
    ax4.set_title("(d) Exact Accounting Variance Decomposition (BTC)", fontsize=10.2)

    _save_fig(fig, out_dir, "fig3_basis_decomposition")


def plot_basis_distributions(root: Path, out_dir: Path) -> None:
    btc = pd.read_csv(root / "data" / "processed" / "btc_jisdor_sync_primary.csv")
    eth = pd.read_csv(root / "data" / "processed" / "eth_jisdor_sync_primary.csv")
    xrp = pd.read_csv(root / "data" / "processed" / "xrp_jisdor_sync_primary.csv")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.8, 6.2))
    bins = np.linspace(-180, 320, 65)
    ax1.hist(btc["b_total_bps"].clip(-180, 320), bins=bins, density=True, alpha=0.40, color=PALETTE["navy"], label="$B^{total}$ (vs. JISDOR)")
    ax1.hist(btc["b_stablecoin_fx_bps"].clip(-180, 320), bins=bins, density=True, alpha=0.40, color=PALETTE["orange"], label="$B^{s\\text{-}FX}$")
    ax1.hist(btc["b_crypto_bps"].clip(-180, 320), bins=bins, density=True, alpha=0.58, color=PALETTE["blue"], label="$B^{crypto}$")
    ax1.axvline(-62.11, color=PALETTE["green"], ls="--", lw=1.2, label="R6 Taker ($\\pm 62.1$ bps)")
    ax1.axvline(62.11, color=PALETTE["green"], ls="--", lw=1.2)
    ax1.set_title("(a) BTC Basis Component Distributions", fontsize=10.4)
    ax1.set_xlabel("Basis (bps)")
    ax1.set_ylabel("Density")
    ax1.legend(loc="upper right", frameon=True, facecolor="white", framealpha=0.92, edgecolor="none")

    for lbl, df, col, ls in [("BTC", btc, PALETTE["blue"], "-"), ("ETH", eth, PALETTE["green"], "--"), ("XRP", xrp, PALETTE["orange"], ":")]:
        s = df["b_crypto_bps"].clip(-120, 120)
        ax2.hist(s, bins=55, density=True, histtype="step", lw=1.6, ls=ls, color=col, label=f"{lbl} (SD={df['b_crypto_bps'].std(ddof=1):.1f} bps)")
    ax2.axvline(-62.11, color=PALETTE["slate"], ls="-.", lw=1.2, label="R6 Taker ($\\pm 62.1$ bps)")
    ax2.axvline(62.11, color=PALETTE["slate"], ls="-.", lw=1.2)
    ax2.set_ylim(0, 0.0255)
    ax2.set_title("(b) Multi-Asset Pure Crypto Basis ($B^{crypto}$)", fontsize=10.4)
    ax2.set_xlabel("Basis (bps)")
    ax2.set_ylabel("Density")
    ax2.legend(loc="upper right", frameon=True, facecolor="white", framealpha=0.92, edgecolor="none")

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig4_basis_distributions")


def plot_rolling_dynamics(root: Path, out_dir: Path) -> None:
    btc = pd.read_csv(root / "data" / "processed" / "btc_jisdor_sync_primary.csv")
    btc["dt"] = pd.to_datetime(btc["date"])

    w = 60
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(6.8, 7.0), sharex=True)
    ax1.plot(btc["dt"], btc["b_total_bps"].rolling(w).mean(), label="$B^{total}$", color=PALETTE["navy"], lw=1.4)
    ax1.plot(btc["dt"], btc["b_stablecoin_fx_bps"].rolling(w).mean(), label="$B^{s\\text{-}FX}$", color=PALETTE["orange"], lw=1.2, ls="--")
    ax1.plot(btc["dt"], btc["b_crypto_bps"].rolling(w).mean(), label="$B^{crypto}$", color=PALETTE["blue"], lw=1.2, ls=":")
    ax1.axhline(0, color="black", lw=0.6)
    ax1.set_ylabel("Mean (bps)")
    ax1.set_title("(a) 60-Business-Day Rolling Mean", fontsize=10.2, pad=6)
    ax1.legend(loc="upper right", ncol=3, frameon=True, facecolor="white", framealpha=0.95, edgecolor="none")

    ax2.plot(btc["dt"], btc["b_total_bps"].rolling(w).std(ddof=1), label="$B^{total}$", color=PALETTE["navy"], lw=1.4)
    ax2.plot(btc["dt"], btc["b_stablecoin_fx_bps"].rolling(w).std(ddof=1), label="$B^{s\\text{-}FX}$", color=PALETTE["orange"], lw=1.2, ls="--")
    ax2.plot(btc["dt"], btc["b_crypto_bps"].rolling(w).std(ddof=1), label="$B^{crypto}$", color=PALETTE["blue"], lw=1.2, ls=":")
    ax2.set_ylabel("SD (bps)")
    ax2.set_title("(b) 60-Business-Day Rolling Volatility (SD)", fontsize=10.2, pad=6)
    ax2.legend(loc="upper right", ncol=3, frameon=True, facecolor="white", framealpha=0.95, edgecolor="none")

    rcorr = btc["b_crypto_bps"].rolling(w).corr(btc["b_stablecoin_fx_bps"])
    ax3.plot(btc["dt"], rcorr, color=PALETTE["purple"], lw=1.3)
    ax3.axhline(0, color="black", lw=0.6)
    ax3.axhline(btc["b_crypto_bps"].corr(btc["b_stablecoin_fx_bps"]), color=PALETTE["slate"], ls="--", lw=1.0,
                label=f"Full-Sample Corr = {btc['b_crypto_bps'].corr(btc['b_stablecoin_fx_bps']):.3f}")
    ax3.set_ylim(-0.68, 0.65)
    ax3.set_ylabel("Corr")
    ax3.set_title("(c) 60-Business-Day Rolling Correlation ($B^{crypto}$ vs. $B^{s\\text{-}FX}$)", fontsize=10.2, pad=6)
    ax3.legend(loc="lower left", frameon=True, facecolor="white", framealpha=0.95, edgecolor="none")
    ax3.xaxis.set_major_locator(mdates.YearLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig5_rolling_dynamics_and_corr")


def plot_cointegration_and_ec(root: Path, out_dir: Path) -> None:
    t3 = pd.read_csv(root / "results" / "tables" / "table3_cointegration_and_reconciliation.csv")
    t5 = pd.read_csv(root / "results" / "tables" / "table5_vecm_error_correction.csv")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.8, 7.6))
    sub = t3[t3["specification"].str.contains("BTC_|ETH_|XRP_")].copy()
    short_names = [s.split(" (")[0].replace("_Converted", "").replace("_", " ") for s in sub["specification"]]
    y = np.arange(len(sub))[::-1]
    colors = [PALETTE["orange"] if "Unadjusted" in n else (PALETTE["blue"] if "JISDOR" in n or "SpotFX" in n else PALETTE["green"]) for n in short_names]
    hatches = ["///" if "Unadjusted" in n else (None if "JISDOR" in n or "SpotFX" in n else "...") for n in short_names]
    for yi, val, col, ht in zip(y, sub["trace_r0_ra"], colors, hatches):
        ax1.barh(yi, val, color=col, hatch=ht, edgecolor="white" if ht is None else "#333333", linewidth=0.4, height=0.62, alpha=0.88)
    ax1.axvline(15.49, color="red", ls="--", lw=1.2, label="5% Critical Value (15.49)")
    ax1.set_xscale("log")
    ax1.set_yticks(y)
    ax1.set_yticklabels(short_names, fontsize=9.5)
    ax1.set_xlabel("Reinsel\u2013Ahn Trace Statistic (Log Scale)")
    ax1.set_title("(a) Cointegration Rank ($H_0: r=0$) Across Conversion Specs", fontsize=10.2, pad=28)
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, 1.005), frameon=True, facecolor="white", framealpha=0.95, edgecolor="none")

    systems = t5["system"].tolist()
    short_sys = [
        s.replace(" (Daily Bus. Days)", "")
         .replace("Indodax USDT/IDR vs BI JISDOR", "USDT/IDR vs JISDOR")
         .replace("Indodax-USDT-Global", "USDT-Conv.")
         .replace("JISDOR-Global", "JISDOR")
        for s in systems
    ]
    y2 = np.arange(len(t5))[::-1]
    h = 0.36
    ax2.barh(y2 + h/2, -t5["alpha_local_hac"], xerr=1.96 * t5["alpha_local_hac_se"], height=h,
             color=PALETTE["blue"], capsize=3, label="Local Speed $-\\hat{\\alpha}_{local}$ (95% CI)")
    ax2.barh(y2 - h/2, t5["alpha_global_hac"], xerr=1.96 * t5["alpha_global_hac_se"], height=h,
             color=PALETTE["orange"], hatch="///", edgecolor="#7A3000", linewidth=0.4, capsize=3, label="Global Speed $\\hat{\\alpha}_{global}$ (95% CI)")
    ax2.axvline(0, color="black", lw=0.7)
    ax2.set_yticks(y2)
    ax2.set_yticklabels(short_sys, fontsize=9.5)
    ax2.set_xlabel("Daily VECM Error-Correction Coefficient (HAC)")
    ax2.set_title("(b) Daily VECM Adjustment Speeds (Local vs. Global)", fontsize=10.2, pad=30)
    ax2.legend(loc="lower center", bbox_to_anchor=(0.5, 1.005), ncol=2, frameon=True, facecolor="white", framealpha=0.95, edgecolor="none", fontsize=9.0)

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig6_cointegration_and_ec")


def plot_regulatory_and_costs(root: Path, out_dir: Path) -> None:
    fee = pd.read_csv(root / "results" / "tables" / "historical_fee_reconstruction.csv")
    ev = pd.read_csv(root / "results" / "tables" / "table7_regulatory_event_windows.csv")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.8, 7.6), gridspec_kw={"height_ratios": [0.95, 1.38]})
    dates = []
    ra_t, ra_m, rb_t = [], [], []
    for _, r in fee.iterrows():
        dates.extend([pd.to_datetime(r["start_date"]), pd.to_datetime(r["end_date"])])
        ra_t.extend([r["route_a_domestic_2leg_taker_bps"], r["route_a_domestic_2leg_taker_bps"]])
        ra_m.extend([r["route_a_domestic_2leg_maker_bps"], r["route_a_domestic_2leg_maker_bps"]])
        rb_t.extend([r["route_b_cross_3leg_taker_bps"], r["route_b_cross_3leg_taker_bps"]])

    ax1.plot(dates, rb_t, color=PALETTE["orange"], lw=1.7, ls="-.", label="Route B Cross 3-Leg (Taker)")
    ax1.plot(dates, ra_t, color=PALETTE["blue"], lw=1.7, ls="-", label="Route A Domestic 2-Leg (Taker)")
    ax1.plot(dates, ra_m, color=PALETTE["green"], lw=1.5, ls="--", label="Route A Domestic 2-Leg (Maker)")
    ax1.set_ylabel("Round-Trip Fee + Tax (bps)")
    ax1.set_title("(a) Statutory Transaction-Cost Regimes (Routes A\u2013B)", fontsize=10.2)
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.set_ylim(-5, 102)
    ax1.legend(loc="lower right", frameon=True, facecolor="white", framealpha=0.94, edgecolor="none")

    ev_c = ev[ev["basis_leg"] == "B_crypto"].reset_index(drop=True)
    ev_s = ev[ev["basis_leg"] == "B_stablecoin_FX"].reset_index(drop=True)
    y = np.arange(len(ev_c))[::-1]
    h = 0.36
    col_diff = "ctrl_diff_bps" if "ctrl_diff_bps" in ev_c.columns else "diff_mean_bps"
    ax2.barh(y + h/2, ev_c[col_diff], height=h, color=PALETTE["blue"], alpha=0.88, label="$\\Delta B^{crypto}$ (Controlled HAC)")
    ax2.barh(y - h/2, ev_s[col_diff], height=h, color=PALETTE["orange"], hatch="///", edgecolor="#7A3000", linewidth=0.4, alpha=0.88, label="$\\Delta B^{s\\text{-}FX}$ (Controlled HAC)")
    if "ctrl_p_holm" in ev_s.columns:
        for yi, (_, rs) in zip(y, ev_s.iterrows()):
            if rs["ctrl_p_holm"] < 0.05:
                x_star = rs[col_diff] + 1.2
                ax2.text(x_star, yi - h/2, "*", va="center", ha="left", fontsize=13, fontweight="bold", color=PALETTE["orange"])
    ax2.axvline(0, color="black", lw=0.7)
    ax2.set_xlim(-27, 23)
    short_ev = [
        f"{r['event_date'][:7]} " + (
            r["label"].split("(")[0].strip()
            .replace("PMK 68/PMK.03/2022 Crypto Tax", "PMK 68/2022")
            .replace("Binance BIDR Delisting", "BIDR Delist")
            .replace("Indodax Security Incident", "Indodax Incid.")
            .replace("CFX Fee Introduction", "CFX Launch")
            .replace("OJK Regulatory Transfer", "OJK Transfer")
            .replace("PMK 50/2025 Tax Overhaul", "PMK 50/2025")
            .replace("CFX First 50% Fee Reduction", "CFX 1st Cut")
            .replace("JISDOR Schedule Shift", "PADG 7/2026")
            .replace("CFX Second 50% Fee Reduction", "CFX 2nd Cut")
            .replace("Indodax Wallet Maintenance", "Indodax Maint. (12d)")
        )
        for _, r in ev_c.iterrows()
    ]
    ax2.set_yticks(y)
    ax2.set_yticklabels(short_ev, fontsize=9.4)
    ax2.set_xlabel("Controlled $\\pm 30$-Day Post Shift (bps; * $p_{\\mathrm{Holm}} < 0.05$)")
    ax2.set_title("(b) Controlled Event-Window Shifts", fontsize=10.2, pad=30)
    ax2.legend(loc="lower center", bbox_to_anchor=(0.5, 1.005), ncol=2, frameon=True, facecolor="white", framealpha=0.95, edgecolor="none", fontsize=9.0)

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig7_regulatory_and_costs")


def plot_robustness_and_orderbook(root: Path, out_dir: Path) -> None:
    t8 = pd.read_csv(root / "results" / "tables" / "table8_synchronization_sensitivity.csv")
    rc = pd.read_csv(root / "results" / "tables" / "route_specific_execution_costs.csv")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.8, 7.2), gridspec_kw={"height_ratios": [1.2, 1.0]})
    y = np.arange(len(t8))[::-1]
    h = 0.36
    ax1.barh(y + h/2, t8["sd_b_total_bps"], height=h, color=PALETTE["navy"], label="$\\mathrm{SD}(B^{total})$")
    ax1.barh(y - h/2, t8["sd_b_crypto_bps"], height=h, color=PALETTE["blue"], hatch="///", edgecolor="#003E63", linewidth=0.4, label="$\\mathrm{SD}(B^{crypto})$")
    short_spec = [
        s.replace("Primary_0m_JISDOR", "Primary 0m JISDOR")
         .replace("ExAnte_Minus15m_JISDOR", "Ex-Ante -15m")
         .replace("Post_Plus5m_JISDOR", "Post +5m")
         .replace("Post_Plus15m_JISDOR", "Post +15m")
         .replace("NextDay_JISDOR_Lead", "Next-Day JISDOR")
         .replace("Mismatched_2359UTC_Close", "23:59 UTC Mismatch")
         .replace("SpotFX_Yahoo_0m", "Spot FX (Yahoo)")
         .replace("ECBFX_Frankfurter_0m", "ECB FX (Frankfurter)")
        for s in t8["specification"]
    ]
    ax1.set_yticks(y)
    ax1.set_yticklabels(short_spec, fontsize=9.5)
    ax1.set_xlim(0, 102)
    ax1.set_xlabel("Dispersion (SD in bps)")
    ax1.set_title("(a) Synchronization Offset & FX Benchmark Sensitivity", fontsize=10.2, pad=30)
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, 1.005), ncol=2, frameon=True, facecolor="white", framealpha=0.95, edgecolor="none", fontsize=9.2)

    sizes = ["1k", "10k", "50k"]
    x = np.arange(3)
    w = 0.25
    hatches_sz = [None, "///", "..."]
    for idx, sz in enumerate(sizes):
        sub = rc[rc["trade_size_usd"] == sz]
        ax2.bar(x + (idx - 1) * w, sub["all_in_taker_plus_slip_bps"], width=w,
                color=[PALETTE["blue"], PALETTE["orange"], PALETTE["purple"]][idx],
                hatch=hatches_sz[idx], edgecolor="white" if hatches_sz[idx] is None else "#333333", linewidth=0.4,
                label=f"Size \\${sz}")
    ax2.set_xticks(x)
    ax2.set_xticklabels(["Route A\n(Domestic 2-Leg)", "Route B\n(Cross 3-Leg)", "Route C\n(Indodax USDT)"], fontsize=9.8)
    ax2.set_ylabel("All-In Taker + Depth Slip (bps)")
    ax2.set_title("(b) Single-Day Order-Book Cost Snapshot (Nov 13, 2026)", fontsize=10.2)
    ax2.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.95, edgecolor="none")

    fig.tight_layout()
    _save_fig(fig, out_dir, "fig8_robustness_and_orderbook")


def generate_all_figures(root: Path) -> List[str]:
    out_dir = root / "manuscript"
    plot_coverage_and_regimes(root, out_dir)
    plot_synchronized_prices(root, out_dir)
    plot_basis_decomposition(root, out_dir)
    plot_basis_distributions(root, out_dir)
    plot_rolling_dynamics(root, out_dir)
    plot_cointegration_and_ec(root, out_dir)
    plot_regulatory_and_costs(root, out_dir)
    plot_robustness_and_orderbook(root, out_dir)
    return sorted(p.name for p in out_dir.glob("fig*.pdf"))
