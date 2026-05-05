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
