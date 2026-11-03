# v1.2.0 — Driver-ready eligibility refresh

This solution release bundles **helper 1.2.0** and **KEXT 1.0.2**.

- Observe the driver's published IOService and validated initialization-completion marker. Handle already-published services immediately; remove kmutil polling and the fixed 20-second settle delay.
- At most one eligibilityd SIGTERM/relaunch attempt per boot, with process identity checks, a persisted attempt checkpoint, bounded verification and root-managed install/status/uninstall.
- The KEXT now writes both region-info=LL/A and country-of-origin=USA, plus a diagnostic marker. This changes the old single-property source scope.
- 29 tests passed; KEXT rebuilt and its ad-hoc signature verified.
- One macOS 27.2 observation confirmed eligibility after 15.564 seconds from boot, versus a separate 69.342-second 1.1.0 observation. This is not a timing guarantee or proof of downloaded/usable Siri models.

See README.md, BUILD.md, INSTALL.md, UNINSTALL.md, SECURITY.md and VALIDATION.md. Existing users with the completion-marker KEXT 1.0.2 can upgrade only the helper. Older KEXTs without the marker are incompatible with this helper's trigger.

The downloadable ZIP includes source, documentation, helper tests and an ad-hoc-signed arm64e KEXT under build/. Verify SHA256SUMS, review the source, and prefer building locally. No local logs, machine identifiers, account data or private workspace paths are bundled. No resetInput permission bypass or experimental reset client is included.
