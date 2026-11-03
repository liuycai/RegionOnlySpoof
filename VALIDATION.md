# Validation: v1.2.0

## Scope

Validated on one Apple Silicon Mac with macOS 27.2 (26B123), KEXT 1.0.2 and helper 1.2.0. This file contains only an aggregate summary; no local log dumps, process IDs, boot UUIDs, serial numbers, account records or private workspace paths are included.

## Causal observations

- In an earlier boot, eligibility region-input initialization preceded the KEXT write by approximately 290 ms.
- The runtime IORegistry later showed LL/A while the original service still rejected device-region qualification.
- After one SIGTERM and demand-start notification, a new service process accepted device-region qualification.
- This supports stale input state in the original process. The exact cache layer was not established by live-memory inspection.

## Cold-boot observations

| Metric | Helper 1.1.0 | Helper 1.2.0 |
|---|---:|---:|
| Boot to confirmed eligibility | 69.342 s | 15.564 s |
| Fixed settle delay | 20 s | 0 s |
| Readiness detection after helper started | Not separately measured | 0.230 s |
| Readiness to starting rebuild | Not separately measured | 0.115 s |
| Helper total elapsed | About 60.48 s | 6.720 s |
| Job runs | 1 | 1 |
| SIGTERM requests | 1 | 1 |
| Demand-start notifications | 1 | 1 |
| Final exit code | 0 | 0 |

In the 1.2.0 boot, the driver was already published when the helper subscribed. That path proceeded immediately after validating the marker. The later-publication callback path has simulated coverage but no separate live-boot observation. Startup throttling, resource load and model availability may change timings.

Current post-boot checks confirmed DEVICE_REGION_CODE status 3 and GREYMATTER, FOUNDATION_MODELS, AMERICIUM answers 4. The helper verifies GREYMATTER/device-region qualification; it does not wait for every domain or model download to complete. The recorded early Siri-language input was not yet final at the moment of the helper result and later converged to its passing state.

## Automated verification

29 local tests passed: 16 flow tests, 7 readiness/marker tests, 6 installer tests. Coverage includes per-boot deduplication, no fixed delay, callback delivery and cleanup, existing services after subscription, incomplete markers, changing service instances, unverified PIDs, signal refusal, qualification timeouts and upgrades from the three prior helper versions.

The KEXT build and strict ad-hoc signature checks are separate from runtime compatibility. The helper used in the publication matches the cold-boot-validated source; only its publication documentation is generalized.

## resetInput experiment

One DEVICE_REGION_CODE resetInput request was sent without replacing the service PID. The daemon rejected it for the missing private `com.apple.private.eligibilityd.resetInput` entitlement; inputs and qualification were unchanged. Static analysis also found that device-region input 6 is absent from this build's allowed resetInput mask. The request did not reach the reset operation. This does not establish what an authorized reset of other inputs would do, and no entitlement bypass or private-XPC fallback is included in this release.

## Limits

Each helper version has one timing observation, not a benchmark distribution. Eligibility passing does not prove fully downloaded models, Siri readiness, service-policy authorization or portability to another OS/hardware configuration. Historical single-property tests belong to the previous release tag and must not be confused with the two-property KEXT in this release.
