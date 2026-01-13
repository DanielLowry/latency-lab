#pragma once

#include <cstdint>
#include <ostream>
#include <string>
#include <vector>

// CLI options are kept separate from the benchmark harness for clarity.
struct CliOptions {
  // If out_dir is set, raw.csv is written inside that directory.
  std::string out_dir;
  std::string out_path = "raw.csv";
  uint64_t iters = 10000;
  uint64_t warmup = 1000;
  std::string case_name;
  bool list_cases = false;
  bool pin_enabled = false;
  int pin_cpu = -1;
  // Tags are captured for metadata; harness does not interpret them yet.
  std::vector<std::string> tags;
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
