#pragma once

#include "case.h"

#include <string>
#include <vector>

void register_case(const Case& bench_case);
const std::vector<const Case*>& cases();
const Case* find_case(const std::string& name);

#define LATENCY_LAB_REGISTER_CASE(bench_case) \
  LATENCY_LAB_REGISTER_CASE_IMPL(bench_case, __COUNTER__)
#define LATENCY_LAB_REGISTER_CASE_IMPL(bench_case, counter) \
  namespace { \
  struct CaseRegistrar_##counter { \
    CaseRegistrar_##counter() { register_case(bench_case); } \
  }; \
  static CaseRegistrar_##counter case_registrar_##counter; \
  }
