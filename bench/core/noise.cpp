#include "noise.h"

#include "pinning.h"

#include <atomic>
#include <cstdint>
#include <exception>
#include <future>
#include <thread>

#if defined(__unix__) || defined(__APPLE__)
#include <unistd.h>
#endif

namespace {

bool noise_mode_requires_pin(NoiseMode mode) {
  return mode == NoiseMode::kSame || mode == NoiseMode::kOther;
}

int read_online_cpus() {
#if defined(_SC_NPROCESSORS_ONLN)
  const long count = sysconf(_SC_NPROCESSORS_ONLN);
  if (count > 0) {
    return static_cast<int>(count);
  }
#endif
  const unsigned int fallback = std::thread::hardware_concurrency();
  if (fallback > 0) {
    return static_cast<int>(fallback);
  }
  return 1;
}

int pick_other_cpu(int pinned_cpu, std::string* error) {
  if (pinned_cpu < 0) {
    if (error) {
      *error = "pin cpu must be >= 0 when choosing a noise cpu";
    }
    return -1;
  }
  const int count = read_online_cpus();
  if (count < 2) {
    if (error) {
      *error = "cannot pick a different cpu (only one core online)";
    }
    return -1;
  }
  const int candidate = (pinned_cpu + 1) % count;
  if (candidate == pinned_cpu) {
    if (error) {
      *error = "failed to pick a different cpu";
    }
    return -1;
  }
  return candidate;
}

void noise_spin(std::atomic<bool>* running) {
  uint64_t value = 0x12345678u;
  while (running->load(std::memory_order_relaxed)) {
    value = value * 1664525u + 1013904223u;
#if defined(__GNUC__) || defined(__clang__)
    asm volatile("" : "+r"(value));
#else
    std::atomic_signal_fence(std::memory_order_seq_cst);
#endif
  }
}

}  // namespace

const char* noise_mode_label(NoiseMode mode) {
  switch (mode) {
    case NoiseMode::kOff:
      return "off";
    case NoiseMode::kFree:
      return "free";
    case NoiseMode::kSame:
      return "same";
    case NoiseMode::kOther:
      return "other";
  }
  return "off";
}

NoiseRunner::~NoiseRunner() {
  Stop();
}

bool NoiseRunner::Start(const NoiseConfig& config, std::string* error) {
  if (config.mode == NoiseMode::kOff) {
    mode_ = NoiseMode::kOff;
    noise_cpu_ = -1;
    return true;
  }
  if (noise_mode_requires_pin(config.mode) && !config.pin_enabled) {
    if (error) {
      *error = "noise mode requires --pin";
    }
    return false;
  }

  int target_cpu = -1;
  if (config.mode == NoiseMode::kSame) {
    if (config.pin_cpu < 0) {
      if (error) {
        *error = "pin cpu must be >= 0 when choosing noise=same";
      }
      return false;
    }
    target_cpu = config.pin_cpu;
  } else if (config.mode == NoiseMode::kOther) {
    target_cpu = pick_other_cpu(config.pin_cpu, error);
    if (target_cpu < 0) {
      return false;
    }
  }

  mode_ = config.mode;
  noise_cpu_ = target_cpu;
  running_.store(true, std::memory_order_release);

  std::promise<std::string> promise;
  auto future = promise.get_future();
  try {
    thread_ = std::thread(
        [this, target_cpu, promise = std::move(promise)]() mutable {
          if (target_cpu >= 0) {
            std::string pin_error;
            if (!pin_to_cpu(target_cpu, &pin_error)) {
              running_.store(false, std::memory_order_release);
              promise.set_value(pin_error);
              return;
            }
          }
          promise.set_value("");
          noise_spin(&running_);
        });
  } catch (const std::exception& exc) {
    running_.store(false, std::memory_order_release);
    if (error) {
      *error = exc.what();
    }
    return false;
  }

  const std::string start_error = future.get();
  if (!start_error.empty()) {
    if (thread_.joinable()) {
      thread_.join();
    }
    if (error) {
      *error = start_error;
    }
    return false;
  }

  return true;
}

void NoiseRunner::Stop() {
  running_.store(false, std::memory_order_release);
  if (thread_.joinable()) {
    thread_.join();
  }
}
