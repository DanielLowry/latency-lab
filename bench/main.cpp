#include "cli.h"
#include "csv.h"
#include "meta.h"
#include "pinning.h"
#include "registry.h"
#include "run_utils.h"
#include "stats.h"
#include "timer.h"

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
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

bool ensure_output_dir(const std::string& out_dir, std::string* error) {
  if (out_dir.empty()) {
    return true;
  }
  // Create parent directories for --out so the run doesn't fail later.
  std::error_code ec;
  std::filesystem::create_directories(out_dir, ec);
  if (ec) {
    if (error) {
      *error = ec.message();
    }
    return false;
  }
  return true;
}

bool write_text_file_atomic(const std::string& path,
                            const std::string& contents,
                            std::string* error) {
  const std::string tmp_path = path + ".tmp";
  std::ofstream out(tmp_path, std::ios::out | std::ios::trunc);
  if (!out.is_open()) {
    if (error) {
      *error = std::strerror(errno);
    }
    return false;
  }
  out << contents;
  out.flush();
  if (!out.good()) {
    if (error) {
      *error = "failed to write file";
    }
    std::remove(tmp_path.c_str());
    return false;
  }
  out.close();

  if (std::rename(tmp_path.c_str(), path.c_str()) != 0) {
    std::remove(path.c_str());
    if (std::rename(tmp_path.c_str(), path.c_str()) != 0) {
      if (error) {
        *error = std::strerror(errno);
      }
      std::remove(tmp_path.c_str());
      return false;
    }
  }
  return true;
}

std::string format_ns(double ns) {
  double value = ns;
  const char* unit = "ns";
  if (value >= 1e9) {
    value /= 1e9;
    unit = "s";
  } else if (value >= 1e6) {
    value /= 1e6;
    unit = "ms";
  } else if (value >= 1e3) {
    value /= 1e3;
    unit = "us";
  }

  std::ostringstream out;
  out << std::fixed << std::setprecision(2) << value << " " << unit;
  return out.str();
}

std::string format_summary(const Case& bench_case,
                           const Quantiles& q,
                           SummaryFormat format) {
  std::ostringstream out;
  out << bench_case.name << "\n";
  if (format == SummaryFormat::kCsv) {
    out << "min,p50,p95,p99,p999,max,mean\n";
    out << q.min << "," << q.p50 << "," << q.p95 << "," << q.p99 << ","
        << q.p999 << "," << q.max << "," << q.mean << "\n";
    return out.str();
  }

  out << "min=" << format_ns(static_cast<double>(q.min))
      << " p50=" << format_ns(static_cast<double>(q.p50))
      << " p95=" << format_ns(static_cast<double>(q.p95))
      << " p99=" << format_ns(static_cast<double>(q.p99))
      << " p999=" << format_ns(static_cast<double>(q.p999))
      << " max=" << format_ns(static_cast<double>(q.max))
      << " mean=" << format_ns(q.mean) << "\n";
  return out.str();
}

// Run the selected case and emit outputs (stdout summary + raw CSV).
int run_benchmark(const Case& bench_case,
                  const CliOptions& options,
                  const std::string& command_line) {
  if (options.pin_enabled) {
    std::string error;
    // Pin before setup/warmup so the entire run stays on one CPU.
    if (!pin_to_cpu(options.pin_cpu, &error)) {
      std::cerr << "failed to pin to cpu " << options.pin_cpu << ": " << error
                << "\n";
      return 1;
    }
  }

  if (!options.out_dir.empty()) {
    std::string error;
    if (!ensure_output_dir(options.out_dir, &error)) {
      std::cerr << "failed to create output dir " << options.out_dir << ": "
                << error << "\n";
      return 1;
    }
  }

  RunMetadata meta = collect_system_metadata();
  meta.command_line = command_line;
  meta.pinning = options.pin_enabled;
  meta.pinned_cpu = options.pin_cpu;
  meta.tags = options.tags;

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
  const std::string summary =
      format_summary(bench_case, q, options.summary_format);
  std::cout << summary;

  if (!options.out_dir.empty()) {
    const std::string stdout_path = resolve_stdout_path(options);
    std::string error;
    if (!write_text_file_atomic(stdout_path, summary, &error)) {
      std::cerr << "failed to write " << stdout_path << ": " << error << "\n";
      return 1;
    }
  }

  const std::string out_path = resolve_output_path(options);
  if (!write_raw_csv(out_path, samples)) {
    std::cerr << "failed to write " << out_path << "\n";
    return 1;
  }

  if (!options.out_dir.empty()) {
    const std::string meta_path = resolve_meta_path(options);
    std::string error;
    if (!write_meta_json(meta_path, meta, &error)) {
      std::cerr << "failed to write " << meta_path << ": " << error << "\n";
      return 1;
    }
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

  const std::string command_line = format_command_line(argc, argv);
  return run_benchmark(*bench_case, parse.options, command_line);
}
