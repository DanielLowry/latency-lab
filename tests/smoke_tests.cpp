#include "test_harness.h"

#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <ctime>
#include <vector>

#if defined(__linux__)
#include <sched.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace {

bool parse_u64(const std::string& text, uint64_t* value) {
  if (!value) {
    return false;
  }
  char* end = nullptr;
  errno = 0;
  const unsigned long long parsed = std::strtoull(text.c_str(), &end, 10);
  if (errno != 0 || !end || *end != '\0') {
    return false;
  }
  *value = static_cast<uint64_t>(parsed);
  return true;
}

bool read_file_contents(const std::filesystem::path& path,
                        std::string* contents,
                        std::string* error) {
  if (!contents) {
    return false;
  }
  std::ifstream in(path);
  if (!in.is_open()) {
    if (error) {
      *error = "failed to open " + path.string();
    }
    return false;
  }
  std::ostringstream out;
  out << in.rdbuf();
  *contents = out.str();
  return true;
}

std::string next_out_dir_name() {
  static unsigned int counter = 0;
  const auto now = static_cast<unsigned long long>(std::time(nullptr));
  return "run_" + std::to_string(now) + "_" + std::to_string(counter++);
}

// Create a unique temp output directory for a test run.
bool make_out_dir(std::filesystem::path* out_dir, std::string* error) {
  if (!out_dir) {
    return false;
  }
  const auto tmp_base =
      std::filesystem::temp_directory_path() / "latency_lab_smoke";
  *out_dir = tmp_base / next_out_dir_name();
  std::error_code ec;
  std::filesystem::create_directories(*out_dir, ec);
  if (ec) {
    if (error) {
      *error = ec.message();
    }
    return false;
  }
  return true;
}

bool smoke_noop(int argc, char** argv) {
  if (argc < 1) {
    std::cerr << "smoke test requires bench executable path\n";
    return false;
  }

  const std::filesystem::path bench_path(argv[0]);
  if (!std::filesystem::exists(bench_path)) {
    std::cerr << "bench executable not found: " << bench_path << "\n";
    return false;
  }

  std::filesystem::path out_dir;
  std::string error;
  if (!make_out_dir(&out_dir, &error)) {
    std::cerr << "failed to create temp dir: " << error << "\n";
    return false;
  }

  const std::string cmd = "\"" + bench_path.string() +
                          "\" --case noop --iters 1 --warmup 0 --out \"" +
                          out_dir.string() + "\"";
  // Keep the smoke run tiny; we only validate outputs, not timing.
  if (std::system(cmd.c_str()) != 0) {
    std::cerr << "bench invocation failed: " << cmd << "\n";
    return false;
  }

  const auto csv_path = out_dir / "raw.csv";
  std::ifstream in(csv_path);
  if (!in.is_open()) {
    std::cerr << "missing raw.csv at " << csv_path << "\n";
    return false;
  }

  std::string header;
  if (!std::getline(in, header)) {
    std::cerr << "raw.csv is empty\n";
    return false;
  }
  if (header != "iter,ns") {
    std::cerr << "unexpected CSV header: " << header << "\n";
    return false;
  }

  std::string line;
  if (!std::getline(in, line)) {
    std::cerr << "raw.csv missing data row\n";
    return false;
  }
  const auto comma = line.find(',');
  if (comma == std::string::npos) {
    std::cerr << "raw.csv row missing comma: " << line << "\n";
    return false;
  }
  const std::string iter_text = line.substr(0, comma);
  const std::string ns_text = line.substr(comma + 1);
  uint64_t iter = 0;
  uint64_t ns = 0;
  if (!parse_u64(iter_text, &iter) || !parse_u64(ns_text, &ns)) {
    std::cerr << "raw.csv row not numeric: " << line << "\n";
    return false;
  }

  const auto meta_path = out_dir / "meta.json";
  std::string meta_contents;
  if (!read_file_contents(meta_path, &meta_contents, &error)) {
    std::cerr << "missing meta.json at " << meta_path << "\n";
    return false;
  }
  const std::vector<std::string> required_keys = {
      "\"cpu_model\"",
      "\"cpu_cores\"",
      "\"kernel_version\"",
      "\"command_line\"",
      "\"compiler_version\"",
      "\"build_flags\"",
      "\"pinning\"",
      "\"tags\"",
  };
  for (const auto& key : required_keys) {
    if (meta_contents.find(key) == std::string::npos) {
      std::cerr << "meta.json missing key: " << key << "\n";
      return false;
    }
  }

  const auto stdout_path = out_dir / "stdout.txt";
  std::string stdout_contents;
  if (!read_file_contents(stdout_path, &stdout_contents, &error)) {
    std::cerr << "missing stdout.txt at " << stdout_path << "\n";
    return false;
  }
  if (stdout_contents.find("min,p50,p95,p99,p999,max,mean") ==
      std::string::npos) {
    std::cerr << "stdout.txt missing summary header\n";
    return false;
  }

  std::error_code ec;
  std::filesystem::remove_all(out_dir, ec);

  return true;
}

#if defined(__linux__)
// Pick any allowed CPU from the current affinity mask.
int first_allowed_cpu(std::string* error) {
  cpu_set_t set;
  CPU_ZERO(&set);
  if (sched_getaffinity(0, sizeof(set), &set) != 0) {
    if (error) {
      *error = std::strerror(errno);
    }
    return -1;
  }
  for (int i = 0; i < CPU_SETSIZE; ++i) {
    if (CPU_ISSET(i, &set)) {
      return i;
    }
  }
  if (error) {
    *error = "no cpu available in affinity mask";
  }
  return -1;
}

// Check that a process is pinned to a single CPU and that CPU matches "cpu".
bool affinity_is_single_cpu(pid_t pid, int cpu, std::string* error) {
  cpu_set_t set;
  CPU_ZERO(&set);
  if (sched_getaffinity(pid, sizeof(set), &set) != 0) {
    if (error) {
      *error = std::strerror(errno);
    }
    return false;
  }
  if (!CPU_ISSET(cpu, &set)) {
    return false;
  }
  int count = 0;
  for (int i = 0; i < CPU_SETSIZE; ++i) {
    if (CPU_ISSET(i, &set)) {
      ++count;
    }
  }
  if (count != 1) {
    if (error) {
      *error = "affinity mask contains multiple CPUs";
    }
    return false;
  }
  return true;
}
#endif

bool smoke_pin_affinity(int argc, char** argv) {
#if !defined(__linux__)
  // Pinning is only supported on Linux, so skip elsewhere.
  (void)argc;
  (void)argv;
  return true;
#else
  if (argc < 1) {
    std::cerr << "pin test requires bench executable path\n";
    return false;
  }

  const std::filesystem::path bench_path(argv[0]);
  if (!std::filesystem::exists(bench_path)) {
    std::cerr << "bench executable not found: " << bench_path << "\n";
    return false;
  }

  std::string error;
  const int cpu = first_allowed_cpu(&error);
  if (cpu < 0) {
    std::cerr << "failed to pick cpu: " << error << "\n";
    return false;
  }

  std::filesystem::path out_dir;
  if (!make_out_dir(&out_dir, &error)) {
    std::cerr << "failed to create temp dir: " << error << "\n";
    return false;
  }

  // Use a large iteration count so the process stays alive while we inspect
  // its affinity from the parent.
  const std::vector<std::string> args = {
      bench_path.string(),
      "--case",
      "noop",
      "--iters",
      "10000000",
      "--warmup",
      "0",
      "--out",
      out_dir.string(),
      "--pin",
      std::to_string(cpu),
  };

  std::vector<char*> exec_argv;
  exec_argv.reserve(args.size() + 1);
  for (const auto& arg : args) {
    exec_argv.push_back(const_cast<char*>(arg.c_str()));
  }
  exec_argv.push_back(nullptr);

  const pid_t pid = fork();
  if (pid == 0) {
    // In the child, replace the process with the bench executable.
    execv(exec_argv[0], exec_argv.data());
    std::perror("execv");
    std::_Exit(127);
  }
  if (pid < 0) {
    std::cerr << "failed to fork\n";
    return false;
  }

  // Poll for a short time to allow the child to start and apply its pinning.
  bool matched = false;
  std::string last_error;
  for (int attempt = 0; attempt < 50; ++attempt) {
    int status = 0;
    const pid_t done = waitpid(pid, &status, WNOHANG);
    if (done == pid) {
      std::cerr << "bench exited before affinity check\n";
      return false;
    }

    std::string affinity_error;
    if (affinity_is_single_cpu(pid, cpu, &affinity_error)) {
      matched = true;
      break;
    }
    if (!affinity_error.empty()) {
      last_error = affinity_error;
    }
    usleep(10000);
  }

  // Wait for the bench run to complete and clean up outputs.
  int status = 0;
  if (waitpid(pid, &status, 0) != pid) {
    std::cerr << "failed waiting for bench process\n";
    return false;
  }

  const auto meta_path = out_dir / "meta.json";
  std::string meta_contents;
  if (!read_file_contents(meta_path, &meta_contents, &error)) {
    std::cerr << "missing meta.json at " << meta_path << "\n";
    return false;
  }
  if (meta_contents.find("\"pinned_cpu\"") == std::string::npos) {
    std::cerr << "meta.json missing pinned_cpu\n";
    return false;
  }

  std::error_code ec;
  std::filesystem::remove_all(out_dir, ec);

  if (!matched) {
    if (!last_error.empty()) {
      std::cerr << "affinity check failed: " << last_error << "\n";
    } else {
      std::cerr << "affinity check failed: timed out\n";
    }
    return false;
  }

  if (!(WIFEXITED(status) && WEXITSTATUS(status) == 0)) {
    std::cerr << "bench exited with failure\n";
    return false;
  }

  return true;
#endif
}

}  // namespace

int main(int argc, char** argv) {
  const std::vector<TestCase> cases = {
      {"noop_smoke", smoke_noop},
      {"pin_affinity", smoke_pin_affinity},
  };

  return run_named_tests(cases, argc, argv);
}
