#pragma once

#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include <tes/events.hpp>
#include <tes/order_book.hpp>
#include <tes/types.hpp>

namespace tes {

struct PriceLevel { Price price; Qty qty; };
struct BookDepth { std::vector<PriceLevel> bids; std::vector<PriceLevel> asks; };
struct BookLevel {
    Symbol symbol{kDefaultSymbol};
    Side side{Side::Bid};
    Price price{};
    Qty qty{};
};
struct BookSnapshot {
    Symbol symbol{kDefaultSymbol};
    std::vector<BookLevel> bids;
    std::vector<BookLevel> asks;
    std::uint64_t sequence_number{0};
};

class MatchingEngine {
  public:
    enum class AccountRiskMode { CashOnly, Margin };
    struct AccountRiskConfig {
        AccountRiskMode mode = AccountRiskMode::CashOnly;
        bool allow_short_selling = false;
        double max_leverage = 1.0;
        double initial_margin_requirement = 1.0;
        double maintenance_margin_requirement = 1.0;
        double short_margin_requirement = 1.0;
        std::unordered_map<Symbol, double> initial_margin_requirement_by_symbol;
        std::unordered_map<Symbol, double> maintenance_margin_requirement_by_symbol;
        std::unordered_map<Symbol, double> short_margin_requirement_by_symbol;
    };
    struct MarginSnapshot {
        double gross_exposure = 0.0;
        double net_liquidation_value = 0.0;
        double equity = 0.0;
        double margin_used = 0.0;
        double available_buying_power = 0.0;
        double short_exposure = 0.0;
        double maintenance_requirement = 0.0;
        bool margin_call = false;
    };
    struct FeeModel {
        double maker_fee_rate = 0.0;
        double taker_fee_rate = 0.0;
        std::optional<std::int64_t> fixed_fee;
    };
    struct AccountLedgerEntry {
        std::uint64_t sequence = 0;
        AccountId account_id = 0;
        Symbol symbol{kDefaultSymbol};
        std::string reason;
        std::int64_t cash_delta = 0;
        std::int64_t position_delta = 0;
        std::int64_t reserved_cash_delta = 0;
        std::int64_t reserved_position_delta = 0;
        std::optional<OrderId> related_order_id;
        std::optional<OrderId> related_trade_id;
        std::int64_t fee_delta = 0;
    };
    struct AccountSnapshot {
        std::int64_t cash_balance = 0;
        std::unordered_map<Symbol, std::int64_t> position_qty_by_symbol;
        std::int64_t reserved_cash = 0;
        std::unordered_map<Symbol, std::int64_t> reserved_qty_by_symbol;
        std::int64_t reserved_short_margin = 0;
        std::unordered_map<Symbol, double> average_cost_by_symbol;
        std::unordered_map<Symbol, double> realized_pnl_by_symbol;
        double realized_pnl = 0.0;
    };
    struct PerformanceSnapshot {
        std::int64_t cash_balance = 0;
        std::int64_t reserved_cash = 0;
        std::unordered_map<Symbol, std::int64_t> position_qty_by_symbol;
        std::unordered_map<Symbol, double> average_cost_by_symbol;
        double realized_pnl = 0.0;
        std::unordered_map<Symbol, double> realized_pnl_by_symbol;
        std::unordered_map<Symbol, double> unrealized_pnl_by_symbol;
        double unrealized_pnl = 0.0;
        double total_equity = 0.0;
    };

    void set_fee_model(FeeModel fee_model);
    void set_account_risk_config(AccountId account_id, AccountRiskConfig config);
    [[nodiscard]] AccountRiskConfig account_risk_config(AccountId account_id) const;
    [[nodiscard]] double account_buying_power(AccountId account_id) const;
    [[nodiscard]] MarginSnapshot account_margin_snapshot(AccountId account_id) const;
    [[nodiscard]] FeeModel fee_model() const;
    void set_account_state(AccountId account_id, std::int64_t cash_balance, std::int64_t position_qty);
    void set_account_state(AccountId account_id, const Symbol& symbol, std::int64_t cash_balance, std::int64_t position_qty);
    [[nodiscard]] AccountSnapshot account_snapshot(AccountId account_id) const;
    [[nodiscard]] std::vector<AccountLedgerEntry> account_ledger(AccountId account_id) const;
    [[nodiscard]] std::vector<AccountLedgerEntry> account_ledger(AccountId account_id, const Symbol& symbol) const;
    [[nodiscard]] AccountSnapshot latest_account_snapshot(AccountId account_id) const;
    [[nodiscard]] PerformanceSnapshot performance_snapshot(AccountId account_id) const;
    [[nodiscard]] std::optional<AccountId> order_owner(OrderId id) const;

    [[nodiscard]] std::vector<Event> place_limit_order(Side side, Price price, Qty qty, TimeInForce tif = TimeInForce::Gtc);
    [[nodiscard]] std::vector<Event> place_limit_order(AccountId account_id, Side side, Price price, Qty qty, TimeInForce tif = TimeInForce::Gtc);
    [[nodiscard]] std::vector<Event> place_limit_order(AccountId account_id, const Symbol& symbol, Side side, Price price, Qty qty, TimeInForce tif = TimeInForce::Gtc);
    [[nodiscard]] std::vector<Event> place_market_order(Side side, Qty qty);
    [[nodiscard]] std::vector<Event> place_market_order(AccountId account_id, Side side, Qty qty);
    [[nodiscard]] std::vector<Event> place_market_order(AccountId account_id, const Symbol& symbol, Side side, Qty qty);
    [[nodiscard]] std::vector<Event> place_stop_order(Side side, Price stop_price, Qty qty);
    [[nodiscard]] std::vector<Event> place_stop_order(AccountId account_id, Side side, Price stop_price, Qty qty);
    [[nodiscard]] std::vector<Event> place_stop_order(AccountId account_id, const Symbol& symbol, Side side, Price stop_price, Qty qty);
    [[nodiscard]] std::vector<Event> place_stop_limit_order(Side side, Price stop_price, Price limit_price, Qty qty);
    [[nodiscard]] std::vector<Event> place_stop_limit_order(AccountId account_id, Side side, Price stop_price, Price limit_price, Qty qty);
    [[nodiscard]] std::vector<Event> place_stop_limit_order(AccountId account_id, const Symbol& symbol, Side side, Price stop_price, Price limit_price, Qty qty);
    [[nodiscard]] std::vector<Event> cancel(OrderId id);
    [[nodiscard]] std::vector<Event> cancel(AccountId account_id, OrderId id);
    [[nodiscard]] std::vector<Event> replace_order(OrderId id, Price new_price, Qty new_qty);
    [[nodiscard]] std::vector<Event> replace_order(AccountId account_id, OrderId id, Price new_price, Qty new_qty);
    [[nodiscard]] std::vector<Event> replace_stop_order(OrderId id, Price new_stop_price, Qty new_qty);
    [[nodiscard]] std::vector<Event> replace_stop_order(AccountId account_id, OrderId id, Price new_stop_price, Qty new_qty);
    [[nodiscard]] std::vector<Event> replace_stop_limit_order(OrderId id, Price new_stop_price, Price new_limit_price, Qty new_qty);
    [[nodiscard]] std::vector<Event> replace_stop_limit_order(AccountId account_id, OrderId id, Price new_stop_price, Price new_limit_price, Qty new_qty);
    [[nodiscard]] BookDepth depth(std::size_t levels) const;
    [[nodiscard]] BookDepth depth(const Symbol& symbol, std::size_t levels) const;
    [[nodiscard]] BookSnapshot snapshot(std::size_t levels) const;
    [[nodiscard]] BookSnapshot snapshot(const Symbol& symbol, std::size_t levels) const;
    [[nodiscard]] std::uint64_t sequence_number() const;
    [[nodiscard]] std::uint64_t sequence_number(const Symbol& symbol) const;

    [[nodiscard]] const OrderBook& book() const;

  private:
    struct OrderOwnership { AccountId account_id; Symbol symbol; Side side; Price price; Qty qty; };
    struct StopOrderState { AccountId account_id; Symbol symbol; Side side; Price stop_price; Qty qty; std::optional<Price> limit_price; OrderId sequence; };
    [[nodiscard]] std::vector<Event> place_limit_order_with_account_and_id(AccountId account_id, const Symbol& symbol, OrderId taker_id, Side side, Price price, Qty qty, TimeInForce tif);
    [[nodiscard]] std::vector<Event> place_market_order_with_account_and_id(AccountId account_id, const Symbol& symbol, OrderId taker_id, Side side, Qty qty);
    [[nodiscard]] std::vector<Event> place_stop_order_with_account_and_id(AccountId account_id, const Symbol& symbol, OrderId stop_id, Side side, Price stop_price, Qty qty, std::optional<Price> limit_price);
    [[nodiscard]] std::vector<Event> evaluate_stop_orders(const Symbol& symbol);
    [[nodiscard]] std::optional<Price> trigger_price(const Symbol& symbol) const;
    void maybe_emit_top_of_book_change(const Symbol& symbol, std::vector<Event>& events, const std::optional<Price>& previous_best_bid, const std::optional<Price>& previous_best_ask);
    [[nodiscard]] OrderBook& book_for(const Symbol& symbol);
    [[nodiscard]] const OrderBook* find_book(const Symbol& symbol) const;
    void track_events(const std::vector<Event>& events);
    void bump_sequence_number_from_events(const std::vector<Event>& events);
    void append_ledger_entry(const AccountLedgerEntry& entry);
    void assert_invariants(const Symbol& symbol, AccountId taker_account_id, AccountId maker_account_id) const;
    [[nodiscard]] std::int64_t fee_for_notional(std::int64_t notional, bool maker) const;
    void apply_position_accounting(AccountSnapshot& account, const Symbol& symbol, Side side, Price price, Qty qty, std::int64_t fee);
    [[nodiscard]] std::optional<double> mark_price(const Symbol& symbol) const;
    [[nodiscard]] AccountRiskConfig effective_risk_config(AccountId account_id) const;
    [[nodiscard]] double initial_margin_requirement(const AccountRiskConfig& config, const Symbol& symbol) const;
    [[nodiscard]] double maintenance_margin_requirement(const AccountRiskConfig& config, const Symbol& symbol) const;
    [[nodiscard]] double short_margin_requirement(const AccountRiskConfig& config, const Symbol& symbol) const;
    [[nodiscard]] std::int64_t buy_reserve(AccountId account_id, const Symbol& symbol, Price price, Qty qty, std::int64_t fee) const;
    [[nodiscard]] std::int64_t short_margin_reserve(AccountId account_id, const Symbol& symbol, Price price, std::int64_t short_qty) const;
    [[nodiscard]] std::optional<RejectReason> validate_order_risk(AccountId account_id, const Symbol& symbol, Side side, Price price, Qty qty, std::optional<OrderId> replacing_order_id = std::nullopt) const;

    std::unordered_map<Symbol, OrderBook> books_;
    OrderId next_order_id_ = 1;
    std::unordered_map<AccountId, AccountSnapshot> accounts_;
    std::unordered_map<OrderId, OrderOwnership> order_ownership_by_id_;
    std::unordered_map<OrderId, StopOrderState> stop_orders_by_id_;
    std::unordered_map<Symbol, std::vector<OrderId>> pending_stop_ids_by_symbol_;
    std::unordered_map<OrderId, std::int64_t> reserved_cash_by_order_id_;
    std::unordered_map<OrderId, std::int64_t> reserved_qty_by_order_id_;
    std::unordered_map<OrderId, std::int64_t> reserved_short_margin_by_order_id_;
    std::unordered_map<AccountId, AccountRiskConfig> risk_configs_;
    std::unordered_map<Symbol, std::uint64_t> sequence_numbers_by_symbol_;
    std::vector<AccountLedgerEntry> account_ledger_;
    std::uint64_t next_ledger_sequence_ = 1;
    FeeModel fee_model_{};
    std::unordered_map<Symbol, double> latest_mark_by_symbol_;
};

}  // namespace tes
