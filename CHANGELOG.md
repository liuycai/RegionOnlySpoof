# Changelog

All notable changes to RegionOnlySpoof will be documented here.

## [1.0.1] - 2026-09-09

### Documentation-only security clarification

- Clarified that `csrutil enable --without kext` on the tested macOS 26.6.2 system disabled both Kext Signing and Kernel Integrity Protections, while Filesystem Protections and Authenticated Root Requirement remained enabled.
- Explained that this weakens multiple kernel-related protections and that different macOS versions require checking `csrutil status` and `csrutil authenticated-root status` again.
- Clarified the ad-hoc signature (`Signature=adhoc`, `TeamIdentifier=not set`) and that "identified developers" is Apple's Startup Security Utility wording, not evidence of an identified Developer ID KEXT certificate for this project.
- No source-code or runtime-behavior changes. The KEXT implementation is identical to v1.0.0.

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
