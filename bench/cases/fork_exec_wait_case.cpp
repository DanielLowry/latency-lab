#include "case.h"
#include "registry.h"

#if !defined(__linux__)
static_assert(false, "fork_exec_wait is supported only on Linux.");
#else

#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {

std::string g_child_exec_path;

std::string find_child_exec_path(std::string* error) {
  const char* override_path = std::getenv("LATENCY_LAB_CHILD_EXEC");
  if (override_path && *override_path) {
    const std::filesystem::path candidate(override_path);
    std::error_code exists_ec; 
    if (std::filesystem::exists(candidate, exists_ec) && !exists_ec) {
      return candidate.string();
    }
    if (error) {
      *error =
          "LATENCY_LAB_CHILD_EXEC was set but does not exist: " +
          candidate.string();
    }
    return "";
  }


  // Find the location of the current executable, and use the path to find child_exec
  std::string current_exe_loc;
  current_exe_loc.resize(4096);
  const ssize_t len = readlink("/proc/self/exe", current_exe_loc.data(), current_exe_loc.size());
  if (len <= 0) {
    if (error) {
      *error = "failed to resolve /proc/self/exe; set LATENCY_LAB_CHILD_EXEC";
    }
    return "";
  }  
  current_exe_loc.resize(static_cast<size_t>(len));

  // Given the parent path, find the child_exec
  const std::filesystem::path exe_path(current_exe_loc);
  const std::filesystem::path candidate = exe_path.parent_path() / "child_exec";
  std::error_code exists_ec;
  if (std::filesystem::exists(candidate, exists_ec) && !exists_ec) {
    return candidate.string();
  }
  if (error) {
    *error = "child_exec not found next to bench: " + candidate.string() +
             " (set LATENCY_LAB_CHILD_EXEC to override)";
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
    // Child process
    char* const argv[] = {const_cast<char*>(g_child_exec_path.c_str()), nullptr};
    execv(g_child_exec_path.c_str(), argv);
    _exit(127);
  }

  if (pid < 0) {
    // Failed to launch child
    return;
  }

  // Parent
  int status = 0;
  while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {
  }
}

const Case kForkExecWaitCase{
    "fork_exec_wait",
    "Forks, execs the tiny child_exec binary, then waits for completion.",
    fork_exec_setup,
    fork_exec_wait_run_once,
    nullptr,
};

}  // namespace

LATENCY_LAB_REGISTER_CASE(kForkExecWaitCase);
#endif
