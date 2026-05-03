#pragma once

#include <cstddef>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

#include <tes/events.hpp>
#include <tes/types.hpp>

namespace tes {

struct LimitOrderCommand {
    Side side;
    Price price;
    Qty qty;
};

struct MarketOrderCommand {
    Side side;
    Qty qty;
};

struct CancelOrderCommand {
    OrderId id;
};

using ReplayCommand = std::variant<LimitOrderCommand, MarketOrderCommand, CancelOrderCommand>;

struct ReplayEntry {
    std::size_t sequence;
    ReplayCommand command;
    std::vector<Event> events;
};

[[nodiscard]] inline std::string json_escape(std::string_view value) {
    std::ostringstream out;
    for (const char ch : value) {
        switch (ch) {
            case '\\':
                out << "\\\\";
                break;
            case '"':
                out << "\\\"";
                break;
            case '\n':
                out << "\\n";
                break;
            case '\r':
                out << "\\r";
                break;
            case '\t':
                out << "\\t";
                break;
            default:
                out << ch;
                break;
        }
    }
    return out.str();
}

[[nodiscard]] inline const char* event_type_name(const Event& event) {
    return std::visit(
        [](const auto& value) -> const char* {
            using T = std::decay_t<decltype(value)>;
            if constexpr (std::is_same_v<T, OrderAccepted>) return "OrderAccepted";
            if constexpr (std::is_same_v<T, OrderRejected>) return "OrderRejected";
            if constexpr (std::is_same_v<T, OrderCanceled>) return "OrderCanceled";
            if constexpr (std::is_same_v<T, CancelRejected>) return "CancelRejected";
            if constexpr (std::is_same_v<T, TradeExecuted>) return "TradeExecuted";
            if constexpr (std::is_same_v<T, OrderPartiallyFilled>) return "OrderPartiallyFilled";
            if constexpr (std::is_same_v<T, OrderFilled>) return "OrderFilled";
            if constexpr (std::is_same_v<T, OrderExpired>) return "OrderExpired";
            if constexpr (std::is_same_v<T, TopOfBook>) return "TopOfBook";
            return "Unknown";
        },
        event);
}

[[nodiscard]] inline std::string serialize_replay_event(const Event& event) {
    std::ostringstream out;
    out << "{\"type\":\"" << event_type_name(event) << "\",\"data\":{}}";
    return out.str();
}

[[nodiscard]] inline std::string serialize_replay_command(const ReplayCommand& command) {
    return std::visit(
        [](const auto& value) {
            using T = std::decay_t<decltype(value)>;
            std::ostringstream out;
            if constexpr (std::is_same_v<T, LimitOrderCommand>) {
                out << "{\"type\":\"LimitOrderCommand\",\"data\":{\"side\":\""
                    << (value.side == Side::Bid ? "Bid" : "Ask") << "\",\"price\":"
                    << value.price.ticks << ",\"qty\":" << value.qty.value << "}}";
            } else if constexpr (std::is_same_v<T, MarketOrderCommand>) {
                out << "{\"type\":\"MarketOrderCommand\",\"data\":{\"side\":\""
                    << (value.side == Side::Bid ? "Bid" : "Ask") << "\",\"qty\":" << value.qty.value
                    << "}}";
            } else {
                out << "{\"type\":\"CancelOrderCommand\",\"data\":{\"id\":" << value.id << "}}";
            }
            return out.str();
        },
        command);
}

[[nodiscard]] inline std::string serialize_replay_entry(const ReplayEntry& entry) {
    std::ostringstream out;
    out << "{\"sequence\":" << entry.sequence << ",\"command\":" << serialize_replay_command(entry.command)
        << ",\"events\":[";
    for (std::size_t i = 0; i < entry.events.size(); ++i) {
        if (i != 0U) {
            out << ",";
        }
        out << serialize_replay_event(entry.events[i]);
    }
    out << "]}";
    return out.str();
}

class ReplayLog {
  public:
    void record(ReplayCommand command, std::vector<Event> events) {
        entries_.push_back(ReplayEntry{next_sequence_++, std::move(command), std::move(events)});
    }

    [[nodiscard]] const std::vector<ReplayEntry>& entries() const {
        return entries_;
    }

    [[nodiscard]] bool empty() const {
        return entries_.empty();
    }

    [[nodiscard]] std::size_t size() const {
        return entries_.size();
    }

    void clear() {
        entries_.clear();
        next_sequence_ = 0;
    }

    [[nodiscard]] std::string to_json() const {
        std::ostringstream out;
        out << "[";
        for (std::size_t i = 0; i < entries_.size(); ++i) {
            if (i != 0U) {
                out << ",";
            }
            out << serialize_replay_entry(entries_[i]);
        }
        out << "]";
        return out.str();
    }

  private:
    std::vector<ReplayEntry> entries_;
    std::size_t next_sequence_{0};
};

}  // namespace tes
