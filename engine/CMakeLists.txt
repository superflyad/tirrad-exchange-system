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

option(TES_BUILD_PYTHON_BINDINGS "Build Python bindings for tes_engine" OFF)

if(TES_BUILD_PYTHON_BINDINGS)
    find_package(Python3 COMPONENTS Interpreter Development.Module REQUIRED)

    message(STATUS "Python3 executable: ${Python3_EXECUTABLE}")
    message(STATUS "Python3 version: ${Python3_VERSION}")
    message(STATUS "Python3 include dirs: ${Python3_INCLUDE_DIRS}")
    message(STATUS "Python3 library dirs: ${Python3_LIBRARY_DIRS}")

    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/third_party/pybind11/CMakeLists.txt")
        message(STATUS "Using vendored pybind11 from engine/third_party/pybind11")
        add_subdirectory(third_party/pybind11)
    else()
        find_package(pybind11 CONFIG QUIET)
        if(NOT pybind11_FOUND)
            execute_process(
                COMMAND "${Python3_EXECUTABLE}" -m pybind11 --cmakedir
                OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
                OUTPUT_STRIP_TRAILING_WHITESPACE
                ERROR_QUIET
                RESULT_VARIABLE PYBIND11_CMAKEDIR_RESULT
            )

            if(PYBIND11_CMAKEDIR_RESULT EQUAL 0 AND EXISTS "${PYBIND11_CMAKE_DIR}")
                find_package(pybind11 CONFIG QUIET PATHS "${PYBIND11_CMAKE_DIR}" NO_DEFAULT_PATH)
            endif()
        endif()

        if(NOT pybind11_FOUND)
            message(FATAL_ERROR
                "TES_BUILD_PYTHON_BINDINGS=ON but pybind11 was not found. "
                "Install pybind11 (for example: 'python3 -m pip install --user pybind11') "
                "or vendor it at engine/third_party/pybind11."
            )
        endif()
        message(STATUS "Using pybind11 from system/Python installation")
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

    if(WIN32 AND MSVC)
        set(TES_PYTHON_LINK_LIBRARIES "")
        if(DEFINED Python3_LIBRARY AND Python3_LIBRARY)
            list(APPEND TES_PYTHON_LINK_LIBRARIES "${Python3_LIBRARY}")
        elseif(DEFINED Python3_LIBRARIES AND Python3_LIBRARIES)
            list(APPEND TES_PYTHON_LINK_LIBRARIES ${Python3_LIBRARIES})
        endif()

        if(TES_PYTHON_LINK_LIBRARIES)
            target_link_libraries(tes_engine_python PRIVATE ${TES_PYTHON_LINK_LIBRARIES})
            message(STATUS "Windows/MSVC Python import library path(s): ${TES_PYTHON_LINK_LIBRARIES}")
        else()
            message(WARNING
                "Windows/MSVC Python import library path was not provided by CMake. "
                "If linking fails, pass -DPython3_LIBRARY=<full path to pythonXY.lib>."
            )
        endif()
    endif()

    target_include_directories(tes_engine_python
        PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/include
    )

    set_target_properties(tes_engine_python PROPERTIES
        OUTPUT_NAME tes_engine
    )

    if(DEFINED Python3_LIBRARY AND Python3_LIBRARY)
        message(STATUS "Python library selected: ${Python3_LIBRARY}")
    elseif(DEFINED Python3_LIBRARIES AND Python3_LIBRARIES)
        message(STATUS "Python libraries selected: ${Python3_LIBRARIES}")
    else()
        message(STATUS "Python library selected: managed via Python3 target only")
    endif()

    message(STATUS "Python bindings enabled: tes_engine module")
endif()
