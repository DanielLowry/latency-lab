#include "meta.h"

#include "build_info.h"

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <thread>

#if defined(__unix__) || defined(__APPLE__)
#include <sys/utsname.h>
#include <unistd.h>
#endif

namespace {

std::string trim_copy(const std::string& text) {
  const auto start = text.find_first_not_of(" \t");
  if (start == std::string::npos) {
    return "";
  }
  const auto end = text.find_last_not_of(" \t");
  return text.substr(start, end - start + 1);
}

std::string read_cpu_model() {
  std::ifstream in("/proc/cpuinfo");
  if (!in.is_open()) {
    return "unknown";
  }
  std::string line;
  while (std::getline(in, line)) {
    const auto colon = line.find(':');
    if (colon == std::string::npos) {
      continue;
    }
    const std::string key = trim_copy(line.substr(0, colon));
    if (key == "model name" || key == "Hardware" || key == "Processor" ||
        key == "Model") {
      const std::string value = trim_copy(line.substr(colon + 1));
      if (!value.empty()) {
        return value;
      }
    }
  }
  return "unknown";
}

uint32_t read_cpu_cores() {
  uint32_t cores = 0;
#if defined(_SC_NPROCESSORS_ONLN)
  const long count = sysconf(_SC_NPROCESSORS_ONLN);
  if (count > 0) {
    cores = static_cast<uint32_t>(count);
  }
#endif
  if (cores == 0) {
    const unsigned int fallback = std::thread::hardware_concurrency();
    if (fallback > 0) {
      cores = static_cast<uint32_t>(fallback);
    }
  }
  return cores;
}

std::string read_kernel_version() {
#if defined(__unix__) || defined(__APPLE__)
  struct utsname info;
  if (uname(&info) == 0) {
    return info.release;
  }
#endif
  return "unknown";
}

std::string compiler_version() {
#if defined(__clang__)
  return std::string("clang ") + __clang_version__;
#elif defined(__GNUC__)
  return std::string("gcc ") + __VERSION__;
#elif defined(_MSC_VER)
  return std::string("msvc ") + std::to_string(_MSC_VER);
#else
  return "unknown";
#endif
}

std::string build_flags() {
#if defined(LATENCY_LAB_BUILD_FLAGS) && defined(LATENCY_LAB_BUILD_TYPE)
  std::string flags = LATENCY_LAB_BUILD_FLAGS;
  std::string type = LATENCY_LAB_BUILD_TYPE;
  if (!type.empty() && type != "unknown") {
    if (!flags.empty()) {
      return type + " " + flags;
    }
    return type;
  }
  if (!flags.empty()) {
    return flags;
  }
#endif
  return "unknown";
}

std::string json_escape(const std::string& text) {
  std::ostringstream out;
  for (unsigned char ch : text) {
    switch (ch) {
      case '"':
        out << "\\\"";
        break;
      case '\\':
        out << "\\\\";
        break;
      case '\b':
        out << "\\b";
        break;
      case '\f':
        out << "\\f";
        break;
      case '\n':
        out << "\\n";
        break;
      case '\r':
        out << "\\r";
        break;
      case '\t':
        out << "\\t";
        break;
      default:
        if (ch < 0x20) {
          static const char kHex[] = "0123456789abcdef";
          out << "\\u00" << kHex[(ch >> 4) & 0x0f] << kHex[ch & 0x0f];
        } else {
          out << ch;
        }
    }
  }
  return out.str();
}

bool write_text_atomic(const std::string& path,
                       const std::string& contents,
                       std::string* error) {
  const std::string tmp_path = path + ".tmp";
  std::ofstream out(tmp_path, std::ios::out | std::ios::trunc);
  if (!out.is_open()) {
    if (error) {
      *error = std::strerror(errno);
    }
    return false;
  }
  out << contents;
  out.flush();
  if (!out.good()) {
    if (error) {
      *error = "failed to write file";
    }
    std::remove(tmp_path.c_str());
    return false;
  }
  out.close();

  if (std::rename(tmp_path.c_str(), path.c_str()) != 0) {
    std::remove(path.c_str());
    if (std::rename(tmp_path.c_str(), path.c_str()) != 0) {
      if (error) {
        *error = std::strerror(errno);
      }
      std::remove(tmp_path.c_str());
      return false;
    }
  }
  return true;
}

std::string quote_arg(const std::string& arg) {
  if (arg.empty()) {
    return "\"\"";
  }
  const auto needs_quotes = arg.find_first_of(" \t\"\\") != std::string::npos;
  if (!needs_quotes) {
    return arg;
  }
  std::string out;
  out.reserve(arg.size() + 2);
  out.push_back('"');
  for (char ch : arg) {
    if (ch == '"' || ch == '\\') {
      out.push_back('\\');
    }
    out.push_back(ch);
  }
  out.push_back('"');
  return out;
}

}  // namespace

RunMetadata collect_system_metadata() {
  RunMetadata meta;
  meta.cpu_model = read_cpu_model();
  meta.cpu_cores = read_cpu_cores();
  meta.kernel_version = read_kernel_version();
  meta.compiler_version = compiler_version();
  meta.build_flags = build_flags();
  return meta;
}

std::string format_command_line(int argc, char** argv) {
  std::ostringstream out;
  for (int i = 0; i < argc; ++i) {
    if (i > 0) {
      out << ' ';
    }
    out << quote_arg(argv[i] ? argv[i] : "");
  }
  return out.str();
}

bool write_meta_json(const std::string& path,
                     const RunMetadata& meta,
                     std::string* error) {
  std::ostringstream out;
  out << "{\n";
  out << "  \"cpu_model\": \"" << json_escape(meta.cpu_model) << "\",\n";
  out << "  \"cpu_cores\": " << meta.cpu_cores << ",\n";
  out << "  \"kernel_version\": \"" << json_escape(meta.kernel_version) << "\",\n";
  out << "  \"command_line\": \"" << json_escape(meta.command_line) << "\",\n";
  out << "  \"compiler_version\": \""
      << json_escape(meta.compiler_version) << "\",\n";
  out << "  \"build_flags\": \"" << json_escape(meta.build_flags) << "\",\n";
  out << "  \"pinning\": " << (meta.pinning ? "true" : "false") << ",\n";
  if (meta.pinning) {
    out << "  \"pinned_cpu\": " << meta.pinned_cpu << ",\n";
  }
  out << "  \"tags\": [";
  for (size_t i = 0; i < meta.tags.size(); ++i) {
    if (i > 0) {
      out << ", ";
    }
    out << "\"" << json_escape(meta.tags[i]) << "\"";
  }
  out << "]\n";
  out << "}\n";

  return write_text_atomic(path, out.str(), error);
}
