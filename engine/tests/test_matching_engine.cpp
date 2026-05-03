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

TEST_CASE("incoming sell partially fills resting buy and remainder rests") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{10});
    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{15});

    const std::vector<tes::TradeExecuted> trades = collect_trades(events);
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 10);
    CHECK(trades[0].price.ticks == 100);
    CHECK(trades[0].taker_side == tes::Side::Ask);

    const std::optional<tes::OrderAccepted> accepted = find_order_accepted(events);
    REQUIRE(accepted.has_value());
    CHECK(accepted->side == tes::Side::Ask);
    CHECK(accepted->price.ticks == 100);
    CHECK(accepted->qty.value == 5);

    CHECK_FALSE(engine.book().best_bid().has_value());
    REQUIRE(engine.book().best_ask().has_value());
    CHECK(engine.book().best_ask()->ticks == 100);
}

TEST_CASE("incoming buy partially fills resting sell and remainder rests") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{10});
    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{15});

    const std::vector<tes::TradeExecuted> trades = collect_trades(events);
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 10);
    CHECK(trades[0].price.ticks == 100);
    CHECK(trades[0].taker_side == tes::Side::Bid);

    const std::optional<tes::OrderAccepted> accepted = find_order_accepted(events);
    REQUIRE(accepted.has_value());
    CHECK(accepted->side == tes::Side::Bid);
    CHECK(accepted->price.ticks == 100);
    CHECK(accepted->qty.value == 5);

    CHECK_FALSE(engine.book().best_ask().has_value());
    REQUIRE(engine.book().best_bid().has_value());
    CHECK(engine.book().best_bid()->ticks == 100);
}

TEST_CASE("incoming order fills multiple resting orders at same price in fifo") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{2});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{4});

    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{8});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 3);
    CHECK(trades[0].maker_id < trades[1].maker_id);
    CHECK(trades[1].maker_id < trades[2].maker_id);
    CHECK(trades[0].qty.value == 2);
    CHECK(trades[1].qty.value == 3);
    CHECK(trades[2].qty.value == 3);

    CHECK_FALSE(find_order_accepted(events).has_value());
    REQUIRE(engine.book().best_ask().has_value());
    CHECK(engine.book().best_ask()->ticks == 100);
    const std::optional<tes::Order> front = engine.book().front_of_level(tes::Side::Ask, tes::Price{100});
    REQUIRE(front.has_value());
    CHECK(front->qty.value == 1);
}

TEST_CASE("fully filled incoming order does not rest after sweeping multiple levels") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{2});

    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{101}, tes::Qty{5});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 2);
    CHECK(trades[0].price.ticks == 100);
    CHECK(trades[0].qty.value == 3);
    CHECK(trades[1].price.ticks == 101);
    CHECK(trades[1].qty.value == 2);

    CHECK_FALSE(find_order_accepted(events).has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
    CHECK_FALSE(engine.book().best_bid().has_value());
}

TEST_CASE("invalid price order is rejected") {
    tes::MatchingEngine engine;

    const std::vector<tes::Event> events = engine.place_limit_order(tes::Side::Bid, tes::Price{-1}, tes::Qty{5});

    REQUIRE(events.size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderRejected>(events[0]));
    const tes::OrderRejected rejected = std::get<tes::OrderRejected>(events[0]);
    CHECK(rejected.side == tes::Side::Bid);
    CHECK(rejected.price.ticks == -1);
    CHECK(rejected.qty.value == 5);
    CHECK(rejected.reason == tes::RejectReason::InvalidPrice);
    CHECK_FALSE(engine.book().best_bid().has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("invalid quantity order is rejected") {
    tes::MatchingEngine engine;

    const std::vector<tes::Event> zero_qty_events =
        engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{0});
    const std::vector<tes::Event> negative_qty_events =
        engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{-3});

    REQUIRE(zero_qty_events.size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderRejected>(zero_qty_events[0]));
    CHECK(std::get<tes::OrderRejected>(zero_qty_events[0]).reason == tes::RejectReason::InvalidQuantity);

    REQUIRE(negative_qty_events.size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderRejected>(negative_qty_events[0]));
    CHECK(std::get<tes::OrderRejected>(negative_qty_events[0]).reason == tes::RejectReason::InvalidQuantity);
    CHECK_FALSE(engine.book().best_bid().has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("cancel unknown order id is rejected") {
    tes::MatchingEngine engine;

    const std::vector<tes::Event> events = engine.cancel(999);

    REQUIRE(events.size() == 1);
    REQUIRE(std::holds_alternative<tes::CancelRejected>(events[0]));
    const tes::CancelRejected rejected = std::get<tes::CancelRejected>(events[0]);
    CHECK(rejected.id == 999);
    CHECK(rejected.reason == tes::RejectReason::UnknownOrderId);
}

TEST_CASE("cancel already canceled order id is rejected") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{2});

    const std::vector<tes::Event> first_cancel = engine.cancel(1);
    const std::vector<tes::Event> second_cancel = engine.cancel(1);

    REQUIRE(first_cancel.size() == 2);
    CHECK(std::holds_alternative<tes::OrderCanceled>(first_cancel[0]));
    CHECK(std::holds_alternative<tes::TopOfBook>(first_cancel[1]));
    REQUIRE(second_cancel.size() == 1);
    REQUIRE(std::holds_alternative<tes::CancelRejected>(second_cancel[0]));
    CHECK(std::get<tes::CancelRejected>(second_cancel[0]).id == 1);
    CHECK(std::get<tes::CancelRejected>(second_cancel[0]).reason == tes::RejectReason::UnknownOrderId);
}

TEST_CASE("cancel fully filled order id is rejected") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{5});
    const std::vector<tes::Event> trade_events = engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5});
    REQUIRE(collect_trades(trade_events).size() == 1);

    const std::vector<tes::Event> cancel_events = engine.cancel(1);
    REQUIRE(cancel_events.size() == 1);
    REQUIRE(std::holds_alternative<tes::CancelRejected>(cancel_events[0]));
    CHECK(std::get<tes::CancelRejected>(cancel_events[0]).id == 1);
    CHECK(std::get<tes::CancelRejected>(cancel_events[0]).reason == tes::RejectReason::UnknownOrderId);
}

TEST_CASE("cancel non-best order does not mutate top of book") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{101}, tes::Qty{1});
    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{1});

    const std::vector<tes::Event> cancel_events = engine.cancel(2);
    REQUIRE(cancel_events.size() == 1);
    CHECK(std::holds_alternative<tes::OrderCanceled>(cancel_events[0]));

    REQUIRE(engine.book().best_bid().has_value());
    CHECK(engine.book().best_bid()->ticks == 101);
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("depth on empty book is empty") {
    tes::MatchingEngine engine;

    const tes::BookDepth depth = engine.depth(5);
    CHECK(depth.bids.empty());
    CHECK(depth.asks.empty());
}

TEST_CASE("depth includes one bid level") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{101}, tes::Qty{7});

    const tes::BookDepth depth = engine.depth(5);
    REQUIRE(depth.bids.size() == 1);
    CHECK(depth.bids[0].price.ticks == 101);
    CHECK(depth.bids[0].qty.value == 7);
    CHECK(depth.asks.empty());
}

TEST_CASE("depth includes one ask level") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{102}, tes::Qty{4});

    const tes::BookDepth depth = engine.depth(5);
    REQUIRE(depth.asks.size() == 1);
    CHECK(depth.asks[0].price.ticks == 102);
    CHECK(depth.asks[0].qty.value == 4);
    CHECK(depth.bids.empty());
}

TEST_CASE("depth bids sorted descending by price") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{1});
    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{103}, tes::Qty{1});
    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{101}, tes::Qty{1});

    const tes::BookDepth depth = engine.depth(5);
    REQUIRE(depth.bids.size() == 3);
    CHECK(depth.bids[0].price.ticks == 103);
    CHECK(depth.bids[1].price.ticks == 101);
    CHECK(depth.bids[2].price.ticks == 100);
}

TEST_CASE("depth asks sorted ascending by price") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{105}, tes::Qty{1});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{1});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{103}, tes::Qty{1});

    const tes::BookDepth depth = engine.depth(5);
    REQUIRE(depth.asks.size() == 3);
    CHECK(depth.asks[0].price.ticks == 101);
    CHECK(depth.asks[1].price.ticks == 103);
    CHECK(depth.asks[2].price.ticks == 105);
}

TEST_CASE("depth aggregates quantities at same price") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{99}, tes::Qty{2});
    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{99}, tes::Qty{3});

    const tes::BookDepth depth = engine.depth(5);
    REQUIRE(depth.bids.size() == 1);
    CHECK(depth.bids[0].price.ticks == 99);
    CHECK(depth.bids[0].qty.value == 5);
}

TEST_CASE("depth obeys level limit and zero levels") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{1});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{102}, tes::Qty{1});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{103}, tes::Qty{1});

    const tes::BookDepth limited = engine.depth(2);
    REQUIRE(limited.asks.size() == 2);
    CHECK(limited.asks[0].price.ticks == 101);
    CHECK(limited.asks[1].price.ticks == 102);

    const tes::BookDepth zero = engine.depth(0);
    CHECK(zero.bids.empty());
    CHECK(zero.asks.empty());
}
