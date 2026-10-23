# UC-06 replication — environment (2026-09-23 13:05:10 PDT)
gNB: srsRAN Project d2f4b70dda (same as original)
Kernel: 6.8.0-138-generic (original run on an older kernel; gtp5g rebuilt for this one)
VM: RAM 12 GB (was 24 GB), vCPU 8. Changed because host was at 95% RAM / 90% CPU (idle RTT avg 91 ms).
After change: idle RTT avg 34 ms, max 127 ms (150 pings). Original idle baseline ~25 ms.
Known issues in this build: #684 (Style 2 multi-metric readiness), RLC latency overflow.
