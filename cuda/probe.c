#include <stdio.h>
#include <cuda.h>

#ifndef PROBE_ARCH
#error "Please define PROBE_ARCH"
#endif

#ifdef __linux__
#include <sys/epoll.h>
#endif

int
main(void)
{
#ifdef __linux__
    // Force GLIBC_2.35, waiting for a better solution
    if (getenv("_probe_glibc_floor"))
        (void)epoll_pwait2(-1, &(struct epoll_event){0}, 0, NULL, NULL);
#endif

    int arch[] = { PROBE_ARCH };
    int n_arch = sizeof(arch) / sizeof(arch[0]);

    int driver = 0;

    if (cuDriverGetVersion(&driver) != CUDA_SUCCESS)
        return 1;

    if (cuInit(0) != CUDA_SUCCESS)
        return 2;

    int count = 0;

    if (cuDeviceGetCount(&count) != CUDA_SUCCESS || !count)
        return 3;

    int best_arch = 0;
    int last_arch = arch[n_arch - 1];

    for (int i = 0; i < count; i++) {
        CUdevice device;

        if (cuDeviceGet(&device, i) != CUDA_SUCCESS)
            continue;

        int major = 0, minor = 0;

        cuDeviceGetAttribute(&major, CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR, device);
        cuDeviceGetAttribute(&minor, CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR, device);

        int device_arch = major * 10 + minor;

        for (int j = 0; j < n_arch; j++) {
            int a = arch[j];
            if (a <= device_arch && a > best_arch &&
                (a / 10 == device_arch / 10 || a == last_arch)) // keep major
                best_arch = a;
        }
    }
    if (!best_arch)
        return 4;

    printf("%d\n", best_arch);
    return 0;
}
