# Load Test Report

Release criteria for local load probes:

- no cross-tenant failures;
- no data corruption;
- no duplicate artifacts;
- no unbounded queue growth;
- at least 95% successful requests under the declared supported local profile;
- typed controlled failures beyond capacity.

The local profile is intentionally small and laptop-bound. It must report hardware, concurrency,
request count, success/error rate, p50/p95/p99 latency, throughput, timeout rate, queue behavior,
and resource observations when executed.

Do not extrapolate laptop results to enterprise traffic.

Executed 2026-07-23 against the v0.2.1 local Docker runtime using
`scripts/local_agentic_load.py` after operational hardening:

| Users | Requests | Success Rate | p50 | p95 | p99 | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 15 | 100% | 80.9 ms | 205.3 ms | 211.8 ms | 13.20 rps |
| 10 | 30 | 100% | 101.9 ms | 371.3 ms | 374.8 ms | 7.66 rps |
| 20 | 60 | 100% | 219.8 ms | 820.5 ms | 851.9 ms | 3.39 rps |

The probe registered throwaway local users and verified controlled responses only. It is a laptop
smoke/load check, not a production capacity benchmark.
