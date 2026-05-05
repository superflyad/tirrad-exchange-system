#include <tes/matching_engine.hpp>

#include <algorithm>
#include <cassert>
#include <limits>
#include <optional>
#include <vector>

#include <tes/order.hpp>

namespace tes {
namespace {
constexpr AccountId kDefaultAccountId = 0;
constexpr std::int64_t kDefaultLegacyCash = std::numeric_limits<std::int64_t>::max() / 4;
constexpr std::int64_t kDefaultLegacyPosition = std::numeric_limits<std::int64_t>::max() / 4;
}


void MatchingEngine::set_account_state(AccountId account_id, std::int64_t cash_balance, std::int64_t position_qty) {
    accounts_[account_id] = AccountSnapshot{cash_balance, position_qty, 0, 0};
}

MatchingEngine::AccountSnapshot MatchingEngine::account_snapshot(AccountId account_id) const {
    const auto it = accounts_.find(account_id);
    return it == accounts_.end() ? AccountSnapshot{} : it->second;
}

std::optional<AccountId> MatchingEngine::order_owner(OrderId id) const {
    const auto it = order_owner_by_id_.find(id);
    return it == order_owner_by_id_.end() ? std::nullopt : std::optional<AccountId>{it->second};
}

std::vector<Event> MatchingEngine::place_limit_order(Side side, Price price, Qty qty, TimeInForce tif) { return place_limit_order(kDefaultAccountId, side, price, qty, tif); }

std::vector<Event> MatchingEngine::place_limit_order(AccountId account_id, Side side, Price price, Qty qty, TimeInForce tif) {
    const OrderId taker_id = next_order_id_++;
    std::vector<Event> events = place_limit_order_with_account_and_id(account_id, taker_id, side, price, qty, tif);
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::place_limit_order_with_id(OrderId taker_id, Side side, Price price, Qty qty, TimeInForce tif) {
    return place_limit_order_with_account_and_id(kDefaultAccountId, taker_id, side, price, qty, tif);
}

std::vector<Event> MatchingEngine::place_limit_order_with_account_and_id(AccountId account_id, OrderId taker_id, Side side, Price price, Qty qty, TimeInForce tif) {
    if (!is_valid_price(price)) return {OrderRejected{side, price, qty, RejectReason::InvalidPrice}};
    if (!is_valid_qty(qty)) return {OrderRejected{side, price, qty, RejectReason::InvalidQuantity}};

    AccountSnapshot& taker = accounts_[account_id];
    if (account_id == kDefaultAccountId && taker.cash_balance == 0 && taker.position_qty == 0 && taker.reserved_cash == 0 &&
        taker.reserved_qty == 0) {
        taker.cash_balance = kDefaultLegacyCash;
        taker.position_qty = kDefaultLegacyPosition;
    }
    const std::int64_t notional = price.ticks * qty.value;
    if (side == Side::Bid && taker.cash_balance - taker.reserved_cash < notional) return {OrderRejected{side, price, qty, RejectReason::InsufficientCash}};
    if (side == Side::Ask && taker.position_qty - taker.reserved_qty < qty.value) return {OrderRejected{side, price, qty, RejectReason::InsufficientPosition}};

    std::vector<Event> events;
    if (tif == TimeInForce::Fok && book_.executable_qty(side, price).value < qty.value) {
        events.emplace_back(OrderExpired{taker_id});
        return events;
    }

    Qty remaining = qty;
    while (remaining.value > 0) {
        const std::optional<Price> previous_best_bid = book_.best_bid();
        const std::optional<Price> previous_best_ask = book_.best_ask();
        if (side == Side::Bid) {
            const auto best_ask = book_.best_ask();
            if (!best_ask.has_value() || best_ask->ticks > price.ticks) break;
            const auto fill = book_.fill_best(Side::Ask, remaining);
            if (!fill.has_value()) break;
            remaining.value -= fill->qty.value;
            events.emplace_back(TradeExecuted{taker_id, fill->maker_id, side, fill->price, fill->qty});
            AccountSnapshot& maker = accounts_[order_owner_by_id_[fill->maker_id]];
            const std::int64_t trade_notional = fill->price.ticks * fill->qty.value;
            taker.cash_balance -= trade_notional; taker.position_qty += fill->qty.value;
            maker.cash_balance += trade_notional; maker.position_qty -= fill->qty.value; maker.reserved_qty -= fill->qty.value;
            if (remaining.value > 0) events.emplace_back(OrderPartiallyFilled{taker_id, fill->qty, Qty{remaining.value}}); else events.emplace_back(OrderFilled{taker_id, fill->qty});
            maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
            continue;
        }
        const auto best_bid = book_.best_bid();
        if (!best_bid.has_value() || best_bid->ticks < price.ticks) break;
        const auto fill = book_.fill_best(Side::Bid, remaining);
        if (!fill.has_value()) break;
        remaining.value -= fill->qty.value;
        events.emplace_back(TradeExecuted{taker_id, fill->maker_id, side, fill->price, fill->qty});
        AccountSnapshot& maker = accounts_[order_owner_by_id_[fill->maker_id]];
        const std::int64_t trade_notional = fill->price.ticks * fill->qty.value;
        taker.cash_balance += trade_notional; taker.position_qty -= fill->qty.value;
        maker.cash_balance -= trade_notional; maker.position_qty += fill->qty.value; maker.reserved_cash -= trade_notional;
        if (remaining.value > 0) events.emplace_back(OrderPartiallyFilled{taker_id, fill->qty, Qty{remaining.value}}); else events.emplace_back(OrderFilled{taker_id, fill->qty});
        maybe_emit_top_of_book_change(events, previous_best_bid, previous_best_ask);
    }

    if (remaining.value > 0) {
        if (tif == TimeInForce::Ioc) {
            events.emplace_back(OrderExpired{taker_id});
        } else {
            const std::vector<Event> rest_events = book_.add_limit_order(Order{taker_id, side, price, Qty{remaining.value}});
            order_owner_by_id_[taker_id] = account_id;
            if (side == Side::Bid) { const std::int64_t reserve = price.ticks * remaining.value; taker.reserved_cash += reserve; reserved_cash_by_order_id_[taker_id] = reserve; }
            else { taker.reserved_qty += remaining.value; reserved_qty_by_order_id_[taker_id] = remaining.value; }
            events.insert(events.end(), rest_events.begin(), rest_events.end());
        }
    }
    return events;
}

std::vector<Event> MatchingEngine::place_market_order(Side side, Qty qty) { return place_market_order(kDefaultAccountId, side, qty); }
std::vector<Event> MatchingEngine::place_market_order(AccountId account_id, Side side, Qty qty) {
    std::vector<Event> events =
        place_limit_order(account_id, side, side == Side::Bid ? Price{INT64_MAX / 4} : Price{0}, qty, TimeInForce::Ioc);
    const bool has_trade = std::any_of(events.begin(), events.end(), [](const Event& event) { return std::holds_alternative<TradeExecuted>(event); });
    if (!has_trade && events.size() == 1 && std::holds_alternative<OrderExpired>(events.front())) {
        events.front() = OrderRejected{side, Price{0}, qty, RejectReason::NoLiquidity};
    }
    return events;
}

std::vector<Event> MatchingEngine::cancel(OrderId id) { return cancel(kDefaultAccountId, id); }
std::vector<Event> MatchingEngine::cancel(AccountId account_id, OrderId id) {
    const auto owner = order_owner_by_id_.find(id);
    if (owner != order_owner_by_id_.end() && owner->second != account_id) return {CancelRejected{id, RejectReason::WrongAccount}};
    std::vector<Event> events = book_.cancel(id);
    if (events.empty()) return {CancelRejected{id, RejectReason::UnknownOrderId}};
    auto& acct = accounts_[owner == order_owner_by_id_.end() ? account_id : owner->second];
    if (auto it = reserved_cash_by_order_id_.find(id); it != reserved_cash_by_order_id_.end()) { acct.reserved_cash -= it->second; reserved_cash_by_order_id_.erase(it); }
    if (auto it = reserved_qty_by_order_id_.find(id); it != reserved_qty_by_order_id_.end()) { acct.reserved_qty -= it->second; reserved_qty_by_order_id_.erase(it); }
    order_owner_by_id_.erase(id);
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::replace_order(OrderId id, Price new_price, Qty new_qty) { return replace_order(kDefaultAccountId, id, new_price, new_qty); }
std::vector<Event> MatchingEngine::replace_order(AccountId account_id, OrderId id, Price new_price, Qty new_qty) {
    const auto existing = book_.find_order(id);
    if (!existing.has_value()) return {CancelRejected{id, RejectReason::UnknownOrderId}};
    const auto owner = order_owner_by_id_.find(id);
    if (owner != order_owner_by_id_.end() && owner->second != account_id) return {CancelRejected{id, RejectReason::WrongAccount}};
    if (!is_valid_price(new_price)) return {OrderRejected{existing->side, new_price, new_qty, RejectReason::InvalidPrice}};
    if (!is_valid_qty(new_qty)) return {OrderRejected{existing->side, new_price, new_qty, RejectReason::InvalidQuantity}};
    std::vector<Event> events = cancel(account_id, id);
    std::vector<Event> placement = place_limit_order_with_account_and_id(account_id, id, existing->side, new_price, new_qty, TimeInForce::Gtc);
    events.insert(events.end(), placement.begin(), placement.end());
    track_events(placement);
    return events;
}

BookDepth MatchingEngine::depth(std::size_t levels) const { const OrderBook::Depth snapshot = book_.depth(levels); BookDepth result; for (const auto& l : snapshot.bids) result.bids.push_back({l.price,l.qty}); for (const auto& l : snapshot.asks) result.asks.push_back({l.price,l.qty}); return result; }

void MatchingEngine::maybe_emit_top_of_book_change(std::vector<Event>& events, const std::optional<Price>& previous_best_bid, const std::optional<Price>& previous_best_ask) { const auto current_best_bid = book_.best_bid(); const auto current_best_ask = book_.best_ask(); if (previous_best_bid != current_best_bid || previous_best_ask != current_best_ask) events.emplace_back(TopOfBook{current_best_bid, current_best_ask}); }

void MatchingEngine::track_events(const std::vector<Event>& events) { for (const Event& event : events) { std::visit([this](const auto& evt) { using T = std::decay_t<decltype(evt)>; if constexpr (std::is_same_v<T, OrderAccepted>) lifecycle_state_by_id_[evt.id] = OrderLifecycleState::Accepted; else if constexpr (std::is_same_v<T, OrderPartiallyFilled>) lifecycle_state_by_id_[evt.id] = OrderLifecycleState::PartiallyFilled; else if constexpr (std::is_same_v<T, OrderFilled>) lifecycle_state_by_id_[evt.id] = OrderLifecycleState::Filled; else if constexpr (std::is_same_v<T, OrderCanceled>) lifecycle_state_by_id_[evt.id] = OrderLifecycleState::Canceled; }, event);} }

}  // namespace tes
