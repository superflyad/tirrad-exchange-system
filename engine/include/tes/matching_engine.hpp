#pragma once

#include <vector>

#include <tes/events.hpp>
#include <tes/order_book.hpp>
#include <tes/types.hpp>

namespace tes {

class MatchingEngine {
  public:
    [[nodiscard]] std::vector<Event> place_limit_order(Side side, Price price, Qty qty);
    [[nodiscard]] std::vector<Event> cancel(OrderId id);

    [[nodiscard]] const OrderBook& book() const {
        return book_;
    }

  private:
    void maybe_emit_top_of_book_change(std::vector<Event>& events, const std::optional<Price>& previous_best_bid,
                                       const std::optional<Price>& previous_best_ask);

    OrderBook book_;
    OrderId next_order_id_ = 1;
};

}  // namespace tes
