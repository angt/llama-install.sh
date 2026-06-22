list(LENGTH CMAKE_CUDA_ARCHITECTURES _arch_count)

if(_arch_count EQUAL 0)
    return()
endif()

include("${CMAKE_ROOT}/Modules/FindCUDAToolkit.cmake")

if(NOT CUDAToolkit_FOUND)
    return()
endif()

if(NOT _arch_count EQUAL 1)
    return()
endif()

find_program(_CUDA_NVPRUNE nvprune HINTS ${CUDAToolkit_BIN_DIR})

if(NOT _CUDA_NVPRUNE)
    message(WARNING "nvprune not found; skipping CUDA static-lib pruning")
    return()
endif()

list(GET CMAKE_CUDA_ARCHITECTURES 0 _arch)
string(REGEX REPLACE "-.*" "" _arch "${_arch}")

set(_pruned_dir "${CMAKE_CURRENT_BINARY_DIR}/pruned_libs")
file(MAKE_DIRECTORY ${_pruned_dir})

foreach(_lib cublas cublasLt)
    get_target_property(_loc CUDA::${_lib}_static IMPORTED_LOCATION)
    if(NOT _loc OR _loc MATCHES "/pruned_libs/")
        continue() # already pruned (re-entrant find_package call)
    endif()

    set(_prune_arch ${_arch})
    if(_lib STREQUAL "cublas" AND _arch EQUAL 89)
        set(_prune_arch 86)
    endif()

    set(_dst "${_pruned_dir}/lib${_lib}_sm${_arch}.a")
    message(STATUS "Pruning ${_lib} for sm_${_prune_arch}...")
    execute_process(
        COMMAND ${_CUDA_NVPRUNE} -arch sm_${_prune_arch} -o "${_dst}" "${_loc}"
        OUTPUT_QUIET
        RESULT_VARIABLE _rc
    )
    if(_rc)
        message(FATAL_ERROR "nvprune failed (rc=${_rc}) pruning ${_lib}")
    endif()
    set_target_properties(CUDA::${_lib}_static PROPERTIES IMPORTED_LOCATION "${_dst}")
endforeach()
