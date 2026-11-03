# Build and test

Use Apple Silicon with Apple's Command Line Tools and a compatible macOS SDK containing Kernel.framework headers. The validated build used Apple clang 21 and an arm64e target.

```bash
xcode-select -p
bash build.sh
```

Output: `build/RegionOnlySpoof.kext`, version 1.0.2, minimum macOS 27.0. The script compiles the checked-in sources and ad-hoc signs and verifies the bundle. It does not install, load or reboot anything. Build outputs are ignored by Git.

```bash
codesign --verify --strict build/RegionOnlySpoof.kext
plutil -lint build/RegionOnlySpoof.kext/Contents/Info.plist
file build/RegionOnlySpoof.kext/Contents/MacOS/RegionOnlySpoof
```

Inspect all `setProperty` calls: the current KEXT writes `region-info`, `country-of-origin` and `RegionOnlySpoofTiming`. It also captures the original region/origin values in the volatile diagnostic dictionary. This is intentionally broader than the historical single-property release.

The helper uses only Python's standard library and the system IOKit/CoreFoundation frameworks; it does not require pip packages. Run tests without sudo:

```bash
/usr/bin/python3 -I autorefresh/test_helper.py
/usr/bin/python3 -I autorefresh/test_readiness.py
/usr/bin/python3 -I autorefresh/test_setup.py
```

There are 29 tests: 16 refresh-flow, 7 readiness/notification, 6 installer tests. Tests use fake daemon operations and temporary files and do not signal system processes or install a job. `autorefresh/previous/` contains exact earlier helper sources needed by upgrade regression tests; they are not installed.

Read-only readiness check on a Mac with KEXT 1.0.2 running:

```bash
/usr/bin/python3 -I autorefresh/helper.py --wait-ready 2
```

A compiled bundle is not evidence that the KEXT will load under default macOS security settings.
