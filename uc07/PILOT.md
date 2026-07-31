# UC-07 — Pilot observations

**Status:** pilot. The pre-registered load sweep
([`PREREGISTRATION.md`](PREREGISTRATION.md)) has **not** been completed. What
follows is the evidence that motivated it, published as observation rather
than as a tested result.

Session: 31 July 2026. One lab, one configuration, `du_report_period: 1000`
unchanged throughout. Timestamps applied host-side as each line reached the
xApp, so they measure arrival at the consumer, not anything internal to the
gNB.

---

## 1. What was measured

Median inter-arrival time between consecutive `RIC Indication Received`
events, over runs of ~65 s, subscribing to `DRB.UEThpDl`.

Load, where present, was generated inside `ue1` so that it traversed the RAN:

```
sudo ip netns exec ue1 iperf3 -c 10.45.0.2 -u -b 30M -l 1200 -t 85 -R
```

## 2. Observations

| Condition | Runs | Indications | Median inter-arrival |
|---|---|---|---|
| Style 2, idle | 4 | 55–59 | **1.148 · 1.144 · 1.166 · 1.200 s** |
| Style 1, idle | 1 | 55 | **1.170 s** |
| Style 2, iperf3 loopback inside `srv` — negative control | 1 | 55 | **1.170 s** |
| Style 2, 30 Mb/s through the RAN | 1 | 27 | **2.340 s** |
| Style 1, 30 Mb/s through the RAN | 1 | 32 | **2.050 s** |

Idle cadence is consistent across four runs and two Report Styles, and matches
the configured 1000 ms reporting period plus ~15% overhead.

Under 30 Mb/s of downlink through the RAN, the interval roughly doubles on both
styles.

**The negative control is the part that makes this worth recording.** Running
iperf3 at the same rate entirely inside the `srv` namespace — so the traffic
never reached the RAN — left the cadence unchanged at 1.170 s. The effect
tracks traffic crossing the RLC queue, not the presence of iperf3 or the CPU
load it creates in isolation.

## 3. Why the styles matter here

Report Style 1 sets `is_ind_msg_ready_` unconditionally; Style 2 gates it on
the last metric's value (see [`../exp-02b/RESULTS.md`](../exp-02b/RESULTS.md)).
If only Style 2 had slowed, the cause would plausibly be that readiness check.
Both slowed, by similar factors, which points away from it and toward
something common to both paths.

This is an argument from one run per style. It is not a result.

## 4. What this pilot does **not** establish

- **Replication.** One run per loaded condition. The idle condition has four.
- **Dose response.** Only 0 and 30 Mb/s were measured with valid runs. A single
  5 Mb/s run gave a median of 1.385 s but was invalidated by a repeated
  Subscription ID and is excluded. Whether the effect is gradual or has a
  threshold is unknown.
- **Mechanism.** Nothing here distinguishes delay in metric collection, ASN.1
  encoding, the E2 agent, or SCTP transport. Attribution would need an
  instrumented build.
- **CPU contention.** iperf3, gNB, srsUE, the core and seven containers share
  one VM. The loopback control argues against pure CPU pressure, since it
  produced the same packet rate with no effect — but loopback traffic does not
  exercise the gNB, so the two are not equivalent.
- **Metric values.** Under real RAN load every sampled value was `0.0` on both
  styles while ~24 Mb/s was flowing. See §6.

## 5. Open observation: a 16-second gap at zero load

One idle run (`20260731T233410Z`, Style 2) delivered 17 Indications in 59.6 s
with a maximum inter-arrival of **16.216 s**, against a median of 1.205 s in
the same run and 55–59 Indications in the three comparable runs.

No hypothesis in this work predicts a 16-second stall with no load applied. It
is recorded because it happened, it is not explained, and a mean or median
alone would have hidden it. The run passed the validity criteria in force at
the time, which checked count and duration but not continuity — those criteria
were insufficient and have been noted as such.

## 6. Open observation: zero-valued throughput under load

Under 30 Mb/s of real RAN traffic, **every** sampled value of `DRB.UEThpDl` was
`0.0` — 27 of 27 on Style 2, 32 of 32 on Style 1 — while the interface counter
confirmed ~24 Mb/s flowing.

This reproduces [`OPEN_QUESTIONS.md`](../OPEN_QUESTIONS.md) OQ-1 within a
single controlled session and on both Report Styles, which the original
observation did not have. It remains unexplained.

Cadence in §2 is measured from arrival times, not values, so the two
observations are independent.

## 7. Why the sweep is not finished

The pre-registered design calls for 5 load levels × 2 styles × 3 replicates.
It was attempted three times and abandoned each time, for one reason:

**A submgr subscription record with `"SubscriptionInstances": null` survives
both the REST `DELETE` and a submgr restart, and silently absorbs the next
identical subscription — routing its Indications to a dead endpoint.**

An affected run returns zero Indications, or duplicates the previous run's
Subscription ID while appearing to work. Either is indistinguishable from a
real measurement unless the ID is checked explicitly.

The records live in two Redis keyspaces:

```
{submgr_e2SubsDb},<id>
{submgr_restSubsDb},<rest-id>
```

Deleting those two keys and restarting submgr clears the condition **without**
disturbing the E2 node registration. `FLUSHALL` also clears it but drops the E2
registration with it, forcing a full gNB restart — an expensive detour that
cost several hours before the narrower fix was found.

A second failure mode compounded it: the xApp process inside the container
sometimes enters a busy loop at ~99% CPU and does not exit when its client is
killed, because `timeout docker exec ...` terminates only the client. Both
symptoms appear together, which is consistent with, but does not prove, a
common cause in RMR routing to a dead endpoint.

Until that is resolved, multi-run experiments on this lab cannot be trusted
without per-run Subscription ID verification.

## 8. What would finish it

1. Characterise the submgr subscription-lifecycle defect properly — minimal
   reproduction, pre-registration, upstream report to O-RAN SC.
2. Add a continuity criterion to run validity: reject any run whose maximum
   inter-arrival exceeds some multiple of its median.
3. Then run the pre-registered sweep.

Step 1 is not a detour. It is the reason steps 2 and 3 have not happened.
