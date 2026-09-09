# Installation

## WARNING

Read `SECURITY.md` first.

RegionOnlySpoof is a legacy kernel extension.

Loading an ad-hoc KEXT on Apple Silicon may require weakening macOS startup security and KEXT-signing protections.

Do not continue unless you understand this trade-off.

## 1. Check the original device properties

Before installation:

```bash
ioreg -rd1 -c IOPlatformExpertDevice | \
grep -Ei '"region-info"|"country-of-origin"'
```

A mainland-China unit may report:

```text
"country-of-origin" = <"CHN">
"region-info" = <43482f4100...>
```

`43 48 2f 41` is ASCII:

```text
CH/A
```

## 2. Keep a security baseline

```bash
csrutil status
csrutil authenticated-root status
nvram boot-args
```

Save the output.

## 3. Apple Silicon Startup Security

Shut the Mac down completely.

Press and hold the power / Touch ID button until Startup Options appears.

Enter:

```text
Options
-> Continue
-> Recovery
```

Open:

```text
Utilities
-> Startup Security Utility
```

Select the macOS system volume.

Open:

```text
Security Policy
```

Select:

```text
Reduced Security
```

and enable:

```text
Allow user management of kernel extensions from identified developers
```

Do NOT select Permissive Security.

Do NOT disable authenticated-root protection.

Restart if required.

## 4. Partial SIP configuration

For the validated ad-hoc test configuration, Recovery Terminal used:

```bash
csrutil enable --without kext
```

This creates a custom SIP configuration.

The validated configuration kept important protections including filesystem protections and authenticated root while disabling the KEXT-signing-related protection required by this experiment.

After reboot:

```bash
csrutil status
```

may display:

```text
System Integrity Protection status: unknown (Custom Configuration).
```

and warn that the configuration is unsupported.

This warning is expected for a custom SIP configuration.

Also verify:

```bash
csrutil authenticated-root status
```

Expected:

```text
Authenticated Root status: enabled
```

### Do not disable additional protections

This project does NOT require you to:

```text
disable authenticated root
disable AMFI
use Permissive Security
modify boot-args to defeat code signing
```

If installation fails, diagnose the failure instead of disabling additional protections.

## 5. Copy the KEXT

Assuming the built KEXT is:

```text
build/RegionOnlySpoof.kext
```

install:

```bash
sudo rm -rf \
  /Library/Extensions/RegionOnlySpoof.kext
```

```bash
sudo cp -R \
  build/RegionOnlySpoof.kext \
  /Library/Extensions/
```

Set ownership:

```bash
sudo chown -R root:wheel \
  /Library/Extensions/RegionOnlySpoof.kext
```

Verify:

```bash
ls -ld \
  /Library/Extensions/RegionOnlySpoof.kext
```

## 6. Request loading

```bash
sudo kmutil load \
  -p /Library/Extensions/RegionOnlySpoof.kext
```

macOS may:

- request approval
- state that the extension will become active after restart
- require another reboot

Follow macOS's own approval prompts.

## 7. Restart

After macOS says the extension has been applied, reboot.

## 8. Verify that it loaded

```bash
kmutil showloaded | \
grep -i RegionOnly
```

Example successful result:

```text
com.local.RegionOnlySpoof (1.0.0)
```

## 9. Verify the single-variable spoof

```bash
ioreg -rd1 -c IOPlatformExpertDevice | \
grep -Ei '"region-info"|"country-of-origin"'
```

Expected:

```text
"country-of-origin" = <"CHN">
"region-info" = <4c4c2f410000...>
```

Hex:

```text
4c 4c 2f 41
```

is:

```text
LL/A
```

The important test condition is:

```text
region-info       CH/A -> LL/A
country-of-origin CHN  -> CHN
```

## 10. Inspect eligibility

This project does not modify Apple's eligibility database.

You can inspect it:

```bash
sudo plutil -p \
  /private/var/db/eligibilityd/eligibility.plist
```

Relevant values include:

```text
OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE
OS_ELIGIBILITY_DOMAIN_FOUNDATION_MODELS
OS_ELIGIBILITY_DOMAIN_GREYMATTER
OS_ELIGIBILITY_DOMAIN_PERSONAL_QA
OS_ELIGIBILITY_DOMAIN_SIRI_WITH_APP_INTENTS
```

See `VALIDATION.md`.

## Language configuration

Apple Intelligence may independently require the device language and Siri language to be supported and compatible.

On the validated system:

```text
Device language: English
Siri language:   en-US
```

resulted in:

```text
DEVICE_AND_SIRI_LANGUAGE_MATCH = 3
GREYMATTER = 4
```

Language configuration is performed through normal macOS settings.

This project does not patch Siri.

## No automatic eligibility patching

RegionOnlySpoof intentionally does NOT:

- edit `eligibility.plist`
- restart system daemons automatically
- alter `countryd`
- spoof GeoServices
- install a LaunchDaemon

This is intentional.
