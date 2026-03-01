#include <cstdint>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <tes/events.hpp>
#include <tes/matching_engine.hpp>
#include <tes/types.hpp>

namespace py = pybind11;

namespace {

[[nodiscard]] std::string side_to_string(tes::Side side) {
    if (side == tes::Side::Bid) {
        return "Bid";
    }
    return "Ask";
}

[[nodiscard]] tes::Side side_from_string(const std::string& side) {
    if (side == "Bid") {
        return tes::Side::Bid;
    }
    if (side == "Ask") {
        return tes::Side::Ask;
    }
    throw std::invalid_argument("side must be either 'Bid' or 'Ask'");
}

[[nodiscard]] py::dict event_to_dict(const tes::Event& event) {
    return std::visit(
        [](const auto& evt) -> py::dict {
            using T = std::decay_t<decltype(evt)>;

            if constexpr (std::is_same_v<T, tes::OrderAccepted>) {
                py::dict out;
                out["type"] = "OrderAccepted";
                out["id"] = evt.id;
                out["side"] = side_to_string(evt.side);
                out["price_ticks"] = evt.price.ticks;
                out["qty"] = evt.qty.value;
                return out;
            } else if constexpr (std::is_same_v<T, tes::OrderCanceled>) {
                py::dict out;
                out["type"] = "OrderCanceled";
                out["id"] = evt.id;
                return out;
            } else if constexpr (std::is_same_v<T, tes::TradeExecuted>) {
                py::dict out;
                out["type"] = "TradeExecuted";
                out["taker_id"] = evt.taker_id;
                out["maker_id"] = evt.maker_id;
                out["taker_side"] = side_to_string(evt.taker_side);
                out["price_ticks"] = evt.price.ticks;
                out["qty"] = evt.qty.value;
                return out;
            } else {
                py::dict out;
                out["type"] = "TopOfBook";
                if (evt.best_bid.has_value()) {
                    out["best_bid_ticks"] = evt.best_bid->ticks;
                } else {
                    out["best_bid_ticks"] = py::none();
                }
                if (evt.best_ask.has_value()) {
                    out["best_ask_ticks"] = evt.best_ask->ticks;
                } else {
                    out["best_ask_ticks"] = py::none();
                }
                return out;
            }
        },
        event);
}

[[nodiscard]] std::vector<py::dict> events_to_dicts(const std::vector<tes::Event>& events) {
    std::vector<py::dict> out;
    out.reserve(events.size());
    for (const tes::Event& event : events) {
        out.emplace_back(event_to_dict(event));
    }
    return out;
}

}  // namespace

PYBIND11_MODULE(tes_engine, m) {
    m.doc() = "Python bindings for TES matching engine";

    py::class_<tes::MatchingEngine>(m, "MatchingEngine")
        .def(py::init<>())
        .def("place_limit_order",
             [](tes::MatchingEngine& self, const std::string& side, std::int64_t price_ticks, std::int64_t qty) {
                 const tes::Side parsed_side = side_from_string(side);
                 const std::vector<tes::Event> events =
                     self.place_limit_order(parsed_side, tes::Price{price_ticks}, tes::Qty{qty});
                 return events_to_dicts(events);
             },
             py::arg("side"), py::arg("price_ticks"), py::arg("qty"))
        .def("cancel",
             [](tes::MatchingEngine& self, std::uint64_t order_id) {
                 const std::vector<tes::Event> events = self.cancel(order_id);
                 return events_to_dicts(events);
             },
             py::arg("order_id"));
}
