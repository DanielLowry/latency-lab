#include "registry.h"

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

}  // namespace

int main() {
#define CHECK(cond)                                              \
  do {                                                           \
    if (!(cond)) {                                                \
      std::cerr << "check failed at line " << __LINE__ << ": "    \
                << #cond << "\n";                                \
      return 1;                                                   \
    }                                                            \
  } while (false)

  register_case(kCaseA);
  register_case(kCaseB);

  const auto& all_cases = cases();
  CHECK(all_cases.size() == 2);
  CHECK(all_cases[0] == &kCaseA);
  CHECK(all_cases[1] == &kCaseB);

  CHECK(find_case("case_a") == &kCaseA);
  CHECK(find_case("case_b") == &kCaseB);
  CHECK(find_case("missing") == nullptr);

#undef CHECK

  std::cout << "registry_tests: ok\n";
  return 0;
}
