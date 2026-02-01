#pragma once

#include <atomic>
#include <string>
#include <thread>

enum class NoiseMode {
  kOff,
  kFree,
  kSame,
  kOther,
};

const char* noise_mode_label(NoiseMode mode);

struct NoiseConfig {
  NoiseMode mode = NoiseMode::kOff;
  bool pin_enabled = false;
  int pin_cpu = -1;
};

class NoiseRunner {
 public:
  NoiseRunner() = default;
  ~NoiseRunner();

  NoiseRunner(const NoiseRunner&) = delete;
  NoiseRunner& operator=(const NoiseRunner&) = delete;

  bool Start(const NoiseConfig& config, std::string* error);
  void Stop();

  int noise_cpu() const { return noise_cpu_; }
  NoiseMode mode() const { return mode_; }

 private:
  std::atomic<bool> running_{false};
  std::thread thread_;
  int noise_cpu_ = -1;
  NoiseMode mode_ = NoiseMode::kOff;
};
