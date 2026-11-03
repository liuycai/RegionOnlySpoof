# RegionOnlySpoof v1.2.0

Apple Silicon runtime-region experiment with an optional, once-per-boot eligibility refresh helper.

**Release/helper version: 1.2.0. KEXT version: 1.0.2.** These are separate version numbers. This release changes the earlier region-only experiment: the KEXT now writes both `region-info = LL/A` and `country-of-origin = USA`, and publishes a diagnostic completion marker.

## What changed

On the tested macOS 27.2 system, eligibility input initialization could precede the KEXT region write. The original eligibility process retained a rejected device-region input after the IORegistry properties changed. Rebuilding that process after the driver completed initialization restored qualification.

The helper registers an IOKit `IOServiceFirstPublish` notification for `com_local_RegionOnlySpoof`, drains already-published services, and checks the `RegionOnlySpoofTiming` completion marker. It then performs at most one eligibility-service rebuild per boot:

```text
Driver writes properties and completion marker
  -> registerService()
  -> helper observes published service + complete marker
  -> verify process identity and persist per-boot attempt
  -> one SIGTERM to eligibilityd, if running
  -> demand-start notification, if needed
  -> verify new PID and qualification; exit
```

There is no fixed 20-second delay and no `kmutil` polling. Region strings and existing qualification answers do not gate the rebuild. A missing completion marker times out without sending a signal. No continuous monitor, SIGKILL loop, language change, account change, network change, or direct edit of Apple's qualification files is performed.

## Quick start

Read [SECURITY.md](SECURITY.md), then [BUILD.md](BUILD.md) and [INSTALL.md](INSTALL.md). Existing users already running the completion-marker KEXT 1.0.2 can install only the helper:

```bash
sudo /usr/bin/python3 -I autorefresh/setup.py install
/usr/bin/python3 -I autorefresh/setup.py status
```

The helper is copied to the system volume; boot execution does not depend on this checkout staying mounted. Installation immediately invokes it. If this boot already has an attempt record, the invocation skips safely.

Uninstall the helper with:

```bash
sudo /usr/bin/python3 -I autorefresh/setup.py uninstall
```

See [UNINSTALL.md](UNINSTALL.md) for full KEXT removal and restoration.

## Validation

One macOS 27.2 / build 26B123 Apple Silicon system was tested. The 1.2.0 boot restored device-region qualification and GREYMATTER, FOUNDATION_MODELS and AMERICIUM eligibility. Observed boot-to-confirmation time was **15.564 seconds**, versus **69.342 seconds** in a separate 1.1.0 boot. This is one observation per version, not a statistical performance guarantee.

The successful 1.2.0 boot used the already-published service path. Later-publication callback handling is covered by simulated tests, not a separate live boot observation. Eligibility passing does not establish that model downloads or all Siri features are ready. [Validation details](VALIDATION.md).

## Compatibility and boundaries

- Tested: Apple Silicon, macOS 27.2, KEXT 1.0.2, helper 1.2.0.
- Build target: arm64e, minimum macOS 27.0. No Intel support or general compatibility guarantee.
- Requires the diagnostic completion marker from this KEXT; older region-only builds time out rather than trigger a rebuild.
- Requires the existing ability to load this ad-hoc KEXT. The helper does not configure startup security, SIP, AMFI or authenticated root.
- A protected daemon may reject SIGTERM or its implementation may change on another OS build; the helper records failure and stops.
- `resetInput` is not implemented as a soft-refresh fallback: a single current-build request was rejected for a missing private entitlement; static analysis also excludes the device-region input from that request's allowed set. No permission bypass is included.

Historical region-only behavior is preserved in the previous Git tag. See [CHANGELOG.md](CHANGELOG.md).

## License

MIT; see [LICENSE](LICENSE). This is unofficial experimental software, not affiliated with Apple. Kernel code and reduced startup security carry material risk; see [SECURITY.md](SECURITY.md).
