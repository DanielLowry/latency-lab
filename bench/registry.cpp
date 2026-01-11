#include "registry.h"

namespace {

std::vector<const Case*>& registry_storage() {
  static std::vector<const Case*> registry;
  return registry;
}

}  // namespace

void register_case(const Case& bench_case) {
  registry_storage().push_back(&bench_case);
}

const std::vector<const Case*>& cases() {
  return registry_storage();
}

const Case* find_case(const std::string& name) {
  for (const Case* bench_case : registry_storage()) {
    if (bench_case && bench_case->name && name == bench_case->name) {
      return bench_case;
    }
  }
  return nullptr;
}
