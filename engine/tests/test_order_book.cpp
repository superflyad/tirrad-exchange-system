#include <doctest.h>

#include <optional>
#include <variant>

#include <tes/events.hpp>
#include <tes/order.hpp>
#include <tes/order_book.hpp>

namespace {

bool is_top_of_book(const tes::Event& event) {
    return std::holds_alternative<tes::TopOfBook>(event);
}

}  // namespace

TEST_CASE("add single bid sets best bid") {
    tes::OrderBook book;

    const std::vector<tes::Event> events =
        book.add_limit_order(tes::Order{1, tes::Side::Bid, tes::Price{100}, tes::Qty{10}});

    REQUIRE(events.size() == 2);
    CHECK(std::holds_alternative<tes::OrderAccepted>(events[0]));

    REQUIRE(std::holds_alternative<tes::TopOfBook>(events[1]));
    const tes::TopOfBook top = std::get<tes::TopOfBook>(events[1]);
    REQUIRE(top.best_bid.has_value());
    CHECK(top.best_bid->ticks == 100);
    CHECK_FALSE(top.best_ask.has_value());

    REQUIRE(book.best_bid().has_value());
    CHECK(book.best_bid()->ticks == 100);
}

TEST_CASE("add two bids at same price preserves fifo") {
    tes::OrderBook book;

    const std::vector<tes::Event> first_events =
        book.add_limit_order(tes::Order{1, tes::Side::Bid, tes::Price{101}, tes::Qty{3}});
    const std::vector<tes::Event> second_events =
        book.add_limit_order(tes::Order{2, tes::Side::Bid, tes::Price{101}, tes::Qty{5}});

    REQUIRE(first_events.size() == 2);
    CHECK(is_top_of_book(first_events[1]));

    REQUIRE(second_events.size() == 1);
    CHECK(std::holds_alternative<tes::OrderAccepted>(second_events[0]));

    const std::optional<tes::Order> front = book.front_of_level(tes::Side::Bid, tes::Price{101});
    REQUIRE(front.has_value());
    CHECK(front->id == 1);
    CHECK(book.level_size(tes::Side::Bid, tes::Price{101}) == 2);
}

TEST_CASE("add better bid updates best bid") {
    tes::OrderBook book;

    const std::vector<tes::Event> first_events =
        book.add_limit_order(tes::Order{1, tes::Side::Bid, tes::Price{100}, tes::Qty{1}});
    const std::vector<tes::Event> second_events =
        book.add_limit_order(tes::Order{2, tes::Side::Bid, tes::Price{101}, tes::Qty{1}});

    REQUIRE(first_events.size() == 2);
    REQUIRE(second_events.size() == 2);
    CHECK(std::holds_alternative<tes::OrderAccepted>(second_events[0]));
    REQUIRE(std::holds_alternative<tes::TopOfBook>(second_events[1]));

    const tes::TopOfBook top = std::get<tes::TopOfBook>(second_events[1]);
    REQUIRE(top.best_bid.has_value());
    CHECK(top.best_bid->ticks == 101);
}

TEST_CASE("add ask sets best ask") {
    tes::OrderBook book;

    const std::vector<tes::Event> events =
        book.add_limit_order(tes::Order{7, tes::Side::Ask, tes::Price{104}, tes::Qty{2}});

    REQUIRE(events.size() == 2);
    CHECK(std::holds_alternative<tes::OrderAccepted>(events[0]));
    REQUIRE(std::holds_alternative<tes::TopOfBook>(events[1]));

    const tes::TopOfBook top = std::get<tes::TopOfBook>(events[1]);
    CHECK_FALSE(top.best_bid.has_value());
    REQUIRE(top.best_ask.has_value());
    CHECK(top.best_ask->ticks == 104);
}

TEST_CASE("cancel removes order correctly") {
    tes::OrderBook book;
    (void)book.add_limit_order(tes::Order{10, tes::Side::Bid, tes::Price{100}, tes::Qty{2}});

    const std::vector<tes::Event> events = book.cancel(10);

    REQUIRE(events.size() == 2);
    REQUIRE(std::holds_alternative<tes::OrderCanceled>(events[0]));
    CHECK(std::get<tes::OrderCanceled>(events[0]).id == 10);
    REQUIRE(std::holds_alternative<tes::TopOfBook>(events[1]));

    const tes::TopOfBook top = std::get<tes::TopOfBook>(events[1]);
    CHECK_FALSE(top.best_bid.has_value());
    CHECK_FALSE(top.best_ask.has_value());
    CHECK(book.level_size(tes::Side::Bid, tes::Price{100}) == 0);
}

TEST_CASE("cancel non-existent returns no events") {
    tes::OrderBook book;

    const std::vector<tes::Event> events = book.cancel(999);

    CHECK(events.empty());
}

TEST_CASE("canceling last order removes price level") {
    tes::OrderBook book;
    (void)book.add_limit_order(tes::Order{1, tes::Side::Ask, tes::Price{105}, tes::Qty{3}});
    (void)book.add_limit_order(tes::Order{2, tes::Side::Ask, tes::Price{105}, tes::Qty{4}});

    const std::vector<tes::Event> first_cancel = book.cancel(1);
    REQUIRE(first_cancel.size() == 1);
    CHECK(std::holds_alternative<tes::OrderCanceled>(first_cancel[0]));
    CHECK(book.level_size(tes::Side::Ask, tes::Price{105}) == 1);
    REQUIRE(book.best_ask().has_value());
    CHECK(book.best_ask()->ticks == 105);

    const std::vector<tes::Event> second_cancel = book.cancel(2);
    REQUIRE(second_cancel.size() == 2);
    CHECK(std::holds_alternative<tes::OrderCanceled>(second_cancel[0]));
    REQUIRE(std::holds_alternative<tes::TopOfBook>(second_cancel[1]));
    CHECK(book.level_size(tes::Side::Ask, tes::Price{105}) == 0);
    CHECK_FALSE(book.best_ask().has_value());
}
