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

add_executable(bench
  bench/bench_main.cpp
  bench/cli.cpp
  bench/noop_case.cpp
  bench/pinning.cpp
  bench/registry.cpp
)

target_include_directories(bench
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/bench
)

enable_testing()

add_executable(bench_cli_tests
  tests/cli_tests.cpp
  bench/cli.cpp
)
target_include_directories(bench_cli_tests
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/bench
)
add_test(NAME cli_tests COMMAND bench_cli_tests)

add_executable(bench_registry_tests
  tests/registry_tests.cpp
  bench/registry.cpp
)
target_include_directories(bench_registry_tests
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/bench
)
add_test(NAME registry_tests COMMAND bench_registry_tests)

add_executable(bench_smoke_tests
  tests/smoke_tests.cpp
)
add_test(NAME smoke_tests COMMAND bench_smoke_tests $<TARGET_FILE:bench>)
