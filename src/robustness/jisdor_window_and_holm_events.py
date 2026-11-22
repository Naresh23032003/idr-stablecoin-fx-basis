"""JISDOR intraday monitoring-window VWAP/TWAP check and Holm-adjusted event tests."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests


def parse_wib_window(window_str: str) -> tuple[int, int]:
    parts = str(window_str).replace("WIB", "").strip().split("-")
    s_h, s_m = map(int, parts[0].strip().split(":"))
    e_h, e_m = map(int, parts[1].strip().split(":"))
    return s_h * 60 + s_m, e_h * 60 + e_m


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    btc = pd.read_csv(root / "data/processed/btc_jisdor_sync_primary.csv")
    p5 = pd.read_csv(root / "data/processed/btc_5m_panel_2021_2026.csv.gz")
    t7 = pd.read_csv(root / "results/tables/table7_regulatory_event_windows.csv")

    p5["ts"] = pd.to_datetime(p5["timestamp_utc"], utc=True)
    p5["wib"] = p5["ts"] + pd.Timedelta(hours=7)
    p5["wib_date"] = p5["wib"].dt.strftime("%Y-%m-%d")
    p5["wib_min"] = p5["wib"].dt.hour * 60 + p5["wib"].dt.minute

    win_map = {w: parse_wib_window(w) for w in btc["monitoring_window_wib"].unique()}
    btc["win_start"] = btc["monitoring_window_wib"].map(lambda w: win_map[w][0])
    btc["win_end"] = btc["monitoring_window_wib"].map(lambda w: win_map[w][1])

    p5_by_date = {d: g for d, g in p5.groupby("wib_date")}
    vwap_u, twap_u, vwap_bi, vwap_bn = [], [], [], []
    for row in btc.itertuples():
        g = p5_by_date.get(row.date)
        sub = g[(g["wib_min"] >= row.win_start) & (g["wib_min"] <= row.win_end)] if g is not None else pd.DataFrame()
        if sub.empty:
            vwap_u.append(np.nan); twap_u.append(np.nan); vwap_bi.append(np.nan); vwap_bn.append(np.nan)
            continue
        twap_u.append(sub["indodax_usdtidr"].mean())
        w_u = sub["indodax_usdtidr_vol"].values
        vwap_u.append(np.average(sub["indodax_usdtidr"].values, weights=w_u) if w_u.sum() > 0 else sub["indodax_usdtidr"].mean())
        w_bi = sub["indodax_btcidr_vol"].values
        vwap_bi.append(np.average(sub["indodax_btcidr"].values, weights=w_bi) if w_bi.sum() > 0 else sub["indodax_btcidr"].mean())
        w_bn = sub["binance_btcusdt_vol"].values
        vwap_bn.append(np.average(sub["binance_btcusdt"].values, weights=w_bn) if w_bn.sum() > 0 else sub["binance_btcusdt"].mean())

    b_sfx_vwap = 1e4 * (np.log(np.array(vwap_u)) - np.log(btc["jisdor_idr_usd"].values))
    b_sfx_twap = 1e4 * (np.log(np.array(twap_u)) - np.log(btc["jisdor_idr_usd"].values))
    b_tot_vwap = 1e4 * (np.log(np.array(vwap_bi)) - np.log(np.array(vwap_bn)) - np.log(btc["jisdor_idr_usd"].values))
    b_cry_vwap = 1e4 * (np.log(np.array(vwap_bi)) - np.log(np.array(vwap_bn)) - np.log(np.array(vwap_u)))

    v_sfx0 = btc["b_stablecoin_fx_bps"].var(ddof=1)
    for label, bsfx, bcry, btot in [
        ("VWAP USDT/IDR + snapshot B_crypto", b_sfx_vwap, btc["b_crypto_bps"].values, btc["b_crypto_bps"].values + b_sfx_vwap),
        ("TWAP USDT/IDR + snapshot B_crypto", b_sfx_twap, btc["b_crypto_bps"].values, btc["b_crypto_bps"].values + b_sfx_twap),
        ("Full-window VWAP all legs", b_sfx_vwap, b_cry_vwap, b_tot_vwap),
    ]:
        vs, vc, vt = np.var(bsfx, ddof=1), np.var(bcry, ddof=1), np.var(btot, ddof=1)
        print(f"{label}: B_sFX mean={np.mean(bsfx):.2f}, sd={np.std(bsfx, ddof=1):.2f}, var_ratio={100*vs/v_sfx0:.2f}%, share={100*vs/vt:.2f}%")

    btc["_dt"] = pd.to_datetime(btc["date"])
    btc["dln_btc"] = btc["ln_p_usdt"].diff()
    btc["dln_fx"] = btc["ln_s_fx"].diff()
    _, t7["welch_p_holm"], _, _ = multipletests(t7["welch_pval"].values, method="holm")
    _, t7["mw_p_holm"], _, _ = multipletests(t7["mw_u_pval"].values, method="holm")

    reg_b, reg_p = [], []
    for row in t7.itertuples():
        ev_dt = pd.Timestamp(row.event_date)
        col = "b_crypto_bps" if row.basis_leg == "B_crypto" else "b_stablecoin_fx_bps"
        sub = btc[(btc["_dt"] >= ev_dt - pd.Timedelta(days=30)) & (btc["_dt"] < ev_dt + pd.Timedelta(days=30))][[col, "_dt", "dln_btc", "dln_fx"]].dropna()
        sub["post"] = (sub["_dt"] >= ev_dt).astype(float)
        m = sm.OLS(sub[col], sm.add_constant(sub[["post", "dln_btc", "dln_fx"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
        reg_b.append(float(m.params["post"]))
        reg_p.append(float(m.pvalues["post"]))
    t7["ctrl_diff_bps"] = reg_b
    t7["ctrl_p_hac"] = reg_p
    _, t7["ctrl_p_holm"], _, _ = multipletests(t7["ctrl_p_hac"].values, method="holm")
    print("\nHolm-adjusted event windows:")
    print(t7[["event_date", "basis_leg", "diff_mean_bps", "welch_pval", "welch_p_holm", "ctrl_diff_bps", "ctrl_p_hac", "ctrl_p_holm"]].to_string(index=False))


if __name__ == "__main__":
    main()
