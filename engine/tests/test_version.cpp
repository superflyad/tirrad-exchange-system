#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest.h>

#include <tes/version.hpp>

TEST_CASE("tes::version_string contains major version") {
    const std::string version = tes::version_string();

    CHECK(version.find(std::to_string(TES_VERSION_MAJOR)) != std::string::npos);
}
