# UC-06R — replication of the Blind Judge, three subscription arms (September 2026)

Same lab and the same gNB build as UC-06 (srsRAN Project `d2f4b70dda`), re-run on
23–24 September 2026 with a faster probe and three subscription arms. It answers the
question UC-06 left open: *what does the xApp receive if it also asks for a delay
measurement?*

## Protocol

Per run: the xApp subscribes (E2SM-KPM Report Style 2, UE 0) and the probe starts
(ICMP from the UE every 200 ms) → at least 120 s idle → 120 s of iperf3 UDP downlink
at 30 Mb/s (`-R -l 1200`) → at least 60 s idle → probe and xApp stopped, graceful
unsubscribe. A run is void if the subscription fails, the xApp errors, the gNB
restarts, or the load never reaches the UE. Void runs are kept and reported.

| Arm | Subscription (metrics, in order) | Runs |
|---|---|---|
| A | `DRB.UEThpDl` | A1, A2, A3 |
| B | `DRB.RlcSduDelayDl` | B1, B2 |
| C1 (control) | `DRB.RlcSduDelayDl, DRB.UEThpDl` | C1 |

A1 and A2 ran on one gNB instance (PID 4422), A3 on a second (3945), B1, B2 and C1 on
a third (4097).

## Results

RTT in ms: pre-load idle as median / p95, load window as median / p95 / max. Rx and loss are from the iperf3 receiver report.

| Run | Pre-load idle RTT | Load-window RTT | Inflation | Rx (loss) | What the xApp received in the load window | Mode |
|---|---|---|---|---|---|---|
| A1 | 35 / 47 | 2,114 / 2,473 / 2,728 | 61× | 22.4 Mb/s (24%) | 56 reports, all 0.0 (0.0 in all 378 reports of the run) | stuck |
| A2 | 36 / 70 | 2,008 / 2,292 / 2,406 | 56× | 23.3 Mb/s (21%) | 56 reports, all non-zero, median 51,778 | blind |
| A3 | 33 / 45 | 2,638 / 2,956 / 3,181 | 79× | 18.2 Mb/s (38%) | 56 reports, all non-zero, median 39,710 | blind |
| B1 | 35 / 50 | 2,807 / 3,174 / 3,352 | 80× | 17.1 Mb/s (42%) | no Indication in the whole run (~15 min subscribed) | silent |
| B2 | 35 / 47 | 2,874 / 3,153 / 3,328 | 81× | 16.7 Mb/s (43%) | no Indication in the whole run (~21 min subscribed) | silent |
| C1 | 36 / 51 | 2,661 / 2,994 / 3,403 | 74× | 17.8 Mb/s (39%) | 42 reports: delay `None`, throughput 0.0 in all | void (delay), stuck (throughput) |

![Time-aligned witnesses](figures/fig_timeseries.png)

**What the six runs show**

- The queue was the same in every run: median RTT 33–36 ms before the load and
  2.0–2.9 s under it (56–81×). No KPM report showed it.
- `DRB.UEThpDl` either looked like a healthy, busy cell (A2, A3) or reported 0.0 for
  the whole subscription (A1, same build and gNB instance as A2).
- In the working runs the reported value is ≈2.2× the rate received at the UE, if
  read as kbit/s (A2: 51,778 vs 23.3 Mb/s; A3: 39,710 vs 18.2 Mb/s), and above the
  30 Mb/s offered load. In A2 the value 59,022 appears in 9 of the 56 load-window
  reports and is never exceeded. See [OQ-3](../OPEN_QUESTIONS.md).
- `DRB.RlcSduDelayDl` requested alone produced no Indication at all in 2 of 2 runs,
  with the subscription accepted and no error.
- C1 produced 206 Indications. 20 of the 118 pre-load reports carried a delay value
  (14.5–25.9 ms) and non-zero throughput (3–5); all 20 fell within the first 118 s
  after subscribing, 27 s before the load began. Every later report, including all 42
  in the load window, carried delay `None` and throughput 0.0.

## Analysis conventions

- Load window: 120 s from load start. A1–A3 and B1: the start noted at the terminal
  when the load was launched. B2 and C1: the first of 25 consecutive probe replies
  above 5× the median of the run's first 300 probe replies. On A1–A3 and B1, detection followed the noted start by
  0.8–1.7 s. Using probe detection for all six runs changes no RTT statistic by more
  than 2 ms and no report count by more than one.
- Pre-load idle: every probe reply before load start.
- Medians and percentiles: numpy defaults (linear interpolation), rounded half-up.
- Every number above is produced by `tools/uc06r/stats.py` and stored in
  `numbers.json`.

## Records

- `PREREGISTRATION.md` — the first 15 lines (protocol, Arms A and B, predictions,
  validity rules) were written and hashed before any data:
  `head -15 PREREGISTRATION.md | sha256sum` gives the value in
  `PREREGISTRATION.sha256`. The rest of the file is the session log, appended as the
  runs went. The A3 note and the C1 control were written before their own runs but
  after earlier data, and were not hashed separately. Some figures in that log were
  quick in-session estimates (for example "~38k–43k", "~14 min"); `numbers.json`
  supersedes them.
- `ENVIRONMENT.md` — host and VM changes, recorded before A1. It lists 8 vCPUs;
  the lab checks before A3 and before Arm B (in the session log) reported 6. We
  treat this as an uncontrolled difference between runs.
- `data/` — raw xApp logs (`*_kpm.log`, every RIC Indication with its arrival time),
  probe logs (`*_ping.log`), iperf3 reports, and the gNB PID before each run.
  `*_analysis.txt` are in-session quick checks (A2's used a wrong window); they are
  kept as recorded and superseded by `stats.py`.
- `data/void/` — the first A1 attempt, voided because iperf3 exited at load start.

## Reproduce

```bash
pip install numpy matplotlib
python3 tools/uc06r/stats.py          # prints every value, writes uc06r-replication/numbers.json
python3 tools/uc06r/make_figs.py      # figures 1–5 and 7 into uc06r-replication/figures
python3 tools/uc06r/make_timeseries.py
```

## Scope

One UE on a ZMQ virtual radio, one VM, one gNB build. All runs used the build that
predates the upstream fix of issue #684 (see [`../exp-02c`](../exp-02c)). Constant-rate
UDP overload is a worst case for queue build-up. Six runs show that the modes occur,
not how often.
