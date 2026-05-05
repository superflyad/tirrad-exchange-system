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
