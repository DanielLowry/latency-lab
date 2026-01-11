#include "cli.h"

#include <cstdlib>
#include <vector>

namespace {

uint64_t parse_u64(const char* arg, uint64_t fallback) {
  // Keep defaults on empty or partially-parsed input to avoid surprises.
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

}  // namespace

CliParseResult parse_cli_args(int argc, char** argv) {
  CliParseResult result;
  std::vector<std::string> positional;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    // Keep parsing minimal: small flag set + positional args.
    if (arg == "--list") {
      result.options.list_cases = true;
    } else if (arg == "--case") {
      if (i + 1 >= argc) {
        result.ok = false;
        result.error = "--case requires a name";
        return result;
      }
      result.options.case_name = argv[++i];
    } else if (arg == "--help" || arg == "-h") {
      result.show_help = true;
      return result;
    } else if (!arg.empty() && arg[0] == '-') {
      result.ok = false;
      result.error = "unknown flag: " + arg;
      return result;
    } else {
      positional.push_back(arg);
    }
  }

  // Positional args map to output path, iteration count, and warmup count.
  if (positional.size() > 0) {
    result.options.out_path = positional[0];
  }
  if (positional.size() > 1) {
    result.options.iters =
        parse_u64(positional[1].c_str(), result.options.iters);
  }
  if (positional.size() > 2) {
    result.options.warmup =
        parse_u64(positional[2].c_str(), result.options.warmup);
  }
  if (positional.size() > 3) {
    result.ok = false;
    result.error = "too many positional args";
    return result;
  }

  return result;
}

void print_usage(const char* argv0, std::ostream& out) {
  out << "usage: " << argv0
      << " [--list] [--case name] [out.csv] [iters] [warmup]\n";
}
