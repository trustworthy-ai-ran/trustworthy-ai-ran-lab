# EXP-02B — Metric Order Dependency in E2SM-KPM Report Style 2

**Status:** PRE-REGISTERED — locked before any data collection
**Date locked:** _____________ (fill before first run)
**Commit hash at lock time:** _____________

---

## 1. Background

EXP-02 observed that adding `DRB.RlcSduDelayDl` to a working Style 2
subscription alongside `DRB.UEThpDl` reduced the RIC Indication stream
from 22 Indications to 0, while the subscription was accepted
(Subscription ID returned, HTTP 200).

Source inspection of `e2sm_kpm_report_service_impl.cpp`
(`e2sm_kpm_report_service_style2::collect_measurements`) identifies a
candidate mechanism.

## 2. Mechanism under test

`meas_records_items` is declared **outside** the metric loop and cleared
at the top of each iteration. After the loop terminates it contains only
the result of the **last** metric in `meas_info_list`.

The readiness check that sets `is_ind_msg_ready_` reads this same
variable. Therefore the readiness of the entire Indication — including
metrics that were successfully collected and already pushed into
`meas_data_item` — is determined solely by the outcome of the last
metric in the subscription list.

**H1:** The Indication stream failure is caused by this loop-scoped
readiness check, and is therefore dependent on the *order* of metrics in
the subscription list, not on the presence of the delay metric per se.

## 3. Predictions

All runs: Style 2, single UE, identical granularity period, identical
E2 node, saturating traffic active throughout (see §4 for the traffic
precondition — this is not optional).

| Run | Metric list order | Prediction | Falsifies H1 if |
|-----|-------------------|------------|-----------------|
| A′ | `DRB.UEThpDl, DRB.RlcSduDelayDl` | 0 Indications in 60 s | Indications > 0 |
| B | `DRB.RlcSduDelayDl, DRB.UEThpDl` | **> 0 Indications in 60 s**, at the configured period | 0 Indications |
| A″ | `DRB.UEThpDl, DRB.RlcSduDelayDl` | 0 Indications in 60 s (reversibility) | Indications > 0 |

**Primary prediction is Run B.** H1 is confirmed only if B yields a
non-zero Indication count while A′ and A″ both yield zero in the same
session.

### Contingent diagnostic

| Run | Metric list | Purpose |
|-----|-------------|---------|
| D | `DRB.RlcSduDelayDl` alone | Run **only if B fails.** Distinguishes the readiness-check hypothesis from an ASN.1 encoding failure (e.g. a non-finite REAL value produced by division by zero in the UE-level branch of `get_drb_dl_rlc_sdu_latency`, where the guard checks the numerator `tot_sdu_latency_us` but not the denominator `tot_num_sdus`). |

If D also yields 0 Indications, the cause is in the delay getter or the
encoder, not in the readiness check, and H1 is rejected.

## 4. Preconditions (must hold for all runs)

1. E2 connection established; subscription accepted with Subscription ID.
2. **Saturating downlink traffic active for the entire measurement
   window.** Without traffic, `ue_aggr_rlc_metrics` is empty and both
   metrics take the `handle_no_meas_data_available` path, which returns
   `no_value` — this would produce zero Indications in *every* run and
   confound the result. Traffic is a control, not a variable.
3. Previous subscription fully terminated before each new run
   (no residual subscriptions in submgr).
4. Report Style = 2 for all runs. Style is not varied in this experiment.

## 5. Measurement

For each run, record over a fixed 60 s window:

- Indication count (from xApp log)
- Timestamp of first and last Indication
- Measurement record contents of the first Indication (values, types)
- gNB E2 log excerpt for the subscription
- Exact command line used

## 6. Analysis rule (locked)

H1 is **confirmed** iff:
`count(A′) == 0` AND `count(B) > 0` AND `count(A″) == 0`

Any other combination is reported as-is. Partial results are not
reinterpreted post hoc. If the result is ambiguous, it is reported as
ambiguous and Run D is executed as the pre-declared next step.

## 7. Declared threats to validity

- Single UE, ZMQ virtual radio, single srsRAN Project version. Findings
  may not generalise to other E2 node implementations.
- Metric ordering in the encoded action definition is assumed to follow
  the order given on the xApp command line. This assumption is verified
  in Step 1 of the procedure and is not itself under test.
- Run-to-run variation in traffic conditions is controlled by keeping
  the generator running continuously across all three runs rather than
  restarting it per run.
