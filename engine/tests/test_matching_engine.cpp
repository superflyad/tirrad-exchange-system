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

TEST_CASE("filled order cannot be canceled or replaced") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{5});
    const std::vector<tes::Event> fill_events = engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5});

    bool saw_fill = false;
    for (const tes::Event& event : fill_events) {
        if (std::holds_alternative<tes::OrderFilled>(event)) {
            saw_fill = true;
            break;
        }
    }
    REQUIRE(saw_fill);

    const std::vector<tes::Event> cancel_events = engine.cancel(2);
    REQUIRE(cancel_events.size() == 1);
    REQUIRE(std::holds_alternative<tes::CancelRejected>(cancel_events[0]));
    CHECK(std::get<tes::CancelRejected>(cancel_events[0]).id == 2);

    const std::vector<tes::Event> replace_events = engine.replace_order(2, tes::Price{101}, tes::Qty{5});
    REQUIRE(replace_events.size() == 1);
    REQUIRE(std::holds_alternative<tes::CancelRejected>(replace_events[0]));
    CHECK(std::get<tes::CancelRejected>(replace_events[0]).id == 2);
}

TEST_CASE("canceled orders cannot be reused by replace") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5});
    const std::vector<tes::Event> cancel_events = engine.cancel(1);
    REQUIRE(cancel_events.size() >= 1);
    REQUIRE(std::holds_alternative<tes::OrderCanceled>(cancel_events[0]));

    const std::vector<tes::Event> replace_events = engine.replace_order(1, tes::Price{99}, tes::Qty{5});
    REQUIRE(replace_events.size() == 1);
    REQUIRE(std::holds_alternative<tes::CancelRejected>(replace_events[0]));
    CHECK(std::get<tes::CancelRejected>(replace_events[0]).id == 1);
}


TEST_CASE("market buy sweeps asks from lowest price upward and never rests") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{2});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{102}, tes::Qty{4});

    const std::vector<tes::Event> events = engine.place_market_order(tes::Side::Bid, tes::Qty{7});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 3);
    CHECK(trades[0].price.ticks == 100);
    CHECK(trades[0].qty.value == 3);
    CHECK(trades[1].price.ticks == 101);
    CHECK(trades[1].qty.value == 2);
    CHECK(trades[2].price.ticks == 102);
    CHECK(trades[2].qty.value == 2);

    CHECK_FALSE(find_order_accepted(events).has_value());
    CHECK_FALSE(engine.book().best_bid().has_value());
    REQUIRE(engine.book().best_ask().has_value());
    CHECK(engine.book().best_ask()->ticks == 102);
}

TEST_CASE("market sell sweeps bids from highest price downward and never rests") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{99}, tes::Qty{2});
    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{101}, tes::Qty{3});
    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{4});

    const std::vector<tes::Event> events = engine.place_market_order(tes::Side::Ask, tes::Qty{8});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 3);
    CHECK(trades[0].price.ticks == 101);
    CHECK(trades[0].qty.value == 3);
    CHECK(trades[1].price.ticks == 100);
    CHECK(trades[1].qty.value == 4);
    CHECK(trades[2].price.ticks == 99);
    CHECK(trades[2].qty.value == 1);

    CHECK_FALSE(find_order_accepted(events).has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
    REQUIRE(engine.book().best_bid().has_value());
    CHECK(engine.book().best_bid()->ticks == 99);
}

TEST_CASE("market buy full fill") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{5});

    const std::vector<tes::Event> events = engine.place_market_order(tes::Side::Bid, tes::Qty{5});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 1);
    CHECK(trades[0].price.ticks == 100);
    CHECK(trades[0].qty.value == 5);
    CHECK(trades[0].taker_side == tes::Side::Bid);
    const std::optional<tes::TopOfBook> top = last_top_of_book(events);
    REQUIRE(top.has_value());
    CHECK_FALSE(top->best_ask.has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("market buy partial fill") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});

    const std::vector<tes::Event> events = engine.place_market_order(tes::Side::Bid, tes::Qty{5});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 3);
    CHECK_FALSE(find_order_accepted(events).has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
    CHECK_FALSE(engine.book().best_bid().has_value());
}

TEST_CASE("market sell full fill") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(tes::Side::Bid, tes::Price{99}, tes::Qty{4});

    const std::vector<tes::Event> events = engine.place_market_order(tes::Side::Ask, tes::Qty{4});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 1);
    CHECK(trades[0].price.ticks == 99);
    CHECK(trades[0].qty.value == 4);
    CHECK(trades[0].taker_side == tes::Side::Ask);
    CHECK_FALSE(engine.book().best_bid().has_value());
}

TEST_CASE("market order with no liquidity is rejected") {
    tes::MatchingEngine engine;

    const std::vector<tes::Event> events = engine.place_market_order(tes::Side::Bid, tes::Qty{5});

    REQUIRE(events.size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderRejected>(events[0]));
    CHECK(std::get<tes::OrderRejected>(events[0]).reason == tes::RejectReason::NoLiquidity);
}

TEST_CASE("market order invalid quantity is rejected") {
    tes::MatchingEngine engine;

    const std::vector<tes::Event> events = engine.place_market_order(tes::Side::Ask, tes::Qty{0});

    REQUIRE(events.size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderRejected>(events[0]));
    CHECK(std::get<tes::OrderRejected>(events[0]).reason == tes::RejectReason::InvalidQuantity);
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

TEST_CASE("fok full fill across one level") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{10});

    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{10}, tes::TimeInForce::Fok);
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 10);
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("fok full fill across multiple levels") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{2});

    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{101}, tes::Qty{5}, tes::TimeInForce::Fok);
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    REQUIRE(trades.size() == 2);
    CHECK(trades[0].price.ticks == 100);
    CHECK(trades[1].price.ticks == 101);
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("fok insufficient quantity does not mutate book") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{4});

    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5}, tes::TimeInForce::Fok);
    REQUIRE(events.size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderExpired>(events[0]));

    REQUIRE(engine.book().best_ask().has_value());
    CHECK(engine.book().best_ask()->ticks == 100);
    const std::optional<tes::Order> front = engine.book().front_of_level(tes::Side::Ask, tes::Price{100});
    REQUIRE(front.has_value());
    CHECK(front->qty.value == 4);
}

TEST_CASE("fok respects limit price") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{3});

    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{4}, tes::TimeInForce::Fok);
    REQUIRE(events.size() == 1);
    CHECK(std::holds_alternative<tes::OrderExpired>(events[0]));

    REQUIRE(engine.book().best_ask().has_value());
    CHECK(engine.book().best_ask()->ticks == 100);
    CHECK(engine.book().level_size(tes::Side::Ask, tes::Price{100}) == 1);
    CHECK(engine.book().level_size(tes::Side::Ask, tes::Price{101}) == 1);
}


TEST_CASE("gtc partial fill rests remainder") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5}, tes::TimeInForce::Gtc);

    const std::vector<tes::TradeExecuted> trades = collect_trades(events);
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 3);
    REQUIRE(find_order_accepted(events).has_value());

    REQUIRE(engine.book().best_bid().has_value());
    CHECK(engine.book().best_bid()->ticks == 100);
    const std::optional<tes::Order> resting = engine.book().front_of_level(tes::Side::Bid, tes::Price{100});
    REQUIRE(resting.has_value());
    CHECK(resting->qty.value == 2);
}

TEST_CASE("ioc full fill executes and does not rest") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{5});
    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5}, tes::TimeInForce::Ioc);

    const std::vector<tes::TradeExecuted> trades = collect_trades(events);
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 5);
    CHECK_FALSE(find_order_accepted(events).has_value());
    CHECK_FALSE(engine.book().best_bid().has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("ioc partial fill cancels remainder without resting") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5}, tes::TimeInForce::Ioc);

    const std::vector<tes::TradeExecuted> trades = collect_trades(events);
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].qty.value == 3);
    CHECK_FALSE(find_order_accepted(events).has_value());

    bool saw_cancel = false;
    for (const tes::Event& event : events) {
        if (std::holds_alternative<tes::OrderExpired>(event)) {
            saw_cancel = true;
        }
    }
    CHECK(saw_cancel);
    CHECK_FALSE(engine.book().best_bid().has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("ioc no fill does not rest") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{105}, tes::Qty{2});
    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{104}, tes::Qty{2}, tes::TimeInForce::Ioc);

    CHECK(collect_trades(events).empty());
    CHECK_FALSE(find_order_accepted(events).has_value());
    REQUIRE(events.size() == 1);
    CHECK(std::holds_alternative<tes::OrderExpired>(events[0]));
    CHECK_FALSE(engine.book().best_bid().has_value());
    REQUIRE(engine.book().best_ask().has_value());
    CHECK(engine.book().best_ask()->ticks == 105);
}

TEST_CASE("ioc does not cross beyond limit price") {
    tes::MatchingEngine engine;

    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{2});
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{101}, tes::Qty{2});

    const std::vector<tes::Event> events =
        engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{4}, tes::TimeInForce::Ioc);

    const std::vector<tes::TradeExecuted> trades = collect_trades(events);
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].price.ticks == 100);
    CHECK(trades[0].qty.value == 2);
    REQUIRE(engine.book().best_ask().has_value());
    CHECK(engine.book().best_ask()->ticks == 101);
    CHECK_FALSE(engine.book().best_bid().has_value());
}

TEST_CASE("replace order changes price level") {
    tes::MatchingEngine engine;

    const std::vector<tes::Event> add_events = engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{10});
    const tes::OrderAccepted accepted = std::get<tes::OrderAccepted>(add_events.front());

    const std::vector<tes::Event> replace_events = engine.replace_order(accepted.id, tes::Price{101}, tes::Qty{10});

    CHECK(std::holds_alternative<tes::OrderCanceled>(replace_events.front()));
    const std::optional<tes::OrderAccepted> replaced = find_order_accepted(replace_events);
    REQUIRE(replaced.has_value());
    CHECK(replaced->id == accepted.id);
    CHECK(replaced->price.ticks == 101);
    CHECK(engine.book().best_bid().has_value());
    CHECK(engine.book().best_bid()->ticks == 101);
}

TEST_CASE("replace order changes resting quantity") {
    tes::MatchingEngine engine;

    const std::vector<tes::Event> add_events = engine.place_limit_order(tes::Side::Ask, tes::Price{105}, tes::Qty{10});
    const tes::OrderAccepted accepted = std::get<tes::OrderAccepted>(add_events.front());

    (void)engine.replace_order(accepted.id, tes::Price{105}, tes::Qty{4});

    const tes::BookDepth depth = engine.depth(1);
    REQUIRE(depth.asks.size() == 1);
    CHECK(depth.asks[0].price.ticks == 105);
    CHECK(depth.asks[0].qty.value == 4);
}

TEST_CASE("replace order loses fifo priority at same price") {
    tes::MatchingEngine engine;

    const tes::OrderId first_id = std::get<tes::OrderAccepted>(
        engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3}).front())
                                     .id;
    const tes::OrderId second_id = std::get<tes::OrderAccepted>(
        engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{3}).front())
                                      .id;

    (void)engine.replace_order(first_id, tes::Price{100}, tes::Qty{3});

    const std::vector<tes::TradeExecuted> trades =
        collect_trades(engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{3}));
    REQUIRE(trades.size() == 1);
    CHECK(trades[0].maker_id == second_id);
}

TEST_CASE("replace unknown order rejects") {
    tes::MatchingEngine engine;

    const std::vector<tes::Event> events = engine.replace_order(999, tes::Price{100}, tes::Qty{1});
    REQUIRE(events.size() == 1);
    REQUIRE(std::holds_alternative<tes::CancelRejected>(events[0]));
    CHECK(std::get<tes::CancelRejected>(events[0]).reason == tes::RejectReason::UnknownOrderId);
}

TEST_CASE("replace invalid values reject without mutating book") {
    tes::MatchingEngine engine;

    const tes::OrderId id =
        std::get<tes::OrderAccepted>(engine.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{5}).front()).id;

    const std::vector<tes::Event> bad_price = engine.replace_order(id, tes::Price{-1}, tes::Qty{5});
    REQUIRE(bad_price.size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderRejected>(bad_price[0]));

    const std::vector<tes::Event> bad_qty = engine.replace_order(id, tes::Price{100}, tes::Qty{0});
    REQUIRE(bad_qty.size() == 1);
    REQUIRE(std::holds_alternative<tes::OrderRejected>(bad_qty[0]));

    const std::optional<tes::Order> front = engine.book().front_of_level(tes::Side::Bid, tes::Price{100});
    REQUIRE(front.has_value());
    CHECK(front->id == id);
    CHECK(front->qty.value == 5);
}

TEST_CASE("replace can execute immediately when crossing") {
    tes::MatchingEngine engine;

    const tes::OrderId bid_id =
        std::get<tes::OrderAccepted>(engine.place_limit_order(tes::Side::Bid, tes::Price{99}, tes::Qty{5}).front()).id;
    (void)engine.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{5});

    const std::vector<tes::Event> events = engine.replace_order(bid_id, tes::Price{100}, tes::Qty{5});
    const std::vector<tes::TradeExecuted> trades = collect_trades(events);

    CHECK(std::holds_alternative<tes::OrderCanceled>(events.front()));

    bool saw_trade = false;
    bool saw_fill = false;
    for (const tes::Event& event : events) {
        saw_trade = saw_trade || std::holds_alternative<tes::TradeExecuted>(event);
        saw_fill = saw_fill || std::holds_alternative<tes::OrderFilled>(event);
    }
    CHECK(saw_trade);
    CHECK(saw_fill);

    REQUIRE(trades.size() == 1);
    CHECK(trades[0].taker_id == bid_id);
    CHECK(trades[0].price.ticks == 100);
    CHECK_FALSE(engine.book().best_bid().has_value());
    CHECK_FALSE(engine.book().best_ask().has_value());
}

TEST_CASE("symbol-aware books isolate resting and crossing orders") {
    tes::MatchingEngine engine;

    const auto ask_a = engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{5});
    const auto bid_b = engine.place_limit_order(0, "BBB", tes::Side::Bid, tes::Price{100}, tes::Qty{5});

    CHECK(find_order_accepted(ask_a)->symbol == "AAA");
    CHECK(find_order_accepted(bid_b)->symbol == "BBB");
    CHECK(collect_trades(bid_b).empty());
    REQUIRE(engine.depth("AAA", 1).asks.size() == 1);
    REQUIRE(engine.depth("BBB", 1).bids.size() == 1);
    CHECK(engine.depth("AAA", 1).bids.empty());
    CHECK(engine.depth("BBB", 1).asks.empty());
}

TEST_CASE("snapshot empty and symbol isolated with level ordering and limits") {
    tes::MatchingEngine engine;
    const tes::BookSnapshot empty = engine.snapshot("AAA", 5);
    CHECK(empty.symbol == "AAA");
    CHECK(empty.sequence_number == 0);
    CHECK(empty.bids.empty());
    CHECK(empty.asks.empty());

    (void)engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{2});
    (void)engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{101}, tes::Qty{1});
    (void)engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{101}, tes::Qty{3});
    (void)engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{105}, tes::Qty{4});
    (void)engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{103}, tes::Qty{2});
    (void)engine.place_limit_order(0, "BBB", tes::Side::Ask, tes::Price{99}, tes::Qty{9});

    const tes::BookSnapshot limited = engine.snapshot("AAA", 1);
    REQUIRE(limited.bids.size() == 1);
    REQUIRE(limited.asks.size() == 1);
    CHECK(limited.bids[0].price.ticks == 101);
    CHECK(limited.bids[0].qty.value == 4);
    CHECK(limited.asks[0].price.ticks == 103);
    CHECK(limited.asks[0].qty.value == 2);
    CHECK(engine.snapshot("BBB", 5).bids.empty());
    CHECK(engine.snapshot("BBB", 5).asks[0].qty.value == 9);
}

TEST_CASE("sequence number increments on book-changing events only") {
    tes::MatchingEngine engine;
    CHECK(engine.sequence_number("AAA") == 0);

    (void)engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{5});
    CHECK(engine.sequence_number("AAA") == 1);

    (void)engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{2});
    CHECK(engine.sequence_number("AAA") == 2);

    const auto accepted = engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{105}, tes::Qty{3});
    const auto accepted_id = std::get<tes::OrderAccepted>(accepted.front()).id;
    CHECK(engine.sequence_number("AAA") == 3);

    (void)engine.cancel(0, accepted_id);
    CHECK(engine.sequence_number("AAA") == 4);

    const auto replace_add = engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{90}, tes::Qty{1});
    const auto replace_id = std::get<tes::OrderAccepted>(replace_add.front()).id;
    (void)engine.replace_order(0, replace_id, tes::Price{91}, tes::Qty{1});
    CHECK(engine.sequence_number("AAA") == 7);

    (void)engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{-1}, tes::Qty{1});
    CHECK(engine.sequence_number("AAA") == 7);
}

TEST_CASE("symbol-aware market ioc and fok route only to target symbol") {
    tes::MatchingEngine engine;
    (void)engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{100}, tes::Qty{3});
    (void)engine.place_limit_order(0, "BBB", tes::Side::Ask, tes::Price{99}, tes::Qty{3});

    const auto fok_fail = engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{99}, tes::Qty{1}, tes::TimeInForce::Fok);
    REQUIRE(fok_fail.size() == 1);
    CHECK(std::holds_alternative<tes::OrderExpired>(fok_fail.front()));
    CHECK(engine.depth("AAA", 1).asks.front().qty.value == 3);

    const auto ioc = engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{5}, tes::TimeInForce::Ioc);
    const auto ioc_trades = collect_trades(ioc);
    REQUIRE(ioc_trades.size() == 1);
    CHECK(ioc_trades.front().symbol == "AAA");
    CHECK(ioc_trades.front().qty.value == 3);
    CHECK(engine.depth("BBB", 1).asks.front().qty.value == 3);

    const auto market = engine.place_market_order(0, "BBB", tes::Side::Bid, tes::Qty{2});
    const auto market_trades = collect_trades(market);
    REQUIRE(market_trades.size() == 1);
    CHECK(market_trades.front().symbol == "BBB");
    CHECK(market_trades.front().price.ticks == 99);
}

TEST_CASE("account positions and sell risk are symbol-specific while cash is global") {
    tes::MatchingEngine engine;
    engine.set_account_state(1, "AAA", 1'000, 5);
    engine.set_account_state(1, "BBB", 1'000, 0);
    engine.set_account_state(2, "AAA", 1'000, 0);

    const auto sell_bbb = engine.place_limit_order(1, "BBB", tes::Side::Ask, tes::Price{10}, tes::Qty{1});
    REQUIRE(std::holds_alternative<tes::OrderRejected>(sell_bbb.front()));
    CHECK(std::get<tes::OrderRejected>(sell_bbb.front()).reason == tes::RejectReason::InsufficientPosition);

    (void)engine.place_limit_order(1, "AAA", tes::Side::Ask, tes::Price{10}, tes::Qty{2});
    (void)engine.place_limit_order(2, "AAA", tes::Side::Bid, tes::Price{10}, tes::Qty{2});

    const auto seller = engine.account_snapshot(1);
    const auto buyer = engine.account_snapshot(2);
    CHECK(seller.cash_balance == 1'020);
    CHECK(seller.position_qty_by_symbol.at("AAA") == 3);
    CHECK(seller.position_qty_by_symbol.at("BBB") == 0);
    CHECK(buyer.cash_balance == 980);
    CHECK(buyer.position_qty_by_symbol.at("AAA") == 2);
}

TEST_CASE("cancel routes by stored symbol and replace preserves symbol") {
    tes::MatchingEngine engine;
    const auto accepted = std::get<tes::OrderAccepted>(
        engine.place_limit_order(0, "ALT", tes::Side::Bid, tes::Price{100}, tes::Qty{4}).front());

    const auto replaced_events = engine.replace_order(0, accepted.id, tes::Price{101}, tes::Qty{4});
    const auto replaced = find_order_accepted(replaced_events);
    REQUIRE(replaced.has_value());
    CHECK(replaced->id == accepted.id);
    CHECK(replaced->symbol == "ALT");
    REQUIRE(engine.depth("ALT", 1).bids.size() == 1);
    CHECK(engine.depth(1).bids.empty());

    const auto canceled = engine.cancel(0, accepted.id);
    REQUIRE(std::holds_alternative<tes::OrderCanceled>(canceled.front()));
    CHECK(std::get<tes::OrderCanceled>(canceled.front()).symbol == "ALT");
    CHECK(engine.depth("ALT", 1).bids.empty());
}
