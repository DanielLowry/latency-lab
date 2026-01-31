#pragma once

// Shared context passed between setup/run/teardown for a case.
// This will grow as the harness adds common helpers.
struct Ctx {};

struct Case {
  const char* name = nullptr;
  void (*setup)(Ctx*) = nullptr;
  void (*run_once)(Ctx*) = nullptr;
  void (*teardown)(Ctx*) = nullptr;
};
