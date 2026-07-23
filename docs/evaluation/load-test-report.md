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

Executed 2026-07-23 against the local Docker runtime using `scripts/local_agentic_load.py`:

| Users | Requests | Success Rate | p50 | p95 | p99 | Throughput |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 15 | 100% | 34.2 ms | 123.0 ms | 135.7 ms | 21.4 rps |
| 10 | 30 | 100% | 82.4 ms | 383.3 ms | 387.0 ms | 7.44 rps |
| 20 | 60 | 100% | 169.5 ms | 493.6 ms | 599.1 ms | 4.79 rps |

The probe registered throwaway local users and verified controlled responses only. It is a laptop
smoke/load check, not a production capacity benchmark.
