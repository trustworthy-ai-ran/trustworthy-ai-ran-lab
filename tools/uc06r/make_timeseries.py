"""Time-aligned RTT and KPM per run, from raw logs."""
import re, os, statistics, datetime as d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_figs.py")).read().split("# ---------------------------------------------------------------- Fig. 1")[0])
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "uc06r-replication", "data"))
tz = d.timezone(d.timedelta(hours=-7))
LOGGED = {"A1": (2026,9,23,13,30,30), "A2": (2026,9,23,13,41,51), "A3": (2026,9,23,22,30,18), "B1": (2026,9,24,10,29,8)}
def ping(r):
    return [(float(a), float(b)) for l in open(f"{DATA}/{r}_ping.log") for a, b in re.findall(r"\[(\d+\.\d+)\].*time=([\d.]+)", l)]
def kpm(r):
    out = []; cur = None
    for l in open(f"{DATA}/{r}_kpm.log", errors="replace"):
        m = re.match(r"^(\d+\.\d+) RIC Indication Received", l)
        if m: cur = {"t": float(m.group(1)), "m": {}}; out.append(cur); continue
        m = re.match(r"^(\d+\.\d+) --Metric: ([\w.]+), Value: \[([^\]]*)\]", l)
        if m and cur is not None: cur["m"][m.group(2)] = m.group(3)
    return out
def load_start(r, p):
    if r in LOGGED: return d.datetime(*LOGGED[r], tzinfo=tz).timestamp()
    base = statistics.median([v for _, v in p[:300]])
    i = next(i for i in range(len(p) - 25) if all(p[j][1] > 5 * base for j in range(i, i + 25)))
    return p[i][0]

cols = [("A2", "A2: blind (throughput works)", "DRB.UEThpDl"),
        ("A1", "A1: stuck (throughput 0.0)", "DRB.UEThpDl"),
        ("C1", "C1: void (delay None)", "DRB.RlcSduDelayDl"),
        ("B1", "B1: silent (delay alone)", None)]
fig, axes = plt.subplots(2, 4, figsize=(7.16, 2.75), sharex=True,
                         gridspec_kw={"height_ratios": [1.25, 1], "hspace": 0.12, "wspace": 0.42})
for c, (r, title, metric) in enumerate(cols):
    p = ping(r); k = kpm(r); t0 = load_start(r, p)
    ax = axes[0, c]
    ax.axvspan(0, 120, color="#F6E3D8", lw=0, zorder=0)
    ax.plot([t - t0 for t, _ in p], [v for _, v in p], color=ORANGE, lw=0.5, zorder=2)
    ax.set_yscale("log"); ax.set_ylim(10, 5000)
    ax.set_yticks([10, 100, 1000]); ax.set_yticklabels(["10", "100", "1k"])
    ax.set_title(title, fontsize=7.5, color=INK, pad=3)
    clean(ax, None)
    if c == 0: ax.set_ylabel("RTT (ms)")
    ax2 = axes[1, c]
    ax2.axvspan(0, 120, color="#F6E3D8", lw=0, zorder=0)
    clean(ax2, None)
    if metric is None:
        ax2.set_yticks([]); ax2.set_ylim(0, 1)
        ax2.text(30, 0.5, "0 RIC Indications\nin the whole run", ha="center", va="center", fontsize=7, color=INK)
    else:
        xs, ys, xn, xz = [], [], [], []
        for i in k:
            v = i["m"].get(metric); t = i["t"] - t0
            if v in (None, "None"): xn.append(t)
            elif float(v) == 0: xz.append(t)
            else: xs.append(t); ys.append(float(v))
        if metric == "DRB.UEThpDl":
            ax2.scatter(xs, [y / 1000 for y in ys], s=3, color=BLUE, lw=0, zorder=3)
            ax2.scatter(xz, [0] * len(xz), s=3, color=MUTED, lw=0, zorder=3)
            ax2.set_ylim(-4, 64); ax2.set_yticks([0, 30, 60])
            if c == 0: ax2.set_ylabel("Thp value (×10³)")
        else:
            ax2.scatter(xs, ys, s=3, color=BLUE, lw=0, zorder=3)
            ax2.scatter(xn, [0] * len(xn), s=3, color=MUTED, marker="|", lw=0.6, zorder=3)
            ax2.set_ylim(-2, 32); ax2.set_yticks([0, 15, 30])
            ax2.set_ylabel("Delay (ms)", labelpad=1)
    ax2.set_xlim(-150, 185); ax2.set_xticks([-120, 0, 120])
    ax2.set_xlabel("s from load start", labelpad=1)
axes[1, 1].text(60, 30, "0.0 in all 378 reports", ha="center", fontsize=6.8, color=INK)
axes[1, 2].text(60, 22, "grey: None", ha="center", fontsize=6.8, color=INK2)
save(fig, "fig_timeseries")
print("ok")
