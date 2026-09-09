# RegionOnlySpoof

Minimal Apple Silicon `region-info` runtime spoof experiment.

> This project changes one property only:
>
> `IOPlatformExpertDevice.region-info`
>
> from `CH/A` to `LL/A` at runtime.
>
> It intentionally does **not** modify `country-of-origin` or other Apple Intelligence eligibility inputs.

## Why this project exists

Some mainland-China Mac hardware reports:

```text
country-of-origin = CHN
region-info       = CH/A
```

On a tested Apple Silicon Mac running macOS 26.6.2, `CH/A` caused:

```text
OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE = 2
```

This project was created to test a single-variable hypothesis:

> Is changing only `region-info` from `CH/A` to `LL/A` sufficient to change Apple's device-region eligibility result?

The answer on the validated system was **yes**.

## Design principle

RegionOnlySpoof deliberately performs the smallest possible runtime modification.

It changes:

```text
region-info:
CH/A -> LL/A
```

It does NOT change:

```text
country-of-origin
eligibility.plist
countryd
GeoServices
Siri configuration
AppleInternalVariant
FeatureFlags
DNS
hosts
proxy settings
network routing
Apple Account region
```

There is no LaunchDaemon and no background script that modifies these services.

## Runtime behavior

The kernel extension matches:

```text
IOPlatformExpertDevice
```

and performs one relevant property write:

```cpp
provider->setProperty("region-info", regionData);
```

The `OSData` payload is 32 bytes long and begins with:

```text
LL/A
```

The original:

```text
country-of-origin = CHN
```

remains unchanged.

## Verified result

Validation platform:

| Item | Value |
|---|---|
| Machine | MacBook Pro |
| Model Identifier | Mac17,9 |
| SoC | Apple M5 Pro |
| Memory | 24 GB |
| Model Number | MGDN4CH/A |
| macOS | 26.6.2 |
| Build | 25G83 |
| Test date | 2026-09-09 |

### IORegistry

| Property | Before | After |
|---|---|---|
| `region-info` | `CH/A` | `LL/A` |
| `country-of-origin` | `CHN` | `CHN` |

### Eligibility

| Eligibility input/domain | Before | After |
|---|---:|---:|
| `DEVICE_REGION_CODE` | 2 | 3 |
| `FOUNDATION_MODELS` | 2 | 4 |
| `PERSONAL_QA` | 2 | 4 |
| `SIRI_WITH_APP_INTENTS` | 2 | 4 |

After changing the macOS device language to English and Siri to `en-US`:

| Eligibility input/domain | Before alignment | After alignment |
|---|---:|---:|
| `DEVICE_AND_SIRI_LANGUAGE_MATCH` | 2 | 3 |
| `SIRI_LANGUAGE` | 3 | 3 |
| `GREYMATTER` | 2 | 4 |

The runtime availability log subsequently reported:

```text
isDeviceEligible: true
isAppleIntelligenceToggleEnabled: true
```

and feature access included:

```text
cloud.llm
ai.paperkit.image-generation
ai.keyboard.emoji-generation
ai.apps.image-playground
```

See [VALIDATION.md](VALIDATION.md) for details.

## Important observation

During the successful test:

```text
COUNTRY_LOCATION = 2
```

remained unchanged.

Nevertheless:

```text
FOUNDATION_MODELS = 4
PERSONAL_QA = 4
SIRI_WITH_APP_INTENTS = 4
GREYMATTER = 4
```

on this specific macOS build.

This suggests that `COUNTRY_LOCATION = 2` was not a hard blocker for those domains in this tested configuration.

This is an experimental observation, not a statement about all macOS versions.

## Security requirements

This project uses a legacy macOS kernel extension.

On Apple Silicon, loading an ad-hoc signed KEXT may require:

- Reduced Security
- user management of kernel extensions
- a custom partial SIP configuration

The validated configuration used:

```bash
csrutil enable --without kext
```

On the validated macOS 26.6.2 system, `csrutil status` reported both:

```text
Kext Signing: disabled
Kernel Integrity Protections: disabled
```

while the following protections remained enabled:

```text
Filesystem Protections: enabled
Authenticated Root Requirement: enabled
```

The exact resulting SIP flags may vary across macOS versions. Always check the actual state with both commands after changing the security policy:

```bash
csrutil status
csrutil authenticated-root status
```

The Startup Security Utility option named:

```text
Allow user management of kernel extensions from identified developers
```

is Apple's UI wording. RegionOnlySpoof itself is ad-hoc signed (`Signature=adhoc`, `TeamIdentifier=not set`) and does not carry an identified Developer ID KEXT certificate.

See [SECURITY.md](SECURITY.md) before attempting installation.

## Build

See:

[BUILD.md](BUILD.md)

## Install

See:

[INSTALL.md](INSTALL.md)

## Uninstall / restore normal security

See:

[UNINSTALL.md](UNINSTALL.md)

## Version compatibility

Validated:

```text
macOS 26.6.2
Build 25G83
Apple M5 Pro
Mac17,9
```

No guarantee is made for:

- future macOS 26.x releases
- macOS 27 or later
- other Apple Silicon generations
- Intel Macs

Apple may change eligibility logic, Kernel Extension Management, AuxKC behavior, or the meaning of these properties at any time.

## Disclaimer

**This is an unofficial research and experimentation project.**

It is not affiliated with, endorsed by, sponsored by, or supported by Apple Inc.

Kernel extensions execute with kernel privileges. Changing macOS startup-security or System Integrity Protection settings weakens important security protections and may increase the impact of malicious or defective kernel software.

Using this project may result in:

- reduced system security
- kernel panic or system instability
- failure to boot
- incompatibility with future macOS releases
- loss of Apple Intelligence functionality after an update
- data loss
- unexpected behavior from Apple services
- violation of applicable organizational security policies

No representation is made that using this project makes a device eligible for any Apple service under Apple's terms, policies, account requirements, or regional regulations.

Users are solely responsible for:

- understanding the security implications
- complying with applicable laws and service terms
- maintaining backups
- deciding whether reduced security is acceptable
- restoring the original security configuration when appropriate

This software is provided **"AS IS"**, without warranty of any kind.

Apple, macOS, Apple Intelligence, Siri, MacBook Pro and related names and trademarks are property of Apple Inc.

## License

MIT. See [LICENSE](LICENSE).
