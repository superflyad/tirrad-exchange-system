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
#include <tes/matching_engine.hpp>
#include <tes/types.hpp>

namespace tes {

struct LimitOrderCommand {
    Side side;
    Price price;
    Qty qty;
    Symbol symbol{kDefaultSymbol};
    TimeInForce time_in_force{TimeInForce::Gtc};
};

struct HiddenOrderCommand {
    Side side;
    Price price;
    Qty qty;
    Symbol symbol{kDefaultSymbol};
};

struct IcebergOrderCommand {
    Side side;
    Price price;
    Qty total_qty;
    Qty display_qty;
    Symbol symbol{kDefaultSymbol};
};

struct MarketOrderCommand {
    Side side;
    Qty qty;
    Symbol symbol{kDefaultSymbol};
};

struct CancelOrderCommand {
    OrderId id;
};

struct SetTradingPhaseCommand {
    Symbol symbol{kDefaultSymbol};
    TradingPhase phase{TradingPhase::Continuous};
};

struct HaltSymbolCommand {
    Symbol symbol{kDefaultSymbol};
    std::string reason;
};

struct ResumeSymbolCommand {
    Symbol symbol{kDefaultSymbol};
};

struct SetPriceBandsCommand {
    Symbol symbol{kDefaultSymbol};
    Price lower_price{};
    Price upper_price{};
};

struct ClearPriceBandsCommand {
    Symbol symbol{kDefaultSymbol};
};

struct AuctionUncrossCommand {
    Symbol symbol{kDefaultSymbol};
};

using ReplayCommand = std::variant<LimitOrderCommand, HiddenOrderCommand, IcebergOrderCommand, MarketOrderCommand, CancelOrderCommand, SetTradingPhaseCommand, HaltSymbolCommand, ResumeSymbolCommand, SetPriceBandsCommand, ClearPriceBandsCommand, AuctionUncrossCommand>;

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
            if constexpr (std::is_same_v<T, HiddenOrderAccepted>) return "HiddenOrderAccepted";
            if constexpr (std::is_same_v<T, IcebergOrderAccepted>) return "IcebergOrderAccepted";
            if constexpr (std::is_same_v<T, IcebergReplenished>) return "IcebergReplenished";
            if constexpr (std::is_same_v<T, OrderRejected>) return "OrderRejected";
            if constexpr (std::is_same_v<T, OrderCanceled>) return "OrderCanceled";
            if constexpr (std::is_same_v<T, CancelRejected>) return "CancelRejected";
            if constexpr (std::is_same_v<T, TradeExecuted>) return "TradeExecuted";
            if constexpr (std::is_same_v<T, OrderPartiallyFilled>) return "OrderPartiallyFilled";
            if constexpr (std::is_same_v<T, OrderFilled>) return "OrderFilled";
            if constexpr (std::is_same_v<T, OrderExpired>) return "OrderExpired";
            if constexpr (std::is_same_v<T, StopOrderAccepted>) return "StopOrderAccepted";
            if constexpr (std::is_same_v<T, StopOrderTriggered>) return "StopOrderTriggered";
            if constexpr (std::is_same_v<T, TopOfBook>) return "TopOfBook";
            if constexpr (std::is_same_v<T, SymbolHalted>) return "SymbolHalted";
            if constexpr (std::is_same_v<T, SymbolResumed>) return "SymbolResumed";
            if constexpr (std::is_same_v<T, PriceBandUpdated>) return "PriceBandUpdated";
            if constexpr (std::is_same_v<T, CircuitBreakerTriggered>) return "CircuitBreakerTriggered";
            if constexpr (std::is_same_v<T, AuctionStarted>) return "AuctionStarted";
            if constexpr (std::is_same_v<T, AuctionEnded>) return "AuctionEnded";
            if constexpr (std::is_same_v<T, AuctionUncross>) return "AuctionUncross";
            if constexpr (std::is_same_v<T, IndicativePriceUpdated>) return "IndicativePriceUpdated";
            return "Unknown";
        },
        event);
}

[[nodiscard]] inline std::string serialize_replay_event(const Event& event) {
    return std::visit(
        [](const auto& value) {
            std::ostringstream out;
            out << "{\"type\":\"" << event_type_name(Event{value}) << "\",\"data\":{\"symbol\":\""
                << json_escape(value.symbol) << "\"}}";
            return out.str();
        },
        event);
}

[[nodiscard]] inline const char* time_in_force_name(TimeInForce time_in_force) {
    switch (time_in_force) {
        case TimeInForce::Gtc:
            return "GTC";
        case TimeInForce::Ioc:
            return "IOC";
        case TimeInForce::Fok:
            return "FOK";
    }

    return "Unknown";
}

[[nodiscard]] inline const char* trading_phase_name(TradingPhase phase) {
    switch (phase) {
        case TradingPhase::Continuous: return "Continuous";
        case TradingPhase::OpeningAuction: return "OpeningAuction";
        case TradingPhase::ClosingAuction: return "ClosingAuction";
        case TradingPhase::Halted: return "Halted";
    }
    return "Unknown";
}

[[nodiscard]] inline std::string serialize_replay_command(const ReplayCommand& command) {
    return std::visit(
        [](const auto& value) {
            using T = std::decay_t<decltype(value)>;
            std::ostringstream out;
            if constexpr (std::is_same_v<T, LimitOrderCommand>) {
                out << "{\"type\":\"LimitOrderCommand\",\"data\":{\"side\":\""
                    << (value.side == Side::Bid ? "Bid" : "Ask") << "\",\"price\":"
                    << value.price.ticks << ",\"qty\":" << value.qty.value << ",\"time_in_force\":\""
                    << time_in_force_name(value.time_in_force) << "\",\"symbol\":\""
                    << json_escape(value.symbol) << "\"}}";
            } else if constexpr (std::is_same_v<T, HiddenOrderCommand>) {
                out << "{\"type\":\"HiddenOrderCommand\",\"data\":{\"side\":\""
                    << (value.side == Side::Bid ? "Bid" : "Ask") << "\",\"price\":"
                    << value.price.ticks << ",\"qty\":" << value.qty.value << ",\"symbol\":\""
                    << json_escape(value.symbol) << "\"}}";
            } else if constexpr (std::is_same_v<T, IcebergOrderCommand>) {
                out << "{\"type\":\"IcebergOrderCommand\",\"data\":{\"side\":\""
                    << (value.side == Side::Bid ? "Bid" : "Ask") << "\",\"price\":"
                    << value.price.ticks << ",\"total_qty\":" << value.total_qty.value
                    << ",\"display_qty\":" << value.display_qty.value << ",\"symbol\":\""
                    << json_escape(value.symbol) << "\"}}";
            } else if constexpr (std::is_same_v<T, MarketOrderCommand>) {
                out << "{\"type\":\"MarketOrderCommand\",\"data\":{\"side\":\""
                    << (value.side == Side::Bid ? "Bid" : "Ask") << "\",\"qty\":" << value.qty.value
                    << ",\"symbol\":\"" << json_escape(value.symbol) << "\"}}";
            } else if constexpr (std::is_same_v<T, CancelOrderCommand>) {
                out << "{\"type\":\"CancelOrderCommand\",\"data\":{\"id\":" << value.id << "}}";
            } else if constexpr (std::is_same_v<T, SetTradingPhaseCommand>) {
                out << "{\"type\":\"SetTradingPhaseCommand\",\"data\":{\"symbol\":\""
                    << json_escape(value.symbol) << "\",\"phase\":\"" << trading_phase_name(value.phase) << "\"}}";
            } else if constexpr (std::is_same_v<T, HaltSymbolCommand>) {
                out << "{\"type\":\"HaltSymbolCommand\",\"data\":{\"symbol\":\""
                    << json_escape(value.symbol) << "\",\"reason\":\"" << json_escape(value.reason) << "\"}}";
            } else if constexpr (std::is_same_v<T, ResumeSymbolCommand>) {
                out << "{\"type\":\"ResumeSymbolCommand\",\"data\":{\"symbol\":\""
                    << json_escape(value.symbol) << "\"}}";
            } else if constexpr (std::is_same_v<T, SetPriceBandsCommand>) {
                out << "{\"type\":\"SetPriceBandsCommand\",\"data\":{\"symbol\":\""
                    << json_escape(value.symbol) << "\",\"lower_price\":" << value.lower_price.ticks
                    << ",\"upper_price\":" << value.upper_price.ticks << "}}";
            } else if constexpr (std::is_same_v<T, ClearPriceBandsCommand>) {
                out << "{\"type\":\"ClearPriceBandsCommand\",\"data\":{\"symbol\":\""
                    << json_escape(value.symbol) << "\"}}";
            } else {
                out << "{\"type\":\"AuctionUncrossCommand\",\"data\":{\"symbol\":\""
                    << json_escape(value.symbol) << "\"}}";
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

[[nodiscard]] inline std::vector<std::vector<Event>> replay_commands(const std::vector<ReplayEntry>& entries) {
    MatchingEngine engine;
    std::vector<std::vector<Event>> replayed_events;
    replayed_events.reserve(entries.size());

    for (const ReplayEntry& entry : entries) {
        std::vector<Event> events = std::visit(
            [&engine](const auto& command) {
                using T = std::decay_t<decltype(command)>;
                if constexpr (std::is_same_v<T, LimitOrderCommand>) {
                    return engine.place_limit_order(0, command.symbol, command.side, command.price, command.qty,
                                                    command.time_in_force);
                } else if constexpr (std::is_same_v<T, HiddenOrderCommand>) {
                    return engine.place_hidden_order(0, command.symbol, command.side, command.price, command.qty);
                } else if constexpr (std::is_same_v<T, IcebergOrderCommand>) {
                    return engine.place_iceberg_order(0, command.symbol, command.side, command.price, command.total_qty, command.display_qty);
                } else if constexpr (std::is_same_v<T, MarketOrderCommand>) {
                    return engine.place_market_order(0, command.symbol, command.side, command.qty);
                } else if constexpr (std::is_same_v<T, CancelOrderCommand>) {
                    return engine.cancel(command.id);
                } else if constexpr (std::is_same_v<T, SetTradingPhaseCommand>) {
                    return engine.set_trading_phase(command.symbol, command.phase);
                } else if constexpr (std::is_same_v<T, HaltSymbolCommand>) {
                    return engine.halt_symbol(command.symbol, command.reason);
                } else if constexpr (std::is_same_v<T, ResumeSymbolCommand>) {
                    return engine.resume_symbol(command.symbol);
                } else if constexpr (std::is_same_v<T, SetPriceBandsCommand>) {
                    return engine.set_price_bands(command.symbol, command.lower_price, command.upper_price);
                } else if constexpr (std::is_same_v<T, ClearPriceBandsCommand>) {
                    return engine.clear_price_bands(command.symbol);
                } else {
                    return engine.uncross(command.symbol);
                }
            },
            entry.command);
        replayed_events.push_back(std::move(events));
    }

    return replayed_events;
}


}  // namespace tes
