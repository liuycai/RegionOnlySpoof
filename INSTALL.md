# Installation

Read [SECURITY.md](SECURITY.md). This release does not change startup-security settings. Loading an ad-hoc KEXT on Apple Silicon requires a separately configured and approved environment. Do not disable additional protections to work around an unexplained error.

## KEXT 1.0.2

Build with `bash build.sh`, or inspect the release bundle against the source and SHA256SUMS. Existing users already running KEXT 1.0.2 with the completion marker can skip this section.

Keep a backup before replacing an existing KEXT. The following guarded block stages the new bundle, preserves an existing bundle at a fixed backup path, and requests macOS loading/approval. It stops if a previous staging or backup path exists. Run from this repository root:

```bash
sudo /bin/bash <<'SH'
set -euo pipefail
source_bundle="$PWD/build/RegionOnlySpoof.kext"
backup=/Library/Extensions/.RegionOnlySpoof-before-v1.2.0.rollback
staged=/Library/Extensions/.RegionOnlySpoof-v1.2.0.stage
test -d "$source_bundle"
test ! -e "$backup"
test ! -e "$staged"
/usr/bin/codesign --verify --strict "$source_bundle"
/usr/bin/ditto "$source_bundle" "$staged"
/usr/sbin/chown -R root:wheel "$staged"
if test -e /Library/Extensions/RegionOnlySpoof.kext; then
  /bin/mv /Library/Extensions/RegionOnlySpoof.kext "$backup"
fi
/bin/mv "$staged" /Library/Extensions/RegionOnlySpoof.kext
/usr/bin/kmutil load -p /Library/Extensions/RegionOnlySpoof.kext
SH
```

A load request can return an approval/restart-required result even after the files have been installed. Follow macOS's approval and restart prompts. Do not keep rerunning the block: it deliberately refuses an existing backup. If approval fails, retain the backup and follow the KEXT rollback steps in [UNINSTALL.md](UNINSTALL.md).

After the required restart:

```bash
kmutil showloaded --list-only --bundle-identifier com.local.RegionOnlySpoof
/usr/bin/python3 -I autorefresh/helper.py --wait-ready 2
```

Expected KEXT version is 1.0.2; readiness should report a complete marker and a published service. The original country-of-origin is now changed to USA along with LL/A; this is not the old single-variable experiment.

## Helper 1.2.0

```bash
sudo /usr/bin/python3 -I autorefresh/setup.py install
/usr/bin/python3 -I autorefresh/setup.py status
```

The helper uses `/usr/bin/python3 -I`, so the system Command Line Tools Python3 must remain available. The installer verifies package hashes and refuses unknown existing destination files. Exact 1.0.0, 1.0.1 and 1.1.0 helper hashes are accepted for upgrade.

Installed paths:

- `/Library/LaunchDaemons/com.local.regiononlyspoof.refresh.plist`: root:wheel, 0644.
- `/Library/PrivilegedHelperTools/com.local.regiononlyspoof.refresh.py`: root:wheel, 0755.
- `/Library/Application Support/RegionOnlySpoofRefresh/state.json`: per-boot result.
- `/Library/Logs/RegionOnlySpoofRefresh.log`: output.

The job uses RunAtLoad=true, KeepAlive=false, no periodic timer. It checks the boot UUID and persists an attempt before signaling. It never sends more than one SIGTERM per boot, even after an upgrade or repeated invocation. Missing readiness, a changing service instance or an unverified PID prevents signaling. The notification only requests demand-start; it does not alter language settings.

`not running` with exit code 0 is the expected final state for this one-shot job. `installedHelperVersion` is the installed file version; `lastRun.helperVersion` can refer to an earlier successful invocation when the current boot was skipped.

Read-only diagnostics:

```bash
/usr/bin/python3 -I autorefresh/helper.py --check
/usr/bin/python3 -I autorefresh/helper.py --wait-ready 2
```

Do not publish raw local diagnostics without reviewing them. Qualification passing and downloaded/usable models are separate states.
