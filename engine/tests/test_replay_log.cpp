#include <doctest.h>

#include <vector>

#include <tes/events.hpp>
#include <tes/replay_log.hpp>
#include <tes/types.hpp>

namespace {

std::vector<tes::TradeExecuted> collect_trades(const std::vector<tes::Event>& events) {
    std::vector<tes::TradeExecuted> trades;
    for (const tes::Event& event : events) {
        if (std::holds_alternative<tes::TradeExecuted>(event)) {
            trades.push_back(std::get<tes::TradeExecuted>(event));
        }
    }
    return trades;
}

bool events_equal(const tes::Event& left, const tes::Event& right) {
    if (left.index() != right.index()) {
        return false;
    }
    return std::visit(
        [](const auto& lhs, const auto& rhs) {
            using L = std::decay_t<decltype(lhs)>;
            using R = std::decay_t<decltype(rhs)>;
            if constexpr (!std::is_same_v<L, R>) {
                return false;
            } else if constexpr (std::is_same_v<L, tes::OrderAccepted>) {
                return lhs.id == rhs.id && lhs.side == rhs.side && lhs.price.ticks == rhs.price.ticks &&
                       lhs.qty.value == rhs.qty.value && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::OrderRejected>) {
                return lhs.side == rhs.side && lhs.price.ticks == rhs.price.ticks && lhs.qty.value == rhs.qty.value &&
                       lhs.reason == rhs.reason && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::OrderCanceled>) {
                return lhs.id == rhs.id && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::CancelRejected>) {
                return lhs.id == rhs.id && lhs.reason == rhs.reason && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::TradeExecuted>) {
                return lhs.taker_id == rhs.taker_id && lhs.maker_id == rhs.maker_id && lhs.taker_side == rhs.taker_side &&
                       lhs.price.ticks == rhs.price.ticks && lhs.qty.value == rhs.qty.value && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::OrderPartiallyFilled>) {
                return lhs.id == rhs.id && lhs.last_fill_qty.value == rhs.last_fill_qty.value &&
                       lhs.remaining_qty.value == rhs.remaining_qty.value && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::OrderFilled>) {
                return lhs.id == rhs.id && lhs.last_fill_qty.value == rhs.last_fill_qty.value &&
                       lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::OrderExpired>) {
                return lhs.id == rhs.id && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::StopOrderAccepted>) {
                return lhs.id == rhs.id && lhs.side == rhs.side && lhs.stop_price.ticks == rhs.stop_price.ticks &&
                       lhs.qty.value == rhs.qty.value && lhs.limit_price == rhs.limit_price && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::StopOrderTriggered>) {
                return lhs.id == rhs.id && lhs.resulting_order_id == rhs.resulting_order_id && lhs.side == rhs.side &&
                       lhs.stop_price.ticks == rhs.stop_price.ticks && lhs.qty.value == rhs.qty.value &&
                       lhs.limit_price == rhs.limit_price && lhs.symbol == rhs.symbol;
            } else if constexpr (std::is_same_v<L, tes::TopOfBook>) {
                return lhs.best_bid == rhs.best_bid && lhs.best_ask == rhs.best_ask && lhs.symbol == rhs.symbol;
            } else {
                return lhs == rhs;
            }
        },
        left, right);
}

}

TEST_CASE("replay log records commands in sequence") {
    tes::ReplayLog log;

    log.record(tes::LimitOrderCommand{tes::Side::Bid, tes::Price{101}, tes::Qty{3}},
               {tes::OrderAccepted{1, tes::Side::Bid, tes::Price{101}, tes::Qty{3}}});
    log.record(tes::CancelOrderCommand{1}, {tes::OrderCanceled{1}});

    REQUIRE(log.size() == 2);
    REQUIRE(std::holds_alternative<tes::LimitOrderCommand>(log.entries()[0].command));
    REQUIRE(std::holds_alternative<tes::CancelOrderCommand>(log.entries()[1].command));
    CHECK(log.entries()[0].sequence == 0);
    CHECK(log.entries()[1].sequence == 1);

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

TEST_CASE("replay log serializes entries with sequence command and events") {
    tes::ReplayLog log;

    log.record(tes::LimitOrderCommand{tes::Side::Ask, tes::Price{104}, tes::Qty{7}},
               {tes::OrderAccepted{7, tes::Side::Ask, tes::Price{104}, tes::Qty{7}},
                tes::TopOfBook{std::nullopt, tes::Price{104}}});
    log.record(tes::CancelOrderCommand{7}, {});

    const std::string serialized = log.to_json();

    CHECK(serialized ==
          "[{\"sequence\":0,\"command\":{\"type\":\"LimitOrderCommand\",\"data\":{\"side\":\"Ask\",\"price\":104,\"qty\":7,\"time_in_force\":\"GTC\",\"symbol\":\"DEFAULT\"}},\"events\":[{\"type\":\"OrderAccepted\",\"data\":{\"symbol\":\"DEFAULT\"}},{\"type\":\"TopOfBook\",\"data\":{\"symbol\":\"DEFAULT\"}}]},{\"sequence\":1,\"command\":{\"type\":\"CancelOrderCommand\",\"data\":{\"id\":7}},\"events\":[]}]");
}

TEST_CASE("replay commands re-executes stream and reproduces recorded events") {
    tes::MatchingEngine engine;
    tes::ReplayLog log;

    std::vector<tes::Event> first = engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{4});
    log.record(tes::LimitOrderCommand{tes::Side::Ask, tes::Price{101}, tes::Qty{4}}, first);

    std::vector<tes::Event> second = engine.place_limit_order(tes::Side::Bid, tes::Price{101}, tes::Qty{2});
    log.record(tes::LimitOrderCommand{tes::Side::Bid, tes::Price{101}, tes::Qty{2}}, second);

    std::vector<tes::Event> third = engine.cancel(1);
    log.record(tes::CancelOrderCommand{1}, third);

    const std::vector<std::vector<tes::Event>> replayed = tes::replay_commands(log.entries());

    REQUIRE(replayed.size() == log.entries().size());
    for (std::size_t index = 0; index < replayed.size(); ++index) {
        const std::vector<tes::Event>& original = log.entries()[index].events;
        const std::vector<tes::Event>& replay = replayed[index];
        REQUIRE(replay.size() == original.size());
        for (std::size_t event_index = 0; event_index < replay.size(); ++event_index) {
            CHECK(events_equal(replay[event_index], original[event_index]));
        }
    }
}

TEST_CASE("replay preserves limit-order time in force to avoid FOK drift") {
    tes::MatchingEngine engine;
    tes::ReplayLog log;

    std::vector<tes::Event> resting = engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{1});
    log.record(tes::LimitOrderCommand{tes::Side::Ask, tes::Price{100}, tes::Qty{1}, "AAA"}, resting);

    std::vector<tes::Event> fok = engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{2},
                                                           tes::TimeInForce::Fok);
    log.record(tes::LimitOrderCommand{tes::Side::Bid, tes::Price{100}, tes::Qty{2}, "AAA", tes::TimeInForce::Fok}, fok);

    const std::string json = log.to_json();
    CHECK(json.find("\"time_in_force\":\"FOK\"") != std::string::npos);

    const std::vector<std::vector<tes::Event>> replayed = tes::replay_commands(log.entries());
    REQUIRE(replayed.size() == 2);
    REQUIRE(replayed[1].size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderExpired>(replayed[1].front()));
    CHECK(events_equal(replayed[1].front(), fok.front()));
}

TEST_CASE("replay serializes and replays symbol-aware commands and events") {
    tes::ReplayLog log;
    log.record(tes::LimitOrderCommand{tes::Side::Ask, tes::Price{100}, tes::Qty{2}, "AAA"},
               {tes::OrderAccepted{1, tes::Side::Ask, tes::Price{100}, tes::Qty{2}, "AAA"}});
    log.record(tes::LimitOrderCommand{tes::Side::Bid, tes::Price{100}, tes::Qty{2}, "BBB"},
               {tes::OrderAccepted{2, tes::Side::Bid, tes::Price{100}, tes::Qty{2}, "BBB"}});

    const std::string json = log.to_json();
    CHECK(json.find("\"symbol\":\"AAA\"") != std::string::npos);
    CHECK(json.find("\"symbol\":\"BBB\"") != std::string::npos);

    const auto replayed = tes::replay_commands(log.entries());
    REQUIRE(replayed.size() == 2);
    CHECK(collect_trades(replayed[1]).empty());
    REQUIRE(std::holds_alternative<tes::OrderAccepted>(replayed[0].front()));
    CHECK(std::get<tes::OrderAccepted>(replayed[0].front()).symbol == "AAA");
    REQUIRE(std::holds_alternative<tes::OrderAccepted>(replayed[1].front()));
    CHECK(std::get<tes::OrderAccepted>(replayed[1].front()).symbol == "BBB");
}

TEST_CASE("replay log replays auction phase and uncross deterministically") {
    tes::ReplayLog log;
    log.record(tes::SetTradingPhaseCommand{"DEFAULT", tes::TradingPhase::OpeningAuction},
               {tes::AuctionStarted{"DEFAULT", tes::TradingPhase::OpeningAuction}});
    log.record(tes::LimitOrderCommand{tes::Side::Ask, tes::Price{100}, tes::Qty{2}},
               {tes::OrderAccepted{1, tes::Side::Ask, tes::Price{100}, tes::Qty{2}}});
    log.record(tes::LimitOrderCommand{tes::Side::Bid, tes::Price{101}, tes::Qty{2}},
               {tes::OrderAccepted{2, tes::Side::Bid, tes::Price{101}, tes::Qty{2}}});
    log.record(tes::AuctionUncrossCommand{"DEFAULT"},
               {tes::AuctionUncross{"DEFAULT", tes::Price{100}, tes::Qty{2}, 0}});

    const auto replayed = tes::replay_commands(log.entries());
    REQUIRE(replayed.size() == 4);
    CHECK(std::holds_alternative<tes::AuctionStarted>(replayed[0][0]));
    CHECK(std::holds_alternative<tes::OrderAccepted>(replayed[1][0]));
    CHECK(std::holds_alternative<tes::OrderAccepted>(replayed[2][0]));
    CHECK(std::holds_alternative<tes::AuctionUncross>(replayed[3][0]));
    CHECK(std::get<tes::AuctionUncross>(replayed[3][0]).qty.value == 2);
    CHECK(collect_trades(replayed[3]).size() == 1);
}

TEST_CASE("replay preserves hidden submissions and iceberg replenishment deterministically") {
    tes::MatchingEngine engine;
    tes::ReplayLog log;

    auto hidden = engine.place_hidden_order(0, "AAA", tes::Side::Ask, tes::Price{99}, tes::Qty{1});
    log.record(tes::HiddenOrderCommand{tes::Side::Ask, tes::Price{99}, tes::Qty{1}, "AAA"}, hidden);
    auto iceberg = engine.place_iceberg_order(0, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{5}, tes::Qty{2});
    log.record(tes::IcebergOrderCommand{tes::Side::Ask, tes::Price{100}, tes::Qty{5}, tes::Qty{2}, "AAA"}, iceberg);
    auto sweep = engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{3});
    log.record(tes::LimitOrderCommand{tes::Side::Bid, tes::Price{100}, tes::Qty{3}, "AAA"}, sweep);

    const std::string json = log.to_json();
    CHECK(json.find("HiddenOrderCommand") != std::string::npos);
    CHECK(json.find("IcebergOrderCommand") != std::string::npos);
    CHECK(json.find("IcebergReplenished") != std::string::npos);

    const auto replayed = tes::replay_commands(log.entries());
    REQUIRE(replayed.size() == log.entries().size());
    for (std::size_t index = 0; index < replayed.size(); ++index) {
        REQUIRE(replayed[index].size() == log.entries()[index].events.size());
        for (std::size_t event_index = 0; event_index < replayed[index].size(); ++event_index) {
            CHECK(events_equal(replayed[index][event_index], log.entries()[index].events[event_index]));
        }
    }
}

TEST_CASE("replay preserves halt resume and price band commands") {
    tes::MatchingEngine engine;
    tes::ReplayLog log;

    auto bands = engine.set_price_bands("AAA", tes::Price{95}, tes::Price{105});
    log.record(tes::SetPriceBandsCommand{"AAA", tes::Price{95}, tes::Price{105}}, bands);
    auto halt = engine.halt_symbol("AAA", "news");
    log.record(tes::HaltSymbolCommand{"AAA", "news"}, halt);
    auto rejected = engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{1});
    log.record(tes::LimitOrderCommand{tes::Side::Bid, tes::Price{100}, tes::Qty{1}, "AAA"}, rejected);
    auto resumed = engine.resume_symbol("AAA");
    log.record(tes::ResumeSymbolCommand{"AAA"}, resumed);
    auto cleared = engine.clear_price_bands("AAA");
    log.record(tes::ClearPriceBandsCommand{"AAA"}, cleared);

    const auto replayed = tes::replay_commands(log.entries());
    REQUIRE(replayed.size() == log.entries().size());
    CHECK(std::holds_alternative<tes::PriceBandUpdated>(replayed[0].front()));
    CHECK(std::holds_alternative<tes::SymbolHalted>(replayed[1].front()));
    REQUIRE(std::holds_alternative<tes::OrderRejected>(replayed[2].front()));
    CHECK(std::get<tes::OrderRejected>(replayed[2].front()).reason == tes::RejectReason::SymbolHalted);
    CHECK(std::holds_alternative<tes::SymbolResumed>(replayed[3].front()));
    CHECK(std::holds_alternative<tes::PriceBandUpdated>(replayed[4].front()));
}
