#include <IOKit/IOService.h>
#include <libkern/c++/OSData.h>

class com_local_RegionOnlySpoof : public IOService {
    OSDeclareDefaultStructors(com_local_RegionOnlySpoof)

public:
    bool start(IOService *provider) override {
        if (!IOService::start(provider))
            return false;

        unsigned char region[32] = {0};

        region[0] = 'L';
        region[1] = 'L';
        region[2] = '/';
        region[3] = 'A';

        OSData *regionData =
            OSData::withBytes(region, sizeof(region));

        if (!regionData)
            return false;

        bool ok = provider->setProperty(
            "region-info",
            regionData
        );

        regionData->release();

        registerService();

        return ok;
    }

    void stop(IOService *provider) override {
        IOService::stop(provider);
    }
};

OSDefineMetaClassAndStructors(
    com_local_RegionOnlySpoof,
    IOService
)
