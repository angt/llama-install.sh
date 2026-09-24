#include <cstdio>
#include <hip/hip_runtime.h>

#ifdef __linux__
#include <sys/epoll.h>
#endif

#ifdef _WIN32
#include <windows.h>
#endif

int
main(void)
{
#ifdef __linux__
    // Force GLIBC_2.35, waiting for a better solution
    if (getenv("_probe_glibc_floor")) {
        struct epoll_event e{0};
        (void)epoll_pwait2(-1, &e, 0, NULL, NULL);
    }
#endif

    int count = 0;

    if (hipGetDeviceCount(&count) != hipSuccess || !count)
        return 1;

    const char *name = NULL;

    for (int i = 0; !name && i < count; i++) {
        hipDeviceProp_t prop;

        if (hipGetDeviceProperties(&prop, i) == hipSuccess)
            name = prop.gcnArchName;
    }
    if (!name)
        return 2;

#ifdef _WIN32
    if (!LoadLibraryW(L"hipblas.dll"))
        return 5;
#endif

    for (; *name && *name != ':'; name++)
        std::putchar(*name);

    std::putchar('\n');
    return 0;
}
