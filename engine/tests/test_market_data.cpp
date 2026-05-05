#include <doctest.h>

#include <tes/market_data.hpp>
#include <tes/matching_engine.hpp>

TEST_CASE("market data recorder tracks symbol histories and analytics") {
    tes::MatchingEngine engine;
    tes::MarketDataRecorder recorder;

    engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{100}, tes::Qty{10});
    recorder.record_snapshot(engine.snapshot("AAA", 5));
    engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{103}, tes::Qty{7});
    recorder.record_snapshot(engine.snapshot("AAA", 5));
    engine.place_limit_order(0, "BBB", tes::Side::Bid, tes::Price{200}, tes::Qty{2});
    recorder.record_snapshot(engine.snapshot("BBB", 5));

    CHECK(recorder.size("AAA") == 2);
    CHECK(recorder.size("BBB") == 1);
    CHECK(recorder.latest("AAA")->sequence_number == 2);
    const auto summary = recorder.summary("AAA");
    CHECK(summary.best_bid == 100);
    CHECK(summary.best_ask == 103);
    CHECK(summary.spread == 3);
    CHECK(summary.total_bid_qty == 10);
    CHECK(summary.total_ask_qty == 7);
    CHECK(summary.mid_price.has_value());
    CHECK(doctest::Approx(*summary.mid_price) == 101.5);
    CHECK(summary.imbalance.has_value());
    CHECK(doctest::Approx(*summary.imbalance) == (10.0 / 17.0));

    const auto spreads = recorder.spread_series("AAA");
    CHECK(spreads.size() == 2);
    CHECK(spreads[0] == std::nullopt);
    CHECK(spreads[1] == 3);

    const auto mids = recorder.mid_price_series("AAA");
    CHECK(mids[0] == std::nullopt);
    CHECK(mids[1].has_value());

    recorder.clear("BBB");
    CHECK(recorder.size("BBB") == 0);
    recorder.clear_all();
    CHECK(recorder.size("AAA") == 0);
}

TEST_CASE("market data recorder bounded history trims oldest") {
    tes::MatchingEngine engine;
    tes::MarketDataRecorder recorder(2);
    for (int i = 0; i < 4; ++i) {
        engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{100 + i}, tes::Qty{1});
        recorder.record_snapshot(engine.snapshot("AAA", 1));
    }
    const auto hist = recorder.history("AAA");
    REQUIRE(hist.size() == 2);
    CHECK(hist[0].sequence_number == 3);
    CHECK(hist[1].sequence_number == 4);
}

TEST_CASE("market data deterministic json for same command stream") {
    auto run = []() {
        tes::MatchingEngine engine;
        tes::MarketDataRecorder recorder;
        engine.place_limit_order(0, "AAA", tes::Side::Ask, tes::Price{101}, tes::Qty{5});
        recorder.record_snapshot(engine.snapshot("AAA", 5));
        const auto events = engine.place_limit_order(0, "AAA", tes::Side::Bid, tes::Price{101}, tes::Qty{2});
        recorder.record_event_snapshot("AAA", engine.sequence_number("AAA"), events, engine.snapshot("AAA", 5));
        return recorder.all_histories_to_json();
    };

    const auto a = run();
    const auto b = run();
    CHECK(a == b);
    CHECK(a.find("\"symbol\":\"AAA\"") != std::string::npos);
    CHECK(a.find("\"sequence_number\":") != std::string::npos);
}
