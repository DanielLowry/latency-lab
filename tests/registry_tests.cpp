#include "registry.h"
#include "test_harness.h"

#include <iostream>

namespace {

void run_once(Ctx*) {}

const Case kCaseA{
    "case_a",
    nullptr,
    run_once,
    nullptr,
};

const Case kCaseB{
    "case_b",
    nullptr,
    run_once,
    nullptr,
};

const Case kCaseC{
    "case_c",
    nullptr,
    run_once,
    nullptr,
};

const Case kCaseD{
    "case_d",
    nullptr,
    run_once,
    nullptr,
};

#define CHECK(cond)                                              \
  do {                                                           \
    if (!(cond)) {                                                \
      std::cerr << "check failed at line " << __LINE__ << ": "    \
                << #cond << "\n";                                \
      return false;                                               \
    }                                                            \
  } while (false)

bool test_register_and_find(int, char**) {
  register_case(kCaseA);
  register_case(kCaseB);

  CHECK(find_case("case_a") == &kCaseA);
  CHECK(find_case("case_b") == &kCaseB);
  CHECK(find_case("missing") == nullptr);

  return true;
}

bool test_insertion_order(int, char**) {
  const auto base = cases().size();
  register_case(kCaseC);
  register_case(kCaseD);

  const auto& all_cases = cases();
  CHECK(all_cases.size() >= base + 2);
  CHECK(all_cases[base] == &kCaseC);
  CHECK(all_cases[base + 1] == &kCaseD);

  return true;
}

#undef CHECK

}  // namespace

int main(int argc, char** argv) {
  const std::vector<TestCase> cases = {
      {"register_and_find", test_register_and_find},
      {"insertion_order", test_insertion_order},
  };

  return run_named_tests(cases, argc, argv);
}
