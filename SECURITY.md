# Security Policy and Risk Disclosure

## This software runs in the kernel

RegionOnlySpoof is a macOS kernel extension.

A KEXT executes with extremely high privileges.

A defect in kernel code can potentially:

- panic the kernel
- corrupt kernel memory
- crash the operating system
- prevent normal startup
- expose sensitive system state
- increase the impact of another vulnerability

This project is intentionally very small to reduce attack surface, but small code size does not eliminate kernel risk.

## macOS security must be weakened

Apple Silicon Macs normally prevent an ad-hoc KEXT like this from loading.

The validated experiment required Reduced Security and a custom partial SIP configuration.

On the tested macOS 26.6.2 system, after running:

```bash
csrutil enable --without kext
```

`csrutil status` reported:

```text
Kext Signing: disabled
Kernel Integrity Protections: disabled
Filesystem Protections: enabled
Authenticated Root Requirement: enabled
```

This lowers multiple kernel-related protections, beyond permitting a single third-party KEXT, and materially weakens the default macOS security state.

The resulting SIP flags may differ across macOS versions. Always verify the actual state after changing the security policy:

```bash
csrutil status
csrutil authenticated-root status
```

## Ad-hoc signature clarification

RegionOnlySpoof is ad-hoc signed. The validated KEXT reported:

```text
Signature=adhoc
TeamIdentifier=not set
```

The Startup Security Utility option:

```text
Allow user management of kernel extensions from identified developers
```

is Apple's UI wording. It does not mean RegionOnlySpoof carries an identified Developer ID KEXT certificate.

## Security boundaries this project does not require disabling

The validated configuration did not require:

```text
Authenticated Root = disabled
AMFI = disabled
Permissive Security
arbitrary boot-arg code-signing bypasses
```

Do not disable additional protections merely to make this project load.

If macOS rejects the KEXT on a future version, assume compatibility has changed until proven otherwise.

## Scope of the source

The intended source performs one relevant mutation:

```cpp
provider->setProperty("region-info", regionData);
```

The project intentionally does not modify:

```text
country-of-origin
eligibility.plist
countryd
GeoServices
Siri
AppleInternalVariant
FeatureFlags
DNS
hosts
proxy configuration
```

Users should inspect the source themselves before building or installing it.

## Binary trust

Do not install an unknown precompiled copy of this KEXT from an untrusted third party.

The preferred security model for this experiment is:

```text
inspect source
-> build locally
-> inspect binary
-> ad-hoc sign locally
-> install your own build
```

## Verification

Useful checks include:

```bash
grep -R -n 'setProperty' src
```

and:

```bash
grep -R -n -E \
'country-of-origin|eligibility|countryd|GeoServices|Siri|AppleInternal|FeatureFlags|hosts|proxy|DNS' \
src
```

The latter should return no matches for the minimal implementation.

## System updates

macOS updates may change:

- KEXT authentication
- Auxiliary Kernel Collection behavior
- Kernel ABI/API compatibility
- IOKit matching
- eligibility logic
- Apple Intelligence availability logic
- interpretation of `region-info`

Do not assume a build validated on one macOS release is safe or functional on another.

Major macOS upgrades should be treated as a new validation target.

## Corporate systems

This project is generally inappropriate for managed corporate endpoints that require:

- standard SIP
- Full Security
- endpoint compliance enforcement
- security certification
- kernel-extension restrictions

Consult your organization's security policy.

## Vulnerability reporting

If you discover a bug in RegionOnlySpoof itself, open a GitHub issue without posting private information, credentials, machine identifiers or sensitive logs.

For vulnerabilities in macOS or Apple services, use Apple's official security reporting channels.

## Disclaimer

This repository is an independent research project.

It is not affiliated with, endorsed by, sponsored by, or supported by Apple Inc.

The software is provided "AS IS", without warranty.

The authors and contributors are not responsible for:

- system damage
- data loss
- security incidents
- account restrictions
- service unavailability
- compliance issues
- software incompatibility
- changes introduced by Apple

Use entirely at your own risk.
