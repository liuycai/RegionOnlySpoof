# Building RegionOnlySpoof

## Validated toolchain

The original experimental build was produced on Apple Silicon using:

```text
Apple clang 21.x
macOS 26.x
Command Line Tools
arm64e
```

The SDK used during validation was compatible with macOS 26.5.

## Requirements

Install Apple's Command Line Tools:

```bash
xcode-select --install
```

Verify:

```bash
xcode-select -p
```

Example:

```text
/Library/Developer/CommandLineTools
```

Verify clang:

```bash
clang --version
```

## Clone

```bash
git clone https://github.com/liuycai/RegionOnlySpoof.git
cd RegionOnlySpoof
```

## SDK variables

```bash
SDK="$(xcrun --sdk macosx --show-sdk-path)"
KH="$SDK/System/Library/Frameworks/Kernel.framework/Headers"
```

Verify:

```bash
echo "$SDK"
echo "$KH"
```

## Compile the IOKit class

```bash
xcrun clang++ \
  -arch arm64e \
  -isysroot "$SDK" \
  -I"$KH" \
  -DKERNEL \
  -DKERNEL_PRIVATE \
  -DDRIVER_PRIVATE \
  -DAPPLE \
  -DNeXT \
  -fno-builtin \
  -fno-common \
  -fapple-kext \
  -mkernel \
  -std=c++17 \
  -fno-rtti \
  -fno-exceptions \
  -fno-stack-protector \
  -O2 \
  -c src/RegionOnlySpoof.cpp \
  -o /tmp/RegionOnlySpoof.o
```

## Compile the kmod declaration

```bash
xcrun clang \
  -arch arm64e \
  -isysroot "$SDK" \
  -I"$KH" \
  -DKERNEL \
  -DKERNEL_PRIVATE \
  -DAPPLE \
  -fno-builtin \
  -fno-common \
  -mkernel \
  -O2 \
  -c src/kmod_info.c \
  -o /tmp/kmod_info.o
```

Verify:

```bash
file /tmp/RegionOnlySpoof.o
file /tmp/kmod_info.o
```

Expected architecture:

```text
arm64e
```

## Link

The kmod libraries are important.

```bash
xcrun clang++ \
  -arch arm64e \
  -isysroot "$SDK" \
  -mmacosx-version-min=26.5 \
  -nostdlib \
  -fapple-kext \
  -Xlinker -kext \
  -lkmod \
  -lkmodc++ \
  -lcc_kext \
  -o /tmp/RegionOnlySpoof \
  /tmp/RegionOnlySpoof.o \
  /tmp/kmod_info.o
```

Verify:

```bash
file /tmp/RegionOnlySpoof
```

Expected:

```text
Mach-O 64-bit kext bundle arm64e
```

Check that unresolved `__start` / `__stop` symbols are absent:

```bash
nm -u /tmp/RegionOnlySpoof | grep -E '__start|__stop'
```

Expected:

```text
(no output)
```

## Assemble the KEXT bundle

```bash
rm -rf build/RegionOnlySpoof.kext

mkdir -p \
  build/RegionOnlySpoof.kext/Contents/MacOS

cp src/Info.plist \
  build/RegionOnlySpoof.kext/Contents/Info.plist

cp /tmp/RegionOnlySpoof \
  build/RegionOnlySpoof.kext/Contents/MacOS/RegionOnlySpoof
```

## Ad-hoc signing

```bash
codesign \
  --force \
  --sign - \
  build/RegionOnlySpoof.kext
```

Inspect:

```bash
codesign -dv --verbose=4 \
  build/RegionOnlySpoof.kext
```

An ad-hoc build normally reports:

```text
Signature=adhoc
TeamIdentifier=not set
```

## Source-scope audit

The implementation should contain only one relevant property mutation:

```bash
grep -R -n 'setProperty' src
```

Expected:

```text
provider->setProperty("region-info", regionData)
```

Check that broad spoof mechanisms were not accidentally introduced:

```bash
grep -R -n -E \
'country-of-origin|eligibility|countryd|GeoServices|Siri|AppleInternal|FeatureFlags|hosts|proxy|DNS' \
src
```

Expected:

```text
(no output)
```

## Important

A successful build does NOT mean it can be loaded under Apple's default security policy.

Read:

- `SECURITY.md`
- `INSTALL.md`

before changing any security setting.
