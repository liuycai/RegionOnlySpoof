# Uninstallation and restoring macOS security

## 1. Remove RegionOnlySpoof

```bash
sudo rm -rf \
  /Library/Extensions/RegionOnlySpoof.kext
```

Restart the Mac.

The runtime property modification is not persistent firmware modification.

Without the KEXT, a reboot should restore the hardware-provided region information.

Verify:

```bash
ioreg -rd1 -c IOPlatformExpertDevice | \
grep -Ei '"region-info"|"country-of-origin"'
```

For the original validated mainland-China system this was:

```text
country-of-origin = CHN
region-info       = CH/A
```

## Note about unloading

The current KEXT does not restore the previous `region-info` value from `stop()`.

Therefore, unloading it during the same boot session should not be considered equivalent to restoration.

The clean restoration boundary is a reboot without RegionOnlySpoof loading.

## Auxiliary Kernel Collection

Once macOS has accepted a third-party KEXT, it may participate in the Auxiliary Kernel Collection / Kernel Extension Management process.

Deleting the bundle from `/Library/Extensions` may therefore require a reboot before the effective kernel environment is refreshed.

Follow any macOS restart prompts.

## 2. Restore full SIP

Boot into macOS Recovery.

Open Terminal and run:

```bash
csrutil enable
```

Restart.

Verify:

```bash
csrutil status
```

Expected:

```text
System Integrity Protection status: enabled.
```

Also verify:

```bash
csrutil authenticated-root status
```

Expected:

```text
Authenticated Root status: enabled
```

## 3. Restore normal startup security

Boot back into Recovery:

```text
Startup Options
-> Options
-> Startup Security Utility
```

Select the system volume.

Restore the normal/default security policy appropriate for your Mac.

If you do not use any other third-party KEXTs, there is generally no reason to retain Reduced Security solely for RegionOnlySpoof after uninstalling it.

## 4. Verify no KEXT is loaded

After boot:

```bash
kmutil showloaded | \
grep -i RegionOnly
```

Expected:

```text
(no output)
```

## 5. Verify the file is gone

```bash
ls \
  /Library/Extensions/RegionOnlySpoof.kext
```

Expected:

```text
No such file or directory
```

## Important

Restoring Apple's normal security configuration is strongly recommended when this experiment is no longer required.
