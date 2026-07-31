# UC-07 — "The Slowing Judge"

**Does the Near-RT RIC's view of the network get older exactly when the
network gets busy?**

Pre-registration. Locked before the confirmatory runs. Sections 1–7 may not be
edited afterwards; corrections go in a dated Amendment section.

---

## 1. Pilot observation that motivated this

Measured 31 July 2026, one session, one configuration, `du_report_period: 1000`
unchanged throughout. Timestamps taken host-side as each Indication reached the
xApp.

| Condition | Indications | Span | Median inter-arrival |
|---|---|---|---|
| Style 2, idle | 56 | 64.2 s | **1.15 s** |
| Style 2, iperf loopback inside `srv` (negative control) | 55 | 64.2 s | **1.17 s** |
| Style 2, 30 Mb/s DL through the RAN | 27 | 63.1 s | **2.34 s** |
| Style 1, idle | 55 | 63.8 s | **1.17 s** |
| Style 1, 30 Mb/s DL through the RAN | 32 | 63.5 s | **2.05 s** |

The negative control matters: running iperf3 at the same rate without the
traffic crossing the RAN changed nothing. Only load that passes through the RLC
queue changed the cadence.

These are **pilot data**. They generated the hypothesis and are not counted as
evidence for it. Everything below is tested on fresh runs.

## 2. Hypotheses — locked

**H1.** Indication inter-arrival time increases with offered downlink load.

**H2.** The effect is not specific to a Report Style: both Style 1 and Style 2
show it.

**H3.** At zero load, the cadence matches the configured `du_report_period`
(1000 ms) to within 25%.

H2 is stated separately because Style 1 sets `is_ind_msg_ready_`
unconditionally while Style 2 gates it on the last metric's value (EXP-02B). If
only Style 2 slowed, the cause would be that readiness check. The pilot
suggests it is not; H2 tests that properly.

## 3. Independent variable

Offered downlink UDP load generated inside `ue1`, so that it traverses the RAN:

```
sudo ip netns exec ue1 iperf3 -c 10.45.0.2 -u -b <RATE> -l 1200 -t 85 -R
```

Levels: **0, 5, 10, 20, 30 Mb/s.** `-l 1200` avoids the EMSGSIZE fragmentation
issue in this GTP-U path.

Report Style: **1 and 2**, each at every load level.
Replicates: **3 per cell** — 5 × 2 × 3 = 30 runs of 70 s.

## 4. Primary measurement

Median inter-arrival time between consecutive `RIC Indication Received` events,
per run, from host wall-clock timestamps applied as each line is read.

Reported per cell as the median of the three replicate medians, with the min
and max across replicates.

## 5. Run validity — locked

A run counts only if all of the following hold. Invalid runs are repeated, not
interpreted:

- the submgr subscription list was `[]` immediately before the run started
- the Subscription ID in the run log differs from the previous run's
- at least 10 Indications were received
- the run lasted at least 60 s
- above zero load, iperf3 reported a client socket on `10.60.0.x`, confirming
  the traffic originated in `ue1` and crossed the RAN
- no `ApiException`, `Traceback`, or `Address already in use` in the log

These subscription checks are not routine hygiene. This lab has a defect in
which a subscription record carrying `"SubscriptionInstances": null` survives
both `DELETE` and a submgr restart, and silently absorbs later identical
subscriptions, routing their Indications to a dead endpoint. An affected run
returns zero Indications — indistinguishable from a real finding if the check
is skipped. Characterising it cost several hours on 30–31 July.

## 6. Analysis rule — locked

- **H1 confirmed** iff, for both styles, cell medians are non-decreasing across
  0 → 5 → 10 → 20 → 30 Mb/s, and the median at 30 Mb/s is at least 1.5× the
  median at 0 Mb/s.
- **H2 confirmed** iff both styles independently satisfy H1.
- **H3 confirmed** iff both zero-load medians fall within 750–1250 ms.

A pattern matching none of these is reported exactly as observed, with no
post-hoc reinterpretation.

## 7. Threats to validity

- **Single build, single UE, ZMQ virtual radio.** No RF, no mobility, no
  multi-user scheduling. The claim is about this stack.
- **`du_report_period` is held at 1000 ms and never varied.** If the effect is
  an interaction with that value, this design will not see it.
- **The mechanism is not identified.** This measures that cadence changes with
  load. It does not establish whether the delay sits in metric collection,
  ASN.1 encoding, the E2 agent, or SCTP transport. Attribution needs an
  instrumented build.
- **Host CPU contention is not controlled.** iperf3, gNB, UE, the core and seven
  containers share one VM. Part of the slowdown may be scheduling pressure
  rather than anything in the E2 path. The loopback control argues against this
  — iperf3 alone at the same rate changed nothing — but does not exclude it,
  because loopback traffic never exercises the gNB.
- **Zero-valued metrics.** Under real RAN load every sampled value was `0.0` on
  both styles while ~24 Mb/s was flowing. That is a separate open question
  (OPEN_QUESTIONS.md, OQ-1) and is not addressed here. Cadence is measured from
  arrival times, not values, so the two are independent.
- **Ordering effects.** Any monotonic drift over the session would mimic H1.
  Mitigation: the two style blocks run in opposite load order, so drift would
  appear as opposite trends rather than one consistent trend.

## 8. What each outcome means

| Result | Reading |
|---|---|
| H1 and H2 confirmed | Telemetry ages fastest when the network is busiest. Any control loop tuned on idle-state cadence runs on staler data than it assumes, precisely when it matters. |
| H1 confirmed, H2 rejected | The effect is style-specific and points back at the Style 2 readiness check — a direct continuation of EXP-02B. |
| H1 rejected | The pilot was an artefact. Reported as such; the pilot table and the negative control stay in the record. |
| H3 rejected | The configured reporting period does not describe the delivered cadence even at rest, which is its own finding. |

## 9. Record

Pre-registered 31 July 2026, after the pilot runs above and before any
confirmatory run. Amendments appear below with timestamps and reasons.
