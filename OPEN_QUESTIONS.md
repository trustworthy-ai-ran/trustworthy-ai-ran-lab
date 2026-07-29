# Open questions

Observations recorded during the UC-06 and EXP-02B sessions that are **not
explained**. They are published because they are reproducible enough to
report and because omitting them would misrepresent what the lab saw.

No causal claims are attached to any of them. Where a candidate cause is
named, it was read from source and is explicitly unconfirmed.

---

## OQ-1 — `DRB.UEThpDl` reporting 0.0 under load

**Observed, 27 July 2026.** With ~24 Mb/s of downlink confirmed by the UE's
`tun_srsue` interface byte counter, and the DU's own scheduler console showing
`brate 59M` with a 5.6–5.9 MB standing queue, the KPI reported `0.0`
continuously **on Report Style 2** — the style that returned 59,043 in UC-06.

Style 1 returning 0.0 is *not* part of this question: METHOD.md §4.3 already
records that Style 1 returns 0.0 for this metric under all conditions on this
stack. The anomaly is confined to Style 2 changing behaviour between sessions.

A metric census taken at the same moment shows the split is by data source,
not by the E2 path:

| Source | Metric | Value |
|---|---|---|
| scheduler | `CQI` | 15 |
| scheduler | `RSRP` | 5 |
| scheduler | `RSRQ` | 5 |
| scheduler | `RRU.PrbTotDl` | 84 |
| scheduler | `RRU.PrbAvailDl` | 16 |
| RLC | `DRB.UEThpDl` | 0.0 |
| RLC | `DRB.UEThpUl` | 0.0 |
| RLC | `DRB.RlcPacketDropRateDl` | 0 |
| RLC | `DRB.RlcSduDelayDl` | `no_value` |

E2 transport, subscription handling and Indication delivery were all healthy;
scheduler-derived metrics carried plausible values throughout.

**Why it is open.** In UC-06, on the same srsRAN build (`d2f4b70dda`), the
same launcher and the same Report Style, this metric returned ≈59,043 across
22 Indications. No configuration difference has been identified between the
two sessions. The gNB debug log confirms RLC metrics *reaching* the E2
measurement provider (`[E2SM-KPM] [D] Received RLC metrics: ue=0 DRB1/DRB2`),
so the store is not empty — the computation returns zero from populated data.

**Not the cause:** `clear_rlc_metrics()` wiping the store via a failed F1AP
UE-ID translation. Ruled out — Style 2 UE-level lookups succeed, and the delay
metric reads real data from the same store.

**Unresolved sub-question.** Why `sum_sdu_latency_us` is populated in the same
store whose byte counters compute to zero.

---

## OQ-2 — `DRB.RlcSduDelayDl` returning impossible values

**Observed, 27 July 2026.** Subscribed alone at Report Style 2, the metric
returned:

```
-1180.0999755859375   1594.4000244140625   -1707.5   -1847.5   -1855
```

Unit is 0.1 ms, so −118 ms to +159 ms with alternating sign. Negative delay is
not physically meaningful. In other runs the same metric returned `no_value`
instead; the conditions separating the two regimes are not characterised.

**Candidate cause, unconfirmed.** In `get_drb_dl_rlc_sdu_latency`:

```cpp
int tot_sdu_latency_us = std::accumulate(
    begin, end, 0,                      // int accumulator
    [](size_t sum, const rlc_metrics& m) { return sum + m.tx.tx_low.sum_sdu_latency_us; });
```

The initial value `0` is an `int`, so accumulation is performed in `int32`.
With a ~5.9 MB standing queue the summed microsecond latencies plausibly
exceed `INT_MAX` and wrap negative. The UE-level branch also guards only the
numerator (`if (tot_sdu_latency_us)`) and not the denominator `tot_num_sdus`,
which is read from `tx_high` while the numerator comes from `tx_low`.

Confirming this requires an instrumented rebuild. It has not been done.

**Note.** This candidate does **not** explain OQ-1. Overflow produces noisy,
sign-flipping garbage; the throughput metric returns a stable, repeated 0.0.

**Practical consequence.** The delay KPI is subscribable, delivers
Indications, and returns a number that cannot be trusted. That is a worse
failure mode than an unavailable metric, because a consumer has no signal
that anything is wrong.

---

## OQ-3 — The scheduler's own throughput figure does not conserve

**Observed, 27 July 2026.** The DU console reported `brate 59M` while:

- offered load was 30 Mb/s
- delivered goodput was ~24–25 Mb/s (interface byte counter)
- `nok` was 0%
- `dl_bs` was constant at 5.6–5.9 MB

A true 59 Mb/s of MAC transmission does not conserve under those conditions.
The counter plausibly includes padding or double-counts segmented bytes
(`get_drb_dl_mean_throughput` sums `num_pdu_bytes_no_segmentation` and
`num_pdu_bytes_with_segmentation`), but this is inference from source, not a
measurement.

**Consequence for UC-06.** The fact that UC-06's `DRB.UEThpDl` (~59,000)
matched this counter shows only that the KPI mirrored the scheduler figure —
not what either number measures. UC-06's claim does not depend on the value
being correct: the claim is that nothing in the stream tracked the latency
collapse, which holds whatever 59,000 represents.

**One thing this resolves.** UC-06 left an unexplained Little's-law gap: a
6.17 MB queue draining at the reported 59 Mb/s predicts 0.84 s of queueing
delay against a measured p95 of 2.1–2.2 s, a 2.5× discrepancy. If the true
drain rate was the delivered goodput (~25 Mb/s), the prediction is
6.17 MB × 8 / 25 ≈ **1.97 s** — within ~10% of the measurement. That is
consistent with the counter being inflated, though it does not prove it.

---

## OQ-4 — `RICSubscriptionFailure` records not mapped to runs

submgr logs from 25–26 July contain
`RICSubscriptionFailure. E2NodeCause: (Cause:6, Value 0)` records that were
never matched to specific subscription attempts. If any of them correspond to
the original EXP-02 dual-metric runs, the mechanism for those specific runs
would be an E2AP-level rejection rather than the readiness-check defect.

This does not affect the EXP-02B result, which was run fresh with
subscriptions verified cleared between runs and the failure mode reproduced
reversibly. It does mean the *original* EXP-02 runs of 25–26 July should not
be cited as independent confirmation of the ordering mechanism.

**Closing this** requires capturing gNB-side E2AP logs during a run with a
nonexistent metric in last position, to determine whether the action
definition is rejected at E2AP or accepted and then discarded at the
readiness check.

---

## What would close these

| ID | Test | Effort |
|---|---|---|
| OQ-1 | Instrumented rebuild logging `num_pdu_bytes_*` and `metrics_period` at each collection | half a day |
| OQ-2 | Same rebuild, log `tot_sdu_latency_us` before and after accumulation; probe the metric alone immediately before and after a dual-metric run to bracket its regime | half a day |
| OQ-3 | Run at 10 Mb/s (low segmentation) vs 30 Mb/s and compare `brate` against interface counters | one hour |
| OQ-4 | Capture gNB E2AP logs in the window of a nonexistent-metric run | ten minutes |
