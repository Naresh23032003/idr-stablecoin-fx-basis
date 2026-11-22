"""Basis variable construction, unit checks, and identity verification."""
from __future__ import annotations

from typing import Dict
import numpy as np
import pandas as pd

BPS_MULT = 10_000.0


def verify_units_and_bounds(
    p_idr: pd.Series,
    p_usdt: pd.Series,
    u_idr: pd.Series,
    s_fx: pd.Series,
    asset: str = "BTC",
) -> None:
    """Assert strictly positive prices and plausible relative quote magnitudes (no inverted pairs)."""
    for name, ser in [("p_idr", p_idr), ("p_usdt", p_usdt), ("u_idr", u_idr), ("s_fx", s_fx)]:
        valid = ser.dropna()
        if len(valid) == 0:
            raise ValueError(f"Empty valid series for {name}")
        if (valid <= 0).any():
            raise ValueError(f"Non-positive prices detected in {name}")

    # Dimension sanity: u_idr and s_fx should be IDR per USD/USDT (~10,000 to 25,000 in 2021-2026)
    med_u = float(u_idr.dropna().median())
    med_s = float(s_fx.dropna().median())
    if not (5_000.0 <= med_u <= 30_000.0):
        raise ValueError(f"USDT/IDR median {med_u} outside plausible IDR/USDT range (possible inversion)")
    if not (5_000.0 <= med_s <= 30_000.0):
        raise ValueError(f"USD/IDR median {med_s} outside plausible IDR/USD range (possible inversion)")

    # Cross-rate check: p_idr / (p_usdt * u_idr) should be near 1.0 (e.g. within [0.7, 1.3])
    ratio = (p_idr / (p_usdt * u_idr)).dropna()
    med_ratio = float(ratio.median())
    if not (0.85 <= med_ratio <= 1.15):
        raise ValueError(f"{asset} implied cross-ratio median {med_ratio:.4f} deviates >15% from unity (unit mismatch)")


def compute_basis_decomposition(
    df: pd.DataFrame,
    p_idr_col: str = "indodax_close_idr",
    p_usdt_col: str = "binance_close_usdt",
    u_idr_col: str = "indodax_usdt_idr",
    s_fx_col: str = "jisdor_idr_usd",
    asset: str = "BTC",
    usdt_usd_col: str | None = None,
) -> pd.DataFrame:
    """Compute exact 3-leg log basis decomposition in basis points and verify algebraic identity."""
    out = df.copy()
    verify_units_and_bounds(out[p_idr_col], out[p_usdt_col], out[u_idr_col], out[s_fx_col], asset=asset)

    out["ln_p_idr"] = np.log(out[p_idr_col])
    out["ln_p_usdt"] = np.log(out[p_usdt_col])
    out["ln_u_idr"] = np.log(out[u_idr_col])
    out["ln_s_fx"] = np.log(out[s_fx_col])

    out["ln_p_global_fx"] = out["ln_p_usdt"] + out["ln_s_fx"]
    out["ln_p_global_usdt"] = out["ln_p_usdt"] + out["ln_u_idr"]

    out["b_total_bps"] = BPS_MULT * (out["ln_p_idr"] - out["ln_p_usdt"] - out["ln_s_fx"])
    out["b_crypto_bps"] = BPS_MULT * (out["ln_p_idr"] - out["ln_p_usdt"] - out["ln_u_idr"])
    out["b_stablecoin_fx_bps"] = BPS_MULT * (out["ln_u_idr"] - out["ln_s_fx"])

    # Verify accounting identity per row
    err = np.abs(out["b_total_bps"] - (out["b_crypto_bps"] + out["b_stablecoin_fx_bps"]))
    max_err = float(err.dropna().max())
    if max_err > 1e-9:
        raise AssertionError(f"Basis accounting identity violated: max_err={max_err}")

    if usdt_usd_col and usdt_usd_col in out.columns:
        valid_peg = out[usdt_usd_col].notna() & (out[usdt_usd_col] > 0)
        out.loc[valid_peg, "usd_usdt_wedge_bps"] = BPS_MULT * np.log(out.loc[valid_peg, usdt_usd_col])
        out.loc[valid_peg, "b_total_usd_adj_bps"] = out.loc[valid_peg, "b_total_bps"] - out.loc[valid_peg, "usd_usdt_wedge_bps"]

    return out


def verify_variance_identity(b_total: pd.Series, b_crypto: pd.Series, b_sf: pd.Series) -> Dict[str, float]:
    """Verify Var(B_total) = Var(B_crypto) + Var(B_sf) + 2*Cov(B_crypto, B_sf)."""
    df = pd.DataFrame({"t": b_total, "c": b_crypto, "s": b_sf}).dropna()
    var_t = float(df["t"].var(ddof=1))
    var_c = float(df["c"].var(ddof=1))
    var_s = float(df["s"].var(ddof=1))
    cov_cs = float(df["c"].cov(df["s"]))
    corr_cs = float(df["c"].corr(df["s"]))
    reconstructed = var_c + var_s + 2.0 * cov_cs
    if abs(var_t - reconstructed) > 1e-6:
        raise AssertionError(f"Variance identity failed: {var_t} vs {reconstructed}")
    return {
        "var_total": var_t,
        "var_crypto": var_c,
        "var_stablecoin_fx": var_s,
        "cov_crypto_sf": cov_cs,
        "corr_crypto_sf": corr_cs,
        "variance_identity_abs_diff": abs(var_t - reconstructed),
        "gross_share_crypto_pct": 100.0 * var_c / var_t if var_t > 0 else float("nan"),
        "gross_share_sf_pct": 100.0 * var_s / var_t if var_t > 0 else float("nan"),
    }
