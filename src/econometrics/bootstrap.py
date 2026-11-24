"""Null-imposed restricted VECM dependent block-wild bootstrap for sequential Johansen rank tests."""
from __future__ import annotations

import math
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List, Sequence
import numpy as np
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen


def _run_boot_chunk(args: tuple) -> tuple[List[float], List[float], int]:
    """Deterministic worker for parallel large-sample block-wild bootstrap chunks."""
    (
        child_seeds, resid_centered, mu_hat, Pi_T, G_T,
        init_Y0, init_dY, init_Yk, N, n, p, k, T_eff,
        n_blocks, b_len, null_rank, det_order,
    ) = args
    tr_list: List[float] = []
    mx_list: List[float] = []
    n_fail = 0
    for s in child_seeds:
        rng = np.random.default_rng(s)
        w_blocks = rng.choice(np.array([-1.0, 1.0]), size=n_blocks)
        w = np.repeat(w_blocks, b_len)[:T_eff]
        u_star = resid_centered * w[:, None]
        rhs = mu_hat[None, :] + u_star

        dY_star = np.empty((N - 1, n), dtype=float)
        if p > 0:
            dY_star[:p, :] = init_dY
        dY_star[p:, :] = rhs

        if null_rank == 0:
            for t in range(p, N - 1):
                acc = dY_star[t].copy()
                for i in range(p):
                    acc += dY_star[t - 1 - i] @ G_T[i]
                dY_star[t] = acc
            Y_star = np.empty((N, n), dtype=float)
            Y_star[0, :] = init_Y0
            Y_star[1:, :] = init_Y0 + np.cumsum(dY_star, axis=0)
        else:
            Y_star = np.empty((N, n), dtype=float)
            Y_star[:k, :] = init_Yk
            for t in range(k, N):
                dy_t = rhs[t - k] + Y_star[t - 1] @ Pi_T
                for i in range(p):
                    dy_t += dY_star[t - 2 - i] @ G_T[i]
                dY_star[t - 1] = dy_t
                Y_star[t] = Y_star[t - 1] + dy_t

        try:
            tr_b_all, mx_b_all = _fast_johansen_stats(Y_star, det_order=det_order, k_ar_diff=p)
            tr_b = float(tr_b_all[null_rank])
            mx_b = float(mx_b_all[null_rank])
            if np.isfinite(tr_b) and np.isfinite(mx_b):
                tr_list.append(tr_b)
                mx_list.append(mx_b)
            else:
                n_fail += 1
        except Exception:
            n_fail += 1
    return tr_list, mx_list, n_fail


def _fast_johansen_stats(Y: np.ndarray, det_order: int = 0, k_ar_diff: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Compute Johansen trace and max-eigenvalue statistics for all ranks r=0..n-1."""
    res = coint_johansen(Y, det_order=det_order, k_ar_diff=k_ar_diff)
    return np.asarray(res.lr1, dtype=float), np.asarray(res.lr2, dtype=float)


def bootstrap_single_rank(
    Y: np.ndarray,
    null_rank: int = 0,
    det_order: int = 0,
    k_ar_diff: int = 1,
    n_boot: int = 9999,
    seed: int = 20261113,
    block_len: int | None = None,
) -> Dict[str, Any]:
    """Null-imposed restricted VECM block-wild bootstrap for H0: rank(Pi) <= null_rank.

    Follows Cavaliere, Rahbek & Taylor (2010, 2012) and Paparoditis & Politis (2003):
      - For null_rank == 0: restricted VAR(k_ar_diff) in first differences (Pi = 0).
      - For null_rank >= 1: ML-estimated reduced-rank VECM with coint_rank = null_rank.
    Centered residual vectors are multiplied by block-level Rademacher weights w_m in {-1, +1}
    of block length b = round(T_eff^{1/4}) by default, preserving contemporaneous cross-market
    covariance Sigma_u, ARCH/GARCH volatility clustering, and within-block serial correlation.
    """
    Y = np.asarray(Y, dtype=float)
    Y = Y[np.all(np.isfinite(Y), axis=1)]
    N, n = Y.shape
    if not (0 <= null_rank < n):
        raise ValueError(f"null_rank={null_rank} must satisfy 0 <= null_rank < n={n}")

    p = int(k_ar_diff)
    k = p + 1
    dY = np.diff(Y, axis=0)
    T_eff = len(dY) - p
    if T_eff < 10:
        raise ValueError(f"Insufficient effective observations T_eff={T_eff} for bootstrap")

    tr_all_obs, mx_all_obs = _fast_johansen_stats(Y, det_order=det_order, k_ar_diff=p)
    trace_obs = float(tr_all_obs[null_rank])
    max_obs = float(mx_all_obs[null_rank])

    b_len = int(block_len) if block_len is not None else max(1, int(round(T_eff ** 0.25)))
    n_blocks = int(math.ceil(T_eff / b_len))

    det_str = {-1: "n", 0: "co", 1: "lo"}.get(det_order, "co")

    if null_rank == 0:
        dep = dY[p:]
        cols = []
        if det_order >= 0:
            cols.append(np.ones(T_eff))
        for i in range(1, p + 1):
            cols.append(dY[p - i : len(dY) - i])
        X = np.column_stack(cols) if cols else np.empty((T_eff, 0))
        B_hat, _, _, _ = np.linalg.lstsq(X, dep, rcond=None)
        resid = dep - X @ B_hat
        col_ptr = 0
        mu_hat = np.zeros(n, dtype=float)
        if det_order >= 0:
            mu_hat = B_hat[0, :]
            col_ptr = 1
        gammas = [B_hat[col_ptr + i * n : col_ptr + (i + 1) * n, :].T for i in range(p)]
        Pi_hat = np.zeros((n, n), dtype=float)
    else:
        vecm_res = VECM(Y, k_ar_diff=p, coint_rank=null_rank, deterministic=det_str).fit()
        resid = vecm_res.resid
        Pi_hat = vecm_res.alpha @ vecm_res.beta.T  # (n, n)
        mu_hat = vecm_res.const[:, 0] if (hasattr(vecm_res, "const") and vecm_res.const.size > 0) else np.zeros(n, dtype=float)
        gammas = [vecm_res.gamma[:, i * n : (i + 1) * n] for i in range(p)]

    resid_centered = resid - resid.mean(axis=0, keepdims=True)
    rng = np.random.default_rng(seed)
    trace_boot = np.empty(n_boot, dtype=float)
    max_boot = np.empty(n_boot, dtype=float)
    n_failed = 0
    valid_count = 0

    init_Y0 = Y[0, :]
    init_dY = dY[:p, :]
    init_Yk = Y[:k, :]
    Pi_T = Pi_hat.T
    G_T = [g.T for g in gammas]

    # Use deterministic parallel workers for large high-frequency panels (N >= 50,000)
    n_workers = min(8, os.cpu_count() or 1)
    if N >= 50_000 and n_workers > 1 and n_boot >= 20:
        child_seeds = np.random.SeedSequence(seed).spawn(n_boot)
        chunk_size = int(math.ceil(n_boot / n_workers))
        chunks = [
            (
                child_seeds[i : i + chunk_size],
                resid_centered, mu_hat, Pi_T, G_T,
                init_Y0, init_dY, init_Yk, N, n, p, k, T_eff,
                n_blocks, b_len, null_rank, det_order,
            )
            for i in range(0, n_boot, chunk_size)
        ]
        tr_all_list: List[float] = []
        mx_all_list: List[float] = []
        with ProcessPoolExecutor(max_workers=n_workers) as ex:
            for tr_c, mx_c, nf_c in ex.map(_run_boot_chunk, chunks):
                tr_all_list.extend(tr_c)
                mx_all_list.extend(mx_c)
                n_failed += nf_c
        valid_count = len(tr_all_list)
        tr_arr = np.asarray(tr_all_list, dtype=float)
        mx_arr = np.asarray(mx_all_list, dtype=float)
    else:
        for _ in range(n_boot):
            w_blocks = rng.choice(np.array([-1.0, 1.0]), size=n_blocks)
            w = np.repeat(w_blocks, b_len)[:T_eff]
            u_star = resid_centered * w[:, None]
            rhs = mu_hat[None, :] + u_star

            dY_star = np.empty((N - 1, n), dtype=float)
            if p > 0:
                dY_star[:p, :] = init_dY
            dY_star[p:, :] = rhs

            if null_rank == 0:
                for t in range(p, N - 1):
                    acc = dY_star[t].copy()
                    for i in range(p):
                        acc += dY_star[t - 1 - i] @ G_T[i]
                    dY_star[t] = acc
                Y_star = np.empty((N, n), dtype=float)
                Y_star[0, :] = init_Y0
                Y_star[1:, :] = init_Y0 + np.cumsum(dY_star, axis=0)
            else:
                Y_star = np.empty((N, n), dtype=float)
                Y_star[:k, :] = init_Yk
                for t in range(k, N):
                    dy_t = rhs[t - k] + Y_star[t - 1] @ Pi_T
                    for i in range(p):
                        dy_t += dY_star[t - 2 - i] @ G_T[i]
                    dY_star[t - 1] = dy_t
                    Y_star[t] = Y_star[t - 1] + dy_t

            try:
                tr_b_all, mx_b_all = _fast_johansen_stats(Y_star, det_order=det_order, k_ar_diff=p)
                tr_b = float(tr_b_all[null_rank])
                mx_b = float(mx_b_all[null_rank])
                if np.isfinite(tr_b) and np.isfinite(mx_b):
                    trace_boot[valid_count] = tr_b
                    max_boot[valid_count] = mx_b
                    valid_count += 1
                else:
                    n_failed += 1
            except Exception:
                n_failed += 1

        tr_arr = trace_boot[:valid_count]
        mx_arr = max_boot[:valid_count]

    p_trace = (1.0 + float(np.sum(tr_arr >= trace_obs))) / (valid_count + 1.0)
    p_max = (1.0 + float(np.sum(mx_arr >= max_obs))) / (valid_count + 1.0)
    mc_se_trace = math.sqrt(p_trace * (1.0 - p_trace) / valid_count)
    mc_se_max = math.sqrt(p_max * (1.0 - p_max) / valid_count)

    return {
        "method": "null_imposed_restricted_vecm_block_wild_bootstrap",
        "null_hypothesis": f"H0: rank(Pi) <= {null_rank}" if null_rank > 0 else "H0: rank(Pi) = 0",
        "null_rank": int(null_rank),
        "deterministic_spec": det_str,
        "block_len": int(b_len),
        "n_levels": int(N),
        "T_eff": int(T_eff),
        "n_vars": int(n),
        "det_order": int(det_order),
        "k_ar_diff": int(p),
        "n_boot_requested": int(n_boot),
        "n_boot_valid": int(valid_count),
        "n_failed": int(n_failed),
        "seed": int(seed),
        "trace_obs": float(trace_obs),
        "trace_boot_pval": float(p_trace),
        "trace_mc_se": float(mc_se_trace),
        "trace_boot_cv90": float(np.quantile(tr_arr, 0.90)),
        "trace_boot_cv95": float(np.quantile(tr_arr, 0.95)),
        "trace_boot_cv99": float(np.quantile(tr_arr, 0.99)),
        "maxeig_obs": float(max_obs),
        "maxeig_boot_pval": float(p_max),
        "maxeig_mc_se": float(mc_se_max),
        "maxeig_boot_cv90": float(np.quantile(mx_arr, 0.90)),
        "maxeig_boot_cv95": float(np.quantile(mx_arr, 0.95)),
        "maxeig_boot_cv99": float(np.quantile(mx_arr, 0.99)),
    }


def sequential_vecm_block_wild_bootstrap(
    Y: np.ndarray,
    det_order: int = 0,
    k_ar_diff: int = 1,
    n_boot: int = 9999,
    seed: int = 20261113,
    block_len: int | None = None,
    ranks: Sequence[int] | None = None,
) -> List[Dict[str, Any]]:
    """Run sequential null-imposed block-wild bootstrap across r_0 = 0, ..., n-1."""
    Y = np.asarray(Y, dtype=float)
    Y = Y[np.all(np.isfinite(Y), axis=1)]
    n = Y.shape[1]
    target_ranks = list(range(n)) if ranks is None else list(ranks)
    out = []
    for r0 in target_ranks:
        out.append(
            bootstrap_single_rank(
                Y,
                null_rank=r0,
                det_order=det_order,
                k_ar_diff=k_ar_diff,
                n_boot=n_boot,
                seed=seed + r0 * 10007,
                block_len=block_len,
            )
        )
    return out


def null_imposed_vecm_residual_bootstrap(
    Y: np.ndarray,
    det_order: int = 0,
    k_ar_diff: int = 1,
    n_boot: int = 9999,
    seed: int = 20261113,
    block_len: int | None = None,
) -> Dict[str, Any]:
    """Backward-compatible entry point for H0: rank(Pi) = 0 block-wild bootstrap."""
    return bootstrap_single_rank(
        Y,
        null_rank=0,
        det_order=det_order,
        k_ar_diff=k_ar_diff,
        n_boot=n_boot,
        seed=seed,
        block_len=block_len,
    )


def evaluate_bootstrap_size_and_power(
    sample_sizes: List[int] = (25, 100, 500),
    n_mc: int = 150,
    n_boot: int = 299,
    seed: int = 20261113,
    phi_ar: float = 0.20,
    block_len: int | None = None,
    innov_dist: str = "normal",
) -> List[Dict[str, Any]]:
    """Controlled DGP Monte Carlo validation of empirical size (rank=0) and power (rank=1)
    under GARCH(1,1) conditional heteroskedasticity and AR(1) serial correlation.
    """
    rng = np.random.default_rng(seed)
    results = []
    corr_mat = np.array([[1.0, 0.944], [0.944, 1.0]])
    L_corr = np.linalg.cholesky(corr_mat)
    omega_g = 0.05 * 0.0009
    alpha_g = 0.12
    beta_g = 0.83

    for T in sample_sizes:
        for true_rank in (0, 1):
            rej_asymp_5 = 0
            rej_ra_5 = 0
            rej_boot_5 = 0
            n_failed = 0
            for m in range(n_mc):
                burn = 80
                tot = T + burn
                if innov_dist == "t5":
                    raw_z = rng.standard_t(df=5, size=(tot, 2)) / math.sqrt(5.0 / 3.0)
                else:
                    raw_z = rng.standard_normal((tot, 2))
                z = raw_z @ L_corr.T
                h = np.full(tot, 0.0009, dtype=float)
                eps = np.zeros((tot, 2), dtype=float)
                u = np.zeros((tot, 2), dtype=float)
                for t in range(1, tot):
                    h[t] = omega_g + alpha_g * (eps[t - 1, 0] ** 2) + beta_g * h[t - 1]
                    eps[t] = math.sqrt(h[t]) * z[t]
                    u[t] = phi_ar * u[t - 1] + eps[t]

                Y = np.zeros((tot, 2), dtype=float)
                for t in range(1, tot):
                    if true_rank == 0:
                        Y[t] = Y[t - 1] + u[t]
                    else:
                        ect = Y[t - 1, 0] - Y[t - 1, 1]
                        Y[t, 0] = Y[t - 1, 0] - 0.35 * ect + u[t, 0]
                        Y[t, 1] = Y[t - 1, 1] + u[t, 1]
                Y_samp = Y[burn:]
                try:
                    res = coint_johansen(Y_samp, det_order=0, k_ar_diff=1)
                    tr_orig = float(res.lr1[0])
                    cv_95 = float(res.cvt[0, 1])
                    T_eff = T - 2
                    ra_factor = (T_eff - 4) / T_eff
                    if tr_orig > cv_95:
                        rej_asymp_5 += 1
                    if ra_factor * tr_orig > cv_95:
                        rej_ra_5 += 1
                    bres = bootstrap_single_rank(
                        Y_samp,
                        null_rank=0,
                        det_order=0,
                        k_ar_diff=1,
                        n_boot=n_boot,
                        seed=seed + m + T * 1000 + true_rank * 100000,
                        block_len=block_len,
                    )
                    if bres["trace_boot_pval"] < 0.05:
                        rej_boot_5 += 1
                except Exception:
                    n_failed += 1

            n_ok = max(1, n_mc - n_failed)
            p_a = rej_asymp_5 / n_ok
            p_ra = rej_ra_5 / n_ok
            p_b = rej_boot_5 / n_ok
            results.append(
                {
                    "T": int(T),
                    "true_rank": int(true_rank),
                    "dgp": f"GARCH(1,1)+AR(1)(phi={phi_ar},{innov_dist})",
                    "block_len": int(block_len) if block_len is not None else max(1, int(round((T - 2) ** 0.25))),
                    "metric": "empirical_size" if true_rank == 0 else "empirical_power",
                    "n_mc": int(n_mc),
                    "n_ok": int(n_ok),
                    "n_failed": int(n_failed),
                    "n_boot": int(n_boot),
                    "rej_rate_asymptotic_5pct": round(p_a, 4),
                    "mc_se_asymptotic": round(math.sqrt(p_a * (1.0 - p_a) / n_ok), 4),
                    "rej_rate_reinsel_ahn_5pct": round(p_ra, 4),
                    "mc_se_reinsel_ahn": round(math.sqrt(p_ra * (1.0 - p_ra) / n_ok), 4),
                    "rej_rate_bootstrap_5pct": round(p_b, 4),
                    "mc_se_bootstrap": round(math.sqrt(p_b * (1.0 - p_b) / n_ok), 4),
                }
            )
    return results
