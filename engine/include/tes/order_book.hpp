#pragma once

#include <algorithm>
#include <functional>
#include <list>
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
    struct PriceLevel { Price price; Qty qty; };
    struct Depth { std::vector<PriceLevel> bids; std::vector<PriceLevel> asks; };
    struct FillResult { OrderId maker_id; Price price; Qty qty; };

    [[nodiscard]] std::vector<Event> add_limit_order(const Order& order) {
        if (!is_valid_price(order.price) || !is_valid_qty(order.qty) || order_index.contains(order.id)) return {};
        const std::optional<Price> previous_best_bid = best_bid();
        const std::optional<Price> previous_best_ask = best_ask();

        if (order.side == Side::Bid) {
            auto [level_it, _] = bids.try_emplace(order.price);
            Level& level = level_it->second;
            level.aggregate_qty.value += order.qty.value;
            auto order_it = level.orders.insert(level.orders.end(), order);
            order_index[order.id] = IndexEntry{Side::Bid, order.price, order_it};
        } else {
            auto [level_it, _] = asks.try_emplace(order.price);
            Level& level = level_it->second;
            level.aggregate_qty.value += order.qty.value;
            auto order_it = level.orders.insert(level.orders.end(), order);
            order_index[order.id] = IndexEntry{Side::Ask, order.price, order_it};
        }

        std::vector<Event> events;
        events.reserve(2);
        events.emplace_back(OrderAccepted{order.id, order.side, order.price, order.qty});
        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
        return events;
    }

    [[nodiscard]] std::vector<Event> cancel(OrderId id) {
        const auto index_it = order_index.find(id);
        if (index_it == order_index.end()) return {};

        const std::optional<Price> previous_best_bid = best_bid();
        const std::optional<Price> previous_best_ask = best_ask();
        erase_by_index(index_it->second);
        order_index.erase(index_it);

        std::vector<Event> events;
        events.reserve(2);
        events.emplace_back(OrderCanceled{id});
        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
        return events;
    }

    [[nodiscard]] std::optional<Price> best_bid() const { return bids.empty() ? std::nullopt : std::optional<Price>{bids.begin()->first}; }
    [[nodiscard]] std::optional<Price> best_ask() const { return asks.empty() ? std::nullopt : std::optional<Price>{asks.begin()->first}; }

    [[nodiscard]] std::optional<Order> front_of_level(Side side, Price price) const {
        const auto* levels = side == Side::Bid ? &bids : nullptr;
        if (levels != nullptr) {
            const auto it = levels->find(price);
            if (it == levels->end() || it->second.orders.empty()) return std::nullopt;
            return it->second.orders.front();
        }
        const auto it = asks.find(price);
        if (it == asks.end() || it->second.orders.empty()) return std::nullopt;
        return it->second.orders.front();
    }

    [[nodiscard]] std::size_t level_size(Side side, Price price) const {
        if (side == Side::Bid) { const auto it = bids.find(price); return it == bids.end() ? 0U : it->second.orders.size(); }
        const auto it = asks.find(price); return it == asks.end() ? 0U : it->second.orders.size();
    }

    [[nodiscard]] std::optional<Order> find_order(OrderId id) const {
        const auto index_it = order_index.find(id);
        return index_it == order_index.end() ? std::nullopt : std::optional<Order>{*index_it->second.order_it};
    }

    [[nodiscard]] std::optional<FillResult> fill_best(Side side, Qty qty) {
        if (!is_valid_qty(qty)) return std::nullopt;
        return side == Side::Bid ? fill_best_from_levels(bids, qty) : fill_best_from_levels(asks, qty);
    }

    [[nodiscard]] bool validate_invariants() const {
        std::size_t total_live_orders = 0;
        const auto validate_side = [this, &total_live_orders](const auto& levels, Side side) {
            for (auto level_it = levels.begin(); level_it != levels.end(); ++level_it) {
                const auto& [price, level] = *level_it;
                if (level.orders.empty()) return false;
                Qty aggregate{0};
                for (auto order_it = level.orders.begin(); order_it != level.orders.end(); ++order_it) {
                    aggregate.value += order_it->qty.value;
                    ++total_live_orders;
                    const auto idx = order_index.find(order_it->id);
                    if (idx == order_index.end()) return false;
                    if (idx->second.side != side || idx->second.price != price) return false;
                    if (idx->second.order_it != order_it) return false;
                }
                if (aggregate.value != level.aggregate_qty.value) return false;
            }
            return true;
        };
        if (!validate_side(bids, Side::Bid) || !validate_side(asks, Side::Ask)) return false;
        return order_index.size() == total_live_orders;
    }

    [[nodiscard]] Qty executable_qty(Side taker_side, Price limit_price) const {
        Qty available{0};
        if (taker_side == Side::Bid) { for (const auto& [price, level] : asks) { if (price.ticks > limit_price.ticks) break; available.value += level.aggregate_qty.value; } return available; }
        for (const auto& [price, level] : bids) { if (price.ticks < limit_price.ticks) break; available.value += level.aggregate_qty.value; }
        return available;
    }

    [[nodiscard]] Depth depth(std::size_t levels) const {
        Depth snapshot; if (levels == 0) return snapshot;
        snapshot.bids.reserve(std::min(levels, bids.size())); snapshot.asks.reserve(std::min(levels, asks.size()));
        append_levels(snapshot.bids, bids, levels); append_levels(snapshot.asks, asks, levels); return snapshot;
    }

  private:
    struct Level { Qty aggregate_qty{0}; std::list<Order> orders; };
    using BidLevels = std::map<Price, Level, std::greater<Price>>;
    using AskLevels = std::map<Price, Level>;

    struct IndexEntry {
        Side side;
        Price price;
        std::list<Order>::iterator order_it;
    };

    template <typename PriceLevels>
    static void append_levels(std::vector<PriceLevel>& out, const PriceLevels& levels, std::size_t limit) {
        std::size_t count = 0; for (const auto& [price, level] : levels) { if (count >= limit) break; out.push_back(PriceLevel{price, level.aggregate_qty}); ++count; }
    }

    void erase_by_index(IndexEntry& entry) {
        if (entry.side == Side::Bid) {
            auto level_it = bids.find(entry.price);
            if (level_it == bids.end()) return;
            Level& level = level_it->second;
            level.aggregate_qty.value -= entry.order_it->qty.value;
            level.orders.erase(entry.order_it);
            if (level.orders.empty()) bids.erase(level_it);
        } else {
            auto level_it = asks.find(entry.price);
            if (level_it == asks.end()) return;
            Level& level = level_it->second;
            level.aggregate_qty.value -= entry.order_it->qty.value;
            level.orders.erase(entry.order_it);
            if (level.orders.empty()) asks.erase(level_it);
        }
    }

    template <typename PriceLevels>
    std::optional<FillResult> fill_best_from_levels(PriceLevels& levels, Qty qty) {
        if (levels.empty()) return std::nullopt;
        auto level_it = levels.begin();
        Level& level = level_it->second;
        if (level.orders.empty()) return std::nullopt;
        auto maker_it = level.orders.begin();
        const Qty traded{std::min(qty.value, maker_it->qty.value)};
        maker_it->qty.value -= traded.value;
        level.aggregate_qty.value -= traded.value;

        const FillResult result{maker_it->id, maker_it->price, traded};
        if (maker_it->qty.value == 0) {
            order_index.erase(maker_it->id);
            level.orders.erase(maker_it);
            if (level.orders.empty()) levels.erase(level_it);
        }
        return result;
    }

    void maybe_emit_top_of_book_change(std::vector<Event>& events, const std::optional<Price>& previous_best_bid, const std::optional<Price>& previous_best_ask) {
        const std::optional<Price> current_best_bid = best_bid(); const std::optional<Price> current_best_ask = best_ask();
        if (previous_best_bid != current_best_bid || previous_best_ask != current_best_ask) events.emplace_back(TopOfBook{current_best_bid, current_best_ask});
    }

    BidLevels bids;
    AskLevels asks;
    std::unordered_map<OrderId, IndexEntry> order_index;
};

}  // namespace tes
