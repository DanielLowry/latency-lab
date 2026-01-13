#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <ctime>

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

std::string next_out_dir_name() {
  static unsigned int counter = 0;
  const auto now = static_cast<unsigned long long>(std::time(nullptr));
  return "run_" + std::to_string(now) + "_" + std::to_string(counter++);
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::cerr << "usage: smoke_tests <bench_exe>\n";
    return 1;
  }

  const std::filesystem::path bench_path(argv[1]);
  if (!std::filesystem::exists(bench_path)) {
    std::cerr << "bench executable not found: " << bench_path << "\n";
    return 1;
  }

  const auto tmp_base =
      std::filesystem::temp_directory_path() / "latency_lab_smoke";
  const auto out_dir = tmp_base / next_out_dir_name();
  std::error_code ec;
  std::filesystem::create_directories(out_dir, ec);
  if (ec) {
    std::cerr << "failed to create temp dir: " << ec.message() << "\n";
    return 1;
  }

  const std::string cmd = "\"" + bench_path.string() +
                          "\" --case noop --iters 1 --warmup 0 --out \"" +
                          out_dir.string() + "\"";
  if (std::system(cmd.c_str()) != 0) {
    std::cerr << "bench invocation failed: " << cmd << "\n";
    return 1;
  }

  const auto csv_path = out_dir / "raw.csv";
  std::ifstream in(csv_path);
  if (!in.is_open()) {
    std::cerr << "missing raw.csv at " << csv_path << "\n";
    return 1;
  }

  std::string header;
  if (!std::getline(in, header)) {
    std::cerr << "raw.csv is empty\n";
    return 1;
  }
  if (header != "iter,ns") {
    std::cerr << "unexpected CSV header: " << header << "\n";
    return 1;
  }

  std::string line;
  if (!std::getline(in, line)) {
    std::cerr << "raw.csv missing data row\n";
    return 1;
  }
  const auto comma = line.find(',');
  if (comma == std::string::npos) {
    std::cerr << "raw.csv row missing comma: " << line << "\n";
    return 1;
  }
  const std::string iter_text = line.substr(0, comma);
  const std::string ns_text = line.substr(comma + 1);
  uint64_t iter = 0;
  uint64_t ns = 0;
  if (!parse_u64(iter_text, &iter) || !parse_u64(ns_text, &ns)) {
    std::cerr << "raw.csv row not numeric: " << line << "\n";
    return 1;
  }

  std::filesystem::remove_all(out_dir, ec);

  std::cout << "smoke_tests: ok\n";
  return 0;
}
