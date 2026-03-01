#include <tes/version.hpp>

namespace tes {

std::string version_string() {
    return std::to_string(TES_VERSION_MAJOR) + "." +
           std::to_string(TES_VERSION_MINOR) + "." +
           std::to_string(TES_VERSION_PATCH);
}

}  // namespace tes
