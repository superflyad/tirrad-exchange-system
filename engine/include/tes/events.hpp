#pragma once

#include <optional>
#include <variant>

#include <tes/types.hpp>

namespace tes {

enum class RejectReason {
    InvalidPrice,
    InvalidQuantity,
    UnknownOrderId,
    NoLiquidity,
};

struct OrderAccepted {
    OrderId id;
    Side side;
    Price price;
    Qty qty;
};

struct OrderRejected {
    Side side;
    Price price;
    Qty qty;
    RejectReason reason;
};

struct OrderCanceled {
    OrderId id;
};

struct CancelRejected {
    OrderId id;
    RejectReason reason;
};

struct TradeExecuted {
    OrderId taker_id;
    OrderId maker_id;
    Side taker_side;
    Price price;
    Qty qty;
};

struct OrderPartiallyFilled {
    OrderId id;
    Qty last_fill_qty;
    Qty remaining_qty;
};

struct OrderFilled {
    OrderId id;
    Qty last_fill_qty;
};

struct OrderExpired {
    OrderId id;
};

struct TopOfBook {
    std::optional<Price> best_bid;
    std::optional<Price> best_ask;
};

using Event = std::variant<OrderAccepted, OrderRejected, OrderCanceled, CancelRejected, TradeExecuted, OrderPartiallyFilled,
                           OrderFilled, OrderExpired, TopOfBook>;

}  // namespace tes
