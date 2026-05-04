#include <tes/matching_engine.hpp>

#include <cassert>
#include <algorithm>
#include <optional>
#include <vector>

#include <tes/order.hpp>

namespace tes {

std::vector<Event> MatchingEngine::place_limit_order(Side side, Price price, Qty qty, TimeInForce tif) {
    const OrderId taker_id = next_order_id_;
    ++next_order_id_;
    std::vector<Event> events = place_limit_order_with_id(taker_id, side, price, qty, tif);
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::place_limit_order_with_id(OrderId taker_id, Side side, Price price, Qty qty,
                                                              TimeInForce tif) {
    if (!is_valid_price(price)) {
        return {OrderRejected{side, price, qty, RejectReason::InvalidPrice}};
    }

    if (!is_valid_qty(qty)) {
        return {OrderRejected{side, price, qty, RejectReason::InvalidQuantity}};
    }

    std::vector<Event> events;
    if (tif == TimeInForce::Fok) {
        const Qty available = book_.executable_qty(side, price);
        if (available.value < qty.value) {
            events.emplace_back(OrderExpired{taker_id});
            return events;
        }
    }

    Qty remaining = qty;

    while (remaining.value > 0) {
        const std::optional<Price> previous_best_bid = book_.best_bid();
        const std::optional<Price> previous_best_ask = book_.best_ask();

        if (side == Side::Bid) {
            const std::optional<Price> best_ask = book_.best_ask();
            if (!best_ask.has_value() || best_ask->ticks > price.ticks) {
                break;
            }

            const auto fill = book_.fill_best(Side::Ask, remaining);
            if (!fill.has_value()) {
                break;
            }

            remaining.value -= fill->qty.value;
            events.emplace_back(TradeExecuted{taker_id, fill->maker_id, side, fill->price, fill->qty});
            if (remaining.value > 0) {
                events.emplace_back(OrderPartiallyFilled{taker_id, fill->qty, Qty{remaining.value}});
            } else {
                events.emplace_back(OrderFilled{taker_id, fill->qty});
            }
            maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
            continue;
        }

        const std::optional<Price> best_bid = book_.best_bid();
        if (!best_bid.has_value() || best_bid->ticks < price.ticks) {
            break;
        }

        const auto fill = book_.fill_best(Side::Bid, remaining);
        if (!fill.has_value()) {
            break;
        }

        remaining.value -= fill->qty.value;
        events.emplace_back(TradeExecuted{taker_id, fill->maker_id, side, fill->price, fill->qty});
        if (remaining.value > 0) {
            events.emplace_back(OrderPartiallyFilled{taker_id, fill->qty, Qty{remaining.value}});
        } else {
            events.emplace_back(OrderFilled{taker_id, fill->qty});
        }
        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
    }

    if (remaining.value > 0) {
        if (tif == TimeInForce::Ioc) {
            events.emplace_back(OrderExpired{taker_id});
        } else {
            const std::vector<Event> rest_events =
                book_.add_limit_order(Order{taker_id, side, price, Qty{remaining.value}});
            events.insert(events.end(), rest_events.begin(), rest_events.end());
        }
    }

    return events;
}

std::vector<Event> MatchingEngine::place_market_order(Side side, Qty qty) {
    if (!is_valid_qty(qty)) {
        return {OrderRejected{side, Price{0}, qty, RejectReason::InvalidQuantity}};
    }

    const std::optional<Price> best_opposite = side == Side::Bid ? book_.best_ask() : book_.best_bid();
    if (!best_opposite.has_value()) {
        return {OrderRejected{side, Price{0}, qty, RejectReason::NoLiquidity}};
    }

    const OrderId taker_id = next_order_id_;
    ++next_order_id_;

    std::vector<Event> events;
    Qty remaining = qty;

    while (remaining.value > 0) {
        const std::optional<Price> previous_best_bid = book_.best_bid();
        const std::optional<Price> previous_best_ask = book_.best_ask();
        const auto fill = book_.fill_best(side == Side::Bid ? Side::Ask : Side::Bid, remaining);
        if (!fill.has_value()) {
            break;
        }

        remaining.value -= fill->qty.value;
        events.emplace_back(TradeExecuted{taker_id, fill->maker_id, side, fill->price, fill->qty});
        if (remaining.value > 0) {
            events.emplace_back(OrderPartiallyFilled{taker_id, fill->qty, Qty{remaining.value}});
        } else {
            events.emplace_back(OrderFilled{taker_id, fill->qty});
        }
        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
    }

    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::cancel(OrderId id) {
    const auto lifecycle_it = lifecycle_state_by_id_.find(id);
    if (lifecycle_it != lifecycle_state_by_id_.end() &&
        lifecycle_it->second != OrderLifecycleState::Accepted &&
        lifecycle_it->second != OrderLifecycleState::PartiallyFilled) {
        return {CancelRejected{id, RejectReason::UnknownOrderId}};
    }

    const std::vector<Event> events = book_.cancel(id);
    if (events.empty()) {
        return {CancelRejected{id, RejectReason::UnknownOrderId}};
    }
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::replace_order(OrderId id, Price new_price, Qty new_qty) {
    const auto lifecycle_it = lifecycle_state_by_id_.find(id);
    if (lifecycle_it != lifecycle_state_by_id_.end() &&
        lifecycle_it->second != OrderLifecycleState::Accepted &&
        lifecycle_it->second != OrderLifecycleState::PartiallyFilled) {
        return {CancelRejected{id, RejectReason::UnknownOrderId}};
    }

    const std::optional<Order> existing = book_.find_order(id);
    if (!existing.has_value()) {
        return {CancelRejected{id, RejectReason::UnknownOrderId}};
    }
    if (!is_valid_price(new_price)) {
        return {OrderRejected{existing->side, new_price, new_qty, RejectReason::InvalidPrice}};
    }
    if (!is_valid_qty(new_qty)) {
        return {OrderRejected{existing->side, new_price, new_qty, RejectReason::InvalidQuantity}};
    }

    std::vector<Event> events = book_.cancel(id);
    track_events(events);
    std::vector<Event> placement = place_limit_order_with_id(id, existing->side, new_price, new_qty, TimeInForce::Gtc);
    events.insert(events.end(), placement.begin(), placement.end());
    track_events(placement);
    return events;
}

BookDepth MatchingEngine::depth(std::size_t levels) const {
    const OrderBook::Depth snapshot = book_.depth(levels);

    BookDepth result;
    result.bids.reserve(snapshot.bids.size());
    result.asks.reserve(snapshot.asks.size());

    for (const OrderBook::PriceLevel& level : snapshot.bids) {
        result.bids.push_back(PriceLevel{level.price, level.qty});
    }

    for (const OrderBook::PriceLevel& level : snapshot.asks) {
        result.asks.push_back(PriceLevel{level.price, level.qty});
    }

    return result;
}

void MatchingEngine::maybe_emit_top_of_book_change(std::vector<Event>& events, const std::optional<Price>& previous_best_bid,
                                                   const std::optional<Price>& previous_best_ask) {
    const std::optional<Price> current_best_bid = book_.best_bid();
    const std::optional<Price> current_best_ask = book_.best_ask();

    if (previous_best_bid != current_best_bid || previous_best_ask != current_best_ask) {
        events.emplace_back(TopOfBook{current_best_bid, current_best_ask});
    }
}

void MatchingEngine::track_events(const std::vector<Event>& events) {
    for (const Event& event : events) {
        std::visit(
            [this](const auto& evt) {
                using T = std::decay_t<decltype(evt)>;
                if constexpr (std::is_same_v<T, OrderAccepted>) {
                    const auto it = lifecycle_state_by_id_.find(evt.id);
                    if (it == lifecycle_state_by_id_.end()) {
                        lifecycle_state_by_id_.emplace(evt.id, OrderLifecycleState::Accepted);
                    } else {
                        assert(it->second == OrderLifecycleState::PartiallyFilled ||
                               it->second == OrderLifecycleState::Canceled);
                        it->second = OrderLifecycleState::Accepted;
                    }
                } else if constexpr (std::is_same_v<T, OrderPartiallyFilled>) {
                    auto [it, inserted] =
                        lifecycle_state_by_id_.try_emplace(evt.id, OrderLifecycleState::Accepted);
                    (void)inserted;
                    assert(it->second == OrderLifecycleState::Accepted ||
                           it->second == OrderLifecycleState::PartiallyFilled);
                    it->second = OrderLifecycleState::PartiallyFilled;
                } else if constexpr (std::is_same_v<T, OrderFilled>) {
                    auto [it, inserted] =
                        lifecycle_state_by_id_.try_emplace(evt.id, OrderLifecycleState::Accepted);
                    (void)inserted;
                    assert(it->second == OrderLifecycleState::Accepted ||
                           it->second == OrderLifecycleState::PartiallyFilled ||
                           it->second == OrderLifecycleState::Canceled);
                    it->second = OrderLifecycleState::Filled;
                } else if constexpr (std::is_same_v<T, OrderCanceled>) {
                    auto it = lifecycle_state_by_id_.find(evt.id);
                    assert(it != lifecycle_state_by_id_.end());
                    assert(it->second == OrderLifecycleState::Accepted ||
                           it->second == OrderLifecycleState::PartiallyFilled);
                    it->second = OrderLifecycleState::Canceled;
                }
            },
            event);
    }
}

}  // namespace tes
