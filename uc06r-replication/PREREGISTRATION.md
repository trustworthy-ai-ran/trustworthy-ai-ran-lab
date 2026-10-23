# UC-06 replication — pre-registration (written before any data)
Build: srsRAN Project d2f4b70dda (same as original). Protocol as original UC-06.
Per run: xApp start -> ping start (-i 0.2) -> 120 s idle -> 120 s load
  (iperf3 UDP 30 Mb/s downlink, -R, -l 1200) -> 60 s idle -> stop ping (Ctrl+C)
  -> stop xApp (Ctrl+C, graceful unsubscribe) -> verify subscriptions == [].
Arm A (replication): Style 2, --metrics DRB.UEThpDl only. 3 runs.
  Prediction: RTT rises sharply during load (sustained, many x idle median);
  DRB.UEThpDl inside the load window does not track the RTT rise.
Arm B (exploratory): Style 2, --metrics DRB.RlcSduDelayDl only (single metric,
  avoids #684). 1-3 runs.
  Prediction: values unusable as a delay signal (negative/implausible), per the
  signed-integer overflow shown in EXP-02C unit tests (old code: -4.3 for 10).
Validity: a run is INVALID if the subscription fails, the xApp errors, the load
  never reaches the UE, or the gNB restarts mid-run. Idle median RTT recorded
  per run; original idle baseline was ~25 ms.
VOID A1 attempt 13:08: iperf3 exited immediately at load start (no load reached UE). See void/A1_iperf.log.
13:1x: iperf3 server restarted (control-socket error), 5 s sanity test OK: 30 Mb/s sent, ~25 Mb/s received at UE.
A1 VALID (13:25-13:33): gNB PID 4422 unchanged, 378 indications, load 30 Mb/s sent / 22.4 Mb/s received (24% loss), clean unsubscribe confirmed on gNB.
A1 result: 57/57 DRB.UEThpDl samples = 0.0 inside the 122 s load window while 22.4 Mb/s reached the UE. Consistent with the old-code throughput truncation seen in EXP-02C unit tests (0 for 0.4); implementation defect not yet separated from semantic question.
A1 RTT: idle median 35 ms (p95 47), load median 2115 ms (p95 2475, max 2728) -> ~60x median inflation (original UC-06: ~50x).
Analysis (terminal-logged LOAD start, 120 s window):
  A1: RTT idle med 35 / load med 2114 ms. KPM: 56/56 zero in load, 271/271 zero in idle (metric stuck at 0 for whole subscription).
  A2: RTT idle med 36 / load med 2008 ms. KPM: 0/56 zero in load (values ~38k-43k); idle mostly 3-5 (= ping traffic ~3.4 kb/s).
  Observation: same build, same gNB PID, same command; metric dead in A1, functional in A2.
  A2 is the semantic test: functional, high throughput reading while RTT ~60x.
  Open: cause of A1 zero-lock; KPM ~40k vs iperf 23.3 Mb/s received (units/definition/DRB summing?).
A3 (pre-registered before run): VM was suspended/resumed after A2; E2 DISCONNECTED, so gNB+UE restarted and RIC made fresh. A3 is therefore on a NEW gNB instance (A1/A2 shared PID 4422).
  RTT prediction: same pattern as A1/A2 (load median >> idle median).
  KPM prediction: NONE. Cause of A1 zero-lock vs A2 functional is unknown; A3 metric behaviour is recorded, not predicted.
  History for reference: gNB 4422's first subscription (12:48, broken xApp) was removed by REST DELETE; A1 followed it; A2 followed a graceful Ctrl+C unsubscribe.
Correction: no core restart was needed; UE obtained PDU session (10.60.0.3) after a delay. A3 runs on fresh gNB+UE+RIC, same core as A1/A2.
A3 setup: VM rebooted after post-resume instability (E2 would not reconnect, UE RRC Release). A3 = fresh VM, core, RIC, gNB, UE.
A3 pre-run (post-reboot): LAB READY 31/31, vCPU 6, idle baseline avg 34 ms, max 47 ms (150 pings). Earlier attempts after reboot: UE registered then released by gNB (NGAP RadioNetwork cause) — ZMQ timing loss suspected.
A3: RTT idle med 33 / load med 2638 ms (~80x). KPM functional: 0/56 zero in load (~30k-34k), idle mostly 3-4 (ping).
ARM A SUMMARY (3 runs): RTT inflation reproduced 3/3 (56x-80x). DRB.UEThpDl functional 2/3 (A2, A3) and blind to the queue in both;
  stuck at zero 1/3 (A1). A3 was the first subscription on a fresh gNB and was functional, so "first subscription after gNB start" does
  not explain A1. A1 cause open.
Arm B start 2026-09-24 10:26:28: clean VM boot, LAB READY 31/31, vCPU 6. Prediction unchanged from pre-registration.
B1 (2026-09-24, load start 10:29:08): subscription accepted (HTTP 200, 10:26:47), xApp alive throughout, gNB PID 4097 unchanged,
  load reached UE (17.1 Mb/s received, 42% loss). ZERO RIC Indications for the entire run (~14 min incl. the 120 s load window).
  PREDICTION MISMATCH: predicted unusable/negative values; observed no reports at all. Same direction (metric unusable), different form.
  Silent: no error anywhere. Contrast: in EXP-02B phase B (delay first, throughput second) indications with delay values did arrive.
  Cause not established. Ping was left running until ~10:40 (analysis uses the load window only).
B2: subscription accepted, gNB PID 4097 unchanged, 16.7 Mb/s received (43% loss), clean stop ([]). ZERO RIC Indications.
ARM B SUMMARY: DRB.RlcSduDelayDl requested alone under Style 2 is SILENT, 2/2 runs, deterministic. Accepted subscription,
  no error, no report, including under saturating load. Mismatch vs prediction (predicted unusable values, observed no values).
C1 (control, pre-registered before run): same gNB/procedure, --metrics DRB.RlcSduDelayDl,DRB.UEThpDl (delay first).
  Prediction: indications arrive (last metric UEThpDl drives readiness under old code) and carry DRB.RlcSduDelayDl values.
  If C1 is also silent, the "silent only when alone" interpretation is rejected.
C1 VALID: PID 4097 unchanged, [] after run, 17.8 Mb/s received (39% loss), 206 indications. Load window (ping-detected) 11:10:08-11:12:11.
  Load (43 ind.): DRB.RlcSduDelayDl 43/43 None; DRB.UEThpDl 43/43 zero.
  Idle (163 ind.): delay 20 values 14.5-25.9 ms (plausible, none negative), 143 None; UEThpDl 20 values 3-5 (ping), 143 zero.
  C1 prediction held (indications arrive, delay values present), BUT delay values only appear under light traffic and vanish under load.
OVERALL (6 loaded runs A1,A2,A3,B1,B2,C1): no KPM metric reflected the 56x-80x RTT inflation in any run.
  Modes: high throughput w/o delay signal (A2,A3); zero (A1,C1); None (C1 delay); no reports at all (B1,B2).
Open: UEThpDl functional in A2/A3 but zero under load in A1/C1 (cause unknown). B1/B2 total silence not fully
  explained by last-metric readiness (C1 shows delay values exist at idle). Mechanism unestablished.
