#include "cli.h"
#include "test_harness.h"

#include <iostream>
#include <initializer_list>
#include <vector>

namespace {

CliParseResult parse_args(std::initializer_list<const char*> args) {
  std::vector<char*> argv;
  argv.reserve(args.size());
  for (const char* arg : args) {
    argv.push_back(const_cast<char*>(arg));
  }
  return parse_cli_args(static_cast<int>(argv.size()), argv.data());
}

#define CHECK(cond)                                              \
  do {                                                           \
    if (!(cond)) {                                                \
      std::cerr << "check failed at line " << __LINE__ << ": "    \
                << #cond << "\n";                                \
      return false;                                               \
    }                                                            \
  } while (false)

bool test_help_flag(int, char**) {
  const auto result = parse_args({"bench", "--help"});
  CHECK(result.show_help);
  return true;
}

bool test_list_flag(int, char**) {
  const auto result = parse_args({"bench", "--list"});
  CHECK(result.ok);
  CHECK(result.options.list_cases);
  return true;
}

bool test_named_options(int, char**) {
  const auto result =
      parse_args({"bench", "--case", "noop", "--iters", "42", "--warmup", "7",
                  "--out", "results", "--pin", "2", "--tag", "quiet", "--tag",
                  "warm"});
  CHECK(result.ok);
  CHECK(result.options.case_name == "noop");
  CHECK(result.options.iters == 42);
  CHECK(result.options.warmup == 7);
  CHECK(result.options.out_dir == "results");
  CHECK(result.options.pin_enabled);
  CHECK(result.options.pin_cpu == 2);
  CHECK(result.options.tags.size() == 2);
  CHECK(result.options.tags[0] == "quiet");
  CHECK(result.options.tags[1] == "warm");
  return true;
}

bool test_positional_args(int, char**) {
  const auto result = parse_args({"bench", "out.csv", "10", "3"});
  CHECK(result.ok);
  CHECK(result.options.out_path == "out.csv");
  CHECK(result.options.iters == 10);
  CHECK(result.options.warmup == 3);
  return true;
}

bool test_missing_iters_value(int, char**) {
  const auto result = parse_args({"bench", "--iters"});
  CHECK(!result.ok);
  return true;
}

bool test_negative_pin(int, char**) {
  const auto result = parse_args({"bench", "--pin", "-1"});
  CHECK(!result.ok);
  return true;
}

bool test_too_many_positionals(int, char**) {
  const auto result = parse_args({"bench", "a", "b", "c", "d"});
  CHECK(!result.ok);
  return true;
}

#undef CHECK

}  // namespace

int main(int argc, char** argv) {
  const std::vector<TestCase> cases = {
      {"help_flag", test_help_flag},
      {"list_flag", test_list_flag},
      {"named_options", test_named_options},
      {"positional_args", test_positional_args},
      {"missing_iters_value", test_missing_iters_value},
      {"negative_pin", test_negative_pin},
      {"too_many_positionals", test_too_many_positionals},
  };

  return run_named_tests(cases, argc, argv);
}
