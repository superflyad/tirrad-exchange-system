cmake_minimum_required(VERSION 3.20)

project(tes_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(tes_engine STATIC
    src/version.cpp
)

target_include_directories(tes_engine
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_executable(tes_engine_tests
    tests/test_version.cpp
    tests/test_types_and_events.cpp
    tests/test_order_book.cpp
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
