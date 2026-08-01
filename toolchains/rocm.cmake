include("${CMAKE_CURRENT_LIST_DIR}/init.cmake")

if(NOT DEFINED ROCM_PATH)
    set(ROCM_PATH "$ENV{ROCM_PATH}")
endif()

list(APPEND CMAKE_PREFIX_PATH "${ROCM_PATH}/lib/cmake")

# TheRock's ROCm clang drives the build on both Linux and Windows.  On
# Windows it targets the MSVC ABI and, as the CXX compiler, also compiles
# the HIP .cu kernels (llama.cpp's ggml-hip/CMakeLists.txt sets LANGUAGE CXX
# there because CMake has no first-class HIP language on Windows yet).
# Using MSVC (cl.exe) as the host compiler instead fails because cl.exe cannot
# parse the __attribute__/__bf16 constructs in the HIP headers.
if(WIN32)
    find_program(CMAKE_C_COMPILER clang.exe
        PATHS "${ROCM_PATH}/bin" "${ROCM_PATH}/lib/llvm/bin"
        NO_DEFAULT_PATH REQUIRED)
    find_program(CMAKE_CXX_COMPILER clang++.exe
        PATHS "${ROCM_PATH}/bin" "${ROCM_PATH}/lib/llvm/bin"
        NO_DEFAULT_PATH REQUIRED)
else()
    set(CMAKE_C_COMPILER   "${ROCM_PATH}/lib/llvm/bin/clang")
    set(CMAKE_CXX_COMPILER "${ROCM_PATH}/lib/llvm/bin/clang++")
endif()

include("${CMAKE_CURRENT_LIST_DIR}/exit.cmake")
