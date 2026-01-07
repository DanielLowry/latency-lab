#pragma once

#include <chrono>
#include <cstdint>
#include <time.h>

inline uint64_t now_ns() {
#if defined(CLOCK_MONOTONIC_RAW)
  timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) == 0) {
    return static_cast<uint64_t>(ts.tv_sec) * 1000000000ull +
           static_cast<uint64_t>(ts.tv_nsec);
  }
#endif
  auto now = std::chrono::steady_clock::now().time_since_epoch();
  return static_cast<uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(now).count());
}
