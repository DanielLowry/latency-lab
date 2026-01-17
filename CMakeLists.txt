cmake_minimum_required(VERSION 3.28)

project(latency_lab LANGUAGES CXX)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
  message(FATAL_ERROR
    "In-source builds are not supported. "
    "Run: cmake -S . -B build -G Ninja")
endif()

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(CMAKE_BUILD_TYPE)
  set(LATENCY_LAB_BUILD_TYPE "${CMAKE_BUILD_TYPE}")
else()
  set(LATENCY_LAB_BUILD_TYPE "unknown")
endif()

set(LATENCY_LAB_BUILD_FLAGS "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${CMAKE_BUILD_TYPE}}")
string(STRIP "${LATENCY_LAB_BUILD_FLAGS}" LATENCY_LAB_BUILD_FLAGS)
string(REPLACE "\"" "\\\"" LATENCY_LAB_BUILD_FLAGS_ESCAPED "${LATENCY_LAB_BUILD_FLAGS}")

set(LATENCY_LAB_GENERATED_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated)
file(MAKE_DIRECTORY ${LATENCY_LAB_GENERATED_DIR})
configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/bench/build_info.h.in
  ${LATENCY_LAB_GENERATED_DIR}/build_info.h
  @ONLY
)

add_executable(bench
  bench/main.cpp
  bench/cli.cpp
  bench/meta.cpp
  bench/noop_case.cpp
  bench/pinning.cpp
  bench/registry.cpp
  bench/run_utils.cpp
)

target_include_directories(bench
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/bench
    ${LATENCY_LAB_GENERATED_DIR}
)

enable_testing()

add_executable(bench_cli_tests
  tests/cli_tests.cpp
  bench/cli.cpp
)
target_include_directories(bench_cli_tests
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/bench
    ${CMAKE_CURRENT_SOURCE_DIR}/tests
)
add_test(NAME cli_tests COMMAND bench_cli_tests)

add_executable(bench_registry_tests
  tests/registry_tests.cpp
  bench/registry.cpp
)
target_include_directories(bench_registry_tests
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/bench
    ${CMAKE_CURRENT_SOURCE_DIR}/tests
)
add_test(NAME registry_tests COMMAND bench_registry_tests)

add_executable(bench_smoke_tests
  tests/smoke_tests.cpp
)
target_include_directories(bench_smoke_tests
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/tests
)
add_test(NAME smoke_tests COMMAND bench_smoke_tests $<TARGET_FILE:bench>)
