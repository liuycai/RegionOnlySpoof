# Validation Record

## Purpose

This validation was designed as a single-variable A/B test.

The hypothesis:

> Is `region-info = CH/A` itself sufficient to produce the mainland-China device-region eligibility result?

Only `region-info` was changed.

## Test platform

```text
Date:             2026-09-09
Machine:          MacBook Pro
Model Identifier: Mac17,9
SoC:              Apple M5 Pro
CPU cores:        15
Memory:           24 GB
Model Number:     MGDN4CH/A
macOS:            26.6.2
Build:            25G83
```

## Before

IORegistry:

```text
country-of-origin = CHN
region-info       = CH/A
```

Relevant eligibility result:

```text
DEVICE_REGION_CODE = 2
```

Observed domains included:

```text
FOUNDATION_MODELS        = 2
GREYMATTER               = 2
PERSONAL_QA              = 2
SIRI_WITH_APP_INTENTS    = 2
```

## Experimental modification

RegionOnlySpoof wrote only:

```text
IOPlatformExpertDevice.region-info = LL/A
```

It did not modify:

```text
country-of-origin
```

## After reboot

KEXT:

```text
com.local.RegionOnlySpoof (1.0.0)
```

IORegistry:

```text
country-of-origin = CHN
region-info       = LL/A
```

This confirms the experiment retained:

```text
country-of-origin = CHN
```

while changing only:

```text
CH/A -> LL/A
```

## Eligibility after region spoof

Observed:

```text
DEVICE_REGION_CODE = 3
```

Domains:

```text
FOUNDATION_MODELS     = 4
PERSONAL_QA           = 4
SIRI_WITH_APP_INTENTS = 4
```

This provides evidence that on this machine and build, changing only `region-info` was sufficient to alter `DEVICE_REGION_CODE`.

## GREYMATTER language requirement

Before language alignment:

```text
Eligible device language: zh-Hans
Eligible Siri language:   en-US

DEVICE_AND_SIRI_LANGUAGE_MATCH = 2
GREYMATTER                     = 2
```

The system language was changed using normal macOS settings to English while Siri remained `en-US`.

After alignment:

```text
Eligible device languages = ["en"]
Eligible Siri language     = en-US

DEVICE_AND_SIRI_LANGUAGE_MATCH = 3
DEVICE_LANGUAGE                 = 3
SIRI_LANGUAGE                   = 3
DEVICE_REGION_CODE              = 3
GENERATIVE_MODEL_SYSTEM         = 3
```

Result:

```text
GREYMATTER = 4
```

## Other domains

After the complete test:

```text
FOUNDATION_MODELS     = 4
GREYMATTER            = 4
PERSONAL_QA           = 4
SIRI_WITH_APP_INTENTS = 4
```

## COUNTRY_LOCATION observation

During successful eligibility:

```text
COUNTRY_LOCATION = 2
```

remained present.

Nevertheless the domains above returned `4`.

Therefore, on this specific configuration:

```text
COUNTRY_LOCATION = 2
```

was not a hard blocker for those tested domains.

This result must not be generalized to other macOS releases.

## Runtime service validation

Both processes were active:

```text
generativeexperiencesd
modelcatalogd
```

The GenerativeExperiences availability reporter logged an effective state equivalent to:

```text
appleIntelligenceUseCase.isDeviceEligible = true

appleIntelligenceDiffusionUseCase.isDeviceEligible = true

isAppleIntelligenceToggleEnabled = true

languages = ["en"]
```

## Cloud feature access

The system reported access to:

```text
cloud.llm
ai.paperkit.image-generation
ai.keyboard.emoji-generation
ai.apps.image-playground
```

Image Playground specifically reported a usable feature state.

## Network-country observation

During this validation, `countryd` reported:

```text
JP
```

from GeoIP.

The ChatGPT partner availability path reported:

```text
isDisabled = false
```

This project did not modify GeoIP or `countryd`.

## Model asset state

At one stage immediately after eligibility became active, `modelcatalogd` reported that no underlying model-catalog assets had yet been installed.

This was interpreted as a model delivery / initialization state rather than an eligibility failure because the runtime simultaneously reported:

```text
isDeviceEligible = true
isAppleIntelligenceToggleEnabled = true
```

## Conclusion

Validated on:

```text
Mac17,9
Apple M5 Pro
MGDN4CH/A
macOS 26.6.2
25G83
```

the following single runtime change:

```text
region-info:
CH/A -> LL/A
```

while leaving:

```text
country-of-origin = CHN
```

was sufficient to produce:

```text
DEVICE_REGION_CODE:
2 -> 3
```

and corresponding eligibility-domain changes.

This is an empirical result for one machine and one OS build.

It is not a guarantee for any other system.
