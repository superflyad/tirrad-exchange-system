#include <tes/matching_engine.hpp>

#include <algorithm>
#include <limits>

#include <tes/order.hpp>

namespace tes {
namespace {
constexpr AccountId kDefaultAccountId = 0;
constexpr std::int64_t kDefaultLegacyCash = std::numeric_limits<std::int64_t>::max() / 4;
constexpr std::int64_t kDefaultLegacyPosition = std::numeric_limits<std::int64_t>::max() / 4;

[[nodiscard]] bool crosses(Side side, Price limit_price, Price resting_price) {
    if (side == Side::Bid) {
        return resting_price.ticks <= limit_price.ticks;
    }
    return resting_price.ticks >= limit_price.ticks;
}
}  // namespace

void MatchingEngine::set_account_state(AccountId account_id, std::int64_t cash_balance, std::int64_t position_qty) {
    set_account_state(account_id, kDefaultSymbol, cash_balance, position_qty);
}

void MatchingEngine::set_account_state(AccountId account_id, const Symbol& symbol, std::int64_t cash_balance,
                                       std::int64_t position_qty) {
    auto& account = accounts_[account_id];
    account.cash_balance = cash_balance;
    account.position_qty_by_symbol[symbol] = position_qty;
}

MatchingEngine::AccountSnapshot MatchingEngine::account_snapshot(AccountId account_id) const {
    const auto it = accounts_.find(account_id);
    return it == accounts_.end() ? AccountSnapshot{} : it->second;
}

std::optional<AccountId> MatchingEngine::order_owner(OrderId id) const {
    const auto it = order_ownership_by_id_.find(id);
    if (it == order_ownership_by_id_.end()) {
        return std::nullopt;
    }
    return it->second.account_id;
}

OrderBook& MatchingEngine::book_for(const Symbol& symbol) {
    return books_[symbol];
}

const OrderBook* MatchingEngine::find_book(const Symbol& symbol) const {
    const auto it = books_.find(symbol);
    return it == books_.end() ? nullptr : &it->second;
}

const OrderBook& MatchingEngine::book() const {
    static const OrderBook empty_book;
    const OrderBook* default_book = find_book(kDefaultSymbol);
    return default_book == nullptr ? empty_book : *default_book;
}

std::vector<Event> MatchingEngine::place_limit_order(Side side, Price price, Qty qty, TimeInForce tif) {
    return place_limit_order(kDefaultAccountId, kDefaultSymbol, side, price, qty, tif);
}

std::vector<Event> MatchingEngine::place_limit_order(AccountId account_id, Side side, Price price, Qty qty,
                                                     TimeInForce tif) {
    return place_limit_order(account_id, kDefaultSymbol, side, price, qty, tif);
}

std::vector<Event> MatchingEngine::place_limit_order(AccountId account_id, const Symbol& symbol, Side side, Price price,
                                                     Qty qty, TimeInForce tif) {
    const OrderId id = next_order_id_++;
    std::vector<Event> events = place_limit_order_with_account_and_id(account_id, symbol, id, side, price, qty, tif);
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::place_limit_order_with_account_and_id(AccountId account_id, const Symbol& symbol,
                                                                         OrderId taker_id, Side side, Price price,
                                                                         Qty qty, TimeInForce tif) {
    if (!is_valid_price(price)) {
        return {OrderRejected{side, price, qty, RejectReason::InvalidPrice, symbol}};
    }
    if (!is_valid_qty(qty)) {
        return {OrderRejected{side, price, qty, RejectReason::InvalidQuantity, symbol}};
    }

    AccountSnapshot& taker = accounts_[account_id];
    if (account_id == kDefaultAccountId) {
        taker.cash_balance = std::max(taker.cash_balance, kDefaultLegacyCash);
        taker.position_qty_by_symbol[symbol] = std::max(taker.position_qty_by_symbol[symbol], kDefaultLegacyPosition);
    }

    const std::int64_t limit_notional = price.ticks * qty.value;
    if (side == Side::Bid && taker.cash_balance - taker.reserved_cash < limit_notional) {
        return {OrderRejected{side, price, qty, RejectReason::InsufficientCash, symbol}};
    }
    if (side == Side::Ask && taker.position_qty_by_symbol[symbol] - taker.reserved_qty_by_symbol[symbol] < qty.value) {
        return {OrderRejected{side, price, qty, RejectReason::InsufficientPosition, symbol}};
    }

    OrderBook& book = book_for(symbol);
    if (tif == TimeInForce::Fok && book.executable_qty(side, price).value < qty.value) {
        return {OrderExpired{taker_id, symbol}};
    }

    std::vector<Event> events;
    Qty remaining = qty;

    while (remaining.value > 0) {
        const std::optional<Price> resting_price = side == Side::Bid ? book.best_ask() : book.best_bid();
        if (!resting_price.has_value() || !crosses(side, price, *resting_price)) {
            break;
        }

        const std::optional<Price> previous_best_bid = book.best_bid();
        const std::optional<Price> previous_best_ask = book.best_ask();
        std::optional<OrderBook::FillResult> fill = book.fill_best(side == Side::Bid ? Side::Ask : Side::Bid, remaining);
        if (!fill.has_value()) {
            break;
        }

        const auto owner_it = order_ownership_by_id_.find(fill->maker_id);
        const AccountId maker_account_id = owner_it == order_ownership_by_id_.end() ? kDefaultAccountId : owner_it->second.account_id;
        AccountSnapshot& maker = accounts_[maker_account_id];
        const std::int64_t notional = fill->price.ticks * fill->qty.value;

        remaining.value -= fill->qty.value;
        events.emplace_back(TradeExecuted{taker_id, fill->maker_id, side, fill->price, fill->qty, symbol});

        if (side == Side::Bid) {
            taker.cash_balance -= notional;
            taker.position_qty_by_symbol[symbol] += fill->qty.value;
            maker.cash_balance += notional;
            maker.position_qty_by_symbol[symbol] -= fill->qty.value;
            maker.reserved_qty_by_symbol[symbol] -= fill->qty.value;
            if (auto reserve_it = reserved_qty_by_order_id_.find(fill->maker_id); reserve_it != reserved_qty_by_order_id_.end()) {
                reserve_it->second -= fill->qty.value;
                if (reserve_it->second == 0) {
                    reserved_qty_by_order_id_.erase(reserve_it);
                }
            }
        } else {
            taker.cash_balance += notional;
            taker.position_qty_by_symbol[symbol] -= fill->qty.value;
            maker.cash_balance -= notional;
            maker.position_qty_by_symbol[symbol] += fill->qty.value;
            maker.reserved_cash -= notional;
            if (auto reserve_it = reserved_cash_by_order_id_.find(fill->maker_id); reserve_it != reserved_cash_by_order_id_.end()) {
                reserve_it->second -= notional;
                if (reserve_it->second == 0) {
                    reserved_cash_by_order_id_.erase(reserve_it);
                }
            }
        }

        if (owner_it != order_ownership_by_id_.end()) {
            owner_it->second.qty.value -= fill->qty.value;
            if (owner_it->second.qty.value == 0) {
                order_ownership_by_id_.erase(owner_it);
            }
        }

        if (remaining.value > 0) {
            events.emplace_back(OrderPartiallyFilled{taker_id, fill->qty, remaining, symbol});
        } else {
            events.emplace_back(OrderFilled{taker_id, fill->qty, symbol});
        }
        maybe_emit_top_of_book_change(symbol, events, previous_best_bid, previous_best_ask);
    }

    if (remaining.value > 0) {
        if (tif == TimeInForce::Ioc) {
            events.emplace_back(OrderExpired{taker_id, symbol});
        } else {
            std::vector<Event> accepted_events = book.add_limit_order(Order{taker_id, side, price, remaining});
            for (Event& event : accepted_events) {
                if (std::holds_alternative<OrderAccepted>(event)) {
                    auto accepted = std::get<OrderAccepted>(event);
                    accepted.symbol = symbol;
                    event = accepted;
                } else if (std::holds_alternative<TopOfBook>(event)) {
                    auto top = std::get<TopOfBook>(event);
                    top.symbol = symbol;
                    event = top;
                }
            }

            order_ownership_by_id_[taker_id] = {account_id, symbol, side, price, remaining};
            if (side == Side::Bid) {
                const std::int64_t reserve = price.ticks * remaining.value;
                taker.reserved_cash += reserve;
                reserved_cash_by_order_id_[taker_id] = reserve;
            } else {
                taker.reserved_qty_by_symbol[symbol] += remaining.value;
                reserved_qty_by_order_id_[taker_id] = remaining.value;
            }
            events.insert(events.end(), accepted_events.begin(), accepted_events.end());
        }
    }

    return events;
}

std::vector<Event> MatchingEngine::place_market_order(Side side, Qty qty) {
    return place_market_order(kDefaultAccountId, kDefaultSymbol, side, qty);
}

std::vector<Event> MatchingEngine::place_market_order(AccountId account_id, Side side, Qty qty) {
    return place_market_order(account_id, kDefaultSymbol, side, qty);
}

std::vector<Event> MatchingEngine::place_market_order(AccountId account_id, const Symbol& symbol, Side side, Qty qty) {
    if (!is_valid_qty(qty)) {
        return {OrderRejected{side, Price{0}, qty, RejectReason::InvalidQuantity, symbol}};
    }
    const OrderBook* book = find_book(symbol);
    const bool has_liquidity = book != nullptr && (side == Side::Bid ? book->best_ask().has_value() : book->best_bid().has_value());
    if (!has_liquidity) {
        return {OrderRejected{side, Price{0}, qty, RejectReason::NoLiquidity, symbol}};
    }
    Price market_limit{0};
    const OrderBook::Depth available_depth = book->depth(std::numeric_limits<std::size_t>::max());
    if (side == Side::Bid) {
        Qty remaining = qty;
        for (const auto& level : available_depth.asks) {
            market_limit = level.price;
            remaining.value -= std::min(remaining.value, level.qty.value);
            if (remaining.value == 0) {
                break;
            }
        }
    } else {
        Qty remaining = qty;
        for (const auto& level : available_depth.bids) {
            market_limit = level.price;
            remaining.value -= std::min(remaining.value, level.qty.value);
            if (remaining.value == 0) {
                break;
            }
        }
    }
    return place_limit_order(account_id, symbol, side, market_limit, qty, TimeInForce::Ioc);
}

std::vector<Event> MatchingEngine::cancel(OrderId id) {
    return cancel(kDefaultAccountId, id);
}

std::vector<Event> MatchingEngine::cancel(AccountId account_id, OrderId id) {
    const auto ownership_it = order_ownership_by_id_.find(id);
    if (ownership_it == order_ownership_by_id_.end()) {
        return {CancelRejected{id, RejectReason::UnknownOrderId, kDefaultSymbol}};
    }
    if (ownership_it->second.account_id != account_id) {
        return {CancelRejected{id, RejectReason::WrongAccount, ownership_it->second.symbol}};
    }

    const Symbol symbol = ownership_it->second.symbol;
    OrderBook& book = book_for(symbol);
    std::vector<Event> events = book.cancel(id);
    if (events.empty()) {
        return {CancelRejected{id, RejectReason::UnknownOrderId, symbol}};
    }

    for (Event& event : events) {
        if (std::holds_alternative<OrderCanceled>(event)) {
            auto canceled = std::get<OrderCanceled>(event);
            canceled.symbol = symbol;
            event = canceled;
        } else if (std::holds_alternative<TopOfBook>(event)) {
            auto top = std::get<TopOfBook>(event);
            top.symbol = symbol;
            event = top;
        }
    }

    AccountSnapshot& account = accounts_[account_id];
    if (const auto reserve_it = reserved_cash_by_order_id_.find(id); reserve_it != reserved_cash_by_order_id_.end()) {
        account.reserved_cash -= reserve_it->second;
        reserved_cash_by_order_id_.erase(reserve_it);
    }
    if (const auto reserve_it = reserved_qty_by_order_id_.find(id); reserve_it != reserved_qty_by_order_id_.end()) {
        account.reserved_qty_by_symbol[symbol] -= reserve_it->second;
        reserved_qty_by_order_id_.erase(reserve_it);
    }
    order_ownership_by_id_.erase(ownership_it);
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::replace_order(OrderId id, Price new_price, Qty new_qty) {
    return replace_order(kDefaultAccountId, id, new_price, new_qty);
}

std::vector<Event> MatchingEngine::replace_order(AccountId account_id, OrderId id, Price new_price, Qty new_qty) {
    const auto ownership_it = order_ownership_by_id_.find(id);
    if (ownership_it == order_ownership_by_id_.end()) {
        return {CancelRejected{id, RejectReason::UnknownOrderId, kDefaultSymbol}};
    }
    if (ownership_it->second.account_id != account_id) {
        return {CancelRejected{id, RejectReason::WrongAccount, ownership_it->second.symbol}};
    }
    if (!is_valid_price(new_price)) {
        return {OrderRejected{ownership_it->second.side, new_price, new_qty, RejectReason::InvalidPrice, ownership_it->second.symbol}};
    }
    if (!is_valid_qty(new_qty)) {
        return {OrderRejected{ownership_it->second.side, new_price, new_qty, RejectReason::InvalidQuantity, ownership_it->second.symbol}};
    }

    const Side side = ownership_it->second.side;
    const Symbol symbol = ownership_it->second.symbol;
    std::vector<Event> events = cancel(account_id, id);
    std::vector<Event> replacement = place_limit_order_with_account_and_id(account_id, symbol, id, side, new_price, new_qty,
                                                                           TimeInForce::Gtc);
    events.insert(events.end(), replacement.begin(), replacement.end());
    track_events(replacement);
    return events;
}

BookDepth MatchingEngine::depth(std::size_t levels) const {
    return depth(kDefaultSymbol, levels);
}

BookDepth MatchingEngine::depth(const Symbol& symbol, std::size_t levels) const {
    BookDepth result;
    const OrderBook* book = find_book(symbol);
    if (book == nullptr) {
        return result;
    }
    const OrderBook::Depth snapshot = book->depth(levels);
    for (const auto& level : snapshot.bids) {
        result.bids.push_back({level.price, level.qty});
    }
    for (const auto& level : snapshot.asks) {
        result.asks.push_back({level.price, level.qty});
    }
    return result;
}

void MatchingEngine::maybe_emit_top_of_book_change(const Symbol& symbol, std::vector<Event>& events,
                                                   const std::optional<Price>& previous_best_bid,
                                                   const std::optional<Price>& previous_best_ask) {
    const OrderBook* book = find_book(symbol);
    const std::optional<Price> current_best_bid = book == nullptr ? std::nullopt : book->best_bid();
    const std::optional<Price> current_best_ask = book == nullptr ? std::nullopt : book->best_ask();
    if (previous_best_bid != current_best_bid || previous_best_ask != current_best_ask) {
        events.emplace_back(TopOfBook{current_best_bid, current_best_ask, symbol});
    }
}

void MatchingEngine::track_events(const std::vector<Event>&) {}

}  // namespace tes
