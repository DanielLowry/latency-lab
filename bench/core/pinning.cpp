#include "pinning.h"

#include <cerrno>
#include <cstring>

#if defined(__linux__)
#include <sched.h>
#endif

bool pin_to_cpu(int cpu, std::string* error) {
#if defined(__linux__)
  // Validate against the build-time CPU bitmap size.
  if (cpu < 0) {
    if (error) {
      *error = "cpu index must be >= 0";
    }
    return false;
  }
  if (cpu >= CPU_SETSIZE) {
    if (error) {
      *error = "cpu index is out of range for this build";
    }
    return false;
  }

  // Apply affinity to the current thread/process.
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(cpu, &set);
  if (sched_setaffinity(0, sizeof(set), &set) != 0) {
    if (error) {
      *error = std::strerror(errno);
    }
    return false;
  }

  return true;
#else
  if (error) {
    *error = "cpu pinning is only supported on Linux";
  }
  return false;
#endif
}
