#include <IOKit/IOService.h>
#include <IOKit/IOLib.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSDictionary.h>
#include <libkern/c++/OSNumber.h>
#include <kern/clock.h>
#include <mach/mach_time.h>

// Diagnostic instrumentation of the installed 1.0.1 behavior. No timers,
// sleeps, service signals, policy overrides, or additional spoofed fields.
class com_local_RegionOnlySpoof : public IOService {
    OSDeclareDefaultStructors(com_local_RegionOnlySpoof)

    static void number(OSDictionary *dict, const char *key, uint64_t value) {
        OSNumber *n = OSNumber::withNumber(value, 64);
        if (n) { dict->setObject(key, n); n->release(); }
    }

public:
    bool start(IOService *provider) override {
        const uint64_t entered = mach_absolute_time();
        if (!IOService::start(provider)) return false;

        OSObject *oldRegion = provider->getProperty("region-info");
        OSObject *oldOrigin = provider->getProperty("country-of-origin");
        if (oldRegion) oldRegion->retain();
        if (oldOrigin) oldOrigin->retain();

        unsigned char region[32] = {0};
        region[0]='L'; region[1]='L'; region[2]='/'; region[3]='A';
        OSData *regionData = OSData::withBytes(region, sizeof(region));
        if (!regionData) {
            if (oldRegion) oldRegion->release();
            if (oldOrigin) oldOrigin->release();
            return false;
        }
        const uint64_t regionBefore = mach_absolute_time();
        bool regionOK = provider->setProperty("region-info", regionData);
        const uint64_t regionAfter = mach_absolute_time();
        regionData->release();

        OSData *originData = OSData::withBytes("USA", 3);
        if (!originData) {
            if (oldRegion) oldRegion->release();
            if (oldOrigin) oldOrigin->release();
            IOLog("ROS_TIMING_V1: origin allocation failed\n");
            return false;
        }
        const uint64_t originBefore = mach_absolute_time();
        bool originOK = provider->setProperty("country-of-origin", originData);
        const uint64_t originAfter = mach_absolute_time();
        originData->release();

        // Emit logs only AFTER the property writes to minimize disturbance.
        // Persist timestamps in IORegistry as early kernel logs may be absent.
        clock_sec_t secs = 0;
        clock_usec_t usecs = 0;
        clock_get_calendar_microtime(&secs, &usecs);
        const uint64_t sampled = mach_absolute_time();
        OSDictionary *diag = OSDictionary::withCapacity(12);
        if (diag) {
            number(diag, "schema", 1);
            number(diag, "startTicks", entered);
            number(diag, "regionBeforeTicks", regionBefore);
            number(diag, "regionAfterTicks", regionAfter);
            number(diag, "originBeforeTicks", originBefore);
            number(diag, "originAfterTicks", originAfter);
            number(diag, "sampleTicks", sampled);
            number(diag, "sampleUnixSeconds", secs);
            number(diag, "sampleMicroseconds", usecs);
            number(diag, "regionWriteOK", regionOK);
            number(diag, "originWriteOK", originOK);
            if (oldRegion) diag->setObject("originalRegion", oldRegion);
            if (oldOrigin) diag->setObject("originalOrigin", oldOrigin);
            provider->setProperty("RegionOnlySpoofTiming", diag);
            diag->release();
        }
        if (oldRegion) oldRegion->release();
        if (oldOrigin) oldOrigin->release();
        IOLog("ROS_TIMING_V1: v1.0.2 entered=%llu region_before=%llu region_after=%llu origin_after=%llu sample=%llu epoch=%llu.%06u ok=%u,%u\n",
              (unsigned long long)entered,
              (unsigned long long)regionBefore,
              (unsigned long long)regionAfter,
              (unsigned long long)originAfter,
              (unsigned long long)sampled,
              (unsigned long long)secs, usecs,
              (unsigned)regionOK, (unsigned)originOK);
        registerService();
        return regionOK && originOK;
    }

    void stop(IOService *provider) override { IOService::stop(provider); }
};

OSDefineMetaClassAndStructors(com_local_RegionOnlySpoof, IOService)
