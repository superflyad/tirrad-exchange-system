#pragma once

#include <string>

#define TES_VERSION_MAJOR 0
#define TES_VERSION_MINOR 1
#define TES_VERSION_PATCH 0

namespace tes {

[[nodiscard]] std::string version_string();

}  // namespace tes
