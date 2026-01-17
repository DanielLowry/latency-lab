#include "run_utils.h"

#include <filesystem>

const Case* resolve_case(const std::string& name) {
  if (!name.empty()) {
    return find_case(name);
  }
  if (const Case* noop_case = find_case("noop")) {
    return noop_case;
  }
  const auto& all_cases = cases();
  if (!all_cases.empty()) {
    return all_cases.front();
  }
  return nullptr;
}

std::string resolve_output_path(const CliOptions& options) {
  if (!options.out_dir.empty()) {
    const std::filesystem::path out_dir(options.out_dir);
    // Keep filenames consistent; out_dir controls placement only.
    return (out_dir / "raw.csv").string();
  }
  return options.out_path;
}

std::string resolve_meta_path(const CliOptions& options) {
  if (options.out_dir.empty()) {
    return "";
  }
  const std::filesystem::path out_dir(options.out_dir);
  return (out_dir / "meta.json").string();
}

std::string resolve_stdout_path(const CliOptions& options) {
  if (options.out_dir.empty()) {
    return "";
  }
  const std::filesystem::path out_dir(options.out_dir);
  return (out_dir / "stdout.txt").string();
}
