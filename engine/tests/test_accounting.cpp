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

TEST_CASE("zero fee preserves legacy settlement cash behavior") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 10'000, 10);
    engine.set_account_state(2, "AAA", 10'000, 0);
    (void)engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{2});
    (void)engine.place_limit_order(2, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{2});

    CHECK(engine.latest_account_snapshot(1).cash_balance == 10'200);
    CHECK(engine.latest_account_snapshot(2).cash_balance == 9'800);
    CHECK(engine.performance_snapshot(2).realized_pnl == doctest::Approx(0.0));
}

TEST_CASE("maker and taker fees are deducted and recorded") {
    tes::MatchingEngine engine;
    engine.set_fee_model(tes::MatchingEngine::FeeModel{0.01, 0.02, 1});
    engine.set_account_state(1, "AAA", 10'000, 10);
    engine.set_account_state(2, "AAA", 10'000, 0);
    (void)engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{10});
    (void)engine.place_limit_order(2, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{10});

    CHECK(engine.latest_account_snapshot(1).cash_balance == 10'989);
    CHECK(engine.latest_account_snapshot(2).cash_balance == 8'979);
    const auto seller_ledger = engine.account_ledger(1, "AAA");
    const auto buyer_ledger = engine.account_ledger(2, "AAA");
    CHECK(seller_ledger.back().reason == "fee");
    CHECK(seller_ledger.back().fee_delta == 11);
    CHECK(buyer_ledger.back().reason == "fee");
    CHECK(buyer_ledger.back().fee_delta == 21);
}

TEST_CASE("realized pnl is positive on profitable sell and negative on losing sell") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 100'000, 0);
    engine.set_account_state(2, "AAA", 100'000, 10);
    engine.set_account_state(3, "AAA", 100'000, 0);
    engine.set_account_state(4, "AAA", 100'000, 0);

    (void)engine.place_limit_order(2, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{10});
    (void)engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{10});
    (void)engine.place_limit_order(3, "AAA", tes::Side::Bid, tes::Price{120}, tes::Qty{5});
    (void)engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{120}, tes::Qty{5});
    CHECK(engine.performance_snapshot(1).realized_pnl == doctest::Approx(100.0));

    (void)engine.place_limit_order(4, "AAA", tes::Side::Bid, tes::Price{90}, tes::Qty{5});
    (void)engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{90}, tes::Qty{5});
    CHECK(engine.performance_snapshot(1).realized_pnl == doctest::Approx(50.0));
    CHECK(engine.performance_snapshot(1).realized_pnl_by_symbol.at("AAA") == doctest::Approx(50.0));
}

TEST_CASE("average cost updates across multiple buys") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 100'000, 0);
    engine.set_account_state(2, "AAA", 100'000, 4);
    engine.set_account_state(3, "AAA", 100'000, 4);

    (void)engine.place_limit_order(2, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{2});
    (void)engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{2});
    (void)engine.place_limit_order(3, "AAA", tes::Side::Ask, tes::Price{200}, tes::Qty{2});
    (void)engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{200}, tes::Qty{2});

    CHECK(engine.latest_account_snapshot(1).average_cost_by_symbol.at("AAA") == doctest::Approx(150.0));
}

TEST_CASE("unrealized pnl uses latest mark") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 100'000, 0);
    engine.set_account_state(2, "AAA", 100'000, 1);
    engine.set_account_state(3, "AAA", 100'000, 0);
    engine.set_account_state(4, "AAA", 100'000, 1);

    (void)engine.place_limit_order(2, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{1});
    (void)engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{1});
    (void)engine.place_limit_order(3, "AAA", tes::Side::Bid, tes::Price{120}, tes::Qty{1});
    (void)engine.place_limit_order(4, "AAA", tes::Side::Ask, tes::Price{140}, tes::Qty{1});

    const auto snapshot = engine.performance_snapshot(1);
    CHECK(snapshot.unrealized_pnl == doctest::Approx(30.0));
    CHECK(snapshot.total_equity == doctest::Approx(100'030.0));
}

TEST_CASE("margin account can buy beyond cash within leverage and rejects beyond leverage") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 10'000, 0);
    engine.set_account_risk_config(1, tes::MatchingEngine::AccountRiskConfig{tes::MatchingEngine::AccountRiskMode::Margin, false, 2.0, 0.5, 0.25, 1.0});

    const auto accepted = engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{150});
    REQUIRE(std::holds_alternative<tes::OrderAccepted>(accepted.front()));
    CHECK(engine.latest_account_snapshot(1).reserved_cash == 7'500);

    const auto rejected = engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{60});
    REQUIRE(std::holds_alternative<tes::OrderRejected>(rejected.front()));
    CHECK(std::get<tes::OrderRejected>(rejected.front()).reason == tes::RejectReason::InsufficientBuyingPower);
}

TEST_CASE("short-enabled account can sell without position and buy to cover") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 10'000, 0);
    engine.set_account_state(2, "AAA", 50'000, 0);
    engine.set_account_risk_config(1, tes::MatchingEngine::AccountRiskConfig{tes::MatchingEngine::AccountRiskMode::Margin, true, 2.0, 0.5, 0.25, 0.5});

    const auto short_order = engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{10});
    REQUIRE(std::holds_alternative<tes::OrderAccepted>(short_order.front()));
    CHECK(engine.latest_account_snapshot(1).reserved_short_margin == 500);

    const auto sell_id = std::get<tes::OrderAccepted>(short_order.front()).id;
    const auto fill_short = engine.place_limit_order(2, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{10});
    REQUIRE(std::holds_alternative<tes::TradeExecuted>(fill_short.front()));
    CHECK(engine.latest_account_snapshot(1).position_qty_by_symbol.at("AAA") == -10);
    CHECK(engine.latest_account_snapshot(1).reserved_short_margin == 0);

    engine.set_account_state(3, "AAA", 0, 10);
    (void)engine.place_limit_order(3, "AAA", tes::Side::Ask, tes::Price{90}, tes::Qty{5});
    const auto cover = engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{90}, tes::Qty{5});
    REQUIRE(std::holds_alternative<tes::TradeExecuted>(cover.front()));
    CHECK(engine.latest_account_snapshot(1).position_qty_by_symbol.at("AAA") == -5);
    CHECK(engine.performance_snapshot(1).realized_pnl == doctest::Approx(50.0));
    (void)sell_id;
}

TEST_CASE("short-disabled account rejects sell without position") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 10'000, 0);
    tes::MatchingEngine::AccountRiskConfig config;
    config.mode = tes::MatchingEngine::AccountRiskMode::Margin;
    config.allow_short_selling = false;
    engine.set_account_risk_config(1, config);
    const auto rejected = engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{1});
    REQUIRE(std::holds_alternative<tes::OrderRejected>(rejected.front()));
    CHECK(std::get<tes::OrderRejected>(rejected.front()).reason == tes::RejectReason::InsufficientPosition);
}

TEST_CASE("cancel and replace release margin and short reserves deterministically") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 10'000, 0);
    engine.set_account_risk_config(1, tes::MatchingEngine::AccountRiskConfig{tes::MatchingEngine::AccountRiskMode::Margin, true, 2.0, 0.5, 0.25, 0.5});

    const auto bid = engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{10});
    const auto bid_id = std::get<tes::OrderAccepted>(bid.front()).id;
    CHECK(engine.latest_account_snapshot(1).reserved_cash == 500);
    (void)engine.cancel(1, bid_id);
    CHECK(engine.latest_account_snapshot(1).reserved_cash == 0);

    const auto ask = engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{10});
    const auto ask_id = std::get<tes::OrderAccepted>(ask.front()).id;
    CHECK(engine.latest_account_snapshot(1).reserved_short_margin == 500);
    const auto replaced = engine.replace_order(1, ask_id, tes::Price{120}, tes::Qty{5});
    REQUIRE(std::holds_alternative<tes::OrderCanceled>(replaced.front()));
    CHECK(engine.latest_account_snapshot(1).reserved_short_margin == 300);
    (void)engine.cancel(1, ask_id);
    CHECK(engine.latest_account_snapshot(1).reserved_short_margin == 0);
}

TEST_CASE("failed replace does not mutate old order or reserves") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 10'000, 0);
    engine.set_account_risk_config(1, tes::MatchingEngine::AccountRiskConfig{tes::MatchingEngine::AccountRiskMode::Margin, false, 2.0, 0.5, 0.25, 1.0});
    const auto bid = engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{100});
    const auto bid_id = std::get<tes::OrderAccepted>(bid.front()).id;
    CHECK(engine.latest_account_snapshot(1).reserved_cash == 5'000);

    const auto rejected = engine.replace_order(1, bid_id, tes::Price{300}, tes::Qty{100});
    REQUIRE(std::holds_alternative<tes::OrderRejected>(rejected.front()));
    CHECK(engine.latest_account_snapshot(1).reserved_cash == 5'000);
    CHECK(engine.depth("AAA", 1).bids.front().price.ticks == 100);
}

TEST_CASE("margin snapshot aggregates multi-symbol exposure and maintenance breach") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 10'000, 0);
    engine.set_account_state(1, "BBB", 10'000, 0);
    engine.set_account_risk_config(1, tes::MatchingEngine::AccountRiskConfig{tes::MatchingEngine::AccountRiskMode::Margin, true, 2.0, 0.5, 0.25, 0.5});
    engine.set_account_state(2, "AAA", 10'000, 10);
    engine.set_account_state(3, "BBB", 10'000, 0);
    engine.set_account_risk_config(3, tes::MatchingEngine::AccountRiskConfig{tes::MatchingEngine::AccountRiskMode::Margin, true, 2.0, 0.5, 0.25, 0.5});
    (void)engine.place_limit_order(2, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{10});
    (void)engine.place_limit_order(1, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{10});
    (void)engine.place_limit_order(1, "BBB", tes::Side::Ask, tes::Price{200}, tes::Qty{5});
    (void)engine.place_limit_order(3, "BBB", tes::Side::Bid, tes::Price{200}, tes::Qty{5});
    const auto snapshot = engine.account_margin_snapshot(1);
    CHECK(snapshot.gross_exposure == doctest::Approx(2'000.0));
    CHECK(snapshot.short_exposure == doctest::Approx(1'000.0));
    CHECK(snapshot.maintenance_requirement == doctest::Approx(500.0));
    CHECK_FALSE(snapshot.margin_call);

    tes::MatchingEngine breached;
    breached.set_account_state(1, "AAA", -1'000, 10);
    breached.set_account_risk_config(1, tes::MatchingEngine::AccountRiskConfig{tes::MatchingEngine::AccountRiskMode::Margin, false, 2.0, 0.5, 0.8, 1.0});
    breached.set_account_state(2, "AAA", 10'000, 1);
    (void)breached.place_limit_order(2, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{1});
    CHECK(breached.account_margin_snapshot(1).margin_call);
}
