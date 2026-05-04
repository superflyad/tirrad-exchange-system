#pragma once

#include <unordered_map>
#include <vector>

#include <tes/events.hpp>
#include <tes/order_book.hpp>
#include <tes/types.hpp>

namespace tes {

struct PriceLevel {
    Price price;
    Qty qty;
};

struct BookDepth {
    std::vector<PriceLevel> bids;
    std::vector<PriceLevel> asks;
};

class MatchingEngine {
  public:
    [[nodiscard]] std::vector<Event> place_limit_order(Side side, Price price, Qty qty,
                                                       TimeInForce time_in_force = TimeInForce::Gtc);
    [[nodiscard]] std::vector<Event> place_market_order(Side side, Qty qty);
    [[nodiscard]] std::vector<Event> cancel(OrderId id);
    [[nodiscard]] std::vector<Event> replace_order(OrderId id, Price new_price, Qty new_qty);
    [[nodiscard]] BookDepth depth(std::size_t levels) const;

    [[nodiscard]] const OrderBook& book() const {
        return book_;
    }

  private:
    enum class OrderLifecycleState { Accepted, PartiallyFilled, Filled, Canceled };

    [[nodiscard]] std::vector<Event> place_limit_order_with_id(OrderId taker_id, Side side, Price price, Qty qty,
                                                               TimeInForce tif);
    void maybe_emit_top_of_book_change(std::vector<Event>& events, const std::optional<Price>& previous_best_bid,
                                       const std::optional<Price>& previous_best_ask);
    void track_events(const std::vector<Event>& events);

    OrderBook book_;
    OrderId next_order_id_ = 1;
    std::unordered_map<OrderId, OrderLifecycleState> lifecycle_state_by_id_;
};

}  // namespace tes
