# Security and operational scope

## KEXT prerequisites

The KEXT runs in the kernel and is ad-hoc signed, without an identified Developer ID KEXT certificate. Loading it on Apple Silicon requires a separately configured Reduced Security/custom SIP environment and user approval. This weakens protections and can increase the consequences of bugs or malicious software. This release neither sets nor further reduces startup security, SIP, AMFI or authenticated-root protections.

Inspect and build the source locally. A successful build or ad-hoc signature verification does not mean Apple endorses or permits the extension under default settings. Do not disable additional protections as an error-handling step. Keep backups and a tested Recovery path; kernel defects can cause panics, boot failure or data loss.

## Current writes and service actions

KEXT 1.0.2 writes exactly these provider properties:

- `region-info`: a 32-byte LL/A payload.
- `country-of-origin`: USA.
- `RegionOnlySpoofTiming`: initialization timing/write-result diagnostics, including the original region/origin properties.

These are volatile runtime writes, not firmware changes. The stop method does not restore them; rebooting without the extension is the restoration boundary.

The optional helper runs as root, checks the exact daemon path and stable PID, and uses a root-owned state directory, lock and atomic state writes. It sends at most one direct SIGTERM per boot, then at most one registered demand-start notification if necessary. Repeated invocation cannot repeatedly signal the daemon. The helper exits after bounded observation rather than running continuously. Unknown existing installation files are refused.

No direct edits are made to Apple's qualification databases, system LaunchDaemon files, language, account, network, DNS, hosts, proxy or FeatureFlags settings. The project does not inject into protected processes, forge private entitlements, patch eligibilityd or include a resetInput permission bypass.

## Data and publication

Local state and logs contain boot UUIDs, process IDs and selected qualification inputs. Review and redact them before sharing. Do not upload raw cloud-feature authorization caches: these can contain account identifiers and signed tokens. The repository and release omit per-machine diagnostic dumps and the local resetInput probe executable.

Package checksums detect an accidental mismatch between bundled helper/plist and their manifest; they are not an independent publisher signature. Review code and use a trusted repository/release channel. The KEXT remains ad-hoc signed.

## Compatibility

This is an unofficial experiment. Apple's daemon interfaces, qualification logic, KEXT management and private implementation details can change with updates. One tested machine/build is not evidence of compatibility with all devices, security policies or future releases. Managed endpoints may prohibit these changes. The project is not affiliated with or supported by Apple and does not establish entitlement to Apple services under account, regional or contractual rules.

Report project bugs without publishing credentials, machine identifiers or raw sensitive logs. Use Apple's official reporting channels for macOS security issues. MIT warranty/disclaimer terms are in [LICENSE](LICENSE).
