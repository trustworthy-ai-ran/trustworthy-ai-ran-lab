# Raw data

- `run2_ping.txt` — Run 2 probe log: 1 Hz timestamped ICMP (`ping -i 1 -D`), UE (netns ue1) → 10.45.0.2. 372 samples spanning idle → load → recovery.
- `run1_kpm.log` — full xApp session log covering Run 2: every E2SM-KPM RIC Indication received (Style 2, UE 0, DRB.UEThpDl, 1 s granularity). CollectStartTime is native UTC.
- `run3_ping.txt` — Run 3 probe log (435 samples, p95 2,125 ms).

Analysis one-liner used for the summary stats:
`grep -oP 'time=\K[0-9.]+' run2_ping.txt | sort -n | awk '{a[NR]=$1} END {print "p50="a[int(NR/2)], "p95="a[int(NR*0.95)], "max="a[NR]}'`
