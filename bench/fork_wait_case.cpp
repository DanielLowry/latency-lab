#include "case.h"
#include "registry.h"

#if defined(__unix__) || defined(__APPLE__)
#include <cerrno>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace {

#if defined(__unix__) || defined(__APPLE__)
void fork_wait_run_once(Ctx*) {
  const pid_t pid = fork();
  if (pid == 0) {
    _exit(0);
  }
  if (pid < 0) {
    return;
  }
  int status = 0;
  while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {
  }
}

const Case kForkWaitCase{
    "fork_wait",
    nullptr,
    fork_wait_run_once,
    nullptr,
};
#endif

}  // namespace

#if defined(__unix__) || defined(__APPLE__)
LATENCY_LAB_REGISTER_CASE(kForkWaitCase);
#endif
