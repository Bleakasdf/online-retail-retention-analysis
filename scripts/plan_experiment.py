"""Check whether the proposed UK CRM retention pilot is statistically feasible."""

import csv
import math
from pathlib import Path
from statistics import NormalDist


ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = ROOT / "outputs" / "tables" / "segment_decision.csv"
CUSTOMERS = ROOT / "outputs" / "tables" / "customer_priority.csv"
OUTPUT = ROOT / "outputs" / "experiment_plan.md"
ALPHA = 0.05
POWER = 0.80
TARGET_ABSOLUTE_LIFT = 0.10


def sample_size_per_arm(baseline: float, variant: float) -> int:
    z_alpha = NormalDist().inv_cdf(1 - ALPHA / 2)
    z_power = NormalDist().inv_cdf(POWER)
    pooled = (baseline + variant) / 2
    numerator = (
        z_alpha * math.sqrt(2 * pooled * (1 - pooled))
        + z_power * math.sqrt(
            baseline * (1 - baseline) + variant * (1 - variant)
        )
    ) ** 2
    return math.ceil(numerator / (variant - baseline) ** 2)


def detectable_rate(baseline: float, per_arm: int) -> float:
    low, high = baseline, 0.999999
    for _ in range(100):
        candidate = (low + high) / 2
        if sample_size_per_arm(baseline, candidate) > per_arm:
            low = candidate
        else:
            high = candidate
    return high


with SEGMENTS.open(encoding="utf-8", newline="") as segment_file:
    segment_rows = list(csv.DictReader(segment_file))
baseline = next(
    float(row["next_12m_repeat_rate"])
    for row in segment_rows
    if row["rfm_segment"] == "High-Value At Risk"
)

with CUSTOMERS.open(encoding="utf-8", newline="") as customer_file:
    customers = list(csv.DictReader(customer_file))
uk_target = sum(
    row["primary_country"] == "United Kingdom"
    and row["rfm_segment"] == "High-Value At Risk"
    for row in customers
)
available_per_arm = uk_target // 2
target_rate = baseline + TARGET_ABSOLUTE_LIFT
required_per_arm = sample_size_per_arm(baseline, target_rate)
minimum_detectable_rate = detectable_rate(baseline, available_per_arm)
minimum_detectable_lift = minimum_detectable_rate - baseline

OUTPUT.write_text(
    f"""# Experiment plan: UK high-value retention

## Feasibility verdict

The first UK wave should be treated as a **signal-seeking pilot**, not as a definitive uplift test. There are only **{uk_target}** eligible High-Value At Risk customers, or about **{available_per_arm} per arm** under a 50/50 split.

## Sizing

- Historical next-12-month repeat rate: **{baseline:.1%}**. This is a planning baseline, not a no-contact counterfactual.
- A **{TARGET_ABSOLUTE_LIFT:.0%} absolute lift** would require about **{required_per_arm} customers per arm** at two-sided alpha **{ALPHA:.0%}** and power **{POWER:.0%}**.
- With only **{available_per_arm} customers per arm**, the approximate minimum detectable lift is **{minimum_detectable_lift:.1%}**, to **{minimum_detectable_rate:.1%}** repeat purchase.

## Recommended design

1. Randomize within the High-Value At Risk segment and stratify by recency and historical value.
2. Keep a true no-contact holdout; analyze everyone as assigned.
3. Use repeat purchase within a fixed follow-up window as the primary KPI.
4. Track incremental revenue and margin per eligible customer; use unsubscribe and discount cost as guardrails.
5. Pool identically designed waves until the predeclared sample is reached, or report the pilot as directional with confidence intervals.

Keep High-Value Lapsed customers in a separate, lower-cost test because their baseline behavior and offer economics differ.

## Caveats

The calculation compares two proportions and does not account for repeated campaign waves, interference, or heterogeneous treatment effects. Final sizing should use the chosen follow-up window and its matching historical baseline.
""",
    encoding="utf-8",
)

print(f"Wrote {OUTPUT.relative_to(ROOT)}")

