include("${CMAKE_CURRENT_LIST_DIR}/init.cmake")

if(NOT DEFINED ROCM_PATH)
    set(ROCM_PATH "$ENV{ROCM_PATH}")
endif()

list(APPEND CMAKE_PREFIX_PATH "${ROCM_PATH}/lib/cmake")

# TheRock ships a multi-arch "rocm" wheel on both Linux and Windows.
# On Linux the ROCm clang is the host compiler; on Windows the build uses
# MSVC as the host compiler and the ROCm clang only compiles HIP device code
# (selected by enable_language(HIP), not set here). Set CMAKE_*_COMPILER only
# on Linux so the Windows path can use MSVC via toolchains/base.cmake.
if(NOT WIN32)
    set(CMAKE_C_COMPILER   "${ROCM_PATH}/lib/llvm/bin/clang")
    set(CMAKE_CXX_COMPILER "${ROCM_PATH}/lib/llvm/bin/clang++")
endif()

include("${CMAKE_CURRENT_LIST_DIR}/exit.cmake")
