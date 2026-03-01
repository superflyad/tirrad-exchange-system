#include <doctest.h>

#include <tes/events.hpp>
#include <tes/format.hpp>
#include <tes/types.hpp>

TEST_CASE("tes::is_valid_price validates zero and negative ticks") {
    CHECK(tes::is_valid_price(tes::Price{0}));
    CHECK(tes::is_valid_price(tes::Price{42}));
    CHECK_FALSE(tes::is_valid_price(tes::Price{-1}));
}

TEST_CASE("tes::is_valid_qty validates strictly positive quantities") {
    CHECK(tes::is_valid_qty(tes::Qty{1}));
    CHECK(tes::is_valid_qty(tes::Qty{99}));
    CHECK_FALSE(tes::is_valid_qty(tes::Qty{0}));
    CHECK_FALSE(tes::is_valid_qty(tes::Qty{-7}));
}

TEST_CASE("tes::to_string(Side) returns canonical names") {
    CHECK(tes::to_string(tes::Side::Bid) == "Bid");
    CHECK(tes::to_string(tes::Side::Ask) == "Ask");
}

TEST_CASE("tes::to_string(Event) formats all event variants") {
    const tes::Event accepted = tes::OrderAccepted{7, tes::Side::Bid, tes::Price{101}, tes::Qty{3}};
    const std::string accepted_text = tes::to_string(accepted);
    CHECK_FALSE(accepted_text.empty());
    CHECK(accepted_text.find("OrderAccepted") != std::string::npos);
    CHECK(accepted_text.find("id=7") != std::string::npos);
    CHECK(accepted_text.find("side=Bid") != std::string::npos);

    const tes::Event canceled = tes::OrderCanceled{11};
    const std::string canceled_text = tes::to_string(canceled);
    CHECK_FALSE(canceled_text.empty());
    CHECK(canceled_text.find("OrderCanceled") != std::string::npos);
    CHECK(canceled_text.find("id=11") != std::string::npos);

    const tes::Event trade = tes::TradeExecuted{13, 5, tes::Side::Ask, tes::Price{99}, tes::Qty{4}};
    const std::string trade_text = tes::to_string(trade);
    CHECK_FALSE(trade_text.empty());
    CHECK(trade_text.find("TradeExecuted") != std::string::npos);
    CHECK(trade_text.find("taker_id=13") != std::string::npos);
    CHECK(trade_text.find("maker_id=5") != std::string::npos);

    const tes::Event top = tes::TopOfBook{tes::Price{100}, std::nullopt};
    const std::string top_text = tes::to_string(top);
    CHECK_FALSE(top_text.empty());
    CHECK(top_text.find("TopOfBook") != std::string::npos);
    CHECK(top_text.find("best_bid=100") != std::string::npos);
    CHECK(top_text.find("best_ask=nullopt") != std::string::npos);
}
