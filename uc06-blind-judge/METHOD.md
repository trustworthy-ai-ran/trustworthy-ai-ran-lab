# UC-06 "The Blind Judge" — Method & Reproducibility Notes

Companion to the repository README. All timestamps UTC unless noted. Run date: 2026-07-17.

## 1. Testbed

| Component | Detail |
|---|---|
| Host | Single Ubuntu 22.04 VM (VMware), ~23 GB RAM |
| RAN | srsRAN Project gNB + srsUE, ZMQ virtual PHY, single cell, single UE |
| Core | free5GC (5G SA), gtp5g kernel module; UE IMSI 208930000000001, PLMN 20893 |
| RIC | O-RAN SC Near-RT RIC, i-release, 7 containers (e2term, e2mgr, submgr, appmgr, rtmgr_sim, dbaas, python_xapp_runner) |
| E2 | Live SCTP to e2term 10.0.2.10:36421; gNB E2 node `gnbd_208_093_00019b_0`; E2SM-KPM + E2SM-RC |
| Monitoring | `kpm_mon_xapp.py` (OSC reference) — **Report Style 2 (UE-level), metric `DRB.UEThpDl`, granularity 1000 ms** |
| Traffic sink | iperf3 server in isolated netns (`srv`, 10.45.0.2) on the N6 side; veth 10.45.0.1 ↔ 10.45.0.2 |
| Probe | ICMP ping, 1 Hz, timestamped (`ping -i 1 -D`), from netns `ue1` to 10.45.0.2 |

## 2. Pre-registered protocol (locked before data collection)

Each run: **60 s idle → 120 s saturating DL UDP (iperf3 `-u -b 30M -t 120 -R`) → ≥60 s recovery**, with (a) every RIC Indication logged by the xApp and (b) the 1 Hz probe recording end-to-end RTT throughout. Three runs planned.

**Hypothesis H1:** during the load phase, user RTT p50 exceeds 1,000 ms while the KPM stream reports healthy throughput with no degradation signal. Rejection criterion: any meaningful KPM anomaly or drop during load falsifies H1 and is reported as such.

**Prior characterization:** the fault mechanism (bufferbloat) was previously isolated on the same testbed — a standing queue of 6,172,672 bytes in the gNB RLC DL buffer, read from the gNB's *local* metrics stream (`rlc queue_size_bytes`, WebSocket :8001). The gNB's local "latency" fields (e.g., `mac.dl.average_latency_us` ≈ 48 µs) describe internal processing latency, not queueing delay.

## 3. Run accounting

| Run | Status | Notes |
|---|---|---|
| 1 | **Voided** | Background probe suspended by a sudo credential prompt before writing any sample; no latency data captured. Voided per protocol; reported for transparency. |
| 2 | Valid | 372 samples; p50 42.8 ms, p95 2,189 ms, max 2,956 ms. Data: `data/run2_ping.txt`, `data/run1_kpm.log` (xApp session covering the run) |
| 3 | Valid | 435 samples; p50 39.9 ms, p95 2,125 ms, max 2,637 ms; full 120 s iperf accounting: 30.0 Mb/s offered, 23.3 Mb/s delivered, ~21% datagram loss, jitter 0.5–1.7 ms |

Time alignment: KPM `CollectStartTime` is native UTC; probe timestamps are epoch (`-D`), converted to UTC. During 05:29:31–46 UTC, KPM reported a constant 59,043 while the probe recorded 2,055–2,519 ms.

Note on the raw KPM stream: values alternate 0.0 / 59,043 on adjacent reporting windows (a windowing artifact of the reporting pipeline); filtering zero-valued windows, the signal is constant. The reported unit is treated as an opaque healthy-state indicator (RLC-level accounting plausibly differs from application goodput); the claim rests on its *constancy*, not its absolute value.

## 4. Reproducibility notes (hard-won)

1. **E2 bind address:** with the RIC co-hosted on the same machine, the srsRAN E2 agent requires an explicit `bind_addr` on the Docker bridge address (here 10.0.2.1). Without it, E2 connect fails ("Network is unreachable") and the failed-retry path crashed on our build.
2. **e2mgr/Redis startup race:** OSC e2mgr retries its dbaas (Redis) connection only 3 × 10 ms at startup and loses the race on a cold `compose up` — the E2 node then attaches at e2term but is never registered, and every xApp subscription returns HTTP 503. Remedy: `docker restart ric_e2mgr ric_submgr` after dbaas is up, then re-attach the gNB.
3. **KPM report styles:** on this stack, Style 1 (node-level) returned 0.0 for `DRB.UEThpDl` under all conditions; only **Style 2 with an explicit UE ID** produced live values.
4. **Traffic direction:** iperf3 from inside `ue1` without `-R` measures uplink (~5 Mb/s on srsUE/ZMQ — normal, not a fault). All baselines and runs are downlink: `-R` is mandatory.
5. **Background probe:** never launch with bare `sudo ... &` (credential prompt suspends the job). Use `sudo ip netns exec ue1 bash -c 'ping -i 1 -D <dst> > FILE 2>&1 &'` and verify the file grows before proceeding.
6. **iperf3 server hygiene:** the netns iperf3 server can die after heavy UDP; a stale listener then causes "control socket has closed" on the next client. `pkill -9 iperf3`, restart with `-s -D`, verify with `ss -tlnp | grep 5201`.

## 5. Limitations

Single-cell, single-UE, virtual-PHY testbed; claims are relative/structural (KPM signal vs. user RTT under a queue-building load), not absolute performance. ICMP is a coarse QoE proxy. One fault class; the systematic generalization (fault × E2-visibility "observability atlas") is the planned next study. Scope: the E2SM-KPM measurement set exposed end-to-end by this stack.
