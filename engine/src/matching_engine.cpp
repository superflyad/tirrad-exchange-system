#include <tes/matching_engine.hpp>

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

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


void MatchingEngine::set_fee_model(FeeModel fee_model) {
    if (fee_model.maker_fee_rate < 0.0 || fee_model.taker_fee_rate < 0.0) {
        throw std::invalid_argument("fee rates must be non-negative");
    }
    if (fee_model.fixed_fee.has_value() && *fee_model.fixed_fee < 0) {
        throw std::invalid_argument("fixed fee must be non-negative");
    }
    fee_model_ = fee_model;
}

MatchingEngine::FeeModel MatchingEngine::fee_model() const { return fee_model_; }

void MatchingEngine::set_account_risk_config(AccountId account_id, AccountRiskConfig config) {
    if (config.max_leverage < 1.0) throw std::invalid_argument("max_leverage must be at least 1.0");
    if (config.initial_margin_requirement <= 0.0 || config.maintenance_margin_requirement <= 0.0 ||
        config.short_margin_requirement <= 0.0) {
        throw std::invalid_argument("margin requirements must be positive");
    }
    risk_configs_[account_id] = std::move(config);
}

MatchingEngine::AccountRiskConfig MatchingEngine::account_risk_config(AccountId account_id) const {
    return effective_risk_config(account_id);
}

MatchingEngine::AccountRiskConfig MatchingEngine::effective_risk_config(AccountId account_id) const {
    const auto it = risk_configs_.find(account_id);
    return it == risk_configs_.end() ? AccountRiskConfig{} : it->second;
}

double MatchingEngine::initial_margin_requirement(const AccountRiskConfig& config, const Symbol& symbol) const {
    const auto it = config.initial_margin_requirement_by_symbol.find(symbol);
    return it == config.initial_margin_requirement_by_symbol.end() ? config.initial_margin_requirement : it->second;
}

double MatchingEngine::maintenance_margin_requirement(const AccountRiskConfig& config, const Symbol& symbol) const {
    const auto it = config.maintenance_margin_requirement_by_symbol.find(symbol);
    return it == config.maintenance_margin_requirement_by_symbol.end() ? config.maintenance_margin_requirement : it->second;
}

double MatchingEngine::short_margin_requirement(const AccountRiskConfig& config, const Symbol& symbol) const {
    const auto it = config.short_margin_requirement_by_symbol.find(symbol);
    return it == config.short_margin_requirement_by_symbol.end() ? config.short_margin_requirement : it->second;
}

std::int64_t MatchingEngine::buy_reserve(AccountId account_id, const Symbol& symbol, Price price, Qty qty, std::int64_t fee) const {
    const std::int64_t notional = price.ticks * qty.value + fee;
    const AccountRiskConfig config = effective_risk_config(account_id);
    if (config.mode == AccountRiskMode::CashOnly) return notional;
    return static_cast<std::int64_t>(std::ceil(static_cast<double>(notional) * initial_margin_requirement(config, symbol)));
}

std::int64_t MatchingEngine::short_margin_reserve(AccountId account_id, const Symbol& symbol, Price price, std::int64_t short_qty) const {
    if (short_qty <= 0) return 0;
    const AccountRiskConfig config = effective_risk_config(account_id);
    return static_cast<std::int64_t>(std::ceil(static_cast<double>(price.ticks * short_qty) * short_margin_requirement(config, symbol)));
}

MatchingEngine::MarginSnapshot MatchingEngine::account_margin_snapshot(AccountId account_id) const {
    MarginSnapshot out;
    const auto it = accounts_.find(account_id);
    if (it == accounts_.end()) return out;
    const AccountSnapshot& account = it->second;
    const AccountRiskConfig config = effective_risk_config(account_id);
    out.equity = static_cast<double>(account.cash_balance);
    for (const auto& [symbol, qty] : account.position_qty_by_symbol) {
        const double mark = mark_price(symbol).value_or(account.average_cost_by_symbol.contains(symbol) ? account.average_cost_by_symbol.at(symbol) : 0.0);
        const double exposure = std::abs(static_cast<double>(qty)) * mark;
        out.gross_exposure += exposure;
        if (qty < 0) out.short_exposure += exposure;
        out.equity += static_cast<double>(qty) * mark;
        out.margin_used += exposure * (qty < 0 ? short_margin_requirement(config, symbol) : initial_margin_requirement(config, symbol));
        out.maintenance_requirement += exposure * maintenance_margin_requirement(config, symbol);
    }
    out.margin_used += static_cast<double>(account.reserved_cash + account.reserved_short_margin);
    out.net_liquidation_value = out.equity;
    if (config.mode == AccountRiskMode::CashOnly) {
        out.available_buying_power = std::max(0.0, static_cast<double>(account.cash_balance - account.reserved_cash));
    } else {
        const double leverage_cap = std::max(0.0, out.equity * config.max_leverage - out.gross_exposure - static_cast<double>(account.reserved_cash + account.reserved_short_margin));
        const double margin_cap = std::max(0.0, out.equity - out.margin_used);
        const double initial = std::max(0.000001, config.initial_margin_requirement);
        out.available_buying_power = std::min(leverage_cap, margin_cap / initial);
    }
    out.margin_call = out.equity < out.maintenance_requirement;
    return out;
}

double MatchingEngine::account_buying_power(AccountId account_id) const {
    return account_margin_snapshot(account_id).available_buying_power;
}

std::optional<RejectReason> MatchingEngine::validate_order_risk(AccountId account_id, const Symbol& symbol, Side side,
                                                                Price price, Qty qty, std::optional<OrderId> replacing_order_id) const {
    const AccountSnapshot empty;
    const auto account_it = accounts_.find(account_id);
    const AccountSnapshot& account = account_it == accounts_.end() ? empty : account_it->second;
    const AccountRiskConfig config = effective_risk_config(account_id);
    const std::int64_t limit_notional = price.ticks * qty.value;
    const std::int64_t limit_fee = std::max(fee_for_notional(limit_notional, false), fee_for_notional(limit_notional, true));
    std::int64_t reserved_cash = account.reserved_cash;
    std::int64_t reserved_short = account.reserved_short_margin;
    std::int64_t reserved_qty = account.reserved_qty_by_symbol.contains(symbol) ? account.reserved_qty_by_symbol.at(symbol) : 0;
    if (replacing_order_id.has_value()) {
        if (const auto it = reserved_cash_by_order_id_.find(*replacing_order_id); it != reserved_cash_by_order_id_.end()) reserved_cash -= it->second;
        if (const auto it = reserved_short_margin_by_order_id_.find(*replacing_order_id); it != reserved_short_margin_by_order_id_.end()) reserved_short -= it->second;
        if (const auto it = reserved_qty_by_order_id_.find(*replacing_order_id); it != reserved_qty_by_order_id_.end()) reserved_qty -= it->second;
    }
    if (side == Side::Bid) {
        const std::int64_t required = config.mode == AccountRiskMode::CashOnly ? limit_notional + limit_fee : buy_reserve(account_id, symbol, price, qty, limit_fee);
        if (config.mode == AccountRiskMode::CashOnly) {
            return account.cash_balance - reserved_cash < required ? std::optional<RejectReason>{RejectReason::InsufficientCash} : std::nullopt;
        }
        MarginSnapshot snapshot = account_margin_snapshot(account_id);
        snapshot.available_buying_power += static_cast<double>(account.reserved_cash - reserved_cash + account.reserved_short_margin - reserved_short) / initial_margin_requirement(config, symbol);
        return snapshot.available_buying_power + 1e-9 < static_cast<double>(limit_notional + limit_fee) ? std::optional<RejectReason>{RejectReason::InsufficientBuyingPower} : std::nullopt;
    }

    const std::int64_t position = account.position_qty_by_symbol.contains(symbol) ? account.position_qty_by_symbol.at(symbol) : 0;
    if (position - reserved_qty >= qty.value) return std::nullopt;
    if (!config.allow_short_selling) {
        return RejectReason::InsufficientPosition;
    }
    const std::int64_t short_qty = qty.value - std::max<std::int64_t>(0, position - reserved_qty);
    const std::int64_t required_short = short_margin_reserve(account_id, symbol, price, short_qty);
    if (config.mode == AccountRiskMode::CashOnly) {
        return account.cash_balance - reserved_cash - reserved_short < required_short ? std::optional<RejectReason>{RejectReason::MarginRequirementFailed} : std::nullopt;
    }
    MarginSnapshot snapshot = account_margin_snapshot(account_id);
    snapshot.available_buying_power += static_cast<double>(account.reserved_short_margin - reserved_short) / short_margin_requirement(config, symbol);
    return snapshot.available_buying_power + 1e-9 < static_cast<double>(price.ticks * short_qty) ? std::optional<RejectReason>{RejectReason::MarginRequirementFailed} : std::nullopt;
}

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


std::vector<MatchingEngine::AccountLedgerEntry> MatchingEngine::account_ledger(AccountId account_id) const {
    std::vector<AccountLedgerEntry> out;
    for (const auto& entry : account_ledger_) {
        if (entry.account_id == account_id) out.push_back(entry);
    }
    return out;
}

std::vector<MatchingEngine::AccountLedgerEntry> MatchingEngine::account_ledger(AccountId account_id, const Symbol& symbol) const {
    std::vector<AccountLedgerEntry> out;
    for (const auto& entry : account_ledger_) {
        if (entry.account_id == account_id && entry.symbol == symbol) out.push_back(entry);
    }
    return out;
}

MatchingEngine::AccountSnapshot MatchingEngine::latest_account_snapshot(AccountId account_id) const {
    return account_snapshot(account_id);
}

void MatchingEngine::append_ledger_entry(const AccountLedgerEntry& entry) {
    AccountLedgerEntry copy = entry;
    copy.sequence = next_ledger_sequence_++;
    account_ledger_.push_back(std::move(copy));
}

void MatchingEngine::assert_invariants(const Symbol& symbol, AccountId account_id, AccountId maker_account_id) const {
    const AccountSnapshot& taker = accounts_.at(account_id);
    const AccountSnapshot& maker = accounts_.at(maker_account_id);
    if (taker.reserved_cash < 0 || maker.reserved_cash < 0 || taker.reserved_short_margin < 0 || maker.reserved_short_margin < 0) {
        throw std::runtime_error("reserved cash invariant violated");
    }
    const auto taker_position = taker.position_qty_by_symbol.contains(symbol) ? taker.position_qty_by_symbol.at(symbol) : 0;
    const auto maker_position = maker.position_qty_by_symbol.contains(symbol) ? maker.position_qty_by_symbol.at(symbol) : 0;
    const auto taker_reserved = taker.reserved_qty_by_symbol.contains(symbol) ? taker.reserved_qty_by_symbol.at(symbol) : 0;
    const auto maker_reserved = maker.reserved_qty_by_symbol.contains(symbol) ? maker.reserved_qty_by_symbol.at(symbol) : 0;
    if (taker_reserved < 0 || maker_reserved < 0) {
        throw std::runtime_error("reserved_position invariant violated");
    }
}

std::int64_t MatchingEngine::fee_for_notional(std::int64_t notional, bool maker) const {
    const double rate = maker ? fee_model_.maker_fee_rate : fee_model_.taker_fee_rate;
    const std::int64_t variable_fee = static_cast<std::int64_t>(std::llround(static_cast<double>(notional) * rate));
    return variable_fee + fee_model_.fixed_fee.value_or(0);
}

void MatchingEngine::apply_position_accounting(AccountSnapshot& account, const Symbol& symbol, Side side, Price price, Qty qty,
                                               std::int64_t fee) {
    auto& position = account.position_qty_by_symbol[symbol];
    auto& average_cost = account.average_cost_by_symbol[symbol];
    auto& realized_for_symbol = account.realized_pnl_by_symbol[symbol];
    std::int64_t remaining = qty.value;
    if (side == Side::Bid) {
        if (position < 0) {
            const std::int64_t cover_qty = std::min<std::int64_t>(remaining, -position);
            const double trade_pnl = (average_cost - static_cast<double>(price.ticks)) * static_cast<double>(cover_qty);
            realized_for_symbol += trade_pnl;
            account.realized_pnl += trade_pnl;
            position += cover_qty;
            remaining -= cover_qty;
            if (position == 0) average_cost = 0.0;
        }
        if (remaining > 0) {
            const std::int64_t previous_long = std::max<std::int64_t>(0, position);
            position += remaining;
            average_cost = ((average_cost * static_cast<double>(previous_long)) +
                            (static_cast<double>(price.ticks) * static_cast<double>(remaining))) /
                           static_cast<double>(position);
        }
    } else {
        if (position > 0) {
            const std::int64_t sell_qty = std::min<std::int64_t>(remaining, position);
            const double trade_pnl = (static_cast<double>(price.ticks) - average_cost) * static_cast<double>(sell_qty);
            realized_for_symbol += trade_pnl;
            account.realized_pnl += trade_pnl;
            position -= sell_qty;
            remaining -= sell_qty;
            if (position == 0) average_cost = 0.0;
        }
        if (remaining > 0) {
            const std::int64_t previous_short = position < 0 ? -position : 0;
            position -= remaining;
            average_cost = ((average_cost * static_cast<double>(previous_short)) +
                            (static_cast<double>(price.ticks) * static_cast<double>(remaining))) /
                           static_cast<double>(-position);
        }
    }
    if (fee != 0) {
        realized_for_symbol -= static_cast<double>(fee);
        account.realized_pnl -= static_cast<double>(fee);
    }
}

std::optional<double> MatchingEngine::mark_price(const Symbol& symbol) const {
    const OrderBook* book = find_book(symbol);
    if (book != nullptr) {
        const auto bid = book->best_bid();
        const auto ask = book->best_ask();
        if (bid.has_value() && ask.has_value()) {
            return (static_cast<double>(bid->ticks) + static_cast<double>(ask->ticks)) / 2.0;
        }
    }
    const auto it = latest_mark_by_symbol_.find(symbol);
    return it == latest_mark_by_symbol_.end() ? std::nullopt : std::optional<double>{it->second};
}

MatchingEngine::PerformanceSnapshot MatchingEngine::performance_snapshot(AccountId account_id) const {
    PerformanceSnapshot out;
    const auto it = accounts_.find(account_id);
    if (it == accounts_.end()) {
        return out;
    }
    const AccountSnapshot& account = it->second;
    out.cash_balance = account.cash_balance;
    out.reserved_cash = account.reserved_cash;
    out.position_qty_by_symbol = account.position_qty_by_symbol;
    out.average_cost_by_symbol = account.average_cost_by_symbol;
    out.realized_pnl = account.realized_pnl;
    out.realized_pnl_by_symbol = account.realized_pnl_by_symbol;
    out.total_equity = static_cast<double>(account.cash_balance);
    for (const auto& [symbol, qty] : account.position_qty_by_symbol) {
        const double avg = account.average_cost_by_symbol.contains(symbol) ? account.average_cost_by_symbol.at(symbol) : 0.0;
        const auto mark = mark_price(symbol);
        const double unrealized = mark.has_value() ? (mark.value() - avg) * static_cast<double>(qty) : 0.0;
        out.unrealized_pnl_by_symbol[symbol] = unrealized;
        out.unrealized_pnl += unrealized;
        if (mark.has_value()) {
            out.total_equity += mark.value() * static_cast<double>(qty);
        }
    }
    return out;
}
std::optional<AccountId> MatchingEngine::order_owner(OrderId id) const {
    const auto it = order_ownership_by_id_.find(id);
    if (it != order_ownership_by_id_.end()) {
        return it->second.account_id;
    }
    const auto stop_it = stop_orders_by_id_.find(id);
    if (stop_it != stop_orders_by_id_.end()) {
        return stop_it->second.account_id;
    }
    return std::nullopt;
}


TradingPhase MatchingEngine::trading_phase(const Symbol& symbol) const {
    const auto it = trading_phases_by_symbol_.find(symbol);
    return it == trading_phases_by_symbol_.end() ? TradingPhase::Continuous : it->second;
}

std::vector<Event> MatchingEngine::set_trading_phase(const Symbol& symbol, TradingPhase phase) {
    const TradingPhase previous = trading_phase(symbol);
    trading_phases_by_symbol_[symbol] = phase;
    std::vector<Event> events;
    if (previous == phase) {
        return events;
    }
    if (phase == TradingPhase::OpeningAuction || phase == TradingPhase::ClosingAuction) {
        events.emplace_back(AuctionStarted{symbol, phase});
        const AuctionIndicative indicative = compute_auction_indicative(symbol);
        events.emplace_back(IndicativePriceUpdated{symbol, indicative.price, indicative.qty, indicative.imbalance});
    } else if (previous == TradingPhase::OpeningAuction || previous == TradingPhase::ClosingAuction) {
        events.emplace_back(AuctionEnded{symbol, phase});
    }
    track_events(events);
    return events;
}

MatchingEngine::AuctionIndicative MatchingEngine::compute_auction_indicative(const Symbol& symbol) const {
    const OrderBook* book = find_book(symbol);
    if (book == nullptr) return {};
    const OrderBook::Depth depth = book->depth(std::numeric_limits<std::size_t>::max());
    std::vector<Price> candidates;
    candidates.reserve(depth.bids.size() + depth.asks.size());
    for (const auto& level : depth.bids) candidates.push_back(level.price);
    for (const auto& level : depth.asks) candidates.push_back(level.price);
    if (candidates.empty()) return {};
    std::sort(candidates.begin(), candidates.end(), [](Price a, Price b) { return a.ticks < b.ticks; });
    candidates.erase(std::unique(candidates.begin(), candidates.end()), candidates.end());

    const auto reference_it = latest_mark_by_symbol_.find(symbol);
    const std::optional<std::int64_t> reference = reference_it == latest_mark_by_symbol_.end()
        ? std::nullopt
        : std::optional<std::int64_t>{static_cast<std::int64_t>(std::llround(reference_it->second))};

    AuctionIndicative best;
    bool have_best = false;
    for (const Price candidate : candidates) {
        std::int64_t bid_qty = 0;
        std::int64_t ask_qty = 0;
        for (const auto& level : depth.bids) {
            if (level.price.ticks < candidate.ticks) break;
            bid_qty += level.qty.value;
        }
        for (const auto& level : depth.asks) {
            if (level.price.ticks > candidate.ticks) break;
            ask_qty += level.qty.value;
        }
        const std::int64_t matched = std::min(bid_qty, ask_qty);
        const std::int64_t imbalance = bid_qty - ask_qty;
        if (matched <= 0) continue;
        const std::int64_t abs_imbalance = std::llabs(imbalance);
        bool better = !have_best || matched > best.qty.value ||
                      (matched == best.qty.value && abs_imbalance < std::llabs(best.imbalance));
        if (!better && have_best && matched == best.qty.value && abs_imbalance == std::llabs(best.imbalance) && reference.has_value()) {
            const std::int64_t current_distance = std::llabs(candidate.ticks - *reference);
            const std::int64_t best_distance = std::llabs(best.price->ticks - *reference);
            better = current_distance < best_distance;
        }
        if (!better && have_best && matched == best.qty.value && abs_imbalance == std::llabs(best.imbalance)) {
            const bool reference_tied = !reference.has_value() ||
                std::llabs(candidate.ticks - *reference) == std::llabs(best.price->ticks - *reference);
            better = reference_tied && candidate.ticks < best.price->ticks;
        }
        if (better) {
            best = AuctionIndicative{candidate, Qty{matched}, imbalance};
            have_best = true;
        }
    }
    return best;
}

std::optional<Price> MatchingEngine::indicative_price(const Symbol& symbol) const { return compute_auction_indicative(symbol).price; }
Qty MatchingEngine::indicative_volume(const Symbol& symbol) const { return compute_auction_indicative(symbol).qty; }
std::int64_t MatchingEngine::auction_imbalance(const Symbol& symbol) const { return compute_auction_indicative(symbol).imbalance; }

std::vector<Event> MatchingEngine::rest_limit_order(AccountId account_id, const Symbol& symbol, OrderId id, Side side, Price price, Qty qty) {
    AccountSnapshot& account = accounts_[account_id];
    OrderBook& book = book_for(symbol);
    std::vector<Event> events = book.add_limit_order(Order{id, side, price, qty});
    for (Event& event : events) {
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
    order_ownership_by_id_[id] = {account_id, symbol, side, price, qty};
    if (side == Side::Bid) {
        const std::int64_t reserve_notional = price.ticks * qty.value;
        const std::int64_t reserve_fee = std::max(fee_for_notional(reserve_notional, false), fee_for_notional(reserve_notional, true));
        const std::int64_t reserve = buy_reserve(account_id, symbol, price, qty, reserve_fee);
        account.reserved_cash += reserve;
        reserved_cash_by_order_id_[id] = reserve;
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "order_accepted_reserve", 0, 0, reserve, 0, id, std::nullopt});
    } else {
        const std::int64_t available_long = std::max<std::int64_t>(0, account.position_qty_by_symbol[symbol] - account.reserved_qty_by_symbol[symbol]);
        const std::int64_t long_reserve = std::min(qty.value, available_long);
        const std::int64_t short_reserve_qty = qty.value - long_reserve;
        if (long_reserve > 0) {
            account.reserved_qty_by_symbol[symbol] += long_reserve;
            reserved_qty_by_order_id_[id] = long_reserve;
        }
        const std::int64_t short_reserve = short_margin_reserve(account_id, symbol, price, short_reserve_qty);
        if (short_reserve > 0) {
            account.reserved_short_margin += short_reserve;
            reserved_short_margin_by_order_id_[id] = short_reserve;
        }
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "order_accepted_reserve", 0, 0, short_reserve, long_reserve, id, std::nullopt});
    }
    if (trading_phase(symbol) == TradingPhase::OpeningAuction || trading_phase(symbol) == TradingPhase::ClosingAuction) {
        const AuctionIndicative indicative = compute_auction_indicative(symbol);
        events.emplace_back(IndicativePriceUpdated{symbol, indicative.price, indicative.qty, indicative.imbalance});
    }
    return events;
}

void MatchingEngine::settle_auction_trade(const Symbol& symbol, OrderId bid_id, OrderId ask_id, Price price, Qty qty, std::vector<Event>& events) {
    auto bid_owner_it = order_ownership_by_id_.find(bid_id);
    auto ask_owner_it = order_ownership_by_id_.find(ask_id);
    const AccountId bid_account_id = bid_owner_it == order_ownership_by_id_.end() ? kDefaultAccountId : bid_owner_it->second.account_id;
    const AccountId ask_account_id = ask_owner_it == order_ownership_by_id_.end() ? kDefaultAccountId : ask_owner_it->second.account_id;
    const std::int64_t bid_qty_before = bid_owner_it == order_ownership_by_id_.end() ? qty.value : bid_owner_it->second.qty.value;
    const std::int64_t ask_qty_before = ask_owner_it == order_ownership_by_id_.end() ? qty.value : ask_owner_it->second.qty.value;
    AccountSnapshot& bid_account = accounts_[bid_account_id];
    AccountSnapshot& ask_account = accounts_[ask_account_id];
    const std::int64_t notional = price.ticks * qty.value;
    const std::int64_t bid_fee = fee_for_notional(notional, false);
    const std::int64_t ask_fee = fee_for_notional(notional, true);

    events.emplace_back(TradeExecuted{bid_id, ask_id, Side::Bid, price, qty, symbol});
    bid_account.cash_balance -= notional + bid_fee;
    apply_position_accounting(bid_account, symbol, Side::Bid, price, qty, bid_fee);
    ask_account.cash_balance += notional - ask_fee;
    apply_position_accounting(ask_account, symbol, Side::Ask, price, qty, ask_fee);

    if (auto reserve_it = reserved_cash_by_order_id_.find(bid_id); reserve_it != reserved_cash_by_order_id_.end()) {
        const std::int64_t release = bid_qty_before <= 0 ? reserve_it->second : static_cast<std::int64_t>(std::ceil(static_cast<double>(reserve_it->second) * static_cast<double>(qty.value) / static_cast<double>(bid_qty_before)));
        const std::int64_t bounded_release = std::min(reserve_it->second, release);
        bid_account.reserved_cash -= bounded_release;
        reserve_it->second -= bounded_release;
        if (reserve_it->second == 0) reserved_cash_by_order_id_.erase(reserve_it);
    }
    if (auto reserve_it = reserved_qty_by_order_id_.find(ask_id); reserve_it != reserved_qty_by_order_id_.end()) {
        const std::int64_t release = std::min(reserve_it->second, qty.value);
        ask_account.reserved_qty_by_symbol[symbol] -= release;
        reserve_it->second -= release;
        if (reserve_it->second == 0) reserved_qty_by_order_id_.erase(reserve_it);
    }
    if (auto reserve_it = reserved_short_margin_by_order_id_.find(ask_id); reserve_it != reserved_short_margin_by_order_id_.end()) {
        const std::int64_t release = ask_qty_before <= 0 ? reserve_it->second : static_cast<std::int64_t>(std::ceil(static_cast<double>(reserve_it->second) * static_cast<double>(qty.value) / static_cast<double>(ask_qty_before)));
        const std::int64_t bounded_release = std::min(reserve_it->second, release);
        ask_account.reserved_short_margin -= bounded_release;
        reserve_it->second -= bounded_release;
        if (reserve_it->second == 0) reserved_short_margin_by_order_id_.erase(reserve_it);
    }

    latest_mark_by_symbol_[symbol] = static_cast<double>(price.ticks);
    append_ledger_entry(AccountLedgerEntry{0, bid_account_id, symbol, "auction_trade_settlement", -notional, qty.value, 0, 0, bid_id, ask_id, 0});
    append_ledger_entry(AccountLedgerEntry{0, ask_account_id, symbol, "auction_trade_settlement", notional, -qty.value, 0, 0, ask_id, bid_id, 0});
    if (bid_fee != 0) append_ledger_entry(AccountLedgerEntry{0, bid_account_id, symbol, "fee", -bid_fee, 0, 0, 0, bid_id, ask_id, bid_fee});
    if (ask_fee != 0) append_ledger_entry(AccountLedgerEntry{0, ask_account_id, symbol, "fee", -ask_fee, 0, 0, 0, ask_id, bid_id, ask_fee});

    if (bid_owner_it != order_ownership_by_id_.end()) {
        bid_owner_it->second.qty.value -= qty.value;
        if (bid_owner_it->second.qty.value == 0) order_ownership_by_id_.erase(bid_owner_it);
    }
    if (ask_owner_it != order_ownership_by_id_.end()) {
        ask_owner_it->second.qty.value -= qty.value;
        if (ask_owner_it->second.qty.value == 0) order_ownership_by_id_.erase(ask_owner_it);
    }
    events.emplace_back(OrderFilled{bid_id, qty, symbol});
    events.emplace_back(OrderFilled{ask_id, qty, symbol});
    assert_invariants(symbol, bid_account_id, ask_account_id);
}

std::vector<Event> MatchingEngine::uncross(const Symbol& symbol) {
    const AuctionIndicative indicative = compute_auction_indicative(symbol);
    std::vector<Event> events;
    if (!indicative.price.has_value() || indicative.qty.value <= 0) {
        events.emplace_back(AuctionUncross{symbol, Price{0}, Qty{0}, 0});
        track_events(events);
        return events;
    }
    OrderBook& book = book_for(symbol);
    Qty remaining = indicative.qty;
    const std::optional<Price> previous_best_bid = book.best_bid();
    const std::optional<Price> previous_best_ask = book.best_ask();
    while (remaining.value > 0) {
        const std::optional<Price> best_bid = book.best_bid();
        const std::optional<Price> best_ask = book.best_ask();
        if (!best_bid.has_value() || !best_ask.has_value() || best_bid->ticks < indicative.price->ticks ||
            best_ask->ticks > indicative.price->ticks) {
            break;
        }
        const std::optional<Order> bid_order = book.front_of_level(Side::Bid, *best_bid);
        const std::optional<Order> ask_order = book.front_of_level(Side::Ask, *best_ask);
        if (!bid_order.has_value() || !ask_order.has_value()) break;
        const Qty traded{std::min({remaining.value, bid_order->qty.value, ask_order->qty.value})};
        const std::optional<OrderBook::FillResult> bid = book.fill_best_at_or_better(Side::Bid, *indicative.price, traded);
        const std::optional<OrderBook::FillResult> ask = book.fill_best_at_or_better(Side::Ask, *indicative.price, traded);
        if (!bid.has_value() || !ask.has_value()) break;
        settle_auction_trade(symbol, bid->maker_id, ask->maker_id, *indicative.price, traded, events);
        remaining.value -= traded.value;
    }
    events.insert(events.begin(), Event{AuctionUncross{symbol, *indicative.price, Qty{indicative.qty.value - remaining.value}, compute_auction_indicative(symbol).imbalance}});
    maybe_emit_top_of_book_change(symbol, events, previous_best_bid, previous_best_ask);
    const TradingPhase previous_phase = trading_phase(symbol);
    if (previous_phase == TradingPhase::OpeningAuction || previous_phase == TradingPhase::ClosingAuction) {
        trading_phases_by_symbol_[symbol] = TradingPhase::Continuous;
        events.emplace_back(AuctionEnded{symbol, TradingPhase::Continuous});
    }
    track_events(events);
    return events;
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
    std::vector<Event> triggered = evaluate_stop_orders(symbol);
    events.insert(events.end(), triggered.begin(), triggered.end());
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
    const std::int64_t limit_fee = std::max(fee_for_notional(limit_notional, false), fee_for_notional(limit_notional, true));
    if (const auto risk_failure = validate_order_risk(account_id, symbol, side, price, qty)) {
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "order_rejected_risk_failure", 0, 0, 0, 0, taker_id, std::nullopt});
        return {OrderRejected{side, price, qty, *risk_failure, symbol}};
    }

    if (trading_phase(symbol) == TradingPhase::OpeningAuction || trading_phase(symbol) == TradingPhase::ClosingAuction) {
        return rest_limit_order(account_id, symbol, taker_id, side, price, qty);
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
        const std::int64_t maker_qty_before = owner_it == order_ownership_by_id_.end() ? fill->qty.value : owner_it->second.qty.value;
        AccountSnapshot& maker = accounts_[maker_account_id];
        const std::int64_t notional = fill->price.ticks * fill->qty.value;

        remaining.value -= fill->qty.value;
        events.emplace_back(TradeExecuted{taker_id, fill->maker_id, side, fill->price, fill->qty, symbol});

        const std::int64_t taker_fee = fee_for_notional(notional, false);
        const std::int64_t maker_fee = fee_for_notional(notional, true);
        if (side == Side::Bid) {
            taker.cash_balance -= notional + taker_fee;
            apply_position_accounting(taker, symbol, Side::Bid, fill->price, fill->qty, taker_fee);
            maker.cash_balance += notional - maker_fee;
            apply_position_accounting(maker, symbol, Side::Ask, fill->price, fill->qty, maker_fee);
            if (auto reserve_it = reserved_qty_by_order_id_.find(fill->maker_id); reserve_it != reserved_qty_by_order_id_.end()) {
                const std::int64_t release = std::min(reserve_it->second, fill->qty.value);
                maker.reserved_qty_by_symbol[symbol] -= release;
                reserve_it->second -= release;
                if (reserve_it->second == 0) {
                    reserved_qty_by_order_id_.erase(reserve_it);
                }
            }
            if (auto reserve_it = reserved_short_margin_by_order_id_.find(fill->maker_id); reserve_it != reserved_short_margin_by_order_id_.end()) {
                const std::int64_t release = maker_qty_before <= 0 ? reserve_it->second : static_cast<std::int64_t>(std::ceil(static_cast<double>(reserve_it->second) * static_cast<double>(fill->qty.value) / static_cast<double>(maker_qty_before)));
                const std::int64_t bounded_release = std::min(reserve_it->second, release);
                maker.reserved_short_margin -= bounded_release;
                reserve_it->second -= bounded_release;
                if (reserve_it->second == 0) {
                    reserved_short_margin_by_order_id_.erase(reserve_it);
                }
            }
        } else {
            taker.cash_balance += notional - taker_fee;
            apply_position_accounting(taker, symbol, Side::Ask, fill->price, fill->qty, taker_fee);
            maker.cash_balance -= notional + maker_fee;
            apply_position_accounting(maker, symbol, Side::Bid, fill->price, fill->qty, maker_fee);
            if (auto reserve_it = reserved_cash_by_order_id_.find(fill->maker_id); reserve_it != reserved_cash_by_order_id_.end()) {
                const std::int64_t release = maker_qty_before <= 0 ? reserve_it->second : static_cast<std::int64_t>(std::ceil(static_cast<double>(reserve_it->second) * static_cast<double>(fill->qty.value) / static_cast<double>(maker_qty_before)));
                const std::int64_t bounded_release = std::min(reserve_it->second, release);
                maker.reserved_cash -= bounded_release;
                reserve_it->second -= bounded_release;
                if (reserve_it->second == 0) {
                    reserved_cash_by_order_id_.erase(reserve_it);
                }
            }
        }
        latest_mark_by_symbol_[symbol] = static_cast<double>(fill->price.ticks);

        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "trade_settlement",
            side == Side::Bid ? -notional : notional,
            side == Side::Bid ? fill->qty.value : -fill->qty.value,
            0, 0, taker_id, fill->maker_id, 0});
        append_ledger_entry(AccountLedgerEntry{0, maker_account_id, symbol, "trade_settlement",
            side == Side::Bid ? notional : -notional,
            side == Side::Bid ? -fill->qty.value : fill->qty.value,
            side == Side::Ask ? -notional : 0,
            side == Side::Bid ? -fill->qty.value : 0,
            fill->maker_id, taker_id, 0});
        if (taker_fee != 0) {
            append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "fee", -taker_fee, 0, 0, 0, taker_id, fill->maker_id, taker_fee});
        }
        if (maker_fee != 0) {
            append_ledger_entry(AccountLedgerEntry{0, maker_account_id, symbol, "fee", -maker_fee, 0, 0, 0, fill->maker_id, taker_id, maker_fee});
        }
        assert_invariants(symbol, account_id, maker_account_id);

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
            append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "ioc_fok_expiration_release", 0, 0, 0, 0, taker_id, std::nullopt});
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
                const std::int64_t reserve_notional = price.ticks * remaining.value;
                const std::int64_t reserve_fee = std::max(fee_for_notional(reserve_notional, false), fee_for_notional(reserve_notional, true));
                const std::int64_t reserve = buy_reserve(account_id, symbol, price, remaining, reserve_fee);
                taker.reserved_cash += reserve;
                reserved_cash_by_order_id_[taker_id] = reserve;
                append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "order_accepted_reserve", 0, 0, reserve, 0, taker_id, std::nullopt});
            } else {
                const std::int64_t available_long = std::max<std::int64_t>(0, taker.position_qty_by_symbol[symbol] - taker.reserved_qty_by_symbol[symbol]);
                const std::int64_t long_reserve = std::min(remaining.value, available_long);
                const std::int64_t short_reserve_qty = remaining.value - long_reserve;
                if (long_reserve > 0) {
                    taker.reserved_qty_by_symbol[symbol] += long_reserve;
                    reserved_qty_by_order_id_[taker_id] = long_reserve;
                }
                const std::int64_t short_reserve = short_margin_reserve(account_id, symbol, price, short_reserve_qty);
                if (short_reserve > 0) {
                    taker.reserved_short_margin += short_reserve;
                    reserved_short_margin_by_order_id_[taker_id] = short_reserve;
                }
                append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "order_accepted_reserve", 0, 0, short_reserve, long_reserve, taker_id, std::nullopt});
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
    const OrderId id = next_order_id_++;
    std::vector<Event> events = place_market_order_with_account_and_id(account_id, symbol, id, side, qty);
    std::vector<Event> triggered = evaluate_stop_orders(symbol);
    events.insert(events.end(), triggered.begin(), triggered.end());
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::place_market_order_with_account_and_id(AccountId account_id, const Symbol& symbol,
                                                                          OrderId taker_id, Side side, Qty qty) {
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
            if (remaining.value == 0) break;
        }
    } else {
        Qty remaining = qty;
        for (const auto& level : available_depth.bids) {
            market_limit = level.price;
            remaining.value -= std::min(remaining.value, level.qty.value);
            if (remaining.value == 0) break;
        }
    }
    return place_limit_order_with_account_and_id(account_id, symbol, taker_id, side, market_limit, qty, TimeInForce::Ioc);
}

std::vector<Event> MatchingEngine::place_stop_order(Side side, Price stop_price, Qty qty) {
    return place_stop_order(kDefaultAccountId, kDefaultSymbol, side, stop_price, qty);
}

std::vector<Event> MatchingEngine::place_stop_order(AccountId account_id, Side side, Price stop_price, Qty qty) {
    return place_stop_order(account_id, kDefaultSymbol, side, stop_price, qty);
}

std::vector<Event> MatchingEngine::place_stop_order(AccountId account_id, const Symbol& symbol, Side side,
                                                    Price stop_price, Qty qty) {
    const OrderId id = next_order_id_++;
    std::vector<Event> events = place_stop_order_with_account_and_id(account_id, symbol, id, side, stop_price, qty, std::nullopt);
    std::vector<Event> triggered = evaluate_stop_orders(symbol);
    events.insert(events.end(), triggered.begin(), triggered.end());
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::place_stop_limit_order(Side side, Price stop_price, Price limit_price, Qty qty) {
    return place_stop_limit_order(kDefaultAccountId, kDefaultSymbol, side, stop_price, limit_price, qty);
}

std::vector<Event> MatchingEngine::place_stop_limit_order(AccountId account_id, Side side, Price stop_price,
                                                          Price limit_price, Qty qty) {
    return place_stop_limit_order(account_id, kDefaultSymbol, side, stop_price, limit_price, qty);
}

std::vector<Event> MatchingEngine::place_stop_limit_order(AccountId account_id, const Symbol& symbol, Side side,
                                                          Price stop_price, Price limit_price, Qty qty) {
    const OrderId id = next_order_id_++;
    std::vector<Event> events = place_stop_order_with_account_and_id(account_id, symbol, id, side, stop_price, qty, limit_price);
    std::vector<Event> triggered = evaluate_stop_orders(symbol);
    events.insert(events.end(), triggered.begin(), triggered.end());
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::place_stop_order_with_account_and_id(AccountId account_id, const Symbol& symbol,
                                                                        OrderId stop_id, Side side, Price stop_price,
                                                                        Qty qty, std::optional<Price> limit_price) {
    if (!is_valid_price(stop_price) || (limit_price.has_value() && !is_valid_price(*limit_price))) {
        return {OrderRejected{side, limit_price.value_or(stop_price), qty, RejectReason::InvalidPrice, symbol}};
    }
    if (!is_valid_qty(qty)) {
        return {OrderRejected{side, limit_price.value_or(stop_price), qty, RejectReason::InvalidQuantity, symbol}};
    }

    AccountSnapshot& account = accounts_[account_id];
    if (account_id == kDefaultAccountId) {
        account.cash_balance = std::max(account.cash_balance, kDefaultLegacyCash);
        account.position_qty_by_symbol[symbol] = std::max(account.position_qty_by_symbol[symbol], kDefaultLegacyPosition);
    }

    const Price risk_price = limit_price.value_or(stop_price);
    if (const auto risk_failure = validate_order_risk(account_id, symbol, side, risk_price, qty)) {
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "stop_order_rejected_risk_failure", 0, 0, 0, 0, stop_id, std::nullopt});
        return {OrderRejected{side, risk_price, qty, *risk_failure, symbol}};
    }

    stop_orders_by_id_[stop_id] = StopOrderState{account_id, symbol, side, stop_price, qty, limit_price, stop_id};
    pending_stop_ids_by_symbol_[symbol].push_back(stop_id);
    append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "stop_order_accepted", 0, 0, 0, 0, stop_id, std::nullopt});
    return {StopOrderAccepted{stop_id, side, stop_price, qty, limit_price, symbol}};
}

std::optional<Price> MatchingEngine::trigger_price(const Symbol& symbol) const {
    if (const auto it = latest_mark_by_symbol_.find(symbol); it != latest_mark_by_symbol_.end()) {
        return Price{static_cast<std::int64_t>(std::llround(it->second))};
    }
    const OrderBook* book = find_book(symbol);
    if (book == nullptr) return std::nullopt;
    const auto bid = book->best_bid();
    const auto ask = book->best_ask();
    if (bid.has_value() && ask.has_value() && bid->ticks < ask->ticks) {
        return Price{(bid->ticks + ask->ticks) / 2};
    }
    return std::nullopt;
}

std::vector<Event> MatchingEngine::evaluate_stop_orders(const Symbol& symbol) {
    std::vector<Event> out;
    while (true) {
        const std::optional<Price> current = trigger_price(symbol);
        if (!current.has_value()) break;
        std::vector<OrderId> ready;
        auto& pending = pending_stop_ids_by_symbol_[symbol];
        for (OrderId id : pending) {
            const auto it = stop_orders_by_id_.find(id);
            if (it == stop_orders_by_id_.end()) continue;
            const StopOrderState& stop = it->second;
            const bool triggers = stop.side == Side::Bid ? current->ticks >= stop.stop_price.ticks : current->ticks <= stop.stop_price.ticks;
            if (triggers) ready.push_back(id);
        }
        if (ready.empty()) break;
        std::sort(ready.begin(), ready.end());
        bool any_resulting_trade = false;
        for (OrderId id : ready) {
            const auto it = stop_orders_by_id_.find(id);
            if (it == stop_orders_by_id_.end()) continue;
            StopOrderState stop = it->second;
            stop_orders_by_id_.erase(it);
            auto pending_it = pending_stop_ids_by_symbol_.find(symbol);
            if (pending_it != pending_stop_ids_by_symbol_.end()) {
                auto& ids = pending_it->second;
                ids.erase(std::remove(ids.begin(), ids.end(), id), ids.end());
            }
            const OrderId resulting_order_id = next_order_id_++;
            out.emplace_back(StopOrderTriggered{id, resulting_order_id, stop.side, stop.stop_price, stop.qty, stop.limit_price, symbol});
            append_ledger_entry(AccountLedgerEntry{0, stop.account_id, symbol, "stop_order_triggered", 0, 0, 0, 0, id, resulting_order_id});
            std::vector<Event> child = stop.limit_price.has_value()
                ? place_limit_order_with_account_and_id(stop.account_id, symbol, resulting_order_id, stop.side, *stop.limit_price, stop.qty, TimeInForce::Gtc)
                : place_market_order_with_account_and_id(stop.account_id, symbol, resulting_order_id, stop.side, stop.qty);
            for (const Event& event : child) {
                any_resulting_trade = any_resulting_trade || std::holds_alternative<TradeExecuted>(event);
            }
            out.insert(out.end(), child.begin(), child.end());
        }
        if (!any_resulting_trade) break;
    }
    return out;
}

std::vector<Event> MatchingEngine::cancel(OrderId id) {
    return cancel(kDefaultAccountId, id);
}

std::vector<Event> MatchingEngine::cancel(AccountId account_id, OrderId id) {
    if (const auto stop_it = stop_orders_by_id_.find(id); stop_it != stop_orders_by_id_.end()) {
        if (stop_it->second.account_id != account_id) {
            return {CancelRejected{id, RejectReason::WrongAccount, stop_it->second.symbol}};
        }
        const Symbol symbol = stop_it->second.symbol;
        stop_orders_by_id_.erase(stop_it);
        auto& ids = pending_stop_ids_by_symbol_[symbol];
        ids.erase(std::remove(ids.begin(), ids.end(), id), ids.end());
        std::vector<Event> events{OrderCanceled{id, symbol}};
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "stop_order_canceled", 0, 0, 0, 0, id, std::nullopt});
        track_events(events);
        return events;
    }
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
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "cancel_release", 0, 0, -reserve_it->second, 0, id, std::nullopt});
        reserved_cash_by_order_id_.erase(reserve_it);
    }
    if (const auto reserve_it = reserved_qty_by_order_id_.find(id); reserve_it != reserved_qty_by_order_id_.end()) {
        account.reserved_qty_by_symbol[symbol] -= reserve_it->second;
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "cancel_release", 0, 0, 0, -reserve_it->second, id, std::nullopt});
        reserved_qty_by_order_id_.erase(reserve_it);
    }
    if (const auto reserve_it = reserved_short_margin_by_order_id_.find(id); reserve_it != reserved_short_margin_by_order_id_.end()) {
        account.reserved_short_margin -= reserve_it->second;
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "cancel_release", 0, 0, -reserve_it->second, 0, id, std::nullopt});
        reserved_short_margin_by_order_id_.erase(reserve_it);
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
    if (const auto risk_failure = validate_order_risk(account_id, symbol, side, new_price, new_qty, id)) {
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "replace_rejected_risk_failure", 0, 0, 0, 0, id, std::nullopt});
        return {OrderRejected{side, new_price, new_qty, *risk_failure, symbol}};
    }
    append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "replace_release_re_reserve", 0, 0, 0, 0, id, std::nullopt});
    std::vector<Event> events = cancel(account_id, id);
    std::vector<Event> replacement = place_limit_order_with_account_and_id(account_id, symbol, id, side, new_price, new_qty,
                                                                           TimeInForce::Gtc);
    events.insert(events.end(), replacement.begin(), replacement.end());
    track_events(replacement);
    return events;
}

std::vector<Event> MatchingEngine::replace_stop_order(OrderId id, Price new_stop_price, Qty new_qty) {
    return replace_stop_order(kDefaultAccountId, id, new_stop_price, new_qty);
}

std::vector<Event> MatchingEngine::replace_stop_order(AccountId account_id, OrderId id, Price new_stop_price, Qty new_qty) {
    const auto stop_it = stop_orders_by_id_.find(id);
    if (stop_it == stop_orders_by_id_.end()) {
        return {CancelRejected{id, RejectReason::UnknownOrderId, kDefaultSymbol}};
    }
    if (stop_it->second.account_id != account_id) {
        return {CancelRejected{id, RejectReason::WrongAccount, stop_it->second.symbol}};
    }
    if (stop_it->second.limit_price.has_value()) {
        return replace_stop_limit_order(account_id, id, new_stop_price, *stop_it->second.limit_price, new_qty);
    }
    const Symbol symbol = stop_it->second.symbol;
    const Side side = stop_it->second.side;
    if (!is_valid_price(new_stop_price)) {
        return {OrderRejected{side, new_stop_price, new_qty, RejectReason::InvalidPrice, symbol}};
    }
    if (!is_valid_qty(new_qty)) {
        return {OrderRejected{side, new_stop_price, new_qty, RejectReason::InvalidQuantity, symbol}};
    }
    if (const auto risk_failure = validate_order_risk(account_id, symbol, side, new_stop_price, new_qty)) {
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "replace_stop_rejected_risk_failure", 0, 0, 0, 0, id, std::nullopt});
        return {OrderRejected{side, new_stop_price, new_qty, *risk_failure, symbol}};
    }
    stop_it->second.stop_price = new_stop_price;
    stop_it->second.qty = new_qty;
    std::vector<Event> events{OrderCanceled{id, symbol}, StopOrderAccepted{id, side, new_stop_price, new_qty, std::nullopt, symbol}};
    std::vector<Event> triggered = evaluate_stop_orders(symbol);
    events.insert(events.end(), triggered.begin(), triggered.end());
    track_events(events);
    return events;
}

std::vector<Event> MatchingEngine::replace_stop_limit_order(OrderId id, Price new_stop_price, Price new_limit_price,
                                                            Qty new_qty) {
    return replace_stop_limit_order(kDefaultAccountId, id, new_stop_price, new_limit_price, new_qty);
}

std::vector<Event> MatchingEngine::replace_stop_limit_order(AccountId account_id, OrderId id, Price new_stop_price,
                                                            Price new_limit_price, Qty new_qty) {
    const auto stop_it = stop_orders_by_id_.find(id);
    if (stop_it == stop_orders_by_id_.end()) {
        return {CancelRejected{id, RejectReason::UnknownOrderId, kDefaultSymbol}};
    }
    if (stop_it->second.account_id != account_id) {
        return {CancelRejected{id, RejectReason::WrongAccount, stop_it->second.symbol}};
    }
    const Symbol symbol = stop_it->second.symbol;
    const Side side = stop_it->second.side;
    if (!is_valid_price(new_stop_price) || !is_valid_price(new_limit_price)) {
        return {OrderRejected{side, new_limit_price, new_qty, RejectReason::InvalidPrice, symbol}};
    }
    if (!is_valid_qty(new_qty)) {
        return {OrderRejected{side, new_limit_price, new_qty, RejectReason::InvalidQuantity, symbol}};
    }
    if (const auto risk_failure = validate_order_risk(account_id, symbol, side, new_limit_price, new_qty)) {
        append_ledger_entry(AccountLedgerEntry{0, account_id, symbol, "replace_stop_limit_rejected_risk_failure", 0, 0, 0, 0, id, std::nullopt});
        return {OrderRejected{side, new_limit_price, new_qty, *risk_failure, symbol}};
    }
    stop_it->second.stop_price = new_stop_price;
    stop_it->second.limit_price = new_limit_price;
    stop_it->second.qty = new_qty;
    std::vector<Event> events{OrderCanceled{id, symbol}, StopOrderAccepted{id, side, new_stop_price, new_qty, new_limit_price, symbol}};
    std::vector<Event> triggered = evaluate_stop_orders(symbol);
    events.insert(events.end(), triggered.begin(), triggered.end());
    track_events(events);
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

void MatchingEngine::track_events(const std::vector<Event>& events) {
    bump_sequence_number_from_events(events);
}

void MatchingEngine::bump_sequence_number_from_events(const std::vector<Event>& events) {
    for (const Event& event : events) {
        if (std::holds_alternative<OrderAccepted>(event)) {
            ++sequence_numbers_by_symbol_[std::get<OrderAccepted>(event).symbol];
        } else if (std::holds_alternative<StopOrderAccepted>(event)) {
            ++sequence_numbers_by_symbol_[std::get<StopOrderAccepted>(event).symbol];
        } else if (std::holds_alternative<StopOrderTriggered>(event)) {
            ++sequence_numbers_by_symbol_[std::get<StopOrderTriggered>(event).symbol];
        } else if (std::holds_alternative<OrderCanceled>(event)) {
            ++sequence_numbers_by_symbol_[std::get<OrderCanceled>(event).symbol];
        } else if (std::holds_alternative<TradeExecuted>(event)) {
            ++sequence_numbers_by_symbol_[std::get<TradeExecuted>(event).symbol];
        }
    }
}

BookSnapshot MatchingEngine::snapshot(std::size_t levels) const { return snapshot(kDefaultSymbol, levels); }

BookSnapshot MatchingEngine::snapshot(const Symbol& symbol, std::size_t levels) const {
    BookSnapshot result;
    result.symbol = symbol;
    result.sequence_number = sequence_number(symbol);
    const BookDepth book_depth = depth(symbol, levels);
    for (const auto& level : book_depth.bids) {
        result.bids.push_back(BookLevel{symbol, Side::Bid, level.price, level.qty});
    }
    for (const auto& level : book_depth.asks) {
        result.asks.push_back(BookLevel{symbol, Side::Ask, level.price, level.qty});
    }
    return result;
}

std::uint64_t MatchingEngine::sequence_number() const { return sequence_number(kDefaultSymbol); }

std::uint64_t MatchingEngine::sequence_number(const Symbol& symbol) const {
    const auto it = sequence_numbers_by_symbol_.find(symbol);
    return it == sequence_numbers_by_symbol_.end() ? 0 : it->second;
}

}  // namespace tes
