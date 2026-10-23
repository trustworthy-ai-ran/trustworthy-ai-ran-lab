"""Every number reported in the paper, recomputed from the raw UC-06R logs.

Conventions (used everywhere in the paper and figures):
  * median / percentiles: numpy defaults (linear interpolation), rounded half-up to integers
  * load window: 120 s from load start. A1-A3 and B1: start logged by the run script.
    B2, C1: first of 25 consecutive probe replies above 5x the idle median.
  * pre-load idle: every probe reply before load start.

Run from anywhere:  python3 tools/uc06r/stats.py   -> prints every value and writes uc06r-replication/numbers.json
"""
import datetime as dt
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "uc06r-replication", "data")
TZ = dt.timezone(dt.timedelta(hours=-7))  # PDT, as printed by the run scripts
LOGGED = {"A1": (2026, 9, 23, 13, 30, 30), "A2": (2026, 9, 23, 13, 41, 51),
          "A3": (2026, 9, 23, 22, 30, 18), "B1": (2026, 9, 24, 10, 29, 8)}
RUNS = ["A1", "A2", "A3", "B1", "B2", "C1"]
SUBS = {"A1": "Thp", "A2": "Thp", "A3": "Thp", "B1": "Delay", "B2": "Delay", "C1": "Delay, Thp"}


def r(x):
    return int(math.floor(x + 0.5))


def ping(run):
    out = []
    for line in open(os.path.join(DATA, f"{run}_ping.log"), errors="replace"):
        for a, b in re.findall(r"\[(\d+\.\d+)\].*time=([\d.]+)", line):
            out.append((float(a), float(b)))
    return out


def kpm(run):
    out, cur, sub, unsub = [], None, None, None
    for line in open(os.path.join(DATA, f"{run}_kpm.log"), errors="replace"):
        if "Successfully subscribed" in line and sub is None:
            sub = float(line.split()[0])
        if "Successfully unsubscribed" in line:
            unsub = float(line.split()[0])
        m = re.match(r"^(\d+\.\d+) RIC Indication Received", line)
        if m:
            cur = {"t": float(m.group(1)), "m": {}}
            out.append(cur)
            continue
        m = re.match(r"^(\d+\.\d+) --Metric: ([\w.]+), Value: \[([^\]]*)\]", line)
        if m and cur is not None:
            cur["m"][m.group(2)] = m.group(3)
    return out, sub, unsub


def iperf_rx(run):
    for line in open(os.path.join(DATA, f"{run}_iperf.log"), errors="replace"):
        if "receiver" in line:
            rate = float(re.search(r"([\d.]+) Mbits/sec", line).group(1))
            loss = int(re.search(r"\((\d+)%\)", line).group(1))
            return rate, loss
    return None, None


def detect(p):
    base = float(np.median([v for _, v in p[:300]]))
    for i in range(len(p) - 25):
        if all(p[j][1] > 5 * base for j in range(i, i + 25)):
            return p[i][0]
    return None


def compute():
    res = {}
    for run in RUNS:
        p = ping(run)
        ind, sub, unsub = kpm(run)
        t_det = detect(p)
        if run in LOGGED:
            t0 = dt.datetime(*LOGGED[run], tzinfo=TZ).timestamp()
            src = "logged"
        else:
            t0, src = t_det, "detected"
        t1 = t0 + 120
        idle = np.array([v for t, v in p if t < t0])
        load = np.array([v for t, v in p if t0 <= t <= t1])
        rx, loss = iperf_rx(run)
        row = dict(
            window_source=src,
            detect_minus_logged_s=(round(t_det - t0, 1) if src == "logged" else None),
            idle_before_load_s=r(t0 - p[0][0]),
            after_load_s=r(p[-1][0] - t1),
            subscribed_s=(r(unsub - sub) if sub and unsub else None),
            rtt_idle=dict(median=r(np.median(idle)), p95=r(np.percentile(idle, 95)), max=r(idle.max())),
            rtt_load=dict(median=r(np.median(load)), p95=r(np.percentile(load, 95)), max=r(load.max())),
            inflation=round(float(np.median(load) / np.median(idle)), 1),
            rx_mbps=rx, loss_pct=loss, indications=len(ind), subscription=SUBS[run],
        )
        for metric in sorted({m for i in ind for m in i["m"]}):
            for phase, sel in (("idle", lambda t: t < t0), ("load", lambda t: t0 <= t <= t1),
                               ("after", lambda t: t > t1)):
                vals = [i["m"][metric] for i in ind if metric in i["m"] and sel(i["t"])]
                num = np.array([float(v) for v in vals if v not in ("None", "")])
                nz = num[num != 0]
                d = dict(n=len(vals), none=vals.count("None"), zero=int((num == 0).sum()), nonzero=len(nz))
                if len(nz):
                    d.update(min=float(nz.min()), max=float(nz.max()), median=r(np.median(nz)),
                             p10=r(np.percentile(nz, 10)), p90=r(np.percentile(nz, 90)))
                row[f"{metric}|{phase}"] = d
            if sub:
                carried = [i["t"] - sub for i in ind if i["m"].get(metric) not in (None, "None", "0.0", "0")]
                row[f"{metric}|last_value_s_after_subscribe"] = round(max(carried), 1) if carried else None
                row[f"{metric}|last_value_s_before_load"] = (round(t0 - sub - max(carried), 1) if carried else None)
        res[run] = row
    return res


if __name__ == "__main__":
    res = compute()
    for run, row in res.items():
        print("=====", run)
        for k, v in row.items():
            print(f"  {k}: {v}")
    with open(os.path.join(REPO, "uc06r-replication", "numbers.json"), "w") as f:
        json.dump(res, f, indent=1)
