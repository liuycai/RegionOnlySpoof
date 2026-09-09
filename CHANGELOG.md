# Changelog

All notable changes to RegionOnlySpoof will be documented here.

## [1.0.0] - 2026-09-09

### Added

Initial public release.

- Minimal Apple Silicon runtime `region-info` spoof.
- Changes `CH/A` to `LL/A`.
- Leaves `country-of-origin` unchanged.
- No `eligibility.plist` modification.
- No `countryd` modification.
- No GeoServices spoof.
- No Siri patching.
- No DNS, hosts or proxy changes.
- No LaunchDaemon.
- Apple M5 Pro / Mac17,9 / macOS 26.6.2 validation record.
- Build documentation.
- Installation documentation.
- Full uninstall and security-restoration documentation.
- Security risk disclosure.
- MIT license.

### Validated result

```text
region-info:
CH/A -> LL/A

country-of-origin:
CHN -> CHN

DEVICE_REGION_CODE:
2 -> 3

FOUNDATION_MODELS:
2 -> 4

PERSONAL_QA:
2 -> 4

SIRI_WITH_APP_INTENTS:
2 -> 4

GREYMATTER:
2 -> 4 after normal device/Siri language alignment
```
