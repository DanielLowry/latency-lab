#include "csv.h"
#include "stats.h"
#include "timer.h"

#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

uint64_t parse_u64(const char* arg, uint64_t fallback) {
  if (!arg || *arg == '\0') {
    return fallback;
  }
  char* end = nullptr;
  const unsigned long long value = std::strtoull(arg, &end, 10);
  if (!end || *end != '\0') {
    return fallback;
  }
  return static_cast<uint64_t>(value);
}

inline void run_noop() {
#if defined(__GNUC__) || defined(__clang__)
  asm volatile("" ::: "memory");
#else
  std::atomic_signal_fence(std::memory_order_seq_cst);
#endif
}

}  // namespace

int main(int argc, char** argv) {
  std::string out_path = "raw.csv";
  uint64_t iters = 10000;
  uint64_t warmup = 1000;

  if (argc > 1) {
    out_path = argv[1];
  }
  if (argc > 2) {
    iters = parse_u64(argv[2], iters);
  }
  if (argc > 3) {
    warmup = parse_u64(argv[3], warmup);
  }

  for (uint64_t i = 0; i < warmup; ++i) {
    run_noop();
  }

  std::vector<uint64_t> samples;
  samples.reserve(static_cast<size_t>(iters));

  for (uint64_t i = 0; i < iters; ++i) {
    const uint64_t start = now_ns();
    run_noop();
    const uint64_t end = now_ns();
    samples.push_back(end - start);
  }

  const Quantiles q = compute_quantiles(samples);
  std::cout << "min,p50,p95,p99,p999,max,mean\n";
  std::cout << q.min << "," << q.p50 << "," << q.p95 << "," << q.p99 << ","
            << q.p999 << "," << q.max << "," << q.mean << "\n";

  if (!write_raw_csv(out_path, samples)) {
    std::cerr << "failed to write " << out_path << "\n";
    return 1;
  }

  return 0;
}
