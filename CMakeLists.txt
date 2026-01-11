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

add_executable(bench_noop
  bench/bench_main.cpp
  bench/cli.cpp
  bench/noop_case.cpp
  bench/registry.cpp
)

target_include_directories(bench_noop
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/bench
)
