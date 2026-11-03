# Uninstall or roll back

## Remove the helper first

From this repository or the unpacked release directory:

```bash
sudo /usr/bin/python3 -I autorefresh/setup.py uninstall
```

This unloads only this project's LaunchDaemon and removes its installed helper/plist. It retains logs, boot state and the KEXT. Retaining boot state prevents an install/uninstall cycle from sending another signal in the same boot.

There is no helper setting to revert in Apple's eligibility databases; none were directly edited. Uninstalling the helper does not immediately reverse eligibility in an already-running service.

## Restore a backed-up KEXT

If the installer block created `/Library/Extensions/.RegionOnlySpoof-before-v1.2.0.rollback`, preserve the current bundle and restore that backup:

```bash
sudo /bin/bash <<'SH'
set -euo pipefail
backup=/Library/Extensions/.RegionOnlySpoof-before-v1.2.0.rollback
removed=/Library/Extensions/.RegionOnlySpoof-v1.2.0.removed
test -d "$backup"
test ! -e "$removed"
if test -e /Library/Extensions/RegionOnlySpoof.kext; then
  /bin/mv /Library/Extensions/RegionOnlySpoof.kext "$removed"
fi
/bin/mv "$backup" /Library/Extensions/RegionOnlySpoof.kext
/usr/sbin/chown -R root:wheel /Library/Extensions/RegionOnlySpoof.kext
/usr/bin/kmutil load -p /Library/Extensions/RegionOnlySpoof.kext
SH
```

Follow macOS approval/restart prompts. An older KEXT without the completion marker is incompatible with the 1.2.0 helper; uninstall the helper first.

## Full removal

After removing the helper, move the KEXT out of `/Library/Extensions`, keeping a copy if desired, and restart. macOS may require rebuilding/refreshing its auxiliary collection through its normal KEXT management flow. Follow system prompts and verify `kmutil showloaded` no longer lists the extension.

The KEXT's stop method does not restore modified properties. Unloading during the same boot is not a substitute for rebooting without it loaded. This project does not modify firmware; a clean boot without the extension restores the hardware-provided runtime properties.

## Restore security settings

When the KEXT is no longer needed, use macOS Recovery to restore your previous/full SIP and normal Startup Security policy as appropriate for other installed software. Verify `csrutil status` and `csrutil authenticated-root status` after restart. This release does not change or automatically restore these settings.
