#include <doctest.h>

#include <optional>
#include <variant>
#include <vector>

#include <tes/events.hpp>
#include <tes/matching_engine.hpp>

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

std::optional<tes::OrderAccepted> find_order_accepted(const std::vector<tes::Event>& events) {
    for (const tes::Event& event : events) {
        if (std::holds_alternative<tes::OrderAccepted>(event)) {
            return std::get<tes::OrderAccepted>(event);
        }
    }
    return std::nullopt;
}

std::optional<tes::TopOfBook> last_top_of_book(const std::vector<tes::Event>& events) {
    std::optional<tes::TopOfBook> result;
    for (const tes::Event& event : events) {
        if (std::holds_alternative<tes::TopOfBook>(event)) {
            result = std::get<tes::TopOfBook>(event);
        }
    }
    return result;
}

}  // namespace

TEST_CASE("full fill removes resting maker and does not rest taker") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{10});
    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{10});

    const std::vector<tes::TradeExecuted> trades = collect_trades(events);
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 10);
    CHECK(trades[0].taker_side == tes::Side::Bid);
    CHECK(trades[0].taker_id > trades[0].maker_id);

    CHECK_FALSE(find_order_accepted(events).has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
    CHECK_FALSE(engine.book().best_bid().has_value());
}

TEST_CASE("partial fill emits trade before order accepted for remainder") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{5});
    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{10});

    const std::vector<tes::TradeExecuted> trades = collect_trades(events);
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 5);

    bool seen_trade = false;
    bool seen_accept = false;
    tes::OrderAccepted accepted{};
    for (const tes::Event& event : events) {
        if (std::holds_alternative<tes::TradeExecuted>(event)) {
            seen_trade = true;
        }
        if (std::holds_alternative<tes::OrderAccepted>(event)) {
            seen_accept = true;
            accepted = std::get<tes::OrderAccepted>(event);
            CHECK(seen_trade);
            break;
        }
    }

    REQUIRE(seen_accept);
    CHECK(accepted.qty.value == 5);
    CHECK(accepted.side == tes::Side::Bid);
    CHECK(accepted.price.ticks == 100);

    REQUIRE(engine.book().best_bid().has_value());
    CHECK(engine.book().best_bid()->ticks == 100);
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("sweep multiple ask levels by price-time priority") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{5});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{5});

    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{101}, tes::Qty{10});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 2);
    CHECK(trades[0].price.ticks == 100);
    CHECK(trades[0].qty.value == 5);
    CHECK(trades[1].price.ticks == 101);
    CHECK(trades[1].qty.value == 5);
    CHECK(trades[0].maker_id < trades[1].maker_id);

    CHECK_FALSE(engine.book().best_ask().has_value());
    CHECK_FALSE(engine.book().best_bid().has_value());
}

TEST_CASE("fifo matching at same price level") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});

    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 2);
    CHECK(trades[0].maker_id < trades[1].maker_id);
    CHECK(trades[0].qty.value == 3);
    CHECK(trades[1].qty.value == 2);

    REQUIRE(engine.book().best_ask().has_value());
    CHECK(engine.book().best_ask()->ticks == 100);
    const std::optional<tes::Order> front = engine.book().front_of_level(tes::Side::Ask, tes::Price{100});
    REQUIRE(front.has_value());
    CHECK(front->qty.value == 1);
}

TEST_CASE("non crossing order rests without trade") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{105}, tes::Qty{5});
    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{104}, tes::Qty{5});

    CHECK(collect_trades(events).empty());

    const std::optional<tes::OrderAccepted> accepted = find_order_accepted(events);
    REQUIRE(accepted.has_value());
    CHECK(accepted->side == tes::Side::Bid);
    CHECK(accepted->price.ticks == 104);
    CHECK(accepted->qty.value == 5);

    const std::optional<tes::TopOfBook> top = last_top_of_book(events);
    REQUIRE(top.has_value());
    REQUIRE(top->best_bid.has_value());
    REQUIRE(top->best_ask.has_value());
    CHECK(top->best_bid->ticks == 104);
    CHECK(top->best_ask->ticks == 105);
}
