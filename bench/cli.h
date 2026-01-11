#pragma once

#include <cstdint>
#include <ostream>
#include <string>

// CLI options are kept separate from the benchmark harness for clarity.
struct CliOptions {
  std::string out_path = "raw.csv";
  uint64_t iters = 10000;
  uint64_t warmup = 1000;
  std::string case_name;
  bool list_cases = false;
};

// Parse result bundles options with simple status flags for main().
struct CliParseResult {
  CliOptions options;
  bool ok = true;
  bool show_help = false;
  std::string error;
};

CliParseResult parse_cli_args(int argc, char** argv);
void print_usage(const char* argv0, std::ostream& out);
