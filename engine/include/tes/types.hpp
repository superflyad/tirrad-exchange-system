#pragma once

#include <compare>
#include <cstdint>
#include <string>

namespace tes {

using OrderId = std::uint64_t;
using AccountId = std::uint64_t;
using Symbol = std::string;

inline constexpr const char* kDefaultSymbol = "DEFAULT";

enum class Side { Bid, Ask };
enum class OrderType { Limit, Market, StopMarket, StopLimit };
enum class TimeInForce { Gtc, Ioc, Fok };

struct Price {
    std::int64_t ticks;

    [[nodiscard]] constexpr auto operator<=>(const Price&) const = default;
};

struct Qty {
    std::int64_t value;
};

[[nodiscard]] constexpr bool is_valid_price(Price price) {
    return price.ticks >= 0;
}

[[nodiscard]] constexpr bool is_valid_qty(Qty qty) {
    return qty.value > 0;
}

}  // namespace tes
