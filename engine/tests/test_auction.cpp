#include <doctest.h>

#include <tes/matching_engine.hpp>

namespace {

template <typename T>
const T* find_event(const std::vector<tes::Event>& events) {
    for (const auto& event : events) {
        if (std::holds_alternative<T>(event)) return &std::get<T>(event);
    }
    return nullptr;
}

void seed_accounts(tes::MatchingEngine& engine) {
    engine.set_account_state(1, "XYZ", 1'000'000, 0);
    engine.set_account_state(2, "XYZ", 0, 1'000);
    engine.set_account_state(3, "ABC", 1'000'000, 0);
    engine.set_account_state(4, "ABC", 0, 1'000);
}

}  // namespace

TEST_CASE("continuous matching pauses and orders accumulate during auction") {
    tes::MatchingEngine engine;
    seed_accounts(engine);

    (void)engine.set_trading_phase("XYZ", tes::TradingPhase::OpeningAuction);
    auto sell = engine.place_limit_order(2, "XYZ", tes::Side::Ask, tes::Price{100}, tes::Qty{10});
    auto buy = engine.place_limit_order(1, "XYZ", tes::Side::Bid, tes::Price{105}, tes::Qty{6});

    CHECK(find_event<tes::TradeExecuted>(sell) == nullptr);
    CHECK(find_event<tes::TradeExecuted>(buy) == nullptr);
    CHECK(engine.depth("XYZ", 1).bids.front().qty.value == 6);
    CHECK(engine.depth("XYZ", 1).asks.front().qty.value == 10);
    REQUIRE(engine.indicative_price("XYZ").has_value());
    CHECK(engine.indicative_volume("XYZ").value == 6);
}

TEST_CASE("auction uncross executes deterministic clearing price and updates accounts") {
    tes::MatchingEngine engine;
    seed_accounts(engine);

    (void)engine.set_trading_phase("XYZ", tes::TradingPhase::OpeningAuction);
    (void)engine.place_limit_order(2, "XYZ", tes::Side::Ask, tes::Price{99}, tes::Qty{4});
    (void)engine.place_limit_order(2, "XYZ", tes::Side::Ask, tes::Price{101}, tes::Qty{4});
    (void)engine.place_limit_order(1, "XYZ", tes::Side::Bid, tes::Price{102}, tes::Qty{6});

    const auto price = engine.indicative_price("XYZ");
    REQUIRE(price.has_value());
    CHECK(price->ticks == 101);
    CHECK(engine.indicative_volume("XYZ").value == 6);

    auto events = engine.uncross("XYZ");
    const auto* uncross = find_event<tes::AuctionUncross>(events);
    REQUIRE(uncross != nullptr);
    CHECK(uncross->price.ticks == 101);
    CHECK(uncross->qty.value == 6);
    CHECK(find_event<tes::TradeExecuted>(events) != nullptr);
    CHECK(engine.trading_phase("XYZ") == tes::TradingPhase::Continuous);

    const auto buyer = engine.account_snapshot(1);
    const auto seller = engine.account_snapshot(2);
    CHECK(buyer.position_qty_by_symbol.at("XYZ") == 6);
    CHECK(buyer.cash_balance == 1'000'000 - (101 * 6));
    CHECK(seller.position_qty_by_symbol.at("XYZ") == 1'000 - 6);
    CHECK(seller.cash_balance == 101 * 6);
}

TEST_CASE("auction tie breaking minimizes imbalance and isolates symbols") {
    tes::MatchingEngine engine;
    seed_accounts(engine);

    (void)engine.set_trading_phase("XYZ", tes::TradingPhase::OpeningAuction);
    (void)engine.place_limit_order(1, "XYZ", tes::Side::Bid, tes::Price{110}, tes::Qty{10});
    (void)engine.place_limit_order(2, "XYZ", tes::Side::Ask, tes::Price{100}, tes::Qty{6});
    (void)engine.place_limit_order(2, "XYZ", tes::Side::Ask, tes::Price{105}, tes::Qty{4});
    CHECK(engine.indicative_price("XYZ")->ticks == 105);
    CHECK(engine.auction_imbalance("XYZ") == 0);

    (void)engine.set_trading_phase("ABC", tes::TradingPhase::OpeningAuction);
    (void)engine.place_limit_order(3, "ABC", tes::Side::Bid, tes::Price{50}, tes::Qty{1});
    (void)engine.place_limit_order(4, "ABC", tes::Side::Ask, tes::Price{50}, tes::Qty{1});
    (void)engine.uncross("ABC");
    CHECK(engine.depth("XYZ", 10).bids.front().qty.value == 10);
    CHECK(engine.indicative_volume("XYZ").value == 10);
}

TEST_CASE("cancel and replace work during auction") {
    tes::MatchingEngine engine;
    seed_accounts(engine);

    (void)engine.set_trading_phase("XYZ", tes::TradingPhase::ClosingAuction);
    auto accepted = engine.place_limit_order(1, "XYZ", tes::Side::Bid, tes::Price{100}, tes::Qty{5});
    const auto order_id = find_event<tes::OrderAccepted>(accepted)->id;
    auto replaced = engine.replace_order(1, order_id, tes::Price{101}, tes::Qty{7});
    CHECK(find_event<tes::OrderCanceled>(replaced) != nullptr);
    CHECK(find_event<tes::OrderAccepted>(replaced) != nullptr);
    CHECK(engine.depth("XYZ", 1).bids.front().price.ticks == 101);
    CHECK(engine.depth("XYZ", 1).bids.front().qty.value == 7);
    auto canceled = engine.cancel(1, order_id);
    CHECK(find_event<tes::OrderCanceled>(canceled) != nullptr);
    CHECK(engine.depth("XYZ", 1).bids.empty());
}
