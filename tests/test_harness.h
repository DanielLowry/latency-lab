#pragma once

#include <cstring>
#include <iostream>
#include <vector>

struct TestCase {
  const char* name = nullptr;
  bool (*fn)(int argc, char** argv) = nullptr;
};

inline int run_named_tests(const std::vector<TestCase>& cases,
                           int argc,
                           char** argv) {
  const char* requested = nullptr;
  int argi = 1;

  auto find_case = [&](const char* name) -> const TestCase* {
    if (!name) {
      return nullptr;
    }
    for (const auto& test_case : cases) {
      if (test_case.name && std::strcmp(test_case.name, name) == 0) {
        return &test_case;
      }
    }
    return nullptr;
  };

  while (argi < argc) {
    const char* arg = argv[argi];
    if (std::strcmp(arg, "--list") == 0) {
      for (const auto& test_case : cases) {
        if (test_case.name) {
          std::cout << test_case.name << "\n";
        }
      }
      return 0;
    }
    if (std::strcmp(arg, "--case") == 0) {
      if (argi + 1 >= argc) {
        std::cerr << "--case requires a name\n";
        return 1;
      }
      requested = argv[argi + 1];
      argi += 2;
      break;
    }
    if (std::strcmp(arg, "--") == 0) {
      argi += 1;
      break;
    }
    if (!requested && find_case(arg)) {
      requested = arg;
      argi += 1;
      break;
    }
    // Unrecognized positional args are passed through to all cases.
    break;
  }

  if (requested && argi < argc && std::strcmp(argv[argi], "--") == 0) {
    argi += 1;
  }

  int test_argc = argc - argi;
  char** test_argv = argv + argi;

  auto run_case = [&](const TestCase& test_case) -> bool {
    if (!test_case.fn) {
      std::cerr << "missing test function for " << test_case.name << "\n";
      return false;
    }
    const bool ok = test_case.fn(test_argc, test_argv);
    std::cout << test_case.name << ": " << (ok ? "ok" : "fail") << "\n";
    return ok;
  };

  if (requested) {
    const TestCase* test_case = find_case(requested);
    if (test_case) {
      return run_case(*test_case) ? 0 : 1;
    }
    std::cerr << "unknown test case: " << requested << "\n";
    std::cerr << "known cases:\n";
    for (const auto& test_case : cases) {
      if (test_case.name) {
        std::cerr << "  " << test_case.name << "\n";
      }
    }
    return 1;
  }

  bool all_ok = true;
  for (const auto& test_case : cases) {
    all_ok = run_case(test_case) && all_ok;
  }
  return all_ok ? 0 : 1;
}
