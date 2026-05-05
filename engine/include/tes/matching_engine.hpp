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
    };
    struct AccountSnapshot {
        std::int64_t cash_balance = 0;
        std::unordered_map<Symbol, std::int64_t> position_qty_by_symbol;
        std::int64_t reserved_cash = 0;
        std::unordered_map<Symbol, std::int64_t> reserved_qty_by_symbol;
    };

    void set_account_state(AccountId account_id, std::int64_t cash_balance, std::int64_t position_qty);
    void set_account_state(AccountId account_id, const Symbol& symbol, std::int64_t cash_balance, std::int64_t position_qty);
    [[nodiscard]] AccountSnapshot account_snapshot(AccountId account_id) const;
    [[nodiscard]] std::vector<AccountLedgerEntry> account_ledger(AccountId account_id) const;
    [[nodiscard]] std::vector<AccountLedgerEntry> account_ledger(AccountId account_id, const Symbol& symbol) const;
    [[nodiscard]] AccountSnapshot latest_account_snapshot(AccountId account_id) const;
    [[nodiscard]] std::optional<AccountId> order_owner(OrderId id) const;

    [[nodiscard]] std::vector<Event> place_limit_order(Side side, Price price, Qty qty, TimeInForce tif = TimeInForce::Gtc);
    [[nodiscard]] std::vector<Event> place_limit_order(AccountId account_id, Side side, Price price, Qty qty, TimeInForce tif = TimeInForce::Gtc);
    [[nodiscard]] std::vector<Event> place_limit_order(AccountId account_id, const Symbol& symbol, Side side, Price price, Qty qty, TimeInForce tif = TimeInForce::Gtc);
    [[nodiscard]] std::vector<Event> place_market_order(Side side, Qty qty);
    [[nodiscard]] std::vector<Event> place_market_order(AccountId account_id, Side side, Qty qty);
    [[nodiscard]] std::vector<Event> place_market_order(AccountId account_id, const Symbol& symbol, Side side, Qty qty);
    [[nodiscard]] std::vector<Event> cancel(OrderId id);
    [[nodiscard]] std::vector<Event> cancel(AccountId account_id, OrderId id);
    [[nodiscard]] std::vector<Event> replace_order(OrderId id, Price new_price, Qty new_qty);
    [[nodiscard]] std::vector<Event> replace_order(AccountId account_id, OrderId id, Price new_price, Qty new_qty);
    [[nodiscard]] BookDepth depth(std::size_t levels) const;
    [[nodiscard]] BookDepth depth(const Symbol& symbol, std::size_t levels) const;
    [[nodiscard]] BookSnapshot snapshot(std::size_t levels) const;
    [[nodiscard]] BookSnapshot snapshot(const Symbol& symbol, std::size_t levels) const;
    [[nodiscard]] std::uint64_t sequence_number() const;
    [[nodiscard]] std::uint64_t sequence_number(const Symbol& symbol) const;

    [[nodiscard]] const OrderBook& book() const;

  private:
    struct OrderOwnership { AccountId account_id; Symbol symbol; Side side; Price price; Qty qty; };
    [[nodiscard]] std::vector<Event> place_limit_order_with_account_and_id(AccountId account_id, const Symbol& symbol, OrderId taker_id, Side side, Price price, Qty qty, TimeInForce tif);
    void maybe_emit_top_of_book_change(const Symbol& symbol, std::vector<Event>& events, const std::optional<Price>& previous_best_bid, const std::optional<Price>& previous_best_ask);
    [[nodiscard]] OrderBook& book_for(const Symbol& symbol);
    [[nodiscard]] const OrderBook* find_book(const Symbol& symbol) const;
    void track_events(const std::vector<Event>& events);
    void bump_sequence_number_from_events(const std::vector<Event>& events);
    void append_ledger_entry(const AccountLedgerEntry& entry);
    void assert_invariants(const Symbol& symbol, AccountId taker_account_id, AccountId maker_account_id,
                           std::int64_t notional, Side taker_side) const;

    std::unordered_map<Symbol, OrderBook> books_;
    OrderId next_order_id_ = 1;
    std::unordered_map<AccountId, AccountSnapshot> accounts_;
    std::unordered_map<OrderId, OrderOwnership> order_ownership_by_id_;
    std::unordered_map<OrderId, std::int64_t> reserved_cash_by_order_id_;
    std::unordered_map<OrderId, std::int64_t> reserved_qty_by_order_id_;
    std::unordered_map<Symbol, std::uint64_t> sequence_numbers_by_symbol_;
    std::vector<AccountLedgerEntry> account_ledger_;
    std::uint64_t next_ledger_sequence_ = 1;
};

}  // namespace tes
