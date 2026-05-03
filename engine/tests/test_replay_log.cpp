#include <doctest.h>

#include <vector>

#include <tes/events.hpp>
#include <tes/replay_log.hpp>
#include <tes/types.hpp>

TEST_CASE("replay log records commands in sequence") {
    tes::ReplayLog log;

    log.record(tes::LimitOrderCommand{tes::Side::Bid, tes::Price{101}, tes::Qty{3}},
               {tes::OrderAccepted{1, tes::Side::Bid, tes::Price{101}, tes::Qty{3}}});
    log.record(tes::CancelOrderCommand{1}, {tes::OrderCanceled{1}});

    REQUIRE(log.size() == 2);
    REQUIRE(std::holds_alternative<tes::LimitOrderCommand>(log.entries()[0].command));
    REQUIRE(std::holds_alternative<tes::CancelOrderCommand>(log.entries()[1].command));

    const tes::LimitOrderCommand first = std::get<tes::LimitOrderCommand>(log.entries()[0].command);
    CHECK(first.side == tes::Side::Bid);
    CHECK(first.price.ticks == 101);
    CHECK(first.qty.value == 3);

    const tes::CancelOrderCommand second = std::get<tes::CancelOrderCommand>(log.entries()[1].command);
    CHECK(second.id == 1);
}

TEST_CASE("replay log associates events with recorded command") {
    tes::ReplayLog log;

    std::vector<tes::Event> events{
        tes::TradeExecuted{2, 1, tes::Side::Bid, tes::Price{100}, tes::Qty{2}},
        tes::TopOfBook{std::nullopt, tes::Price{101}},
    };

    log.record(tes::MarketOrderCommand{tes::Side::Bid, tes::Qty{2}}, std::move(events));

    REQUIRE(log.size() == 1);
    REQUIRE(std::holds_alternative<tes::MarketOrderCommand>(log.entries()[0].command));
    REQUIRE(log.entries()[0].events.size() == 2);
    CHECK(std::holds_alternative<tes::TradeExecuted>(log.entries()[0].events[0]));
    CHECK(std::holds_alternative<tes::TopOfBook>(log.entries()[0].events[1]));
}

TEST_CASE("replay log preserves empty event lists") {
    tes::ReplayLog log;

    log.record(tes::CancelOrderCommand{42}, {});

    REQUIRE(log.size() == 1);
    CHECK(log.entries()[0].events.empty());
}
