# Experiment plan: UK high-value retention

## Feasibility verdict

The first UK wave should be treated as a **signal-seeking pilot**, not as a definitive uplift test. There are only **78** eligible High-Value At Risk customers, or about **39 per arm** under a 50/50 split.

## Sizing

- Historical next-12-month repeat rate: **67.6%**. This is a planning baseline, not a no-contact counterfactual.
- A **10% absolute lift** would require about **312 customers per arm** at two-sided alpha **5%** and power **80%**.
- With only **39 customers per arm**, the approximate minimum detectable lift is **25.0%**, to **92.6%** repeat purchase.

## Recommended design

1. Randomize within the High-Value At Risk segment and stratify by recency and historical value.
2. Keep a true no-contact holdout; analyze everyone as assigned.
3. Use repeat purchase within a fixed follow-up window as the primary KPI.
4. Track incremental revenue and margin per eligible customer; use unsubscribe and discount cost as guardrails.
5. Pool identically designed waves until the predeclared sample is reached, or report the pilot as directional with confidence intervals.

Keep High-Value Lapsed customers in a separate, lower-cost test because their baseline behavior and offer economics differ.

## Caveats

The calculation compares two proportions and does not account for repeated campaign waves, interference, or heterogeneous treatment effects. Final sizing should use the chosen follow-up window and its matching historical baseline.

