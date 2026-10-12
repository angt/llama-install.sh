#ifdef __linux__
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <spawn.h>
#include <unistd.h>
#endif

#ifdef _WIN32
#include <windows.h>
#endif

#include <stdlib.h>
#include <vulkan/vulkan.h>

struct probe {
    VkInstance instance;
    uint32_t count;
    VkPhysicalDevice *devices;
};

static int
probe_setup(struct probe *p)
{
    PFN_vkEnumerateInstanceVersion get_version =
        (PFN_vkEnumerateInstanceVersion)vkGetInstanceProcAddr(VK_NULL_HANDLE, "vkEnumerateInstanceVersion");

    uint32_t version = 0;

    if (!get_version || get_version(&version) != VK_SUCCESS || version < VK_API_VERSION_1_2)
        return 1;

    VkApplicationInfo appInfo = {
        .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
        .apiVersion = VK_API_VERSION_1_2,
    };
    VkInstanceCreateInfo createInfo = {
        .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        .pApplicationInfo = &appInfo,
    };
    if (vkCreateInstance(&createInfo, NULL, &p->instance) != VK_SUCCESS)
        return 1;

    if (vkEnumeratePhysicalDevices(p->instance, &p->count, NULL) != VK_SUCCESS || !p->count)
        return 2;

    p->devices = calloc(p->count, sizeof(VkPhysicalDevice));

    if (!p->devices)
        return 3;

    if (vkEnumeratePhysicalDevices(p->instance, &p->count, p->devices) != VK_SUCCESS)
        return 4;

    return 0;
}

static void
probe_cleanup(struct probe *p)
{
    free(p->devices);

    if (p->instance)
        vkDestroyInstance(p->instance, NULL);
}

static int
device_is_usable(VkPhysicalDevice physical_device)
{
    VkPhysicalDeviceProperties props;
    vkGetPhysicalDeviceProperties(physical_device, &props);

    if (props.deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU)
        return 0;

    if (props.apiVersion < VK_MAKE_API_VERSION(0, 1, 2, 0))
        return 0;

    uint32_t queue_count = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical_device, &queue_count, NULL);

    if (!queue_count)
        return 0;

    VkQueueFamilyProperties *queues = calloc(queue_count, sizeof(VkQueueFamilyProperties));

    if (!queues)
        return 0;

    vkGetPhysicalDeviceQueueFamilyProperties(physical_device, &queue_count, queues);

    uint32_t queue_family = 0;
    int has_compute = 0;

    for (uint32_t i = 0; i < queue_count; i++) {
        if (queues[i].queueCount && (queues[i].queueFlags & VK_QUEUE_COMPUTE_BIT)) {
            queue_family = i;
            has_compute = 1;
            break;
        }
    }
    free(queues);

    if (!has_compute)
        return 0;

    const float priority = 1.0f;

    VkDeviceQueueCreateInfo queueInfo = {
        .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        .queueFamilyIndex = queue_family,
        .queueCount = 1,
        .pQueuePriorities = &priority,
    };
    VkPhysicalDevice16BitStorageFeatures storage16 = {
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_16BIT_STORAGE_FEATURES,
        .storageBuffer16BitAccess = VK_TRUE,
    };
    const char *extensions[] = { VK_KHR_16BIT_STORAGE_EXTENSION_NAME };

    VkDeviceCreateInfo deviceInfo = {
        .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
        .pNext = &storage16,
        .queueCreateInfoCount = 1,
        .pQueueCreateInfos = &queueInfo,
        .enabledExtensionCount = 1,
        .ppEnabledExtensionNames = extensions,
    };
    VkDevice device;

    if (vkCreateDevice(physical_device, &deviceInfo, NULL, &device) != VK_SUCCESS)
        return 0;

    vkDestroyDevice(device, NULL);
    return 1;
}

int
main(void)
{
#ifdef __linux__
    // Force GLIBC_2.29, waiting for a better solution
    if (getenv("_probe_glibc_floor")) {
        posix_spawn_file_actions_t a;
        if (posix_spawn_file_actions_init(&a) == 0) {
            (void)posix_spawn_file_actions_addchdir_np(&a, "");
            posix_spawn_file_actions_destroy(&a);
        }
    }
#endif

#ifdef _WIN32
    // Force Windows 8, waiting for a better solution
    if (getenv("_probe_win32_floor"))
        (void)CreateFile2(L"", 0, 0, 0, NULL);
#endif

    struct probe p = { 0 };
    int ret = probe_setup(&p);

    if (!ret) {
        int capable = 0;

        for (uint32_t i = 0; !capable && i < p.count; i++)
            capable = device_is_usable(p.devices[i]);

        ret = capable ? 0 : 5;
    }
    probe_cleanup(&p);
    return ret;
}
