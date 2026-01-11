#pragma once

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

inline bool write_raw_csv(const std::string& path,
                          const std::vector<uint64_t>& samples) {
  // Write to a temp file and rename to avoid partially-written outputs.
  // If the process crashes mid-write, we either keep the old file or have
  // a complete new file, never a truncated CSV.
  const std::string tmp_path = path + ".tmp";
  std::ofstream out(tmp_path, std::ios::out | std::ios::trunc);
  if (!out.is_open()) {
    return false;
  }

  out << "iter,ns\n";
  for (size_t i = 0; i < samples.size(); ++i) {
    out << i << "," << samples[i] << "\n";
  }
  out.flush();
  if (!out.good()) {
    std::remove(tmp_path.c_str());
    return false;
  }
  out.close();

  if (std::rename(tmp_path.c_str(), path.c_str()) != 0) {
    std::remove(path.c_str());
    if (std::rename(tmp_path.c_str(), path.c_str()) != 0) {
      std::remove(tmp_path.c_str());
      return false;
    }
  }

  return true;
}
