#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct RunMetadata {
  std::string cpu_model;
  uint32_t cpu_cores = 0;
  std::string kernel_version;
  std::string command_line;
  std::string compiler_version;
  std::string build_flags;
  bool pinning = false;
  int pinned_cpu = -1;
  std::vector<std::string> tags;
};

RunMetadata collect_system_metadata();
std::string format_command_line(int argc, char** argv);
bool write_meta_json(const std::string& path,
                     const RunMetadata& meta,
                     std::string* error);
