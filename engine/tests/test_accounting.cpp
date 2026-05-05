#include <doctest.h>
#include <tes/matching_engine.hpp>

TEST_CASE("buy rejected with insufficient cash") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, 100, 0);
    const auto events = engine.place_limit_order(1, tes::Side::Bid, tes::Price{50}, tes::Qty{3});
    REQUIRE(std::holds_alternative<tes::OrderRejected>(events[0]));
    CHECK(std::get<tes::OrderRejected>(events[0]).reason == tes::RejectReason::InsufficientCash);
}

TEST_CASE("sell rejected with insufficient position") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, 0, 1);
    const auto events = engine.place_limit_order(1, tes::Side::Ask, tes::Price{10}, tes::Qty{2});
    REQUIRE(std::holds_alternative<tes::OrderRejected>(events[0]));
    CHECK(std::get<tes::OrderRejected>(events[0]).reason == tes::RejectReason::InsufficientPosition);
}

TEST_CASE("sell reserves release only for the order symbol") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 1'000, 5);
    engine.set_account_state(1, "BBB", 1'000, 1);

    const auto resting_aaa = engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{10}, tes::Qty{4});
    REQUIRE(std::holds_alternative<tes::OrderAccepted>(resting_aaa.front()));

    const auto blocked_aaa = engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{11}, tes::Qty{2});
    REQUIRE(std::holds_alternative<tes::OrderRejected>(blocked_aaa.front()));
    CHECK(std::get<tes::OrderRejected>(blocked_aaa.front()).reason == tes::RejectReason::InsufficientPosition);

    const auto resting_bbb = engine.place_limit_order(1, "BBB", tes::Side::Ask, tes::Price{20}, tes::Qty{1});
    REQUIRE(std::holds_alternative<tes::OrderAccepted>(resting_bbb.front()));

    const auto aaa_id = std::get<tes::OrderAccepted>(resting_aaa.front()).id;
    const auto canceled_aaa = engine.cancel(1, aaa_id);
    REQUIRE(std::holds_alternative<tes::OrderCanceled>(canceled_aaa.front()));

    const auto released_aaa = engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{12}, tes::Qty{5});
    REQUIRE(std::holds_alternative<tes::OrderAccepted>(released_aaa.front()));

    const auto still_blocked_bbb = engine.place_limit_order(1, "BBB", tes::Side::Ask, tes::Price{21}, tes::Qty{1});
    REQUIRE(std::holds_alternative<tes::OrderRejected>(still_blocked_bbb.front()));
    CHECK(std::get<tes::OrderRejected>(still_blocked_bbb.front()).reason == tes::RejectReason::InsufficientPosition);
}

TEST_CASE("ledger records reserves and settlement and filtering") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 10'000, 10);
    engine.set_account_state(2, "AAA", 10'000, 10);
    const auto ask = engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{2});
    const auto bid = engine.place_limit_order(2, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{2});
    REQUIRE(std::holds_alternative<tes::OrderAccepted>(ask.front()));
    REQUIRE(std::holds_alternative<tes::TradeExecuted>(bid.front()));

    const auto seller_ledger = engine.account_ledger(1, "AAA");
    const auto buyer_ledger = engine.account_ledger(2, "AAA");
    CHECK(seller_ledger.size() >= 2);
    CHECK(buyer_ledger.size() >= 1);
    CHECK(seller_ledger.front().reason == "order_accepted_reserve");
    CHECK(buyer_ledger.front().reason == "trade_settlement");
}

TEST_CASE("cancel and replace create release trail once") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 1'000, 10);
    const auto accepted = engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{101}, tes::Qty{5});
    const auto id = std::get<tes::OrderAccepted>(accepted.front()).id;
    (void)engine.replace_order(1, id, tes::Price{102}, tes::Qty{4});
    (void)engine.cancel(1, id);
    const auto ledger = engine.account_ledger(1, "AAA");
    std::size_t releases = 0;
    for (const auto& e : ledger) if (e.reason == "cancel_release") ++releases;
    CHECK(releases == 2);
}

TEST_CASE("risk rejection creates audit entry") {
    tes::MatchingEngine engine;
    engine.set_account_state(7, "BBB", 5, 0);
    (void)engine.place_limit_order(7, "BBB", tes::Side::Bid, tes::Price{10}, tes::Qty{1});
    const auto ledger = engine.account_ledger(7, "BBB");
    REQUIRE(!ledger.empty());
    CHECK(ledger.back().reason == "order_rejected_risk_failure");
}
