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
    InsufficientCash,
    InsufficientPosition,
    WrongAccount,
    InsufficientBuyingPower,
    ShortSellingDisabled,
    MarginRequirementFailed,
    MaintenanceMarginBreached,
};

struct OrderAccepted {
    OrderId id;
    Side side;
    Price price;
    Qty qty;
    Symbol symbol{kDefaultSymbol};
};

struct OrderRejected {
    Side side;
    Price price;
    Qty qty;
    RejectReason reason;
    Symbol symbol{kDefaultSymbol};
};

struct OrderCanceled {
    OrderId id;
    Symbol symbol{kDefaultSymbol};
};

struct CancelRejected {
    OrderId id;
    RejectReason reason;
    Symbol symbol{kDefaultSymbol};
};

struct TradeExecuted {
    OrderId taker_id;
    OrderId maker_id;
    Side taker_side;
    Price price;
    Qty qty;
    Symbol symbol{kDefaultSymbol};
};

struct OrderPartiallyFilled {
    OrderId id;
    Qty last_fill_qty;
    Qty remaining_qty;
    Symbol symbol{kDefaultSymbol};
};

struct OrderFilled {
    OrderId id;
    Qty last_fill_qty;
    Symbol symbol{kDefaultSymbol};
};

struct OrderExpired {
    OrderId id;
    Symbol symbol{kDefaultSymbol};
};

struct StopOrderAccepted {
    OrderId id;
    Side side;
    Price stop_price;
    Qty qty;
    std::optional<Price> limit_price;
    Symbol symbol{kDefaultSymbol};
};

struct StopOrderTriggered {
    OrderId id;
    OrderId resulting_order_id;
    Side side;
    Price stop_price;
    Qty qty;
    std::optional<Price> limit_price;
    Symbol symbol{kDefaultSymbol};
};

struct TopOfBook {
    std::optional<Price> best_bid;
    std::optional<Price> best_ask;
    Symbol symbol{kDefaultSymbol};
};

struct AuctionStarted {
    Symbol symbol{kDefaultSymbol};
    TradingPhase phase{TradingPhase::OpeningAuction};
    [[nodiscard]] bool operator==(const AuctionStarted&) const = default;
};

struct AuctionEnded {
    Symbol symbol{kDefaultSymbol};
    TradingPhase phase{TradingPhase::Continuous};
    [[nodiscard]] bool operator==(const AuctionEnded&) const = default;
};

struct AuctionUncross {
    Symbol symbol{kDefaultSymbol};
    Price price{};
    Qty qty{};
    std::int64_t imbalance{0};
    [[nodiscard]] bool operator==(const AuctionUncross&) const = default;
};

struct IndicativePriceUpdated {
    Symbol symbol{kDefaultSymbol};
    std::optional<Price> price;
    Qty qty{};
    std::int64_t imbalance{0};
    [[nodiscard]] bool operator==(const IndicativePriceUpdated&) const = default;
};

using Event = std::variant<OrderAccepted, OrderRejected, OrderCanceled, CancelRejected, TradeExecuted, OrderPartiallyFilled,
                           OrderFilled, OrderExpired, StopOrderAccepted, StopOrderTriggered, TopOfBook, AuctionStarted,
                           AuctionEnded, AuctionUncross, IndicativePriceUpdated>;

}  // namespace tes
