include("${CMAKE_CURRENT_LIST_DIR}/init.cmake")

if(NOT DEFINED ROCM_PATH)
    set(ROCM_PATH "$ENV{ROCM_PATH}")
endif()

list(APPEND CMAKE_PREFIX_PATH "${ROCM_PATH}/lib/cmake")

# TheRock's ROCm clang drives the build on both Linux and Windows.
# On Linux ROCm clang is also the host compiler.
# On Windows it targets the MSVC ABI.
if(WIN32)
    # llama.cpp's ggml-hip/CMakeLists.txt forces CXX_IS_HIPCC TRUE on Windows,
    # so .cu files are compiled as LANGUAGE CXX (HIP language is not supported
    # by CMake yet).  Clang must therefore be found explicitly here because
    # CMake would otherwise use MSVC (cl.exe), which cannot parse the
    # __attribute__/__bf16 constructs in the HIP headers.
    find_program(CMAKE_C_COMPILER clang.exe
        PATHS "${ROCM_PATH}/bin" "${ROCM_PATH}/lib/llvm/bin"
        NO_DEFAULT_PATH REQUIRED)
    find_program(CMAKE_CXX_COMPILER clang++.exe
        PATHS "${ROCM_PATH}/bin" "${ROCM_PATH}/lib/llvm/bin"
        NO_DEFAULT_PATH REQUIRED)

    # TheRock's pip-installed ROCm sits in a non-standard prefix; clang++
    # needs --rocm-path and --rocm-device-lib-path to locate the embedded
    # device headers and bitcode libraries.  Unfortunately ggml-hip forces
    # .cu sources to LANGUAGE CXX, so they are compiled with CXX flags
    # rather than HIP flags; the only way to pass these options is through
    # the global CMAKE_CXX_FLAGS_INIT.  Non-HIP C++ files will warn about
    # unused arguments; we silence those with -Wno-unused-command-line-argument.
    set(_HIP_CLANG_FLAGS " -Wno-unused-command-line-argument")
    if(ROCM_PATH)
        string(APPEND _HIP_CLANG_FLAGS " --rocm-path=\"${ROCM_PATH}\"")
    endif()
    if(NOT "$ENV{ROCM_DEVICE_LIB_PATH}" STREQUAL "")
        string(APPEND _HIP_CLANG_FLAGS " --rocm-device-lib-path=\"$ENV{ROCM_DEVICE_LIB_PATH}\"")
    endif()
    string(STRIP "${_HIP_CLANG_FLAGS}" _HIP_CLANG_FLAGS)
    set(CMAKE_CXX_FLAGS_INIT "${CMAKE_CXX_FLAGS_INIT}${_HIP_CLANG_FLAGS}")
else()
    set(CMAKE_C_COMPILER   "${ROCM_PATH}/lib/llvm/bin/clang")
    set(CMAKE_CXX_COMPILER "${ROCM_PATH}/lib/llvm/bin/clang++")
endif()

include("${CMAKE_CURRENT_LIST_DIR}/exit.cmake")
