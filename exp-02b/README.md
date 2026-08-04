# EXP-02B — Metric order dependency in E2SM-KPM Report Style 2

A pre-registered test showing that RIC Indication delivery under E2SM-KPM
Report Style 2 depends on the **order** of metrics in `meas_info_list`.
When the last metric in the subscription produces no record, the Indication
is silently withheld — including the records already collected for earlier
metrics — with nothing logged at any level.

**Upstream issue:** https://gitlab.com/ocudu/ocudu/-/work_items/684)

## Result

Confirmation rule fixed before execution: H1 confirmed iff P>0, A1=0, B>0, A2=0.
All four pre-registered predictions matched.

| Run | Metrics requested (in order) | Purpose | Predicted | Observed |
|-----|------------------------------|---------|-----------|----------|
| P  | `DRB.UEThpDl` | positive control | > 0 | **24** |
| A1 | `DRB.UEThpDl`, `DRB.RlcSduDelayDl` | reproduce failure | 0 | **0** |
| B  | `DRB.RlcSduDelayDl`, `DRB.UEThpDl` | same metrics, order swapped | > 0 | **24** |
| A2 | `DRB.UEThpDl`, `DRB.RlcSduDelayDl` | reversibility | 0 | **0** |
| C  | `DRB.UEThpDl`, `DRB.FakeMetric123` | discriminator | 0 | **0** |

Runs A1 and B are the core result: the *same two metrics* yield 24 Indications
or complete silence depending only on their order.

Run C rules out the competing explanation. `DRB.FakeMetric123` does not exist,
so it can never produce a value and therefore cannot corrupt ASN.1 encoding of
the Indication message. Run C returned zero Indications anyway — consistent
with the readiness-check reading, not with an encoding fault.

## Root cause (hypothesis)

In `e2sm_kpm_report_service_style2::collect_measurements()`, the vector
`meas_records_items` is declared outside the collection loop and cleared at
the top of every iteration. The `is_ind_msg_ready_` check runs after the loop
and therefore inspects only the final metric — both through the early
`return false` on `meas_records_items.empty()` and through the `no_value`
type check on `meas_records_items[0]`.

Style 5 in the same file carries the identical intent comment and iterates
over the returned records, which suggests the Style 2 behaviour is unintended.

Verified present in both srsRAN Project `d2f4b70` (2025-11-11) and OCUDU
`b0515eb9` (2026-07-31, branch `dev`) — the function body is identical.

## Files

| File | Contents |
|------|----------|
| `exp02b_run.sh` | The pre-registered run script; run definitions locked before execution |
| `PREREGISTRATION.md` | Pre-registration document |
| `PREREGISTRATION_amendment1.md` | Amendment 1, filed before any data collection |
| `RESULTS.md` | Results write-up |
| `run_P.log` … `run_C.log` | Raw xApp logs, one per run |
| `ENVIRONMENT.txt` | Commit hashes, compiler, build type, platform |
| `gnb_config.yml` | gNB configuration used for the runs |

## Reproducing

Indications are counted by matching `RIC Indication Received` in the xApp log:

```bash
for f in P A1 B A2 C; do echo "$f: $(grep -c 'RIC Indication Received' run_$f.log)"; done
```

Each run used a 60-second measurement window with a 15-second teardown gap.
Subscriptions were explicitly deleted through the Subscription Manager REST API
between runs to prevent subscription merging.
