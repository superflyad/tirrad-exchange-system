#pragma once

#include <optional>
#include <variant>

#include <tes/types.hpp>

namespace tes {

struct OrderAccepted {
    OrderId id;
    Side side;
    Price price;
    Qty qty;
};

struct OrderCanceled {
    OrderId id;
};

struct TradeExecuted {
    OrderId taker_id;
    OrderId maker_id;
    Side taker_side;
    Price price;
    Qty qty;
};

struct TopOfBook {
    std::optional<Price> best_bid;
    std::optional<Price> best_ask;
};

using Event = std::variant<OrderAccepted, OrderCanceled, TradeExecuted, TopOfBook>;

}  // namespace tes
