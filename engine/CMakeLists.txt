cmake_minimum_required(VERSION 3.20)

project(tes_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(tes_engine STATIC
    src/version.cpp
    src/matching_engine.cpp
)

set_target_properties(tes_engine PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

target_include_directories(tes_engine
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_executable(tes_engine_tests
    tests/test_version.cpp
    tests/test_types_and_events.cpp
    tests/test_order_book.cpp
    tests/test_matching_engine.cpp
)

target_include_directories(tes_engine_tests
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/doctest
)

target_link_libraries(tes_engine_tests
    PRIVATE
        tes_engine
)

enable_testing()
add_test(NAME tes_engine_tests COMMAND tes_engine_tests)

option(TES_BUILD_PYTHON_BINDINGS "Build Python bindings for tes_engine" ON)

if(TES_BUILD_PYTHON_BINDINGS)
    find_package(Python3 COMPONENTS Interpreter Development.Module REQUIRED)

    message(STATUS "Python3 executable: ${Python3_EXECUTABLE}")
    message(STATUS "Python3 version: ${Python3_VERSION}")
    message(STATUS "Python3 include dirs: ${Python3_INCLUDE_DIRS}")
    message(STATUS "Python3 library dirs: ${Python3_LIBRARY_DIRS}")

    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/third_party/pybind11/CMakeLists.txt")
        add_subdirectory(third_party/pybind11)
    else()
        find_package(pybind11 CONFIG REQUIRED)
    endif()

    pybind11_add_module(tes_engine_python MODULE
        python/bindings.cpp
    )

    target_link_libraries(tes_engine_python
        PRIVATE
            tes_engine
    )

    if(TARGET Python3::Module)
        target_link_libraries(tes_engine_python PRIVATE Python3::Module)
    elseif(TARGET Python3::Python)
        target_link_libraries(tes_engine_python PRIVATE Python3::Python)
    endif()

    target_include_directories(tes_engine_python
        PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/include
    )

    set_target_properties(tes_engine_python PROPERTIES
        OUTPUT_NAME tes_engine
    )

    message(STATUS "Python bindings enabled: tes_engine module")
endif()
