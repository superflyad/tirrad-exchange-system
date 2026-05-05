#pragma once

#include <cstddef>
#include <cstdint>
#include <deque>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include <tes/events.hpp>
#include <tes/matching_engine.hpp>

namespace tes {

struct MarketDataRecord {
    Symbol symbol{kDefaultSymbol};
    std::uint64_t sequence_number{0};
    std::uint64_t step{0};
    std::uint64_t timestamp{0};
    std::vector<BookLevel> bids;
    std::vector<BookLevel> asks;
    std::vector<std::string> triggering_event_names;
};

struct MarketDataSummary {
    std::optional<std::int64_t> best_bid;
    std::optional<std::int64_t> best_ask;
    std::optional<double> mid_price;
    std::optional<std::int64_t> spread;
    std::int64_t total_bid_qty{0};
    std::int64_t total_ask_qty{0};
    std::optional<double> imbalance;
};

class MarketDataRecorder {
  public:
    explicit MarketDataRecorder(std::optional<std::size_t> max_records_per_symbol = std::nullopt);
    void record_snapshot(const BookSnapshot& snapshot);
    void record_event_snapshot(const Symbol& symbol, std::uint64_t sequence_number, const std::vector<Event>& events,
                               const BookSnapshot& snapshot);

    [[nodiscard]] std::vector<MarketDataRecord> history(const Symbol& symbol) const;
    [[nodiscard]] std::optional<MarketDataRecord> latest(const Symbol& symbol) const;
    void clear(const Symbol& symbol);
    void clear_all();
    [[nodiscard]] std::size_t size(const Symbol& symbol) const;
    [[nodiscard]] std::vector<Symbol> symbols() const;

    [[nodiscard]] MarketDataSummary summary(const Symbol& symbol) const;
    [[nodiscard]] std::vector<std::optional<std::int64_t>> spread_series(const Symbol& symbol) const;
    [[nodiscard]] std::vector<std::optional<double>> mid_price_series(const Symbol& symbol) const;
    [[nodiscard]] std::vector<std::uint64_t> sequence_series(const Symbol& symbol) const;

    [[nodiscard]] std::string record_to_json(const MarketDataRecord& record) const;
    [[nodiscard]] std::string history_to_json(const Symbol& symbol) const;
    [[nodiscard]] std::string all_histories_to_json() const;

  private:
    void append_record(MarketDataRecord&& record);
    static MarketDataSummary summarize(const MarketDataRecord& record);

    std::optional<std::size_t> max_records_per_symbol_;
    std::unordered_map<Symbol, std::deque<MarketDataRecord>> records_by_symbol_;
    std::uint64_t next_step_{1};
    std::uint64_t next_timestamp_{1};
};

}  // namespace tes
