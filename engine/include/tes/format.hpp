#pragma once

#include <sstream>
#include <string>
#include <type_traits>
#include <variant>

#include <tes/events.hpp>

namespace tes {

[[nodiscard]] inline std::string to_string(Side side) {
    switch (side) {
        case Side::Bid:
            return "Bid";
        case Side::Ask:
            return "Ask";
    }

    return "Unknown";
}

[[nodiscard]] inline std::string to_string(Price price) {
    return std::to_string(price.ticks);
}

[[nodiscard]] inline std::string to_string(Qty qty) {
    return std::to_string(qty.value);
}

[[nodiscard]] inline std::string to_string(const Event& event) {
    return std::visit(
        [](const auto& value) -> std::string {
            using T = std::decay_t<decltype(value)>;

            std::ostringstream stream;
            if constexpr (std::is_same_v<T, OrderAccepted>) {
                stream << "OrderAccepted{id=" << value.id << ", side=" << to_string(value.side)
                       << ", price=" << to_string(value.price) << ", qty=" << to_string(value.qty)
                       << "}";
                return stream.str();
            }

            else if constexpr (std::is_same_v<T, OrderCanceled>) {
                stream << "OrderCanceled{id=" << value.id << "}";
                return stream.str();
            }

            else if constexpr (std::is_same_v<T, TradeExecuted>) {
                stream << "TradeExecuted{taker_id=" << value.taker_id << ", maker_id=" << value.maker_id
                       << ", taker_side=" << to_string(value.taker_side)
                       << ", price=" << to_string(value.price) << ", qty=" << to_string(value.qty)
                       << "}";
                return stream.str();
            }

            else if constexpr (std::is_same_v<T, TopOfBook>) {
                stream << "TopOfBook{best_bid=";
                if (value.best_bid.has_value()) {
                    stream << to_string(*value.best_bid);
                } else {
                    stream << "nullopt";
                }

                stream << ", best_ask=";
                if (value.best_ask.has_value()) {
                    stream << to_string(*value.best_ask);
                } else {
                    stream << "nullopt";
                }
                stream << "}";
                return stream.str();
            }

            return "UnknownEvent";
        },
        event);
}

}  // namespace tes
