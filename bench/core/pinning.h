#pragma once

#include <string>

// Best-effort CPU pinning. Returns false with a human-readable error on failure.
// Keeping this separate from the harness keeps main() focused on benchmarking.
bool pin_to_cpu(int cpu, std::string* error);
