#include "cli.h"
#include "csv.h"
#include "registry.h"
#include "stats.h"
#include "timer.h"

#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace {

// Keep listing logic in one place for --list and error paths.
void list_cases(std::ostream& out) {
  for (const Case* bench_case : cases()) {
    if (bench_case && bench_case->name) {
      out << bench_case->name << "\n";
    }
  }
}

// Resolve an explicit case name, or fall back to the first registered case.
const Case* resolve_case(const std::string& name) {
  if (!name.empty()) {
    return find_case(name);
  }
  const auto& all_cases = cases();
  if (!all_cases.empty()) {
    return all_cases.front();
  }
  return nullptr;
}

// Run the selected case and emit outputs (stdout summary + raw CSV).
int run_benchmark(const Case& bench_case, const CliOptions& options) {
  Ctx ctx;
  if (bench_case.setup) {
    bench_case.setup(&ctx);
  }

  // Warmup reduces cold-start effects (cache/branch predictor) in the samples.
  for (uint64_t i = 0; i < options.warmup; ++i) {
    bench_case.run_once(&ctx);
  }

  std::vector<uint64_t> samples;
  samples.reserve(static_cast<size_t>(options.iters));

  for (uint64_t i = 0; i < options.iters; ++i) {
    // Timed region is only the operation under test.
    const uint64_t start = now_ns();
    bench_case.run_once(&ctx);
    const uint64_t end = now_ns();
    samples.push_back(end - start);
  }

  if (bench_case.teardown) {
    bench_case.teardown(&ctx);
  }

  const Quantiles q = compute_quantiles(samples);
  std::cout << bench_case.name << "\n";
  std::cout << "min,p50,p95,p99,p999,max,mean\n";
  std::cout << q.min << "," << q.p50 << "," << q.p95 << "," << q.p99 << ","
            << q.p999 << "," << q.max << "," << q.mean << "\n";

  if (!write_raw_csv(options.out_path, samples)) {
    std::cerr << "failed to write " << options.out_path << "\n";
    return 1;
  }

  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  const CliParseResult parse = parse_cli_args(argc, argv);
  if (parse.show_help) {
    print_usage(argv[0], std::cout);
    return 0;
  }
  if (!parse.ok) {
    std::cerr << parse.error << "\n";
    print_usage(argv[0], std::cerr);
    return 1;
  }

  if (parse.options.list_cases) {
    list_cases(std::cout);
    return 0;
  }

  const Case* bench_case = resolve_case(parse.options.case_name);

  if (!parse.options.case_name.empty() && !bench_case) {
    std::cerr << "unknown case: " << parse.options.case_name << "\n";
    std::cerr << "known cases:\n";
    list_cases(std::cerr);
    return 1;
  }

  if (!bench_case || !bench_case->run_once) {
    std::cerr << "no runnable case found\n";
    return 1;
  }

  return run_benchmark(*bench_case, parse.options);
}
