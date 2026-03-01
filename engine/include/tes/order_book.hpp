#pragma once

#include <algorithm>
#include <deque>
#include <functional>
#include <map>
#include <optional>
#include <unordered_map>
#include <utility>
#include <vector>

#include <tes/events.hpp>
#include <tes/order.hpp>

namespace tes {

class OrderBook {
  public:
    struct FillResult {
        OrderId maker_id;
        Price price;
        Qty qty;
    };

    [[nodiscard]] std::vector<Event> add_limit_order(const Order& order) {
        if (!is_valid_price(order.price) || !is_valid_qty(order.qty)) {
            return {};
        }

        if (order_index.contains(order.id)) {
            return {};
        }

        const std::optional<Price> previous_best_bid = best_bid();
        const std::optional<Price> previous_best_ask = best_ask();

        if (order.side == Side::Bid) {
            bids[order.price].push_back(order);
        } else {
            asks[order.price].push_back(order);
        }
        order_index[order.id] = {order.side, order.price};

        std::vector<Event> events;
        events.emplace_back(OrderAccepted{order.id, order.side, order.price, order.qty});

        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
        return events;
    }

    [[nodiscard]] std::vector<Event> cancel(OrderId id) {
        const auto index_it = order_index.find(id);
        if (index_it == order_index.end()) {
            return {};
        }

        const std::optional<Price> previous_best_bid = best_bid();
        const std::optional<Price> previous_best_ask = best_ask();

        const Side side = index_it->second.first;
        const Price price = index_it->second.second;

        if (side == Side::Bid) {
            erase_from_levels(bids, id, price);
        } else {
            erase_from_levels(asks, id, price);
        }

        order_index.erase(index_it);

        std::vector<Event> events;
        events.emplace_back(OrderCanceled{id});

        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
        return events;
    }

    [[nodiscard]] std::optional<Price> best_bid() const {
        if (bids.empty()) {
            return std::nullopt;
        }
        return bids.begin()->first;
    }

    [[nodiscard]] std::optional<Price> best_ask() const {
        if (asks.empty()) {
            return std::nullopt;
        }
        return asks.begin()->first;
    }

    [[nodiscard]] std::optional<Order> front_of_level(Side side, Price price) const {
        if (side == Side::Bid) {
            const auto it = bids.find(price);
            if (it == bids.end() || it->second.empty()) {
                return std::nullopt;
            }
            return it->second.front();
        }

        const auto it = asks.find(price);
        if (it == asks.end() || it->second.empty()) {
            return std::nullopt;
        }
        return it->second.front();
    }

    [[nodiscard]] std::size_t level_size(Side side, Price price) const {
        if (side == Side::Bid) {
            const auto it = bids.find(price);
            return it == bids.end() ? 0U : it->second.size();
        }

        const auto it = asks.find(price);
        return it == asks.end() ? 0U : it->second.size();
    }

    [[nodiscard]] std::optional<FillResult> fill_best(Side side, Qty qty) {
        if (!is_valid_qty(qty)) {
            return std::nullopt;
        }

        if (side == Side::Bid) {
            return fill_best_from_levels(bids, qty);
        }

        return fill_best_from_levels(asks, qty);
    }

  private:
    template <typename PriceLevels>
    static void erase_from_levels(PriceLevels& levels, OrderId id, Price price) {
        auto level_it = levels.find(price);
        if (level_it == levels.end()) {
            return;
        }

        auto& level_orders = level_it->second;
        const auto order_it = std::find_if(level_orders.begin(), level_orders.end(), [id](const Order& order) {
            return order.id == id;
        });

        if (order_it == level_orders.end()) {
            return;
        }

        level_orders.erase(order_it);
        if (level_orders.empty()) {
            levels.erase(level_it);
        }
    }

    template <typename PriceLevels>
    std::optional<FillResult> fill_best_from_levels(PriceLevels& levels, Qty qty) {
        if (levels.empty()) {
            return std::nullopt;
        }

        auto level_it = levels.begin();
        auto& level_orders = level_it->second;
        if (level_orders.empty()) {
            return std::nullopt;
        }

        Order& maker = level_orders.front();
        const Qty traded{std::min(qty.value, maker.qty.value)};
        maker.qty.value -= traded.value;

        const FillResult result{maker.id, maker.price, traded};

        if (maker.qty.value == 0) {
            order_index.erase(maker.id);
            level_orders.pop_front();
            if (level_orders.empty()) {
                levels.erase(level_it);
            }
        }

        return result;
    }

    [[nodiscard]] static bool prices_equal(const std::optional<Price>& lhs, const std::optional<Price>& rhs) {
        return lhs == rhs;
    }

    void maybe_emit_top_of_book_change(std::vector<Event>& events, const std::optional<Price>& previous_best_bid,
                                       const std::optional<Price>& previous_best_ask) {
        const std::optional<Price> current_best_bid = best_bid();
        const std::optional<Price> current_best_ask = best_ask();

        if (!prices_equal(previous_best_bid, current_best_bid) || !prices_equal(previous_best_ask, current_best_ask)) {
            events.emplace_back(TopOfBook{current_best_bid, current_best_ask});
        }
    }

    std::map<Price, std::deque<Order>, std::greater<Price>> bids;
    std::map<Price, std::deque<Order>> asks;
    std::unordered_map<OrderId, std::pair<Side, Price>> order_index;
};

}  // namespace tes
