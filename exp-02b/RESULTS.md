# EXP-02B — Results

**Status:** COMPLETE — pre-registered analysis rule satisfied
**Date of confirming run:** 2026-07-27
**Pre-registration:** `EXP-02B_PREREGISTRATION.md` + Amendment 1, locked
before any data collection and not modified afterwards.

---

## 1. Result

| Run | Metric list (Report Style 2, UE level) | Predicted | Observed |
|-----|----------------------------------------|-----------|----------|
| P  | `DRB.UEThpDl` | > 0 | **24** |
| A1 | `DRB.UEThpDl, DRB.RlcSduDelayDl` | 0 | **0** |
| B  | `DRB.RlcSduDelayDl, DRB.UEThpDl` | > 0 | **24** |
| A2 | `DRB.UEThpDl, DRB.RlcSduDelayDl` | 0 | **0** |
| C  | `DRB.UEThpDl, DRB.FakeMetric123` | 0 (diagnostic) | **0** |

Locked rule: *H1 confirmed iff P>0 AND A1=0 AND B>0 AND A2=0.*
All four conditions met. **H1 is confirmed.**

Every run lasted 70 s, none produced a subscription rejection, a Python
exception or a port conflict, and the submgr subscription list was
verified empty (`[]`) after each. A2 reproduces A1, so the effect is
reversible rather than a one-off state fault.

## 2. Finding

**In srsRAN's E2SM-KPM Report Style 2, whether a RIC Indication is
emitted at all is decided solely by the last metric in the subscription
list.** If that metric yields `no_value` or is unsupported, the entire
indication is discarded — including values from other metrics in the
same subscription that were collected successfully.

The failure is silent end to end. The subscription is accepted, a
Subscription ID is returned over HTTP 200, an E2EventInstanceId mapping
is received, and the RIC then simply never gets an indication.

### Mechanism

`e2sm_kpm_report_service_style2::collect_measurements`
(`lib/e2/e2sm/e2sm_kpm/e2sm_kpm_report_service_impl.cpp`):

```cpp
std::vector<meas_record_item_c> meas_records_items;   // declared outside the loop
for (auto& meas_info : meas_info_list) {
    meas_records_items.clear();                       // cleared each iteration
    meas_provider.get_meas_data(..., meas_records_items);
    if (meas_records_items.empty()) { continue; }
    meas_data_item.meas_record.push_back(meas_records_items[0]);
}
ric_ind_message.meas_data.push_back(meas_data_item);

if (not is_ind_msg_ready_) {
    if (meas_records_items.empty()) { return false; }
    if (meas_records_items[0].type() != meas_record_item_c::types_opts::no_value) {
        is_ind_msg_ready_ = true;
    }
}
```

After the loop, `meas_records_items` holds only the last metric's
result. The readiness check reads that variable, so the readiness of the
whole indication — including records already pushed into
`meas_data_item` — depends on one metric's outcome.

The snippet above was verified verbatim against the source captured in
the session transcript (`sed -n '140,230p'` of
`e2sm_kpm_report_service_impl.cpp`, srsRAN commit `d2f4b70dda`). The
same capture shows `clear_collect_measurements()` resetting
`is_ind_msg_ready_ = false` at the start of each collection cycle, so
the last-metric decision is taken afresh for every indication, not only
the first.

Report Style 1 does not have this defect; it sets `is_ind_msg_ready_`
unconditionally (verified in the same capture).

### Why the encoding hypothesis is excluded

The primary evidence is the content of Run B itself: the very same
`no_value` record that (in last position) kills runs A1/A2 is encoded
and **delivered successfully** when it is not last — `[None]` appears
inside B's received indications. A record that ships cleanly in one
position cannot be breaking the encoder in another.

Run C (`DRB.FakeMetric123`, non-existent) corroborates this — a metric
that produces no value at all also kills the stream when last — but C
alone is not decisive: a silent E2AP-level rejection of an action
definition containing an unknown metric would produce the same zero
(cf. the unresolved `RICSubscriptionFailure Cause:6` records of 25–26
July). C's gNB-side E2AP handling was not independently verified.

Two distinct paths to the same failure are established:
- last metric returns `no_value` → readiness never set (A1, A2 — the
  `no_value` outcome in those runs is inferred from B's delivered
  content in the same window, since A1/A2 themselves emit nothing)
- last metric is unsupported, items empty → early `return false` (C)

### Direct evidence from Run B

```
--Metric: DRB.RlcSduDelayDl, Value: [None]
--Metric: DRB.UEThpDl, Value: [0.0]
```

The delay metric returns `no_value` in both orders. In first position it
is harmless and the indication is delivered; in last position it
destroys the indication.

### Suggested fix

Test `meas_data_item.meas_record` rather than the loop-scoped
`meas_records_items`, so readiness reflects whether *any* metric
produced a usable record.

---

## 3. Two further findings, independent of H1

Both were recorded during the same session on the same node and are
reported separately because they do not bear on the pre-registered
hypothesis.

### 3.1 `DRB.UEThpDl` reports 0.0 under sustained load

Measured simultaneously, one node, one instant:

| Source | Value |
|---|---|
| DU scheduler console | `brate 59M`, `dl_bs` 5.6–5.9 MB standing queue |
| UE `tun_srsue` RX counter | ~24 Mb/s actually delivered |
| E2SM-KPM `DRB.UEThpDl` | **0.0** |
| Queueing delay implied by `dl_bs` / drain rate | ~1.9 s |

A metric census run separately at Report Style 1 shows the split is by
data source, not by the E2 path:

- scheduler-derived — `CQI` 15, `RSRP` 5, `RSRQ` 5, `RRU.PrbTotDl` 84,
  `RRU.PrbAvailDl` 16 — all plausible
- RLC-derived — `DRB.UEThpDl` 0.0, `DRB.UEThpUl` 0.0,
  `DRB.RlcPacketDropRateDl` 0, `DRB.RlcSduDelayDl` `no_value`

The E2 transport, subscription handling and indication path are all
healthy; the fault is confined to the RLC-derived metric family.

The scheduler's own `brate 59M` should itself be treated with caution:
offered load was 30 Mb/s, delivered ~24–25 Mb/s, `nok = 0%`, and the
buffer was constant — under those conditions a true 59 Mb/s of MAC
transmission does not conserve. The counter plausibly includes padding
or double-counts, which is unresolved. Consequently, the fact that the
original EXP-02's `DRB.UEThpDl` (~59,000 kbps) matched this counter
shows only that the KPI mirrored the scheduler figure **in that
session** — not what either number measures. In the present session the
same KPI reports 0.0 against the same scheduler figure, so even the
mirroring is not stable.

**Cross-session inconsistency (open).** In UC-06, on the same build
(`d2f4b70dda`), the same three-overlay launcher, the same Report Style 2
and the same metric, `DRB.UEThpDl` returned ~59,000 kbps across 22
indications. In this session it returns 0.0 under comparable load. No
configuration difference has been identified; the KPI's behaviour is
therefore inconsistent across sessions in a way this work does not
explain.

One consequence of treating 59M as inflated is positive: the previously
unexplained Little's-law gap dissolves. UC-06 measured a 6.17 MB
standing queue and p95 RTT of 2.1–2.2 s, while the reported 59 Mb/s
drain predicted only 0.84 s (a 2.5× gap). If the true drain was the
delivered goodput (~25 Mb/s, assuming UC-06's goodput was comparable to
today's), the predicted queueing delay is 6.17 MB × 8 / 25 ≈ 1.97 s —
within ~10% of the measurement.

### 3.2 `DRB.RlcSduDelayDl` returns physically impossible values

At Report Style 2, subscribed alone, the metric returned:

```
-1180.0999755859375   1594.4000244140625   -1707.5   -1847.5   -1855
```

Unit is 0.1 ms, so −118 ms to +159 ms with alternating sign. Negative
delay is not physically meaningful. In other runs the same metric
returned `no_value` instead.

Candidate cause in `get_drb_dl_rlc_sdu_latency`:

```cpp
int tot_sdu_latency_us = std::accumulate(
    begin, end, 0,                      // int accumulator
    [](size_t sum, const rlc_metrics& m) { return sum + m.tx.tx_low.sum_sdu_latency_us; });
```

The initial value `0` is an `int`, so accumulation is performed in
`int32`. With a ~5.9 MB standing queue the summed microsecond latencies
exceed `INT_MAX` and wrap negative. The UE-level branch also guards only
the numerator (`if (tot_sdu_latency_us)`) and not the denominator
`tot_num_sdus`, which is read from `tx_high` while the numerator comes
from `tx_low`.

The practical consequence is stronger than an unavailable metric: the
delay KPI is subscribable, delivers indications, and returns a number
that cannot be trusted.

---

## 4. Configuration required for any of this to be testable

`ue_aggr_rlc_metrics` is only populated when RLC metric reporting is
enabled in the gNB. Without it, every RLC-derived metric is empty and
`handle_no_meas_data_available` produces:
- Style 1 → a record with value 0, indications still flow
- Style 2 → **no record at all**, so the readiness check above fires and
  zero indications are sent

Note carefully what this does and does not explain. An empty RLC store
kills Style 2 delivery for **every** metric list, single or dual — that
is the all-zero symptom seen mid-session on 27 July before the overlay
was applied. It does **not** reproduce the original EXP-02 pattern
(single metric delivering 22 indications, dual metric delivering zero):
that pattern requires the store to be populated and is exactly what H1
explains. The original EXP-02 environment therefore had RLC metrics
enabled. This configuration state must be verified before the ordering
effect can be observed at all.
The working overlay is:

```yaml
metrics:
  enable_json: true
  autostart_stdout_metrics: true
  layers:
    enable_sched: true
    enable_rlc: true
  periodicity:
    du_report_period: 1000
```

launched as
`gnb -c gnb_zmq.yml -c gnb_metrics.yml -c gnb_e2.yml`.

---

## 5. Scope and threats to validity

- Single UE, ZMQ virtual radio, one srsRAN Project build
  (commit `d2f4b70dda`), O-RAN SC RIC i-release.
- Report Style 2 only for the ordering result; Style 1 was used as the
  data-path control and does not show the defect.
- The ordering effect is demonstrated for two metric pairs and one
  non-existent metric. It is not established for every metric
  combination.
- `DRB.RlcSduDelayDl` returned `no_value` in the confirming runs and
  overflowed negative values in the earlier census. Both behaviours were
  observed; the conditions separating them are not yet characterised.
- The throughput and delay defects (§3) are reported as observed. The
  `int` accumulator is a candidate cause for the **delay** metric's
  negative values only; it does not explain the throughput 0.0, whose
  consistency across runs argues against overflow noise. The throughput
  cause is unknown, as is why `sum_sdu_latency_us` is populated in the
  same store whose byte counters compute to zero. Confirming any of
  this requires an instrumented rebuild.
- Downlink was verified before the run sequence but not re-measured
  between runs. Under the confirmed mechanism, delivery counts do not
  depend on load (an idle `DRB.UEThpDl` still yields a real 0.0 record,
  so P/B would deliver regardless), but this was not instrumented.
- The delay metric's regime was not logged per run. In the earlier
  census it returned real (overflowed) values when subscribed alone; in
  the confirming runs it returned `no_value` (visible in B's content).
  Had it been in the real-value regime during A1/A2, the mechanism
  itself predicts A1 > 0. The observed A1 = 0 is consistent, but the
  regime should be bracketed in any replication: probe the delay metric
  alone immediately before and after each dual-metric run.
- Indications arrived roughly every 3 s against a granularity period of
  1000 ms; the discrepancy is unexplained. The roles of DRB1 vs DRB2
  (which bearer carries the iperf flow) were not established.

## 6. Corrections made during this work

Recorded because they affected earlier interpretations:

1. An intermediate hypothesis that Report Style 2 structurally cannot
   emit indications was **wrong**. It emits normally once RLC metrics
   are enabled.
2. An intermediate hypothesis that the fault lay in RMR routing between
   e2term and the xApp was **wrong**; `NOENDPT` in the logs came from
   `E2_TERM_INIT` at startup, not from indication forwarding.
3. A stale submgr subscription with `"SubscriptionInstances": null`
   caused submgr to merge every new request into a dead entry, making
   several earlier run sequences non-independent. Subscriptions are now
   deleted between runs and the list verified empty.
4. An intermediate claim that `clear_rlc_metrics()` was wiping the
   store via a failing F1AP UE-ID translation was **wrong**: the census
   showed Style 2 UE-level lookups succeeding (real 0.0 records require
   a successful `ue_idx` resolution) and the delay metric reading real
   data from the same store.
5. An intermediate claim that the empty-store mechanism "explains the
   original EXP-02" was **wrong** in scope — it explains only the
   all-zero interlude of 27 July, not the original single-vs-dual
   pattern (see §4).
