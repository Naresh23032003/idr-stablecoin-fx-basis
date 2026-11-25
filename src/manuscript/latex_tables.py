"""Generate verified LaTeX tables directly from results/ into manuscript/."""
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


def _fmt_p(p: float, digits: int = 4) -> str:
    if pd.isna(p):
        return "--"
    if p < 0.0001:
        return "$<$0.0001"
    return f"{p:.{digits}f}"


def generate_all_latex_tables(root: Path) -> List[str]:
    tdir = root / "results" / "tables"
    mdir = root / "results" / "models"
    out_dir = root / "manuscript"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []

    # 1. Coverage summary table (tab_coverage.tex)
    cov = pd.read_csv(root / "data" / "source_coverage_matrix.csv")
    cov_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Data provenance and historical coverage summary (2021--2026)}",
        "\\label{tab:coverage}",
        "\\fontsize{6.6}{7.8}\\selectfont\\setlength{\\tabcolsep}{1.8pt}",
        "\\begingroup",
        "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{1.9cm}llrrl>{\\raggedright\\arraybackslash}p{2.3cm}@{}}",
        "\\toprule",
        "Venue & Inst. & Freq. & Start--End & Rows & Zero-Vol & Role / Limits \\\\",
        "\\midrule",
    ]
    keep_rows = [
        ("Bank Indonesia", "JISDOR", "1d", "Official FX; bus. days"),
        ("Indodax", "BTCIDR", "5m", "Primary BTC; 1.73\\% stale"),
        ("Indodax", "USDTIDR", "5m", "Local USDT; 0.61\\% stale"),
        ("Indodax", "ETHIDR", "5m", "Secondary ETH; 5.97\\% stale"),
        ("Indodax", "XRPIDR", "5m", "Auxiliary XRP; 6.64\\% stale"),
        ("Indodax", "BTCUSDT", "5m", "Route C; 78.57\\% zero-vol"),
        ("Binance Spot", "BTCUSDT", "5m", "Global BTC; SHA-256"),
        ("Binance Spot", "ETHUSDT", "5m", "Global ETH; SHA-256"),
        ("Binance Spot", "XRPUSDT", "5m", "Global XRP; SHA-256"),
        ("Binance Spot", "BTCBIDR", "5m", "Delisted 2024-05-17"),
        ("Binance Spot", "BTCIDR", "5m", "Launched 2025-11-29"),
        ("Coinbase", "USDT-USD", "1h", "Listed 2021-05-04"),
        ("Kraken", "USDTUSD", "1d", "720-bar API cap"),
        ("Yahoo Finance", "IDR=X", "1d", "Continuous FX check"),
        ("Frankfurter (ECB)", "USD/IDR", "1d", "ECB benchmark"),
    ]
    for ex, inst, fp, note in keep_rows:
        sub = cov[(cov["exchange"].str.contains(ex, regex=False)) & (cov["instrument"] == inst) & (cov["frequency"].str.startswith(fp))]
        if sub.empty:
            continue
        r = sub.iloc[0]
        span = f"{str(r['first_timestamp'])[:7]}--{str(r['last_timestamp'])[:7]}"
        zv = "--"
        if "zero-volume" in str(r["known_limitations"]):
            m = re.search(r"\(([\d.]+)% zero-volume\)", str(r["known_limitations"]))
            if m:
                zv = f"{m.group(1)}\\%"
        cov_lines.append(
            f"{_tex_escape(ex)} & \\texttt{{{_tex_escape(inst)}}} & {_tex_escape(fp)} & {span} & {int(r['rows_retrieved']):,} & {zv} & {note} \\\\"
        )
    cov_lines += [
        "\\bottomrule",
        "\\end{tabular}\\endgroup",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} All series retrieved directly from official endpoints or public historical archives on November 13, 2026 with SHA-256 manifests. BI JISDOR excludes weekends and Indonesian holidays; Coinbase \\texttt{USDT-USD} commenced trading May 4, 2021; Binance \\texttt{BIDR} delisted May 17, 2024; Binance direct \\texttt{IDR} pairs launched November 29, 2025.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_coverage.tex").write_text("\n".join(cov_lines) + "\n")
    written.append("tab_coverage.tex")

    # 2. Table 1: Descriptive Statistics & Variance Decomposition (tab_descriptive.tex)
    t1 = pd.read_csv(tdir / "table1_descriptive_statistics.csv")
    vd = json.loads((mdir / "variance_decomposition.json").read_text())
    t1_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Descriptive statistics of basis components and variance decomposition (bps)}",
        "\\label{tab:descriptive}",
        "\\fontsize{6.8}{8}\\selectfont\\setlength{\\tabcolsep}{1.8pt}",
        "\\begingroup",
        "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{2.6cm}rrrrrrr@{}}",
        "\\toprule",
        "Sample / Basis Series & $N$ & Mean [95\\% CI] & SD & Med. & IQR & $\\%>0$ & $\\le$ Fixed Tkr \\\\",
        "\\midrule",
    ]
    series_map = {
        "B_total (vs JISDOR)": "$B^{total}$",
        "B_crypto (vs Indodax USDT)": "$B^{crypto}$",
        "B_stablecoin_FX (USDT/IDR - JISDOR)": "$B^{s\\text{-}FX}$",
        "W_USD_USDT (Coinbase)": "$W^{USD/USDT}$",
        "B_total (Carry-Forward JISDOR)": "$B^{total}$",
        "B_total (Weekend Carry-Forward)": "$B^{total}$",
        "B_crypto (Weekends Only)": "$B^{crypto}$",
    }
    sample_map = {
        "BTC Primary (JISDOR Bus. Days)": "BTC Primary",
        "ETH Primary (JISDOR Bus. Days)": "ETH Primary",
        "XRP Primary (JISDOR Bus. Days)": "XRP Primary",
        "BTC All Calendar Days (Sensitivity)": "BTC Calendar Days",
        "BTC Weekends Only (FX Closed)": "BTC Weekends Only",
    }
    for _, r in t1.iterrows():
        s_lbl = sample_map.get(r["sample"], _tex_escape(r["sample"]))
        c_lbl = series_map.get(r["series"], _tex_escape(r["series"]))
        ci = f"{r['mean_bps']:.2f} [{r['ci95_low_bps']:.2f}, {r['ci95_high_bps']:.2f}]"
        t1_lines.append(
            f"{s_lbl}: {c_lbl} & {int(r['n_obs']):,} & {ci} & {r['sd_bps']:.2f} & {r['median_bps']:.2f} & {r['iqr_bps']:.2f} & {r['pct_positive']:.1f}\\% & {r['pct_within_taker_band']:.1f}\\% \\\\"
        )
    b_vd = vd["BTC"]
    cov_share = 100.0 - b_vd["gross_share_crypto_pct"] - b_vd["gross_share_sf_pct"]
    t1_lines += [
        "\\bottomrule",
        "\\end{tabular}\\endgroup",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        f"\\emph{{Notes:}} The final column ($\\le$ Fixed Tkr) evaluates $|B_t|$ against a fixed benchmark: the sample-average Route A taker fee ({vd['BTC_mean_2leg_taker_band_bps']:.2f}\\text{{ bps}}) for primary business-day rows ({vd['BTC_pct_crypto_inside_fixed_mean_2leg_taker_band']:.2f}\\% for BTC $B^{{crypto}}$), and the Regime R6 Route A taker fee (62.11\\text{{ bps}}) for calendar-day and weekend sensitivity rows. Evaluated date-by-date against the time-varying regime Route A taker schedule (60.0--81.0\\text{{ bps}}), BTC $B^{{crypto}}$ containment is {vd['BTC_pct_crypto_inside_dynamic_2leg_taker_band']:.2f}\\% (sensitivity range [{vd['BTC_pct_crypto_inside_dynamic_2leg_taker_r2_low']:.2f}\\%, {vd['BTC_pct_crypto_inside_dynamic_2leg_taker_r2_high']:.2f}\\%] across partially verified 2022--2024 fee tiers; {vd['BTC_pct_crypto_inside_dynamic_2leg_maker_band']:.2f}\\% inside dynamic Route A maker; {vd['BTC_pct_crypto_inside_dynamic_3leg_taker_band']:.2f}\\% inside dynamic Route B taker). \\emph{{Exact variance identity (BTC, $n=1,414$):}} $\\mathrm{{Var}}(B^{{total}}) = {b_vd['var_total']:.2f}$ = $\\mathrm{{Var}}(B^{{crypto}})\\ ({b_vd['var_crypto']:.2f},\\ {b_vd['gross_share_crypto_pct']:.2f}\\%)$ + $\\mathrm{{Var}}(B^{{s\\text{{-}}FX}})\\ ({b_vd['var_stablecoin_fx']:.2f},\\ {b_vd['gross_share_sf_pct']:.2f}\\%)$ + $2\\mathrm{{Cov}}\\,({2*b_vd['cov_crypto_sf']:.2f},\\ {cov_share:.2f}\\%)$.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_descriptive.tex").write_text("\n".join(t1_lines) + "\n")
    written.append("tab_descriptive.tex")

    # 3. Table 2: Unit-Root & Stationarity Suite (tab_unit_roots.tex)
    t2 = pd.read_csv(tdir / "table2_unit_root_tests.csv")
    t2_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Unit-root and stationarity tests (2021--2026 synchronized business-day panel)}",
        "\\label{tab:unit_roots}",
        "\\fontsize{6.6}{7.8}\\selectfont\\setlength{\\tabcolsep}{2pt}",
        "\\begingroup",
        "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{3.4cm}rrrrrr@{}}",
        "\\toprule",
        "Series & $N$ & ADF (Const.) & $p$-val & PP ($Z_t$) & KPSS ($\\eta_\\mu$) & Zivot--Andrews \\\\",
        "\\midrule",
    ]
    for _, r in t2.iterrows():
        za = f"{r['za_c_stat']:.3f}" if pd.notna(r["za_c_stat"]) else "--"
        t2_lines.append(
            f"{_tex_escape(r['series'])} & {int(r['n_obs']):,} & {r['adf_c_stat']:.3f} & {_fmt_p(r['adf_c_pval'])} & {r['pp_c_stat']:.3f} & {r['kpss_c_stat']:.3f} & {za} \\\\"
        )
    t2_lines += [
        "\\bottomrule",
        "\\end{tabular}\\endgroup",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} 5\\% critical values: ADF constant $-2.864$, KPSS constant $0.463$ ($H_0$: stationarity), Zivot--Andrews single-break $-4.80$. All log price levels and FX series are $I(1)$; first differences and all basis spreads reject a unit root at $p < 0.0001$.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_unit_roots.tex").write_text("\n".join(t2_lines) + "\n")
    written.append("tab_unit_roots.tex")

    # 4. Table 3: Cointegration & Sequential Block-Wild Bootstrap (tab_cointegration.tex)
    t3 = pd.read_csv(tdir / "table3_cointegration_and_reconciliation.csv")
    t3_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Engle--Granger, Fixed-$(1,-1)$, Johansen (Reinsel--Ahn), and sequential block-wild bootstrap cointegration tests ($B=9,999$)}",
        "\\label{tab:cointegration}",
        "\\fontsize{6.3}{7.6}\\selectfont\\setlength{\\tabcolsep}{1.6pt}",
        "\\begingroup",
        "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{2.7cm}rrrrrrrr@{}}",
        "\\toprule",
        "Specification & $T_{eff}$ & EG $\\hat{\\beta}$ & EG $t$ & Fixed ADF & Trace (RA) & MaxEig (RA) & $p_{boot}(r=0)$ & $p_{boot}(r\\le 1)$ \\\\",
        "\\midrule",
    ]
    for _, r in t3.iterrows():
        spec_short = str(r["specification"]).split(" (")[0].replace("_Converted", "").replace("_", " ").replace("USDT IDR vs JISDOR", "USDT/IDR vs.\\ JISDOR")
        t3_lines.append(
            f"{spec_short} & {int(r['T_eff']):,} & {r['eg_beta_hat']:.4f} & {r['eg_t_stat']:.2f} & {r['fixed_adf_stat']:.2f} & {r['trace_r0_ra']:.2f} & {r['maxeig_r0_ra']:.2f} & {_fmt_p(r['boot_trace_pval'])} & {_fmt_p(r['boot_r1_trace_pval'])} \\\\"
        )
    t3_lines += [
        "\\bottomrule",
        "\\end{tabular}\\endgroup",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} 5\\% critical values (unrestricted constant $H_1(r)$, \\texttt{det\\_order=0}): Engle--Granger $-3.340$; Fixed-$(1,-1)$ ADF $-2.864$; Johansen asymptotic Trace $15.49$, MaxEig $14.26$ (Cheung--Lai 5\\% CV at $T_{eff}=1,412$: Trace $15.54$, MaxEig $14.30$). Final two columns report sequential $p$-values from the null-imposed restricted-VECM block-wild bootstrap ($B=9,999$ replications, block length $b = \\mathrm{round}(T_{eff}^{1/4}) = 6$, Rademacher multipliers) under $H_0: r=0$ and $H_0: r\\le 1$; smallest reportable $p$-value is $1/(B+1) = 0.0001$. Monte Carlo size and power validation ($n_{MC}=1,000$) is reported in Appendix Table~\\ref{tab:boot_mc}.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_cointegration.tex").write_text("\n".join(t3_lines) + "\n")
    written.append("tab_cointegration.tex")

    # 5. Table 4 / VECM Error Correction (tab_vecm_ecm.tex)
    t5 = pd.read_csv(tdir / "table5_vecm_error_correction.csv")
    tar_j = json.loads((mdir / "intraday_and_tar_results.json").read_text())
    t5_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{VECM error correction, three-variable intraday price discovery, and full-system half-lives}",
        "\\label{tab:vecm_ecm}",
        "\\fontsize{6.2}{7.4}\\selectfont\\setlength{\\tabcolsep}{1.1pt}",
        "\\begingroup",
        "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{2.35cm}rrrrrrr@{}}",
        "\\toprule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel A: Daily bivariate VECM estimates (native business-day units, \\texttt{co}, HAC $L=5$)}} \\\\",
        "System & $T_{eff}$ & $\\hat{\\alpha}_{local}$ (SE) & $p_{loc}$ & $\\hat{\\alpha}_{glob}$ (SE) & $p_{glob}$ & HL (d) & $|\\lambda_{\\max}|$ \\\\",
        "\\midrule",
    ]
    for _, r in t5.iterrows():
        sys_lbl = str(r["system"]).replace(" (Daily Bus. Days)", "").replace("Indodax-USDT-Global", "USDT-Global").replace("Indodax USDT/IDR vs BI JISDOR", "USDT/IDR vs.\\ BI JISDOR").replace(" vs ", " vs.\\ ")
        t5_lines.append(
            f"{sys_lbl} & {int(r['T_eff']):,} & {r['alpha_local_hac']:.3f} ({r['alpha_local_hac_se']:.3f}) & {_fmt_p(r['alpha_local_hac_pval'])} & {r['alpha_global_hac']:.3f} ({r['alpha_global_hac_se']:.3f}) & {_fmt_p(r['alpha_global_hac_pval'])} & {r['half_life_native_units']:.2f} & {r['max_non_unit_eig']:.4f} \\\\"
        )

    t5_lines += [
        "\\midrule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel B: 5m 3-var VECM ($[\\ln P^{IDR}_{BTC}, \\ln P^{USDT}_{BTC}, \\ln U^{IDR/USDT}]'$, 5 lags, \\texttt{co}, $L=12$)}} \\\\",
        "Sample / Equation & $T_{eff}$ & $\\hat{\\alpha}_i$ (HAC SE) & $p_{\\text{HAC}}$ & Adj.\\ Share & IS Low & IS High & HL (bars) \\\\",
        "\\midrule",
    ]
    for label_prefix, key in [
        ("Primary (All 5m)", "hf_vecm_3var_all_5m"),
        ("Active Subsample", "hf_vecm_3var_active_5m"),
        ("349d Indep-FX", "hf_vecm_indep_fx_349d_3var"),
    ]:
        v = tar_j[key]
        if v is None:
            continue
        eq_pretty = {
            "Indodax_BTCIDR": "Indodax BTC/IDR",
            "Binance_BTCUSDT": "Binance BTC/USDT",
            "Indodax_USDTIDR": "Indodax USDT/IDR",
            "Binance_USDTIDR": "Binance USDT/IDR",
        }
        hl_col = [
            f"{v['half_life_companion']:.2f}",
            f"(IRF: {v['half_life_irf_local']:.2f})",
            f"(sc: {v['half_life_scalar']:.2f})",
        ]
        for idx_m, nm in enumerate(v["names"]):
            is_b = v["hasbrouck_is_y1_bounds"][nm]
            t5_lines.append(
                f"{label_prefix}: {eq_pretty.get(nm, nm)} & {v['T_eff']:,} & {v['alpha_hac'][idx_m]:.4f} ({v['se_hac'][idx_m]:.4f}) & {_fmt_p(v['pval_hac'][idx_m])} & {v['adj_share_ml_pct'][idx_m]:.1f}\\% & {100*is_b['low']:.1f}\\% & {100*is_b['high']:.1f}\\% & {hl_col[idx_m]} \\\\"
            )

    hf_all = tar_j["hf_vecm_3var_all_5m"]
    b_seq = tar_j["hf_vecm_3var_all_5m_bootstrap_seq"]
    p_r0 = b_seq[0]["trace_boot_pval"]
    cv95_r0 = b_seq[0]["trace_boot_cv95"]
    p_r1 = b_seq[1]["trace_boot_pval"]
    p_r2 = b_seq[2]["trace_boot_pval"]
    top3_s = ", ".join(f"{x:.4f}" for x in hf_all["top3_non_unit_eigs"])
    beta_s = ", ".join(f"{x:.4f}" for x in hf_all["beta"])
    t5_lines += [
        "\\bottomrule",
        "\\end{tabular}\\endgroup",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        f"\\emph{{Notes:}} Panel~B reports the companion-matrix slowest-mode half-life ($-\\ln 2/\\ln|\\lambda_{{\\max}}| = {hf_all['half_life_companion']:.2f}$ bars, carrying $47.0\\%$ of a local shock), the local-shock ECT impulse-response half-life (IRF: {hf_all['half_life_irf_local']:.2f} bars; generalized {hf_all['half_life_irf_gen']:.2f} bars), and the scalar $1+\\beta'\\alpha$ benchmark (sc: {hf_all['half_life_scalar']:.2f} bars). In the primary 5-minute system ($T_{{eff}}={hf_all['T_eff']:,}$), Johansen trace is ${hf_all['joh_trace'][0]:,.1f}$ for $r=0$ (block-wild $p={p_r0:.4f}$, $B=499$, $b=28$, 95\\% boot CV ${cv95_r0:.2f}$), ${hf_all['joh_trace'][1]:.2f}$ for $r\\le 1$ (block-wild $p={p_r1:.4f}$), and ${hf_all['joh_trace'][2]:.2f}$ for $r\\le 2$ (block-wild $p={p_r2:.4f}$), with $\\hat{{\\beta}} = [{beta_s}]'$ and top-3 non-unit companion moduli $\\{{{top3_s}\\}}$. The active subsample removes 11,527 zero-volume bars (irregular event-time sensitivity); the 349-day Independent-FX check replaces Indodax \\texttt{{USDT/IDR}} with Binance \\texttt{{USDT/IDR}} (Nov 29, 2025--Nov 12, 2026).",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_vecm_ecm.tex").write_text("\n".join(t5_lines) + "\n")
    written.append("tab_vecm_ecm.tex")

    # 6. Historical Fees & Orderbook Route Costs (tab_fees.tex)
    fee = pd.read_csv(tdir / "historical_fee_reconstruction.csv")
    rc = pd.read_csv(tdir / "route_specific_execution_costs.csv")
    reg_short = {
        "R1_PRE_TAX_2021": "R1: Pre-tax baseline",
        "R2A_PMK68_0_30": "R2A: PMK 68 (0/30)$^\\dagger$",
        "R2B_INDODAX_PRO_CUT": "R2B: Indodax Pro cut$^\\dagger$",
        "R3_CFX_LAUNCH_PMK68": "R3: CFX fee launch",
        "R3B_PMK81_VAT12_ADJ": "R3B: PMK 81/131 VAT",
        "R4_PMK50_2025": "R4: PMK 50/2025",
        "R5_CFX_CUT_MAR2026": "R5: CFX cut (Mar 2026)",
        "R6_CFX_CUT_OCT2026": "R6: CFX cut (Oct 2026)",
    }
    fee_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Indonesian statutory crypto tax, CFX/KKI, platform commission, and route execution costs (bps)}",
        "\\label{tab:fees}",
        "\\fontsize{6.3}{7.5}\\selectfont\\setlength{\\tabcolsep}{1.8pt}",
        "\\begingroup",
        "\\begin{tabular}{@{}l>{\\raggedright\\arraybackslash}p{2.3cm}rrrrrr@{}}",
        "\\toprule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel A: Chronological fee and tax regimes (2021--2026)}} \\\\",
        "Window & Regime & M/T & VAT & PPh22 & CFX & Rte A (M/T) & Rte B (M/T) \\\\",
        "\\midrule",
    ]
    for _, r in fee.iterrows():
        win = f"{r['start_date'][:7]} to {r['end_date'][:7]}"
        lbl = reg_short.get(r["regime_id"], _tex_escape(r["regime_id"]))
        mt = f"{int(r['indodax_idr_maker_bps'])}/{int(r['indodax_idr_taker_bps'])}"
        ra = f"{r['route_a_domestic_2leg_maker_bps']:.1f}/{r['route_a_domestic_2leg_taker_bps']:.1f}"
        rb = f"{r['route_b_cross_3leg_maker_bps']:.1f}/{r['route_b_cross_3leg_taker_bps']:.1f}"
        fee_lines.append(
            f"{win} & {lbl} & {mt} & {r['asset_vat_buyer_bps']:.0f} & {r['asset_pph22_seller_bps']:.0f} & {r['cfx_idr_bps']:.3g} & {ra} & {rb} \\\\"
        )
    fee_lines += [
        "\\midrule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel B: Live order-book costs by route and trade size (Nov 13, 2026 snapshot, R6)}} \\\\",
        "Route & Scope & Size & \\multicolumn{2}{r}{Stat. (Mkr/Tkr)} & \\multicolumn{2}{r}{Depth Slip} & All-In Tkr \\\\",
        "\\midrule",
    ]
    scope_map = {
        "Route A": "Domestic 2-Leg",
        "Route B": "Cross-Exchange 3-Leg",
        "Route C": "Same-Exchange Indodax",
    }
    for _, r in rc.iterrows():
        rname = str(r["route"]).split(": ")[0]
        rscope = scope_map.get(rname, _tex_escape(str(r["route"]).split(": ")[1].split(" (")[0]))
        fee_lines.append(
            f"{_tex_escape(rname)} & {rscope} & \\${_tex_escape(r['trade_size_usd'])} & \\multicolumn{{2}}{{r}}{{{r['statutory_fee_maker_bps']:.2f}/{r['statutory_fee_taker_bps']:.2f}}} & \\multicolumn{{2}}{{r}}{{{r['snapshot_half_spread_slip_bps']:.2f}}} & {r['all_in_taker_plus_slip_bps']:.2f} \\\\"
        )
    fee_lines += [
        "\\bottomrule",
        "\\end{tabular}\\endgroup",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} $^\\dagger$The August 2023 platform fee transition (Regimes R2A--R2B) is only partially documented in public archives and is bracketed with sensitivity bounds in the empirical containment checks. Regime R6 matches published Indodax Pro rates to the fifth decimal place (0.10555\\%/0.20555\\% buy; 0.31555\\%/0.41555\\% sell; 0.2511\\%/0.2811\\% USDT). Route B and Route C calculations assume pre-funded inventory and exclude on-chain withdrawal fees.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_fees.tex").write_text("\n".join(fee_lines) + "\n")
    written.append("tab_fees.tex")

    # 7. Event Studies Table (tab_events.tex)
    ev = pd.read_csv(tdir / "table7_regulatory_event_windows.csv")
    ev_short = {
        "PMK 68/PMK.03/2022 Crypto Tax": "PMK 68/2022",
        "Binance BIDR Delisting": "BIDR Delist",
        "Indodax Security Incident": "Indodax Incid.",
        "CFX Fee Introduction (PERBA 9/2024)": "CFX Launch",
        "OJK Regulatory Transfer (POJK 27/2024)": "OJK Transfer",
        "PMK 50/2025 Tax Overhaul": "PMK 50/2025",
        "CFX First 50% Fee Reduction": "CFX 1st Cut",
        "JISDOR Schedule Shift (PADG 7/2026)": "PADG 7/2026",
        "CFX Second 50% Fee Reduction": "CFX 2nd Cut",
        "Indodax Wallet Maintenance": "Indodax Maint.$^\\dagger$",
    }
    ev_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Institutional and regulatory event windows (BTC basis, bps): controlled $\\pm 30$-day HAC OLS (primary) and joint non-overlapping $\\pm 15$-day checks}",
        "\\label{tab:events}",
        "\\fontsize{6.1}{7.3}\\selectfont\\setlength{\\tabcolsep}{1.0pt}",
        "\\begingroup",
        "\\begin{tabular}{@{}l>{\\raggedright\\arraybackslash}p{1.8cm}rrrrrr@{}}",
        "\\toprule",
        "Date & Event & $\\Delta B^{cry}_{\\text{ctrl30}}$ (SE) & $p_{\\text{HAC}}$ ($p_H$) & $\\Delta B^{cry}_{\\text{jnt15}}$ ($p_H$) & $\\Delta B^{s\\text{-}FX}_{\\text{ctrl30}}$ (SE) & $p_{\\text{HAC}}$ ($p_H$) & $\\Delta B^{s\\text{-}FX}_{\\text{jnt15}}$ ($p_H$) \\\\",
        "\\midrule",
    ]
    ev_c = ev[ev["basis_leg"] == "B_crypto"].reset_index(drop=True)
    ev_s = ev[ev["basis_leg"] == "B_stablecoin_FX"].reset_index(drop=True)
    for idx in range(len(ev_c)):
        rc_i = ev_c.iloc[idx]
        rs_i = ev_s.iloc[idx]
        lbl = ev_short.get(rc_i["label"], _tex_escape(rc_i["label"]))
        star_s = "$^*$" if rs_i["ctrl_p_holm"] < 0.05 else ""
        ev_lines.append(
            f"{rc_i['event_date']} & {lbl} & {rc_i['ctrl_diff_bps']:.2f} ({rc_i['ctrl_se_hac']:.2f}) & {rc_i['ctrl_p_hac']:.3f} ({rc_i['ctrl_p_holm']:.2f}) & {rc_i['joint15_diff_bps']:.2f} ({rc_i['joint15_p_holm']:.3f}) & {rs_i['ctrl_diff_bps']:.2f}{star_s} ({rs_i['ctrl_se_hac']:.2f}) & {rs_i['ctrl_p_hac']:.3f} ({rs_i['ctrl_p_holm']:.3f}{star_s}) & {rs_i['joint15_diff_bps']:.2f} ({rs_i['joint15_p_holm']:.2f}) \\\\"
        )
    ev_lines += [
        "\\bottomrule",
        "\\end{tabular}\\endgroup",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        "\\emph{Notes:} Primary columns ($\\Delta B_{\\text{ctrl30}}$, HAC SE, $p_{\\text{HAC}}$) report $\\pm 30$-calendar-day OLS regressions on a post-event indicator controlling for daily global BTC and JISDOR log returns with Newey--West HAC standard errors ($L=5$). Joint columns ($\\Delta B_{\\text{jnt15}}$) report a simultaneous full-sample regression using non-overlapping $\\pm 15$-calendar-day pre/post indicators for all ten events. $p_H$ adjusts across the 20-test family (10 events $\\times$ 2 BTC legs) via Holm's procedure. $^\\dagger$The October 31, 2026 maintenance event has a truncated 12-calendar-day post-window. Because placebo dates on the persistent $B^{s\\text{-}FX}$ leg also yield significant $\\pm 30$-day shifts (e.g., $-18.70\\text{ bps}$ on 2023-06-15, $p<0.0001$), the November 1, 2024 CFX Launch shift ($^*$) is a descriptive post-event association rather than an identified causal effect.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_events.tex").write_text("\n".join(ev_lines) + "\n")
    written.append("tab_events.tex")

    # 8. Robustness & Falsification Table (tab_robustness.tex)
    t8 = pd.read_csv(tdir / "table8_synchronization_sensitivity.csv")
    t9 = pd.read_csv(tdir / "table9_falsification_tests.csv")
    vwap_j = json.loads((mdir / "jisdor_window_vwap.json").read_text())
    t8_names = {
        "Primary_0m_JISDOR": "Primary 0m JISDOR",
        "ExAnte_Minus15m_JISDOR": "Ex-ante $-15\\text{m}$ JISDOR",
        "Post_Plus5m_JISDOR": "Post $+5\\text{m}$ JISDOR",
        "Post_Plus15m_JISDOR": "Post $+15\\text{m}$ JISDOR",
        "NextDay_JISDOR_Lead": "Next-day JISDOR lead",
        "Mismatched_2359UTC_Close": "23:59 UTC close mismatch",
        "SpotFX_Yahoo_0m": "Spot FX (Yahoo) 0m",
        "ECBFX_Frankfurter_0m": "ECB FX (Frankfurter) 0m",
    }
    t89_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Synchronization sensitivity, FX benchmark robustness, and falsification suite (BTC)}",
        "\\label{tab:robustness}",
        "\\fontsize{6.6}{7.8}\\selectfont\\setlength{\\tabcolsep}{1.6pt}",
        "\\begingroup",
        "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{3.0cm}rrrrrrr@{}}",
        "\\toprule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel A: Timestamp offset, JISDOR-window averaging, and FX benchmark sensitivity}} \\\\",
        "Specification & $N$ & Mean $B^{tot}$ & SD $B^{tot}$ & Mean $B^{cry}$ & SD $B^{cry}$ & EG $t$ & Trace / Share \\\\",
        "\\midrule",
    ]
    for _, r in t8.iterrows():
        lbl = t8_names.get(r["specification"], _tex_escape(r["specification"]))
        t89_lines.append(
            f"{lbl} & {int(r['n_obs']):,} & {r['mean_b_total_bps']:.2f} & {r['sd_b_total_bps']:.2f} & {r['mean_b_crypto_bps']:.2f} & {r['sd_b_crypto_bps']:.2f} & {r['eg_t_stat']:.3f} & {r['joh_trace_ra']:.2f} \\\\"
        )
    v_u = vwap_j["usdt_vwap_only"]
    v_3 = vwap_j["all_3_legs_vwap"]
    t89_lines.append(
        f"JISDOR-win.\\ VWAP (USDT only)$^\\dagger$ & {v_u['n_obs']:,} & {v_u['mean_b_total_bps']:.2f} & {v_u['sd_b_total_bps']:.2f} & {v_u['mean_b_crypto_bps']:.2f} & {v_u['sd_b_crypto_bps']:.2f} & -- & {v_u['var_share_sfx_pct']:.1f}\\%$^\\dagger$ \\\\"
    )
    t89_lines.append(
        f"JISDOR-win.\\ VWAP (all 3 legs)$^\\dagger$ & {v_3['n_obs']:,} & {v_3['mean_b_total_bps']:.2f} & {v_3['sd_b_total_bps']:.2f} & {v_3['mean_b_crypto_bps']:.2f} & {v_3['sd_b_crypto_bps']:.2f} & -- & {v_3['var_share_sfx_pct']:.1f}\\%$^\\dagger$ \\\\"
    )
    t9_names = {
        "Omitted_FX_Unadjusted_BTC_IDR_vs_USDT": ("Omitted FX (BTC/IDR vs.\\ USDT)", "Fail cointegration"),
        "Placebo_Wrong_FX_EURUSD": ("Wrong-FX placebo (EUR/USD)", "Fail cointegration"),
        "Placebo_CrossAsset_BTCIDR_vs_XRP_JISDOR": ("Cross-asset (BTC/IDR vs.\\ XRP$\\times$JISDOR)", "Mixed (EG fail)"),
        "Deliberate_30d_Time_Mismatch_BTC": ("30-day time mismatch (BTC)", "SD explodes"),
        "Placebo_Break_2023_06_15_CalmSubsample": ("Calm-period break (2023-06-15)", "No Chow break"),
    }
    t89_lines += [
        "\\midrule",
        "\\multicolumn{8}{@{}l}{\\textbf{Panel B: Negative controls and falsification tests}} \\\\",
        "Falsification Test & $N$ & SD (bps) & EG $t$ / $F$ & $p$-val & Trace & Rej.\\ 5\\% & Expected Outcome \\\\",
        "\\midrule",
    ]
    for _, r in t9.iterrows():
        tr = f"{r['joh_trace_ra']:.2f}" if pd.notna(r["joh_trace_ra"]) else "--"
        t_lbl, exp_lbl = t9_names.get(r["test"], (_tex_escape(r["test"]), _tex_escape(r["expected_outcome"])))
        rej = "Yes" if bool(r["rejected_no_coint_5pct"]) else "No"
        t89_lines.append(
            f"{t_lbl} & {int(r['n_obs']):,} & {r['spread_sd_bps']:.1f} & {r['eg_t_stat']:.3f} & {_fmt_p(r['eg_pval'])} & {tr} & {rej} & {exp_lbl} \\\\"
        )
    t89_lines += [
        "\\bottomrule",
        "\\end{tabular}\\endgroup",
        "\\begin{minipage}{\\textwidth}\\footnotesize\\vspace{3pt}",
        f"\\emph{{Notes:}} $^\\dagger$For the two JISDOR monitoring-window VWAP rows, the final column reports the resulting $\\mathrm{{Var}}(B^{{s\\text{{-}}FX}})/\\mathrm{{Var}}(B^{{total}})$ share (baseline snapshot share: {vd['BTC']['gross_share_sf_pct']:.2f}\\%). In Panel~B, the 30-day mismatch retains algebraic cointegration because a fixed lag of an $I(1)$ price differs by a stationary 30-day return, while inflating dispersion $27.5\\times$.",
        "\\end{minipage}",
        "\\end{table}",
    ]
    (out_dir / "tab_robustness.tex").write_text("\n".join(t89_lines) + "\n")
    written.append("tab_robustness.tex")

    return written
