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
    struct FillResult {
        OrderId maker_id;
        Price price;
        Qty qty;
        Qty maker_remaining_qty{0};
        OrderVisibility maker_visibility{OrderVisibility::Displayed};
        bool maker_filled{false};
        std::optional<IcebergReplenished> replenished;
    };

    [[nodiscard]] std::vector<Event> add_limit_order(const Order& order) { return add_order(order, OrderVisibility::Displayed); }

    [[nodiscard]] std::vector<Event> add_hidden_order(const Order& order) { return add_order(order, OrderVisibility::Hidden); }

    [[nodiscard]] std::vector<Event> add_iceberg_order(const Order& order) { return add_order(order, OrderVisibility::Iceberg); }

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

    [[nodiscard]] std::optional<Price> best_bid() const { return best_displayed_price(bids); }
    [[nodiscard]] std::optional<Price> best_ask() const { return best_displayed_price(asks); }

    [[nodiscard]] std::optional<Price> best_match_price(Side taker_side, Price limit_price) const {
        if (taker_side == Side::Bid) return best_match_price_from_levels(asks, taker_side, limit_price);
        return best_match_price_from_levels(bids, taker_side, limit_price);
    }

    [[nodiscard]] std::optional<Order> front_of_level(Side side, Price price) const {
        const Level* level = find_level(side, price);
        if (level == nullptr) return std::nullopt;
        if (!level->displayed_orders.empty()) return level->displayed_orders.front();
        if (!level->iceberg_orders.empty()) return level->iceberg_orders.front();
        if (!level->hidden_orders.empty()) return level->hidden_orders.front();
        return std::nullopt;
    }

    [[nodiscard]] std::size_t level_size(Side side, Price price) const {
        const Level* level = find_level(side, price);
        return level == nullptr ? 0U : level->displayed_orders.size() + level->iceberg_orders.size() + level->hidden_orders.size();
    }

    [[nodiscard]] std::optional<Order> find_order(OrderId id) const {
        const auto index_it = order_index.find(id);
        return index_it == order_index.end() ? std::nullopt : std::optional<Order>{*index_it->second.order_it};
    }

    [[nodiscard]] std::optional<FillResult> fill_best(Side side, Qty qty) {
        if (!is_valid_qty(qty)) return std::nullopt;
        return side == Side::Bid ? fill_best_from_levels(bids, qty) : fill_best_from_levels(asks, qty);
    }

    [[nodiscard]] std::optional<FillResult> fill_best_at_or_better(Side side, Price auction_price, Qty qty) {
        if (!is_valid_qty(qty)) return std::nullopt;
        if (side == Side::Bid) {
            auto it = first_match_at_or_better(bids, side, auction_price);
            if (it == bids.end()) return std::nullopt;
            return fill_from_level(bids, it, qty);
        }
        auto it = first_match_at_or_better(asks, side, auction_price);
        if (it == asks.end()) return std::nullopt;
        return fill_from_level(asks, it, qty);
    }

    [[nodiscard]] bool validate_invariants() const {
        std::size_t total_live_orders = 0;
        const auto validate_side = [this, &total_live_orders](const auto& levels, Side side) {
            for (auto level_it = levels.begin(); level_it != levels.end(); ++level_it) {
                const auto& [price, level] = *level_it;
                Qty aggregate{0};
                const auto validate_orders = [&](const std::list<Order>& orders) {
                    for (auto order_it = orders.begin(); order_it != orders.end(); ++order_it) {
                        aggregate.value += visible_qty(*order_it).value;
                        ++total_live_orders;
                        const auto idx = order_index.find(order_it->id);
                        if (idx == order_index.end()) return false;
                        if (idx->second.side != side || idx->second.price != price) return false;
                    }
                    return true;
                };
                if (!validate_orders(level.displayed_orders) || !validate_orders(level.iceberg_orders) || !validate_orders(level.hidden_orders)) return false;
                if (aggregate.value != level.aggregate_qty.value) return false;
                if (level.displayed_orders.empty() && level.iceberg_orders.empty() && level.hidden_orders.empty()) return false;
            }
            return true;
        };
        if (!validate_side(bids, Side::Bid) || !validate_side(asks, Side::Ask)) return false;
        return order_index.size() == total_live_orders;
    }

    [[nodiscard]] Qty executable_qty(Side taker_side, Price limit_price) const {
        Qty available{0};
        if (taker_side == Side::Bid) {
            for (const auto& [price, level] : asks) {
                if (price.ticks > limit_price.ticks) break;
                available.value += total_qty(level).value;
            }
        } else {
            for (const auto& [price, level] : bids) {
                if (price.ticks < limit_price.ticks) break;
                available.value += total_qty(level).value;
            }
        }
        return available;
    }

    [[nodiscard]] Depth depth(std::size_t levels) const {
        Depth snapshot; if (levels == 0) return snapshot;
        snapshot.bids.reserve(std::min(levels, bids.size())); snapshot.asks.reserve(std::min(levels, asks.size()));
        append_levels(snapshot.bids, bids, levels); append_levels(snapshot.asks, asks, levels); return snapshot;
    }

  private:
    struct Level { Qty aggregate_qty{0}; std::list<Order> displayed_orders; std::list<Order> iceberg_orders; std::list<Order> hidden_orders; };
    using BidLevels = std::map<Price, Level, std::greater<Price>>;
    using AskLevels = std::map<Price, Level>;

    enum class QueueKind { Displayed, Iceberg, Hidden };
    struct IndexEntry { Side side; Price price; QueueKind queue; std::list<Order>::iterator order_it; };

    [[nodiscard]] static Qty visible_qty(const Order& order) { return order.visibility == OrderVisibility::Hidden ? Qty{0} : order.qty; }
    [[nodiscard]] static Qty total_remaining_qty(const Order& order) { return Qty{order.qty.value + order.reserve_qty.value}; }
    [[nodiscard]] static Qty total_qty(const Level& level) {
        Qty out{0};
        for (const Order& order : level.displayed_orders) out.value += total_remaining_qty(order).value;
        for (const Order& order : level.iceberg_orders) out.value += total_remaining_qty(order).value;
        for (const Order& order : level.hidden_orders) out.value += total_remaining_qty(order).value;
        return out;
    }

    template <typename PriceLevels>
    [[nodiscard]] static std::optional<Price> best_displayed_price(const PriceLevels& levels) {
        for (const auto& [price, level] : levels) if (level.aggregate_qty.value > 0) return price;
        return std::nullopt;
    }

    template <typename PriceLevels>
    [[nodiscard]] std::optional<Price> best_match_price_from_levels(const PriceLevels& levels, Side taker_side, Price limit_price) const {
        for (const auto& [price, level] : levels) {
            const bool crosses = taker_side == Side::Bid ? price.ticks <= limit_price.ticks : price.ticks >= limit_price.ticks;
            if (!crosses) break;
            if (total_qty(level).value > 0) return price;
        }
        return std::nullopt;
    }

    [[nodiscard]] Level* find_level_mut(Side side, Price price) {
        if (side == Side::Bid) { auto it = bids.find(price); return it == bids.end() ? nullptr : &it->second; }
        auto it = asks.find(price); return it == asks.end() ? nullptr : &it->second;
    }
    [[nodiscard]] const Level* find_level(Side side, Price price) const {
        if (side == Side::Bid) { auto it = bids.find(price); return it == bids.end() ? nullptr : &it->second; }
        auto it = asks.find(price); return it == asks.end() ? nullptr : &it->second;
    }

    [[nodiscard]] std::vector<Event> add_order(Order order, OrderVisibility visibility) {
        if (!is_valid_price(order.price) || !is_valid_qty(order.qty) || order_index.contains(order.id)) return {};
        if (visibility == OrderVisibility::Iceberg && (!is_valid_qty(order.display_qty) || order.qty.value < order.display_qty.value)) return {};
        const std::optional<Price> previous_best_bid = best_bid();
        const std::optional<Price> previous_best_ask = best_ask();
        order.visibility = visibility;
        if (visibility == OrderVisibility::Displayed) {
            order.total_qty = order.qty; order.display_qty = order.qty; order.reserve_qty = Qty{0};
        } else if (visibility == OrderVisibility::Hidden) {
            order.total_qty = order.qty; order.display_qty = Qty{0}; order.reserve_qty = order.qty; order.qty = Qty{0};
        } else {
            order.total_qty = order.qty;
            const Qty visible{std::min(order.qty.value, order.display_qty.value)};
            order.reserve_qty = Qty{order.qty.value - visible.value};
            order.qty = visible;
        }

        Level& level = get_or_create_level(order.side, order.price);
        level.aggregate_qty.value += visible_qty(order).value;
        auto& queue = visibility == OrderVisibility::Displayed ? level.displayed_orders : visibility == OrderVisibility::Iceberg ? level.iceberg_orders : level.hidden_orders;
        const QueueKind kind = visibility == OrderVisibility::Displayed ? QueueKind::Displayed : visibility == OrderVisibility::Iceberg ? QueueKind::Iceberg : QueueKind::Hidden;
        auto order_it = queue.insert(queue.end(), order);
        order_index[order.id] = IndexEntry{order.side, order.price, kind, order_it};

        std::vector<Event> events;
        events.reserve(2);
        if (visibility == OrderVisibility::Displayed) events.emplace_back(OrderAccepted{order.id, order.side, order.price, order.qty});
        else if (visibility == OrderVisibility::Hidden) events.emplace_back(HiddenOrderAccepted{order.id, order.side, order.price, order.total_qty});
        else events.emplace_back(IcebergOrderAccepted{order.id, order.side, order.price, order.total_qty, order.display_qty, order.reserve_qty, order.qty});
        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
        return events;
    }

    [[nodiscard]] Level& get_or_create_level(Side side, Price price) {
        if (side == Side::Bid) return bids.try_emplace(price).first->second;
        return asks.try_emplace(price).first->second;
    }

    template <typename PriceLevels>
    static void append_levels(std::vector<PriceLevel>& out, const PriceLevels& levels, std::size_t limit) {
        std::size_t count = 0;
        for (const auto& [price, level] : levels) {
            if (count >= limit) break;
            if (level.aggregate_qty.value <= 0) continue;
            out.push_back(PriceLevel{price, level.aggregate_qty});
            ++count;
        }
    }

    void erase_by_index(IndexEntry& entry) {
        Level* level = find_level_mut(entry.side, entry.price);
        if (level == nullptr) return;
        level->aggregate_qty.value -= visible_qty(*entry.order_it).value;
        if (entry.queue == QueueKind::Displayed) level->displayed_orders.erase(entry.order_it);
        else if (entry.queue == QueueKind::Iceberg) level->iceberg_orders.erase(entry.order_it);
        else level->hidden_orders.erase(entry.order_it);
        erase_empty_level(entry.side, entry.price);
    }

    void erase_empty_level(Side side, Price price) {
        if (side == Side::Bid) {
            auto it = bids.find(price);
            if (it != bids.end() && it->second.displayed_orders.empty() && it->second.iceberg_orders.empty() && it->second.hidden_orders.empty()) bids.erase(it);
        } else {
            auto it = asks.find(price);
            if (it != asks.end() && it->second.displayed_orders.empty() && it->second.iceberg_orders.empty() && it->second.hidden_orders.empty()) asks.erase(it);
        }
    }

    template <typename PriceLevels>
    typename PriceLevels::iterator first_match_at_or_better(PriceLevels& levels, Side side, Price auction_price) {
        for (auto it = levels.begin(); it != levels.end(); ++it) {
            const bool ok = side == Side::Bid ? it->first.ticks >= auction_price.ticks : it->first.ticks <= auction_price.ticks;
            if (!ok) break;
            if (total_qty(it->second).value > 0) return it;
        }
        return levels.end();
    }

    template <typename PriceLevels>
    std::optional<FillResult> fill_best_from_levels(PriceLevels& levels, Qty qty) {
        if (levels.empty()) return std::nullopt;
        for (auto level_it = levels.begin(); level_it != levels.end(); ++level_it) {
            if (total_qty(level_it->second).value <= 0) continue;
            return fill_from_level(levels, level_it, qty);
        }
        return std::nullopt;
    }

    template <typename PriceLevels>
    std::optional<FillResult> fill_from_level(PriceLevels& levels, typename PriceLevels::iterator level_it, Qty qty) {
        Level& level = level_it->second;
        if (!level.displayed_orders.empty()) return fill_from_queue(levels, level_it, level.displayed_orders, QueueKind::Displayed, qty);
        if (!level.iceberg_orders.empty()) return fill_from_queue(levels, level_it, level.iceberg_orders, QueueKind::Iceberg, qty);
        if (!level.hidden_orders.empty()) return fill_from_queue(levels, level_it, level.hidden_orders, QueueKind::Hidden, qty);
        return std::nullopt;
    }

    template <typename PriceLevels>
    std::optional<FillResult> fill_from_queue(PriceLevels& levels, typename PriceLevels::iterator level_it, std::list<Order>& queue, QueueKind kind, Qty qty) {
        Level& level = level_it->second;
        auto maker_it = queue.begin();
        const Qty available = kind == QueueKind::Hidden ? maker_it->reserve_qty : maker_it->qty;
        const Qty traded{std::min(qty.value, available.value)};
        if (kind == QueueKind::Hidden) maker_it->reserve_qty.value -= traded.value;
        else { maker_it->qty.value -= traded.value; level.aggregate_qty.value -= traded.value; }

        FillResult result{maker_it->id, maker_it->price, traded, total_remaining_qty(*maker_it), maker_it->visibility, false, std::nullopt};
        if (total_remaining_qty(*maker_it).value == 0) {
            result.maker_filled = true;
            order_index.erase(maker_it->id);
            queue.erase(maker_it);
        } else if (kind == QueueKind::Iceberg && maker_it->qty.value == 0 && maker_it->reserve_qty.value > 0) {
            const Qty replenished{std::min(maker_it->display_qty.value, maker_it->reserve_qty.value)};
            maker_it->reserve_qty.value -= replenished.value;
            maker_it->qty = replenished;
            level.aggregate_qty.value += replenished.value;
            result.maker_remaining_qty = total_remaining_qty(*maker_it);
            result.replenished = IcebergReplenished{maker_it->id, maker_it->side, maker_it->price, replenished, maker_it->reserve_qty, result.maker_remaining_qty};
            Order moved = *maker_it;
            queue.erase(maker_it);
            auto new_it = queue.insert(queue.end(), moved);
            order_index[moved.id] = IndexEntry{moved.side, moved.price, QueueKind::Iceberg, new_it};
        }
        if (level.displayed_orders.empty() && level.iceberg_orders.empty() && level.hidden_orders.empty()) levels.erase(level_it);
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
