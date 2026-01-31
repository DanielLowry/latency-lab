#include "case.h"
#include "registry.h"

#include <atomic>

namespace {

inline void run_noop() {
  // Prevent the compiler from optimizing away the loop body or reordering.
  // This is a "do nothing" payload that still enforces a compiler-level barrier:
  // it has no runtime cost beyond the fence, but keeps the timed region intact.
#if defined(__GNUC__) || defined(__clang__)
  // Empty asm with a "memory" clobber blocks reordering across the barrier.
  asm volatile("" ::: "memory");
#else
  // Portable fallback: a signal fence blocks compiler reordering.
  std::atomic_signal_fence(std::memory_order_seq_cst);
#endif
}

void noop_run_once(Ctx*) {
  run_noop();
}

const Case kNoopCase{
    "noop",
    nullptr,
    noop_run_once,
    nullptr,
};

}  // namespace

LATENCY_LAB_REGISTER_CASE(kNoopCase);
