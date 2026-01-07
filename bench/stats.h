#pragma once

#include <algorithm>
#include <cstdint>
#include <numeric>
#include <vector>

struct Quantiles {
  uint64_t min = 0;
  uint64_t p50 = 0;
  uint64_t p95 = 0;
  uint64_t p99 = 0;
  uint64_t p999 = 0;
  uint64_t max = 0;
  double mean = 0.0;
};

inline uint64_t percentile(const std::vector<uint64_t>& sorted, double p) {
  if (sorted.empty()) {
    return 0;
  }
  const double idx = p * static_cast<double>(sorted.size() - 1);
  const size_t pos = static_cast<size_t>(idx);
  return sorted[pos];
}

inline Quantiles compute_quantiles(const std::vector<uint64_t>& samples) {
  Quantiles q;
  if (samples.empty()) {
    return q;
  }

  std::vector<uint64_t> sorted = samples;
  std::sort(sorted.begin(), sorted.end());

  q.min = sorted.front();
  q.p50 = percentile(sorted, 0.50);
  q.p95 = percentile(sorted, 0.95);
  q.p99 = percentile(sorted, 0.99);
  q.p999 = percentile(sorted, 0.999);
  q.max = sorted.back();

  long double sum = 0.0;
  for (uint64_t v : samples) {
    sum += static_cast<long double>(v);
  }
  q.mean = static_cast<double>(sum / samples.size());

  return q;
}
