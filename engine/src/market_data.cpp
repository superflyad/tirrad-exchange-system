#include <tes/market_data.hpp>

#include <algorithm>
#include <sstream>
#include <type_traits>

namespace tes {
namespace {
std::string event_name(const Event& event) {
    return std::visit([](const auto& evt) -> std::string {
        using T = std::decay_t<decltype(evt)>;
        if constexpr (std::is_same_v<T, OrderAccepted>) return "OrderAccepted";
        else if constexpr (std::is_same_v<T, OrderRejected>) return "OrderRejected";
        else if constexpr (std::is_same_v<T, OrderCanceled>) return "OrderCanceled";
        else if constexpr (std::is_same_v<T, CancelRejected>) return "CancelRejected";
        else if constexpr (std::is_same_v<T, TradeExecuted>) return "TradeExecuted";
        else if constexpr (std::is_same_v<T, OrderPartiallyFilled>) return "OrderPartiallyFilled";
        else if constexpr (std::is_same_v<T, OrderFilled>) return "OrderFilled";
        else if constexpr (std::is_same_v<T, OrderExpired>) return "OrderExpired";
        else if constexpr (std::is_same_v<T, StopOrderAccepted>) return "StopOrderAccepted";
        else if constexpr (std::is_same_v<T, StopOrderTriggered>) return "StopOrderTriggered";
        else return "TopOfBook";
    }, event);
}

std::string json_escape(const std::string& value) {
    std::string out;
    out.reserve(value.size());
    for (const char ch : value) {
        if (ch == '\\' || ch == '"') {
            out.push_back('\\');
        }
        out.push_back(ch);
    }
    return out;
}
}  // namespace

MarketDataRecorder::MarketDataRecorder(std::optional<std::size_t> max_records_per_symbol)
    : max_records_per_symbol_(max_records_per_symbol) {}

void MarketDataRecorder::record_snapshot(const BookSnapshot& snapshot) {
    append_record(MarketDataRecord{snapshot.symbol, snapshot.sequence_number, next_step_++, next_timestamp_++, snapshot.bids,
                                   snapshot.asks, {}});
}

void MarketDataRecorder::record_event_snapshot(const Symbol& symbol, std::uint64_t sequence_number,
                                               const std::vector<Event>& events, const BookSnapshot& snapshot) {
    std::vector<std::string> names;
    names.reserve(events.size());
    for (const auto& event : events) names.push_back(event_name(event));
    append_record(MarketDataRecord{symbol, sequence_number, next_step_++, next_timestamp_++, snapshot.bids, snapshot.asks,
                                   std::move(names)});
}

std::vector<MarketDataRecord> MarketDataRecorder::history(const Symbol& symbol) const {
    const auto it = records_by_symbol_.find(symbol);
    if (it == records_by_symbol_.end()) return {};
    return {it->second.begin(), it->second.end()};
}

std::optional<MarketDataRecord> MarketDataRecorder::latest(const Symbol& symbol) const {
    const auto it = records_by_symbol_.find(symbol);
    if (it == records_by_symbol_.end() || it->second.empty()) return std::nullopt;
    return it->second.back();
}

void MarketDataRecorder::clear(const Symbol& symbol) { records_by_symbol_.erase(symbol); }
void MarketDataRecorder::clear_all() { records_by_symbol_.clear(); }
std::size_t MarketDataRecorder::size(const Symbol& symbol) const {
    const auto it = records_by_symbol_.find(symbol);
    return it == records_by_symbol_.end() ? 0 : it->second.size();
}

std::vector<Symbol> MarketDataRecorder::symbols() const {
    std::vector<Symbol> out;
    out.reserve(records_by_symbol_.size());
    for (const auto& [symbol, _] : records_by_symbol_) out.push_back(symbol);
    std::sort(out.begin(), out.end());
    return out;
}

void MarketDataRecorder::append_record(MarketDataRecord&& record) {
    auto& dq = records_by_symbol_[record.symbol];
    dq.push_back(std::move(record));
    if (max_records_per_symbol_.has_value()) {
        while (dq.size() > *max_records_per_symbol_) dq.pop_front();
    }
}
MarketDataSummary MarketDataRecorder::summarize(const MarketDataRecord& record) {
    MarketDataSummary s;
    if (!record.bids.empty()) s.best_bid = record.bids.front().price.ticks;
    if (!record.asks.empty()) s.best_ask = record.asks.front().price.ticks;
    for (const auto& l : record.bids) s.total_bid_qty += l.qty.value;
    for (const auto& l : record.asks) s.total_ask_qty += l.qty.value;
    const auto total_qty = s.total_bid_qty + s.total_ask_qty;
    if (total_qty > 0) s.imbalance = static_cast<double>(s.total_bid_qty) / static_cast<double>(total_qty);
    if (s.best_bid.has_value() && s.best_ask.has_value()) {
        s.spread = *s.best_ask - *s.best_bid;
        s.mid_price = (static_cast<double>(*s.best_ask) + static_cast<double>(*s.best_bid)) / 2.0;
    }
    return s;
}

MarketDataSummary MarketDataRecorder::summary(const Symbol& symbol) const {
    const auto rec = latest(symbol);
    if (!rec.has_value()) return {};
    return summarize(*rec);
}
std::vector<std::optional<std::int64_t>> MarketDataRecorder::spread_series(const Symbol& symbol) const {
    std::vector<std::optional<std::int64_t>> out;
    for (const auto& rec : history(symbol)) out.push_back(summarize(rec).spread);
    return out;
}
std::vector<std::optional<double>> MarketDataRecorder::mid_price_series(const Symbol& symbol) const {
    std::vector<std::optional<double>> out;
    for (const auto& rec : history(symbol)) out.push_back(summarize(rec).mid_price);
    return out;
}
std::vector<std::uint64_t> MarketDataRecorder::sequence_series(const Symbol& symbol) const {
    std::vector<std::uint64_t> out;
    for (const auto& rec : history(symbol)) out.push_back(rec.sequence_number);
    return out;
}

std::string MarketDataRecorder::record_to_json(const MarketDataRecord& record) const {
    std::ostringstream out;
    out << "{\"symbol\":\"" << json_escape(record.symbol) << "\",\"sequence_number\":" << record.sequence_number
        << ",\"step\":" << record.step << ",\"timestamp\":" << record.timestamp << ",\"bids\":[";
    bool first = true;
    for (const auto& l : record.bids) {
        if (!first) out << ',';
        out << "{\"symbol\":\"" << json_escape(l.symbol) << "\",\"side\":\"BUY\",\"price\":" << l.price.ticks
            << ",\"qty\":" << l.qty.value << '}';
        first = false;
    }
    out << "],\"asks\":[";
    first = true;
    for (const auto& l : record.asks) {
        if (!first) out << ',';
        out << "{\"symbol\":\"" << json_escape(l.symbol) << "\",\"side\":\"SELL\",\"price\":" << l.price.ticks
            << ",\"qty\":" << l.qty.value << '}';
        first = false;
    }
    auto s = summarize(record);
    out << "],\"triggering_event_names\":[";
    for (std::size_t i = 0; i < record.triggering_event_names.size(); ++i) {
        if (i > 0) out << ',';
        out << "\"" << json_escape(record.triggering_event_names[i]) << "\"";
    }
    out << "],\"summary\":{";
    out << "\"best_bid\":" << (s.best_bid ? std::to_string(*s.best_bid) : "null") << ',';
    out << "\"best_ask\":" << (s.best_ask ? std::to_string(*s.best_ask) : "null") << ',';
    out << "\"mid_price\":" << (s.mid_price ? std::to_string(*s.mid_price) : "null") << ',';
    out << "\"spread\":" << (s.spread ? std::to_string(*s.spread) : "null") << ',';
    out << "\"total_bid_qty\":" << s.total_bid_qty << ',';
    out << "\"total_ask_qty\":" << s.total_ask_qty << ',';
    out << "\"imbalance\":" << (s.imbalance ? std::to_string(*s.imbalance) : "null");
    out << "}}";
    return out.str();
}
std::string MarketDataRecorder::history_to_json(const Symbol& symbol) const {
    std::ostringstream out;
    out << '[';
    const auto records = history(symbol);
    for (std::size_t i = 0; i < records.size(); ++i) {
        if (i > 0) out << ',';
        out << record_to_json(records[i]);
    }
    out << ']';
    return out.str();
}
std::string MarketDataRecorder::all_histories_to_json() const {
    std::ostringstream out;
    out << '{';
    auto syms = symbols();
    for (std::size_t i = 0; i < syms.size(); ++i) {
        if (i > 0) out << ',';
        out << "\"" << json_escape(syms[i]) << "\":" << history_to_json(syms[i]);
    }
    out << '}';
    return out.str();
}

}  // namespace tes
