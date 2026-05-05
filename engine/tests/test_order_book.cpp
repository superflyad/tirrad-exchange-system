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

TEST_CASE("depth aggregate updates after partial fill") {
    tes::OrderBook book;
    (void)book.add_limit_order(tes::Order{1, tes::Side::Ask, tes::Price{100}, tes::Qty{7}});
    (void)book.fill_best(tes::Side::Ask, tes::Qty{3});

    const tes::OrderBook::Depth d = book.depth(1);
    REQUIRE(d.asks.size() == 1);
    CHECK(d.asks[0].price.ticks == 100);
    CHECK(d.asks[0].qty.value == 4);
}

TEST_CASE("depth aggregate updates after cancel") {
    tes::OrderBook book;
    (void)book.add_limit_order(tes::Order{1, tes::Side::Bid, tes::Price{99}, tes::Qty{2}});
    (void)book.add_limit_order(tes::Order{2, tes::Side::Bid, tes::Price{99}, tes::Qty{3}});

    (void)book.cancel(1);
    const tes::OrderBook::Depth d = book.depth(1);
    REQUIRE(d.bids.size() == 1);
    CHECK(d.bids[0].price.ticks == 99);
    CHECK(d.bids[0].qty.value == 3);
}

TEST_CASE("cancel first middle and last preserve fifo and invariants") {
    tes::OrderBook book;
    (void)book.add_limit_order(tes::Order{11, tes::Side::Bid, tes::Price{100}, tes::Qty{2}});
    (void)book.add_limit_order(tes::Order{12, tes::Side::Bid, tes::Price{100}, tes::Qty{3}});
    (void)book.add_limit_order(tes::Order{13, tes::Side::Bid, tes::Price{100}, tes::Qty{4}});

    (void)book.cancel(11);
    REQUIRE(book.front_of_level(tes::Side::Bid, tes::Price{100}).has_value());
    CHECK(book.front_of_level(tes::Side::Bid, tes::Price{100})->id == 12);
    CHECK(book.validate_invariants());

    (void)book.cancel(12);
    REQUIRE(book.front_of_level(tes::Side::Bid, tes::Price{100}).has_value());
    CHECK(book.front_of_level(tes::Side::Bid, tes::Price{100})->id == 13);
    CHECK(book.validate_invariants());

    (void)book.cancel(13);
    CHECK(book.level_size(tes::Side::Bid, tes::Price{100}) == 0);
    CHECK(book.validate_invariants());
}

TEST_CASE("find_order transitions through add cancel and fill") {
    tes::OrderBook book;
    (void)book.add_limit_order(tes::Order{21, tes::Side::Ask, tes::Price{101}, tes::Qty{5}});
    const auto found = book.find_order(21);
    REQUIRE(found.has_value());
    CHECK(found->qty.value == 5);

    (void)book.cancel(21);
    CHECK_FALSE(book.find_order(21).has_value());

    (void)book.add_limit_order(tes::Order{22, tes::Side::Ask, tes::Price{101}, tes::Qty{5}});
    (void)book.fill_best(tes::Side::Ask, tes::Qty{2});
    REQUIRE(book.find_order(22).has_value());
    CHECK(book.find_order(22)->qty.value == 3);
    (void)book.fill_best(tes::Side::Ask, tes::Qty{3});
    CHECK_FALSE(book.find_order(22).has_value());
    CHECK(book.validate_invariants());
}

TEST_CASE("aggregate qty stays correct after add cancel and partial fill") {
    tes::OrderBook book;
    (void)book.add_limit_order(tes::Order{31, tes::Side::Ask, tes::Price{105}, tes::Qty{6}});
    (void)book.add_limit_order(tes::Order{32, tes::Side::Ask, tes::Price{105}, tes::Qty{2}});
    (void)book.fill_best(tes::Side::Ask, tes::Qty{4});
    auto d = book.depth(1);
    REQUIRE(d.asks.size() == 1);
    CHECK(d.asks[0].qty.value == 4);
    (void)book.cancel(32);
    d = book.depth(1);
    REQUIRE(d.asks.size() == 1);
    CHECK(d.asks[0].qty.value == 2);
    CHECK(book.validate_invariants());
}
