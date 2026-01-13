#include "cli.h"

#include <cstdlib>
#include <limits>
#include <vector>

namespace {

bool parse_u64_strict(const char* arg, uint64_t* value) {
  if (!arg || *arg == '\0') {
    return false;
  }
  char* end = nullptr;
  const unsigned long long parsed = std::strtoull(arg, &end, 10);
  if (!end || *end != '\0') {
    return false;
  }
  *value = static_cast<uint64_t>(parsed);
  return true;
}

bool parse_int_strict(const char* arg, int* value) {
  if (!arg || *arg == '\0') {
    return false;
  }
  char* end = nullptr;
  const long parsed = std::strtol(arg, &end, 10);
  if (!end || *end != '\0') {
    return false;
  }
  if (parsed < std::numeric_limits<int>::min() ||
      parsed > std::numeric_limits<int>::max()) {
    return false;
  }
  *value = static_cast<int>(parsed);
  return true;
}

uint64_t parse_u64_lenient(const char* arg, uint64_t fallback) {
  // Keep defaults on empty or partially-parsed input to avoid surprises.
  uint64_t value = 0;
  if (!parse_u64_strict(arg, &value)) {
    return fallback;
  }
  return value;
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
    } else if (arg == "--out") {
      if (i + 1 >= argc) {
        result.ok = false;
        result.error = "--out requires a directory";
        return result;
      }
      result.options.out_dir = argv[++i];
    } else if (arg == "--iters") {
      if (i + 1 >= argc) {
        result.ok = false;
        result.error = "--iters requires a number";
        return result;
      }
      uint64_t value = 0;
      if (!parse_u64_strict(argv[++i], &value)) {
        result.ok = false;
        result.error = "--iters expects an unsigned integer";
        return result;
      }
      result.options.iters = value;
    } else if (arg == "--warmup") {
      if (i + 1 >= argc) {
        result.ok = false;
        result.error = "--warmup requires a number";
        return result;
      }
      uint64_t value = 0;
      if (!parse_u64_strict(argv[++i], &value)) {
        result.ok = false;
        result.error = "--warmup expects an unsigned integer";
        return result;
      }
      result.options.warmup = value;
    } else if (arg == "--pin") {
      if (i + 1 >= argc) {
        result.ok = false;
        result.error = "--pin requires a cpu index";
        return result;
      }
      int value = 0;
      if (!parse_int_strict(argv[++i], &value)) {
        result.ok = false;
        result.error = "--pin expects an integer cpu index";
        return result;
      }
      if (value < 0) {
        result.ok = false;
        result.error = "--pin expects a non-negative cpu index";
        return result;
      }
      result.options.pin_enabled = true;
      result.options.pin_cpu = value;
    } else if (arg == "--tag") {
      if (i + 1 >= argc) {
        result.ok = false;
        result.error = "--tag requires a string";
        return result;
      }
      result.options.tags.push_back(argv[++i]);
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
        parse_u64_lenient(positional[1].c_str(), result.options.iters);
  }
  if (positional.size() > 2) {
    result.options.warmup =
        parse_u64_lenient(positional[2].c_str(), result.options.warmup);
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
      << " [--list] [--case name] [--out dir] [--iters N] [--warmup N]"
         " [--pin cpu] [--tag label] [out.csv] [iters] [warmup]\n";
}
