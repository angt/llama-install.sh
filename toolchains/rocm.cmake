include("${CMAKE_CURRENT_LIST_DIR}/init.cmake")

if(NOT DEFINED ROCM_PATH)
    set(ROCM_PATH "$ENV{ROCM_PATH}")
endif()

list(APPEND CMAKE_PREFIX_PATH "${ROCM_PATH}/lib/cmake")

# TheRock's ROCm clang drives the build on both Linux and Windows.  On
# Windows it targets the MSVC ABI.  llama.cpp's ggml-hip/CMakeLists.txt
# enables the HIP language on Windows (since neither hipcc nor hipcc.bat
# matches its regex) so .cu files are compiled as LANGUAGE HIP.  In that
# mode CMake uses the detected HIP compiler (which falls back to the CXX
# compiler on Windows) and therefore requires --rocm-path in HIP flags as
# well.  Using MSVC (cl.exe) as the host compiler fails because cl.exe
# cannot parse the __attribute__/__bf16 constructs in the HIP headers.
if(WIN32)
    find_program(CMAKE_C_COMPILER clang.exe
        PATHS "${ROCM_PATH}/bin" "${ROCM_PATH}/lib/llvm/bin"
        NO_DEFAULT_PATH REQUIRED)
    find_program(CMAKE_CXX_COMPILER clang++.exe
        PATHS "${ROCM_PATH}/bin" "${ROCM_PATH}/lib/llvm/bin"
        NO_DEFAULT_PATH REQUIRED)
    # TheRock clang is installed in a non-standard (pip) prefix and cannot
    # discover the ROCm device bitcode libraries on its own.
    # On Windows llama.cpp enables HIP as a language, so --rocm-path must
    # be injected into CMAKE_HIP_FLAGS_INIT for .cu kernel compilation.
    # It is intentionally omitted from C/CXX init flags to avoid the
    # "argument unused" warning on plain CPU source files.
    set(CMAKE_HIP_FLAGS_INIT "${CMAKE_HIP_FLAGS_INIT} --rocm-path=\"${ROCM_PATH}\"")
    # TheRock splits device bitcode into separate pip packages on Windows;
    # if the caller found the correct directory, pass it explicitly.
    if(DEFINED ENV{ROCM_DEVICE_LIB_PATH})
        set(CMAKE_HIP_FLAGS_INIT "${CMAKE_HIP_FLAGS_INIT} --rocm-device-lib-path=\"$ENV{ROCM_DEVICE_LIB_PATH}\"")
    endif()
else()
    set(CMAKE_C_COMPILER   "${ROCM_PATH}/lib/llvm/bin/clang")
    set(CMAKE_CXX_COMPILER "${ROCM_PATH}/lib/llvm/bin/clang++")
endif()

include("${CMAKE_CURRENT_LIST_DIR}/exit.cmake")
