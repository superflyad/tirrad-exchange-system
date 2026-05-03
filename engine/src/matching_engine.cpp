#include <tes/matching_engine.hpp>

#include <algorithm>
#include <optional>
#include <vector>

#include <tes/order.hpp>

namespace tes {

std::vector<Event> MatchingEngine::place_limit_order(Side side, Price price, Qty qty) {
    if (!is_valid_price(price)) {
        return {OrderRejected{side, price, qty, RejectReason::InvalidPrice}};
    }

    if (!is_valid_qty(qty)) {
        return {OrderRejected{side, price, qty, RejectReason::InvalidQuantity}};
    }

    const OrderId taker_id = next_order_id_;
    ++next_order_id_;

    std::vector<Event> events;
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
        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
    }

    if (remaining.value > 0) {
        const std::vector<Event> rest_events =
            book_.add_limit_order(Order{taker_id, side, price, Qty{remaining.value}});
        events.insert(events.end(), rest_events.begin(), rest_events.end());
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
        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
    }

    return events;
}

std::vector<Event> MatchingEngine::cancel(OrderId id) {
    const std::vector<Event> events = book_.cancel(id);
    if (events.empty()) {
        return {CancelRejected{id, RejectReason::UnknownOrderId}};
    }
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

}  // namespace tes
