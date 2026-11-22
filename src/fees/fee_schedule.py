"""Historical Indonesian tax, CFX, and exchange transaction-cost reconstruction (2021-2026)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd


@dataclass(frozen=True)
class FeeRegime:
    regime_id: str
    start_date: str
    end_date: str
    label: str
    # Indodax IDR pair base service commission (before/inclusive of service VAT as documented)
    indodax_idr_maker_bps: float
    indodax_idr_taker_bps: float
    indodax_commission_vat_included: bool
    indodax_service_vat_rate: float  # effective VAT on service fee when not included (0.11 = 11%)
    # Indodax USDT pair base commission
    indodax_usdt_maker_bps: Optional[float]
    indodax_usdt_taker_bps: Optional[float]
    # Statutory asset taxes (PMK 68/2022, PMK 81/2024, PMK 50/2025)
    asset_vat_buyer_bps: float
    asset_pph22_seller_bps: float
    offshore_tax_bps: float
    # CFX + KKI bourse & clearing fee (VAT-inclusive)
    cfx_idr_bps: float
    cfx_usdt_bps: float
    # Binance spot commission (bps)
    binance_std_bps: float
    binance_bnb_bps: float
    # Verification & confidence
    verification_status: str
    confidence_level: str
    primary_sources: str
    uncertainty_notes: str


HISTORICAL_REGIMES: List[FeeRegime] = [
    FeeRegime(
        regime_id="R1_PRE_TAX_2021",
        start_date="2021-01-01",
        end_date="2022-04-30",
        label="Pre-Tax Baseline (0% Maker / 0.30% Taker)",
        indodax_idr_maker_bps=0.0,
        indodax_idr_taker_bps=30.0,
        indodax_commission_vat_included=True,
        indodax_service_vat_rate=0.0,
        indodax_usdt_maker_bps=0.0,
        indodax_usdt_taker_bps=30.0,
        asset_vat_buyer_bps=0.0,
        asset_pph22_seller_bps=0.0,
        offshore_tax_bps=0.0,
        cfx_idr_bps=0.0,
        cfx_usdt_bps=0.0,
        binance_std_bps=10.0,
        binance_bnb_bps=7.5,
        verification_status="VERIFIED_SECONDARY_AND_ARCHIVE",
        confidence_level="HIGH (IDR) / MEDIUM (USDT)",
        primary_sources="Indodax 2021 maker-free schedule; CNBC Indonesia (2022)",
        uncertainty_notes="Indodax 0% maker / 0.30% taker documented on IDR pairs; USDT pair exact pre-2023 tier less documented.",
    ),
    FeeRegime(
        regime_id="R2A_PMK68_0_30",
        start_date="2022-05-01",
        end_date="2023-08-22",
        label="PMK 68/2022 Initial (0% Maker / 0.30% Taker + 0.11% PPN + 0.10% PPh)",
        indodax_idr_maker_bps=0.0,
        indodax_idr_taker_bps=30.0,
        indodax_commission_vat_included=True,
        indodax_service_vat_rate=0.11,
        indodax_usdt_maker_bps=None,
        indodax_usdt_taker_bps=None,
        asset_vat_buyer_bps=11.0,
        asset_pph22_seller_bps=10.0,
        offshore_tax_bps=42.0,
        cfx_idr_bps=0.0,
        cfx_usdt_bps=0.0,
        binance_std_bps=10.0,
        binance_bnb_bps=7.5,
        verification_status="PARTIALLY_VERIFIED",
        confidence_level="HIGH (Taxes) / MEDIUM (Platform Fee)",
        primary_sources="PMK No. 68/PMK.03/2022 Art. 5 & 14; Indodax Aug 2023 fee cut announcement",
        uncertainty_notes="Statutory 11 bps PPN + 10 bps PPh22 exact; Indodax platform commission kept 0% maker / 30 bps taker pre-Aug 2023 (tested in sensitivity vs 10/20).",
    ),
    FeeRegime(
        regime_id="R2B_INDODAX_PRO_CUT",
        start_date="2023-08-23",
        end_date="2024-10-31",
        label="Post-Aug 2023 Indodax Fee Cut + PMK 68/2022",
        indodax_idr_maker_bps=10.0,
        indodax_idr_taker_bps=20.0,
        indodax_commission_vat_included=True,
        indodax_service_vat_rate=0.11,
        indodax_usdt_maker_bps=3.0,
        indodax_usdt_taker_bps=6.0,
        asset_vat_buyer_bps=11.0,
        asset_pph22_seller_bps=10.0,
        offshore_tax_bps=42.0,
        cfx_idr_bps=0.0,
        cfx_usdt_bps=0.0,
        binance_std_bps=10.0,
        binance_bnb_bps=7.5,
        verification_status="PARTIALLY_VERIFIED",
        confidence_level="MEDIUM-HIGH",
        primary_sources="Indodax Aug 22-23, 2023 Pro Taker Fee Reduction notice; PMK 68/2022",
        uncertainty_notes="Aug 2023 announcement cut taker fees by 40% (approx 30 -> 18-20 bps) and introduced Pro 10/20 bps structure; tested with 0/18-20 sensitivity.",
    ),
    FeeRegime(
        regime_id="R3_CFX_LAUNCH_PMK68",
        start_date="2024-11-01",
        end_date="2024-12-31",
        label="PERBA 9/2024 CFX Fee Launch (2.22 bps IDR / 4.44 bps USDT)",
        indodax_idr_maker_bps=10.0,
        indodax_idr_taker_bps=20.0,
        indodax_commission_vat_included=True,
        indodax_service_vat_rate=0.11,
        indodax_usdt_maker_bps=3.0,
        indodax_usdt_taker_bps=6.0,
        asset_vat_buyer_bps=11.0,
        asset_pph22_seller_bps=10.0,
        offshore_tax_bps=42.0,
        cfx_idr_bps=2.22,
        cfx_usdt_bps=4.44,
        binance_std_bps=10.0,
        binance_bnb_bps=7.5,
        verification_status="VERIFIED_PRIMARY",
        confidence_level="HIGH",
        primary_sources="help.indodax.com/articles/39505059756569; PERBA No. 9/2024; CFX SEB 003/004",
        uncertainty_notes="Exact effective timestamp 2024-10-31 23:59:59 WIB verified on Indodax Help Center.",
    ),
    FeeRegime(
        regime_id="R3B_PMK81_VAT12_ADJ",
        start_date="2025-01-01",
        end_date="2025-07-31",
        label="PMK 81/2024 & PMK 131/2024 Transition (11% effective VAT retained for non-luxury)",
        indodax_idr_maker_bps=10.0,
        indodax_idr_taker_bps=20.0,
        indodax_commission_vat_included=True,
        indodax_service_vat_rate=0.11,
        indodax_usdt_maker_bps=3.0,
        indodax_usdt_taker_bps=6.0,
        asset_vat_buyer_bps=11.0,
        asset_pph22_seller_bps=10.0,
        offshore_tax_bps=42.0,
        cfx_idr_bps=2.22,
        cfx_usdt_bps=4.44,
        binance_std_bps=10.0,
        binance_bnb_bps=7.5,
        verification_status="VERIFIED_PRIMARY",
        confidence_level="HIGH",
        primary_sources="PMK No. 81/2024; PMK No. 131/2024 (12% * 11/12 = 11% effective VAT)",
        uncertainty_notes="Some secondary blogs briefly cited 0.12% before 11/12 DPP adjustment clarified 0.11% effective.",
    ),
    FeeRegime(
        regime_id="R4_PMK50_2025",
        start_date="2025-08-01",
        end_date="2026-02-28",
        label="PMK 50/2025 Tax Overhaul (0% Asset VAT + 0.21% Seller PPh 22)",
        indodax_idr_maker_bps=10.0,
        indodax_idr_taker_bps=20.0,
        indodax_commission_vat_included=True,
        indodax_service_vat_rate=0.11,
        indodax_usdt_maker_bps=3.0,
        indodax_usdt_taker_bps=6.0,
        asset_vat_buyer_bps=0.0,
        asset_pph22_seller_bps=21.0,
        offshore_tax_bps=100.0,
        cfx_idr_bps=2.22,
        cfx_usdt_bps=4.44,
        binance_std_bps=10.0,
        binance_bnb_bps=7.5,
        verification_status="VERIFIED_PRIMARY",
        confidence_level="HIGH",
        primary_sources="PMK No. 50 Tahun 2025 Art. 2 & 11; DJP Official Explanation; Indodax Help Center",
        uncertainty_notes="Exact shift: buyer asset VAT abolished; seller PPh 22 raised to 21 bps domestic / 100 bps foreign.",
    ),
    FeeRegime(
        regime_id="R5_CFX_CUT_MAR2026",
        start_date="2026-03-01",
        end_date="2026-09-30",
        label="CFX 50% Reduction Stage 1 (SEB 001/2026: 1.11 bps IDR / 2.22 bps USDT)",
        indodax_idr_maker_bps=10.0,
        indodax_idr_taker_bps=20.0,
        indodax_commission_vat_included=True,
        indodax_service_vat_rate=0.11,
        indodax_usdt_maker_bps=3.0,
        indodax_usdt_taker_bps=6.0,
        asset_vat_buyer_bps=0.0,
        asset_pph22_seller_bps=21.0,
        offshore_tax_bps=100.0,
        cfx_idr_bps=1.11,
        cfx_usdt_bps=2.22,
        binance_std_bps=10.0,
        binance_bnb_bps=7.5,
        verification_status="VERIFIED_PRIMARY",
        confidence_level="HIGH",
        primary_sources="SEB No. 001/SEB/CFX-KKI/SPOT/II/2026; Indodax announcement",
        uncertainty_notes="Verified 0.0111% IDR and 0.0222% USDT CFX fee.",
    ),
    FeeRegime(
        regime_id="R6_CFX_CUT_OCT2026",
        start_date="2026-10-01",
        end_date="2026-11-12",
        label="CFX 50% Reduction Stage 2 (0.555 bps IDR / 1.11 bps USDT)",
        indodax_idr_maker_bps=10.0,
        indodax_idr_taker_bps=20.0,
        indodax_commission_vat_included=True,
        indodax_service_vat_rate=0.11,
        indodax_usdt_maker_bps=3.0,
        indodax_usdt_taker_bps=6.0,
        asset_vat_buyer_bps=0.0,
        asset_pph22_seller_bps=21.0,
        offshore_tax_bps=100.0,
        cfx_idr_bps=0.555,
        cfx_usdt_bps=1.11,
        binance_std_bps=10.0,
        binance_bnb_bps=7.5,
        verification_status="VERIFIED_PRIMARY",
        confidence_level="HIGH",
        primary_sources="Indodax Pro all-in schedule (0.10555/0.20555 buy; 0.31555/0.41555 sell; 0.2511/0.2811 USDT)",
        uncertainty_notes="Reverse-engineered to 5th decimal place against published Indodax all-in rates; base 10/20 bps is VAT-inclusive.",
    ),
]


def compute_regime_costs(reg: FeeRegime) -> Dict[str, float]:
    """Compute exact single-leg and multi-leg route transaction costs in bps."""
    buy_maker = reg.indodax_idr_maker_bps + reg.asset_vat_buyer_bps + reg.cfx_idr_bps
    buy_taker = reg.indodax_idr_taker_bps + reg.asset_vat_buyer_bps + reg.cfx_idr_bps
    sell_maker = reg.indodax_idr_maker_bps + reg.asset_pph22_seller_bps + reg.cfx_idr_bps
    sell_taker = reg.indodax_idr_taker_bps + reg.asset_pph22_seller_bps + reg.cfx_idr_bps

    # Route A: Domestic 2-leg cycle (Sell BTC/IDR + Buy USDT/IDR on Indodax)
    route_a_maker = sell_maker + buy_maker
    route_a_taker = sell_taker + buy_taker

    # Route B: Cross-exchange 3-leg cycle (Sell BTC/IDR + Buy USDT/IDR on Indodax + Buy BTC/USDT on Binance)
    # Note: excludes on-chain withdrawal/deposit network fees and bid-ask spreads, modeled separately.
    route_b_maker = route_a_maker + reg.binance_bnb_bps
    route_b_taker = route_a_taker + reg.binance_std_bps

    # Route C: Same-exchange Indodax BTC/USDT direct swap + IDR legs
    if reg.indodax_usdt_maker_bps is not None and reg.indodax_usdt_taker_bps is not None:
        # Under PMK 50/2025 or PMK 68/2022 crypto-to-crypto swap incurs asset tax + CFX USDT fee
        usdt_leg_maker = reg.indodax_usdt_maker_bps + reg.asset_pph22_seller_bps + reg.cfx_usdt_bps
        usdt_leg_taker = reg.indodax_usdt_taker_bps + reg.asset_pph22_seller_bps + reg.cfx_usdt_bps
        route_c_maker = route_a_maker + usdt_leg_maker
        route_c_taker = route_a_taker + usdt_leg_taker
    else:
        route_c_maker = float("nan")
        route_c_taker = float("nan")

    return {
        "buy_idr_maker_bps": round(buy_maker, 4),
        "buy_idr_taker_bps": round(buy_taker, 4),
        "sell_idr_maker_bps": round(sell_maker, 4),
        "sell_idr_taker_bps": round(sell_taker, 4),
        "route_a_domestic_2leg_maker_bps": round(route_a_maker, 4),
        "route_a_domestic_2leg_taker_bps": round(route_a_taker, 4),
        "route_b_cross_3leg_maker_bps": round(route_b_maker, 4),
        "route_b_cross_3leg_taker_bps": round(route_b_taker, 4),
        "route_c_indodax_usdt_maker_bps": round(route_c_maker, 4) if pd.notna(route_c_maker) else float("nan"),
        "route_c_indodax_usdt_taker_bps": round(route_c_taker, 4) if pd.notna(route_c_taker) else float("nan"),
    }


def build_historical_fee_table() -> pd.DataFrame:
    rows = []
    for reg in HISTORICAL_REGIMES:
        costs = compute_regime_costs(reg)
        rows.append(
            {
                "regime_id": reg.regime_id,
                "start_date": reg.start_date,
                "end_date": reg.end_date,
                "label": reg.label,
                "indodax_idr_maker_bps": reg.indodax_idr_maker_bps,
                "indodax_idr_taker_bps": reg.indodax_idr_taker_bps,
                "asset_vat_buyer_bps": reg.asset_vat_buyer_bps,
                "asset_pph22_seller_bps": reg.asset_pph22_seller_bps,
                "offshore_tax_bps": reg.offshore_tax_bps,
                "cfx_idr_bps": reg.cfx_idr_bps,
                "cfx_usdt_bps": reg.cfx_usdt_bps,
                "binance_std_bps": reg.binance_std_bps,
                "binance_bnb_bps": reg.binance_bnb_bps,
                **costs,
                "verification_status": reg.verification_status,
                "confidence_level": reg.confidence_level,
                "primary_sources": reg.primary_sources,
                "uncertainty_notes": reg.uncertainty_notes,
            }
        )
    return pd.DataFrame(rows)


def lookup_costs_for_dates(dates: pd.Series) -> pd.DataFrame:
    """Map YYYY-MM-DD date strings to exact regime execution costs."""
    d_strs = pd.to_datetime(dates).dt.strftime("%Y-%m-%d")
    out_rows = []
    for ds in d_strs:
        matched = None
        for reg in HISTORICAL_REGIMES:
            if reg.start_date <= ds <= reg.end_date:
                matched = reg
                break
        if matched is None:
            matched = HISTORICAL_REGIMES[-1]
        c = compute_regime_costs(matched)
        c["date"] = ds
        c["fee_regime_id"] = matched.regime_id
        out_rows.append(c)
    return pd.DataFrame(out_rows)
