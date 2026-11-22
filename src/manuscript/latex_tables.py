"""Generate verified LaTeX tables directly from results/ with zero horizontal margin overflow."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

import pandas as pd


def _tex_escape(val: object) -> str:
    s = str(val)
    for old, new in [
        ("\\", "\\textbackslash{}"),
        ("&", "\\&"),
        ("%", "\\%"),
        ("$", "\\$"),
        ("#", "\\#"),
        ("_", "\\_"),
    ]:
        s = s.replace(old, new)
    return s


def _fmt_p(p: float) -> str:
    if pd.isna(p):
        return "--"
    if p < 0.0001:
        return "$<$0.0001"
    if p < 0.001:
        return "$<$0.001"
    return f"{p:.4f}"


def generate_all_latex_tables(root: Path) -> List[str]:
    tdir = root / "results" / "tables"
    mdir = root / "results" / "models"
    out_dir = root / "manuscript" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []

    # 1. Coverage summary table
    cov = pd.read_csv(root / "data" / "source_coverage_matrix.csv")
    cov_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Data Provenance and Historical Coverage Summary (2021--2026)}",
        "\\label{tab:coverage}",
        "\\scriptsize\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabularx}{\\textwidth}{@{}llccrrX@{}}",
        "\\toprule",
        "Provider / Venue & Instrument & Freq. & Start--End (UTC) & Rows & Zero-Vol & Role / Limitations \\\\",
        "\\midrule",
    ]
    keep_rows = [
        ("Bank Indonesia", "JISDOR", "1d", "Official FX benchmark; bus. days"),
        ("Indodax", "BTCIDR", "5m", "Primary local BTC; 1.73\\% stale"),
        ("Indodax", "USDTIDR", "5m", "Local stablecoin; 0.61\\% stale"),
        ("Indodax", "ETHIDR", "5m", "Secondary ETH; 5.97\\% stale"),
        ("Indodax", "XRPIDR", "5m", "Auxiliary XRP; 6.64\\% stale"),
        ("Indodax", "BTCUSDT", "5m", "Route C venue; 78.57\\% zero-vol"),
        ("Binance Spot", "BTCUSDT", "5m", "Global USDT ref.; SHA-256"),
        ("Binance Spot", "ETHUSDT", "5m", "Global ETH ref.; SHA-256"),
        ("Binance Spot", "XRPUSDT", "5m", "Global XRP ref.; SHA-256"),
        ("Binance Spot", "BTCBIDR", "5m", "Delisted 2024-05-17"),
        ("Binance Spot", "BTCIDR", "5m", "Launched 2025-11-29"),
        ("Coinbase", "USDT-USD", "1h", "Listed 2021-05-04 (peg wedge)"),
        ("Kraken", "USDTUSD", "1d", "720-bar API cap (validation)"),
        ("Yahoo Finance", "IDR=X", "1d", "Continuous FX sensitivity"),
        ("Frankfurter (ECB)", "USD/IDR", "1d", "ECB cross-check benchmark"),
    ]
    for ex, inst, fp, note in keep_rows:
        sub = cov[(cov["exchange"].str.contains(ex, regex=False)) & (cov["instrument"] == inst) & (cov["frequency"].str.startswith(fp))]
        if sub.empty:
            continue
        r = sub.iloc[0]
        span = f"{str(r['first_timestamp'])[:10]} to {str(r['last_timestamp'])[:10]}"
        zv = "--"
        if "zero-volume" in str(r["known_limitations"]):
            m = re.search(r"\(([\d.]+)% zero-volume\)", str(r["known_limitations"]))
            if m:
                zv = f"{m.group(1)}\\%"
        cov_lines.append(
            f"{_tex_escape(ex)} & {_tex_escape(inst)} & {_tex_escape(fp)} & {span} & {int(r['rows_retrieved']):,} & {zv} & {note} \\\\"
        )
    cov_lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} All series retrieved directly from official endpoints or public historical archives with SHA-256 manifests. BI JISDOR excludes weekends and Indonesian holidays; Coinbase USDT-USD commenced trading May 4, 2021; Binance BIDR delisted May 17, 2024; Binance direct IDR pairs launched November 29, 2025.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_coverage.tex").write_text("\n".join(cov_lines) + "\n")
    written.append("tab_coverage.tex")

    # 2. Table 1: Descriptive Statistics & Variance Decomposition
    t1 = pd.read_csv(tdir / "table1_descriptive_statistics.csv")
    vd = json.loads((mdir / "variance_decomposition.json").read_text())
    t1_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Descriptive Statistics of Basis Components and Exact Variance Decomposition (bps)}",
        "\\label{tab:descriptive}",
        "\\scriptsize\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabularx}{\\textwidth}{@{}Xrrrrrrr@{}}",
        "\\toprule",
        "Sample / Basis Series & $N$ & Mean [95\\% CI] & SD & Med. & IQR & $\\%>0$ & $\\le$ Taker \\\\",
        "\\midrule",
    ]
    for _, r in t1.iterrows():
        lbl = f"{_tex_escape(r['sample'].split(' (')[0])}: {_tex_escape(r['series'].split(' (')[0])}"
        ci = f"{r['mean_bps']:.2f} [{r['ci95_low_bps']:.2f}, {r['ci95_high_bps']:.2f}]"
        t1_lines.append(
            f"{lbl} & {int(r['n_obs']):,} & {ci} & {r['sd_bps']:.2f} & {r['median_bps']:.2f} & {r['iqr_bps']:.2f} & {r['pct_positive']:.1f}\\% & {r['pct_within_taker_band']:.1f}\\% \\\\"
        )
    b_vd = vd["BTC"]
    t1_lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        f"\\emph{{Exact Variance Identity (BTC, $n=1,414$):}} $\\mathrm{{Var}}(B^{{total}}) = {b_vd['var_total']:.2f}$ = $\\mathrm{{Var}}(B^{{crypto}})\\ ({b_vd['var_crypto']:.2f},\\ {b_vd['gross_share_crypto_pct']:.2f}\\%)$ + $\\mathrm{{Var}}(B^{{stable\\text{{-}}FX}})\\ ({b_vd['var_stablecoin_fx']:.2f},\\ {b_vd['gross_share_sf_pct']:.2f}\\%)$ + $2\\mathrm{{Cov}}\\,({2*b_vd['cov_crypto_sf']:.2f},\\ {100 - b_vd['gross_share_crypto_pct'] - b_vd['gross_share_sf_pct']:.2f}\\%)$. \\emph{{Dynamic Fee Band Containment (BTC $B^{{crypto}}$):}} {vd['BTC_pct_crypto_inside_dynamic_2leg_maker_band']:.2f}\\% inside Route A maker band; {vd['BTC_pct_crypto_inside_dynamic_2leg_taker_band']:.2f}\\% inside Route A taker band; {vd['BTC_pct_crypto_inside_dynamic_3leg_taker_band']:.2f}\\% inside Route B taker band.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_descriptive.tex").write_text("\n".join(t1_lines) + "\n")
    written.append("tab_descriptive.tex")

    # 3. Table 2: Unit-Root & Stationarity Suite
    t2 = pd.read_csv(tdir / "table2_unit_root_tests.csv")
    t2_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Unit-Root and Stationarity Tests (2021--2026 Synchronized Business-Day Panel)}",
        "\\label{tab:unit_roots}",
        "\\scriptsize\\setlength{\\tabcolsep}{4pt}",
        "\\begin{tabularx}{\\textwidth}{@{}Xrrrrrr@{}}",
        "\\toprule",
        "Series & $N$ & ADF (Const.) & $p$-val & PP ($Z_t$) & KPSS ($\\eta_\\mu$) & Zivot--Andrews \\\\",
        "\\midrule",
    ]
    for _, r in t2.iterrows():
        t2_lines.append(
            f"{_tex_escape(r['series'])} & {int(r['n_obs']):,} & {r['adf_c_stat']:.3f} & {_fmt_p(r['adf_c_pval'])} & {r['pp_c_stat']:.3f} & {r['kpss_c_stat']:.3f} & {r['za_c_stat']:.3f} \\\\"
        )
    t2_lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} 5\\% critical values: ADF constant $-2.864$, KPSS constant $0.463$ ($H_0$: stationarity), Zivot--Andrews single-break $-4.80$. All log price levels and FX series are $I(1)$; first differences and all basis spreads reject a unit root at $p < 0.001$.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_unit_roots.tex").write_text("\n".join(t2_lines) + "\n")
    written.append("tab_unit_roots.tex")

    # 4. Table 3: Cointegration & Bootstrap Rank Tests
    t3 = pd.read_csv(tdir / "table3_cointegration_and_reconciliation.csv")
    t4b = pd.read_csv(tdir / "table4b_bootstrap_dgp_validation.csv")
    t3_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Engle--Granger, Fixed-$(1,-1)$, Johansen (Reinsel--Ahn), and Bootstrap Cointegration Tests ($B=9,999$)}",
        "\\label{tab:cointegration}",
        "\\scriptsize\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabularx}{\\textwidth}{@{}Xrrrrrrr@{}}",
        "\\toprule",
        "Specification & $T_{eff}$ & EG $\\hat{\\beta}$ & EG $t$ & Fixed ADF & Trace (RA) & MaxEig (RA) & Boot $p$ \\\\",
        "\\midrule",
    ]
    for _, r in t3.iterrows():
        spec_short = str(r["specification"]).split(" (")[0].replace("_Converted", "").replace("_", " ")
        t3_lines.append(
            f"{_tex_escape(spec_short)} & {int(r['T_eff']):,} & {r['eg_beta_hat']:.4f} & {r['eg_t_stat']:.2f} & {r['fixed_adf_stat']:.2f} & {r['trace_r0_ra']:.2f} & {r['maxeig_r0_ra']:.2f} & {_fmt_p(r['boot_trace_pval'])} \\\\"
        )
    t3_lines += [
        "\\midrule",
        "\\multicolumn{8}{@{}l}{\\textbf{Monte Carlo Validation of Null-Imposed VECM Bootstrap Size \\& Power ($n_{MC}=150$, $B=299$):}} \\\\",
    ]
    for _, r in t4b.iterrows():
        metric_short = "Size" if "size" in str(r["metric"]) else "Power"
        t3_lines.append(
            f"DGP $T={int(r['T'])}$, $r={int(r['true_rank'])}$ ({metric_short}) & \\multicolumn{{2}}{{r}}{{Asymp: {100*r['rej_rate_asymptotic_5pct']:.1f}\\%}} & \\multicolumn{{2}}{{r}}{{RA: {100*r['rej_rate_reinsel_ahn_5pct']:.1f}\\%}} & \\multicolumn{{3}}{{r}}{{Bootstrap: {100*r['rej_rate_bootstrap_5pct']:.1f}\\%}} \\\\"
        )
    t3_lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} 5\\% critical values: Engle--Granger $-3.340$; Fixed-$(1,-1)$ ADF $-2.864$; Johansen asymptotic Trace $15.49$, MaxEig $14.26$ (Cheung--Lai 5\\% CV at $T_{eff}=1,412$: Trace $15.54$, MaxEig $14.30$). Null-imposed restricted-VECM i.i.d. residual bootstrap uses $B=9,999$ replications.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_cointegration.tex").write_text("\n".join(t3_lines) + "\n")
    written.append("tab_cointegration.tex")

    # 5. Table 5 & 6: VECM Error Correction, Intraday Price Discovery & Return Pass-Through
    t5 = pd.read_csv(tdir / "table5_vecm_error_correction.csv")
    t6 = pd.read_csv(tdir / "table6_return_passthrough.csv")
    tar_j = json.loads((mdir / "intraday_and_tar_results.json").read_text())
    t5_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{VECM Error Correction, Price Discovery, Band-TAR, and Return Pass-Through}",
        "\\label{tab:vecm_ecm}",
        "\\scriptsize\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabularx}{\\textwidth}{@{}Xrrrrrrr@{}}",
        "\\toprule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel A: Daily Bivariate VECM Estimates (Native Day Units, HAC $L=5$)}} \\\\",
        "System & $T_{eff}$ & $\\hat{\\alpha}_{local}$ (SE) & $p_{loc}$ & $\\hat{\\alpha}_{glob}$ & $p_{glob}$ & HL (d) & GG $w_g$ \\\\",
        "\\midrule",
    ]
    for _, r in t5.iterrows():
        sys_lbl = str(r["system"]).replace(" (Daily Bus. Days)", "").replace("Indodax-", "")
        t5_lines.append(
            f"{_tex_escape(sys_lbl)} & {int(r['T_eff']):,} & {r['alpha_local_hac']:.3f} ({r['alpha_local_hac_se']:.3f}) & {_fmt_p(r['alpha_local_hac_pval'])} & {r['alpha_global_hac']:.3f} & {_fmt_p(r['alpha_global_hac_pval'])} & {r['half_life_native_units']:.2f} & {100*r['gg_share_global']:.1f}\\% \\\\"
        )
    hf_a = tar_j["hf_vecm_active_5m"]
    hf_all = tar_j["hf_vecm_all_5m"]
    td_c = tar_j["tar_daily_b_crypto"]
    t5m = tar_j["tar_5m_recent_25k_active"]
    t5_lines += [
        "\\midrule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel B: 5-Minute 24/7 BTC VECM \\& Band-TAR Diagnostics (Native 5m Bar Units)}} \\\\",
        f"5m All Bars ($k=5$, HAC $L=12$) & {hf_all['T_eff']:,} & {hf_all['alpha_local_hac']:.4f} ({hf_all['alpha_local_hac_se']:.4f}) & {_fmt_p(hf_all['alpha_local_hac_pval'])} & {hf_all['alpha_global_hac']:.4f} & {_fmt_p(hf_all['alpha_global_hac_pval'])} & {hf_all['half_life_native_units']:.2f} & {100*hf_all['gg_share_global']:.1f}\\% \\\\",
        f"5m Active-Vol Bars ($k=5$) & {hf_a['T_eff']:,} & {hf_a['alpha_local_hac']:.4f} ({hf_a['alpha_local_hac_se']:.4f}) & {_fmt_p(hf_a['alpha_local_hac_pval'])} & {hf_a['alpha_global_hac']:.4f} & {_fmt_p(hf_a['alpha_global_hac_pval'])} & {hf_a['half_life_native_units']:.2f} & {100*hf_a['gg_share_global']:.1f}\\% \\\\",
        "\\midrule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel C: Daily Log-Return Pass-Through $\\Delta\\ln P_t^{IDR} = c + \\beta_1 \\Delta\\ln P_t^{USDT} + \\beta_2 \\Delta\\ln S_t^{FX} + \\beta_3 \\Delta(B_t^{s\\text{-}FX})$}} \\\\",
        "Asset & $N$ & $\\hat{\\beta}_{crypto}$ (SE) & $\\hat{\\beta}_{FX}$ (SE) & $\\hat{\\beta}_{s\\text{-}FX}$ (SE) & Adj. $R^2$ & $\\hat{\\beta}_{t-1}^{cry}$ & $p_{t-1}$ \\\\",
        "\\midrule",
    ]
    for _, r in t6.iterrows():
        t5_lines.append(
            f"{_tex_escape(r['asset'])} & {int(r['n_obs']):,} & {r['m3_beta_global_crypto']:.4f} ({r['m3_beta_global_crypto_se']:.4f}) & {r['m3_beta_fx_jisdor']:.4f} ({r['m3_beta_fx_jisdor_se']:.4f}) & {r['m3_beta_sf_wedge']:.4f} ({r['m3_beta_sf_wedge_se']:.4f}) & {r['m3_adj_r2']:.4f} & {r['m2_beta_global_crypto_t1']:.4f} & {_fmt_p(r['m2_beta_global_crypto_t1_pval'])} \\\\"
        )
    t5_lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        f"\\emph{{Notes:}} 5m Active Hasbrouck Information Share (Global): [{100*hf_a['hasbrouck_is_global_low']:.1f}\\%, {100*hf_a['hasbrouck_is_global_high']:.1f}\\%] (midpoint {100*hf_a['hasbrouck_is_global_mid']:.1f}\\%, $\\rho_u={hf_a['resid_corr_cross_market']:.3f}$); daily BTC $\\rho_u={t5.iloc[0]['resid_corr_cross_market']:.3f}$. Band-TAR daily $B^{{crypto}}$: $\\hat{{\\tau}}={td_c['tau_hat_bps']:.2f}$ bps, $\\sup W={td_c['sup_wald']:.2f}$ ($p={td_c['sup_wald_boot_pval']:.3f}$); 5m Active ($n=25k$): $\\hat{{\\tau}}={t5m['tau_hat_bps']:.2f}$ bps, $\\sup W={t5m['sup_wald']:.2f}$ ($p={t5m['sup_wald_boot_pval']:.4f}$, $\\rho_{{in}}={t5m['rho_in']:.3f}$, $\\rho_{{out}}={t5m['rho_out']:.3f}$).",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_vecm_ecm.tex").write_text("\n".join(t5_lines) + "\n")
    written.append("tab_vecm_ecm.tex")

    # 6. Historical Fees & Orderbook Route Costs
    fee = pd.read_csv(tdir / "historical_fee_reconstruction.csv")
    rc = pd.read_csv(tdir / "route_specific_execution_costs.csv")
    fee_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Indonesian Statutory Crypto Tax, CFX, Platform Commission, and Route Execution Costs (bps)}",
        "\\label{tab:fees}",
        "\\scriptsize\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabularx}{\\textwidth}{@{}lXrrrrrr@{}}",
        "\\toprule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel A: Chronological Fee \\& Tax Regimes (2021--2026)}} \\\\",
        "Window & Regime ID & M/T & VAT & PPh22 & CFX & Rte A (M/T) & Rte B (M/T) \\\\",
        "\\midrule",
    ]
    for _, r in fee.iterrows():
        win = f"{r['start_date'][:7]}--{r['end_date'][:7]}"
        lbl = _tex_escape(str(r["regime_id"]).replace("_", " "))
        mt = f"{int(r['indodax_idr_maker_bps'])}/{int(r['indodax_idr_taker_bps'])}"
        ra = f"{r['route_a_domestic_2leg_maker_bps']:.1f}/{r['route_a_domestic_2leg_taker_bps']:.1f}"
        rb = f"{r['route_b_cross_3leg_maker_bps']:.1f}/{r['route_b_cross_3leg_taker_bps']:.1f}"
        fee_lines.append(
            f"{win} & {lbl} & {mt} & {r['asset_vat_buyer_bps']:.0f} & {r['asset_pph22_seller_bps']:.0f} & {r['cfx_idr_bps']:.3g} & {ra} & {rb} \\\\"
        )
    fee_lines += [
        "\\midrule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel B: Live Order-Book Execution Costs by Route \\& Size (Nov 13, 2026 Depth Snapshot, Regime R6)}} \\\\",
        "Route & Scope & Size & \\multicolumn{2}{r}{Stat. (Mkr/Tkr)} & \\multicolumn{2}{r}{Depth Slip} & All-In Tkr \\\\",
        "\\midrule",
    ]
    for _, r in rc.iterrows():
        rname = str(r["route"]).split(": ")[0]
        rscope = str(r["route"]).split(": ")[1].split(" (")[0]
        fee_lines.append(
            f"{_tex_escape(rname)} & {_tex_escape(rscope)} & \\${_tex_escape(r['trade_size_usd'])} & \\multicolumn{{2}}{{r}}{{{r['statutory_fee_maker_bps']:.2f}/{r['statutory_fee_taker_bps']:.2f}}} & \\multicolumn{{2}}{{r}}{{{r['snapshot_half_spread_slip_bps']:.2f}}} & {r['all_in_taker_plus_slip_bps']:.2f} \\\\"
        )
    fee_lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} Regime R2A/R2B August 2023 platform fee transition carries PARTIALLY\\_VERIFIED status; R6 matches published Indodax Pro rates to the fifth decimal place (0.10555\\%/0.20555\\% buy; 0.31555\\%/0.41555\\% sell; 0.2511\\%/0.2811\\% USDT). Route B and Route C calculations assume pre-funded inventory and exclude on-chain withdrawal fees.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_fees.tex").write_text("\n".join(fee_lines) + "\n")
    written.append("tab_fees.tex")

    # 7. Event Studies Table 7
    ev = pd.read_csv(tdir / "table7_regulatory_event_windows.csv")
    ev_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{30-Calendar-Day Pre/Post Institutional and Regulatory Event Windows (BTC Basis, bps)}",
        "\\label{tab:events}",
        "\\scriptsize\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabularx}{\\textwidth}{@{}lXrrrrrr@{}}",
        "\\toprule",
        "Date & Event & $\\Delta\\bar{B}^{crypto}$ & Welch $p$ & MW $p$ & $\\Delta\\bar{B}^{s\\text{-}FX}$ & Welch $p$ & MW $p$ \\\\",
        "\\midrule",
    ]
    ev_c = ev[ev["basis_leg"] == "B_crypto"].reset_index(drop=True)
    ev_s = ev[ev["basis_leg"] == "B_stablecoin_FX"].reset_index(drop=True)
    for idx in range(len(ev_c)):
        rc_i = ev_c.iloc[idx]
        rs_i = ev_s.iloc[idx]
        ev_lines.append(
            f"{rc_i['event_date']} & {_tex_escape(rc_i['label'])} & {rc_i['diff_mean_bps']:.2f} & {_fmt_p(rc_i['welch_pval'])} & {_fmt_p(rc_i['mw_u_pval'])} & {rs_i['diff_mean_bps']:.2f} & {_fmt_p(rs_i['welch_pval'])} & {_fmt_p(rs_i['mw_u_pval'])} \\\\"
        )
    ev_lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\end{table}",
    ]
    (out_dir / "tab_events.tex").write_text("\n".join(ev_lines) + "\n")
    written.append("tab_events.tex")

    # 8. Robustness & Falsification Table 8+9
    t8 = pd.read_csv(tdir / "table8_synchronization_sensitivity.csv")
    t9 = pd.read_csv(tdir / "table9_falsification_tests.csv")
    t89_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Synchronization Sensitivity, FX Benchmark Robustness, and Falsification Suite (BTC)}",
        "\\label{tab:robustness}",
        "\\scriptsize\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabularx}{\\textwidth}{@{}Xrrrrrrr@{}}",
        "\\toprule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel A: Timestamp Offset \\& FX Benchmark Sensitivity}} \\\\",
        "Specification & $N$ & Mean $B^{tot}$ & SD $B^{tot}$ & Mean $B^{cry}$ & SD $B^{cry}$ & EG $t$ & Trace (RA) \\\\",
        "\\midrule",
    ]
    for _, r in t8.iterrows():
        spec_clean = str(r["specification"]).replace("_", " ")
        t89_lines.append(
            f"{_tex_escape(spec_clean)} & {int(r['n_obs']):,} & {r['mean_b_total_bps']:.2f} & {r['sd_b_total_bps']:.2f} & {r['mean_b_crypto_bps']:.2f} & {r['sd_b_crypto_bps']:.2f} & {r['eg_t_stat']:.3f} & {r['joh_trace_ra']:.2f} \\\\"
        )
    t89_lines += [
        "\\midrule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel B: Negative Controls \\& Falsification Tests}} \\\\",
        "Falsification Test & $N$ & SD (bps) & EG $t$/$F$ & $p$-val & Trace & Rej. 5\\% & Expected Outcome \\\\",
        "\\midrule",
    ]
    for _, r in t9.iterrows():
        tr = f"{r['joh_trace_ra']:.2f}" if pd.notna(r["joh_trace_ra"]) else "--"
        test_clean = str(r["test"]).replace("_", " ")
        exp_short = str(r["expected_outcome"]).split(" (")[0]
        t89_lines.append(
            f"{_tex_escape(test_clean)} & {int(r['n_obs']):,} & {r['spread_sd_bps']:.1f} & {r['eg_t_stat']:.3f} & {_fmt_p(r['eg_pval'])} & {tr} & {r['rejected_no_coint_5pct']} & {_tex_escape(exp_short)} \\\\"
        )
    t89_lines += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\end{table}",
    ]
    (out_dir / "tab_robustness.tex").write_text("\n".join(t89_lines) + "\n")
    written.append("tab_robustness.tex")

    return written
