#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SDK_PATH="$(/usr/bin/xcrun --sdk macosx --show-sdk-path)"
KERNEL_HEADERS="$SDK_PATH/System/Library/Frameworks/Kernel.framework/Headers"
OUT="$ROOT/build"
/bin/mkdir -p "$OUT/RegionOnlySpoof.kext/Contents/MacOS"
/usr/bin/xcrun clang++ -arch arm64e -isysroot "$SDK_PATH" -I"$KERNEL_HEADERS" \
  -DKERNEL -DKERNEL_PRIVATE -DDRIVER_PRIVATE -DAPPLE -DNeXT \
  -fno-builtin -fno-common -fapple-kext -mkernel -std=c++17 \
  -fno-rtti -fno-exceptions -fno-stack-protector -O2 \
  -c "$ROOT/src/RegionOnlySpoof.cpp" -o "$OUT/RegionOnlySpoof.o"
/usr/bin/xcrun clang -arch arm64e -isysroot "$SDK_PATH" -I"$KERNEL_HEADERS" \
  -DKERNEL -DKERNEL_PRIVATE -DAPPLE -fno-builtin -fno-common -mkernel -O2 \
  -c "$ROOT/src/kmod_info.c" -o "$OUT/kmod_info.o"
/usr/bin/xcrun clang++ -arch arm64e -isysroot "$SDK_PATH" \
  -mmacosx-version-min=27.0 -nostdlib -fapple-kext -Xlinker -kext \
  -lkmod -lkmodc++ -lcc_kext \
  -o "$OUT/RegionOnlySpoof.kext/Contents/MacOS/RegionOnlySpoof" \
  "$OUT/RegionOnlySpoof.o" "$OUT/kmod_info.o"
/bin/cp "$ROOT/src/Info.plist" "$OUT/RegionOnlySpoof.kext/Contents/Info.plist"
/usr/bin/codesign --force --sign - "$OUT/RegionOnlySpoof.kext"
/usr/bin/codesign --verify --strict "$OUT/RegionOnlySpoof.kext"
/usr/bin/plutil -lint "$OUT/RegionOnlySpoof.kext/Contents/Info.plist"
