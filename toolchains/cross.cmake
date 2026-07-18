include("${CMAKE_CURRENT_LIST_DIR}/init.cmake")

set(CROSS_ABI "none")

if(LLAMA_INSTALL_OS STREQUAL "linux")
    if(CROSS_GLIBC)
        set(CROSS_ABI "gnu.2.27")
    else()
        set(CROSS_ABI "musl")
    endif()
elseif(LLAMA_INSTALL_OS STREQUAL "windows")
    if(CMAKE_HOST_WIN32)
        set(CROSS_ABI "msvc")
    else()
        set(CROSS_ABI "gnu")
    endif()
endif()

set(CROSS_TARGET "${LLAMA_INSTALL_ARCH}-${LLAMA_INSTALL_OS}-${CROSS_ABI}")

find_program(ZIG NAMES zig HINTS "${CMAKE_CURRENT_LIST_DIR}/../deps/zig" REQUIRED)

if(NOT EXISTS "${CMAKE_BINARY_DIR}/zig-cc")
    file(CREATE_LINK "${ZIG}" "${CMAKE_BINARY_DIR}/zig" SYMBOLIC COPY_ON_ERROR)

    execute_process(
        COMMAND ${ZIG} cc "${CMAKE_CURRENT_LIST_DIR}/zig.c" -o "${CMAKE_BINARY_DIR}/zig-cc"
    )
    foreach(WRAPPER c++ ar ranlib objcopy rc dlltool)
        file(COPY_FILE "${CMAKE_BINARY_DIR}/zig-cc" "${CMAKE_BINARY_DIR}/zig-${WRAPPER}")
    endforeach()
endif()

set(CMAKE_LINK_DEPENDS_USE_COMPILER FALSE CACHE BOOL "" FORCE)
set(CMAKE_DEPENDS_USE_COMPILER FALSE CACHE BOOL "" FORCE)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY CACHE STRING "" FORCE)

set(CMAKE_C_COMPILER   "${CMAKE_BINARY_DIR}/zig-cc")
set(CMAKE_ASM_COMPILER "${CMAKE_BINARY_DIR}/zig-cc")
set(CMAKE_CXX_COMPILER "${CMAKE_BINARY_DIR}/zig-c++")
set(CMAKE_AR           "${CMAKE_BINARY_DIR}/zig-ar")
set(CMAKE_RANLIB       "${CMAKE_BINARY_DIR}/zig-ranlib")
set(CMAKE_OBJCOPY      "${CMAKE_BINARY_DIR}/zig-objcopy")
set(CMAKE_RC_COMPILER  "${CMAKE_BINARY_DIR}/zig-rc")
set(CMAKE_DLLTOOL      "${CMAKE_BINARY_DIR}/zig-dlltool")

set(CMAKE_C_COMPILER_AR     "${CMAKE_AR}")
set(CMAKE_C_COMPILER_RANLIB "${CMAKE_RANLIB}")
set(CMAKE_C_COMPILER_TARGET "${CROSS_TARGET}")

set(CMAKE_CXX_COMPILER_AR     "${CMAKE_AR}")
set(CMAKE_CXX_COMPILER_RANLIB "${CMAKE_RANLIB}")
set(CMAKE_CXX_COMPILER_TARGET "${CROSS_TARGET}")

set(HOST_C_COMPILER   "${CMAKE_C_COMPILER}")
set(HOST_CXX_COMPILER "${CMAKE_CXX_COMPILER}")

include("${CMAKE_CURRENT_LIST_DIR}/exit.cmake")
