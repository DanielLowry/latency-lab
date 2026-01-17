#include "case.h"
#include "registry.h"

#if defined(__unix__) || defined(__APPLE__)
#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>
#endif

namespace {

#if defined(__unix__) || defined(__APPLE__)
std::string g_child_exec_path;

std::string find_child_exec_path(std::string* error) {
  std::vector<std::filesystem::path> candidates;
#if defined(__linux__)
  char buffer[4096];
  const ssize_t len = readlink("/proc/self/exe", buffer, sizeof(buffer) - 1);
  if (len > 0) {
    buffer[len] = '\0';
    const std::filesystem::path exe_path(buffer);
    candidates.push_back(exe_path.parent_path() / "child_exec");
  }
#endif
  std::error_code ec;
  const auto cwd = std::filesystem::current_path(ec);
  if (!ec) {
    candidates.push_back(cwd / "child_exec");
  }

  for (const auto& candidate : candidates) {
    std::error_code exists_ec;
    if (std::filesystem::exists(candidate, exists_ec) && !exists_ec) {
      return candidate.string();
    }
  }

  if (error) {
    std::string message = "child_exec not found. Looked in:";
    for (const auto& candidate : candidates) {
      message += " " + candidate.string();
    }
    *error = message;
  }
  return "";
}

void fork_exec_setup(Ctx*) {
  std::string error;
  g_child_exec_path = find_child_exec_path(&error);
  if (g_child_exec_path.empty()) {
    std::cerr << error << "\n";
    std::exit(1);
  }
}

void fork_exec_wait_run_once(Ctx*) {
  const pid_t pid = fork();
  if (pid == 0) {
    char* const argv[] = {const_cast<char*>(g_child_exec_path.c_str()), nullptr};
    execv(g_child_exec_path.c_str(), argv);
    _exit(127);
  }
  if (pid < 0) {
    return;
  }
  int status = 0;
  while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {
  }
}

const Case kForkExecWaitCase{
    "fork_exec_wait",
    fork_exec_setup,
    fork_exec_wait_run_once,
    nullptr,
};
#endif

}  // namespace

#if defined(__unix__) || defined(__APPLE__)
LATENCY_LAB_REGISTER_CASE(kForkExecWaitCase);
#endif
