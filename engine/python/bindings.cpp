#include <cstdint>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/detail/common.h>
#include <pybind11/stl.h>

#include <tes/events.hpp>
#include <tes/market_data.hpp>
#include <tes/matching_engine.hpp>
#include <tes/types.hpp>

namespace py = pybind11;
using namespace pybind11::literals;

namespace {

[[nodiscard]] std::string side_to_string(tes::Side side) {
    if (side == tes::Side::Bid) {
        return "BUY";
    }
    return "SELL";
}

[[nodiscard]] std::string reject_reason_to_string(tes::RejectReason reason) {
    if (reason == tes::RejectReason::InvalidPrice) return "InvalidPrice";
    if (reason == tes::RejectReason::InvalidQuantity) return "InvalidQuantity";
    if (reason == tes::RejectReason::UnknownOrderId) return "UnknownOrderId";
    if (reason == tes::RejectReason::NoLiquidity) return "NoLiquidity";
    if (reason == tes::RejectReason::InsufficientCash) return "InsufficientCash";
    if (reason == tes::RejectReason::InsufficientPosition) return "InsufficientPosition";
    return "WrongAccount";
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

[[nodiscard]] py::dict event_to_py(const tes::Event& event) {
    return std::visit(
        [](const auto& evt) -> py::dict {
            using T = std::decay_t<decltype(evt)>;

            if constexpr (std::is_same_v<T, tes::OrderAccepted>) {
                py::dict out;
                out["type"] = "OrderAccepted";
                py::dict data;
                data["order_id"] = evt.id;
                data["side"] = side_to_string(evt.side);
                data["price"] = evt.price.ticks;
                data["qty"] = evt.qty.value;
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::OrderRejected>) {
                py::dict out;
                out["type"] = "OrderRejected";
                py::dict data;
                data["side"] = side_to_string(evt.side);
                data["price"] = evt.price.ticks;
                data["qty"] = evt.qty.value;
                data["reason"] = reject_reason_to_string(evt.reason);
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::OrderCanceled>) {
                py::dict out;
                out["type"] = "OrderCanceled";
                py::dict data;
                data["order_id"] = evt.id;
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::CancelRejected>) {
                py::dict out;
                out["type"] = "CancelRejected";
                py::dict data;
                data["order_id"] = evt.id;
                data["reason"] = reject_reason_to_string(evt.reason);
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::TradeExecuted>) {
                py::dict out;
                out["type"] = "TradeExecuted";
                py::dict data;
                data["price"] = evt.price.ticks;
                data["qty"] = evt.qty.value;
                data["maker_order_id"] = evt.maker_id;
                data["taker_order_id"] = evt.taker_id;
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::OrderPartiallyFilled>) {
                py::dict out;
                out["type"] = "OrderPartiallyFilled";
                py::dict data;
                data["order_id"] = evt.id;
                data["last_fill_qty"] = evt.last_fill_qty.value;
                data["remaining_qty"] = evt.remaining_qty.value;
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::OrderFilled>) {
                py::dict out;
                out["type"] = "OrderFilled";
                py::dict data;
                data["order_id"] = evt.id;
                data["last_fill_qty"] = evt.last_fill_qty.value;
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::OrderExpired>) {
                py::dict out;
                out["type"] = "OrderExpired";
                py::dict data;
                data["order_id"] = evt.id;
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else {
                py::dict out;
                out["type"] = "TopOfBook";
                py::dict data;
                if (evt.best_bid.has_value()) {
                    data["best_bid"] = evt.best_bid->ticks;
                } else {
                    data["best_bid"] = py::none();
                }
                if (evt.best_ask.has_value()) {
                    data["best_ask"] = evt.best_ask->ticks;
                } else {
                    data["best_ask"] = py::none();
                }
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            }
        },
        event);
}


[[nodiscard]] py::dict depth_to_py(const tes::BookDepth& depth) {
    auto level_to_py = [](const tes::PriceLevel& level) {
        py::dict out;
        out["price"] = level.price.ticks;
        out["qty"] = level.qty.value;
        return out;
    };

    py::list bids;
    for (const tes::PriceLevel& level : depth.bids) {
        bids.append(level_to_py(level));
    }

    py::list asks;
    for (const tes::PriceLevel& level : depth.asks) {
        asks.append(level_to_py(level));
    }

    py::dict out;
    out["bids"] = bids;
    out["asks"] = asks;
    return out;
}

[[nodiscard]] py::dict snapshot_to_py(const tes::BookSnapshot& snapshot) {
    auto level_to_py = [](const tes::BookLevel& level) {
        py::dict out;
        out["symbol"] = level.symbol;
        out["side"] = level.side == tes::Side::Bid ? "BUY" : "SELL";
        out["price"] = level.price.ticks;
        out["qty"] = level.qty.value;
        return out;
    };

    py::list bids;
    for (const tes::BookLevel& level : snapshot.bids) {
        bids.append(level_to_py(level));
    }
    py::list asks;
    for (const tes::BookLevel& level : snapshot.asks) {
        asks.append(level_to_py(level));
    }

    py::dict out;
    out["symbol"] = snapshot.symbol;
    out["sequence_number"] = snapshot.sequence_number;
    out["bids"] = bids;
    out["asks"] = asks;
    return out;
}


[[nodiscard]] py::dict account_snapshot_to_py(const tes::MatchingEngine::AccountSnapshot& snapshot) {
    py::dict positions;
    for (const auto& [symbol, qty] : snapshot.position_qty_by_symbol) positions[symbol.c_str()] = qty;
    py::dict reserved_positions;
    for (const auto& [symbol, qty] : snapshot.reserved_qty_by_symbol) reserved_positions[symbol.c_str()] = qty;
    py::dict out;
    out["cash_balance"] = snapshot.cash_balance;
    out["reserved_cash"] = snapshot.reserved_cash;
    out["positions"] = positions;
    out["reserved_positions"] = reserved_positions;
    return out;
}

[[nodiscard]] py::dict ledger_entry_to_py(const tes::MatchingEngine::AccountLedgerEntry& entry) {
    py::dict out;
    out["sequence"] = entry.sequence;
    out["account_id"] = entry.account_id;
    out["symbol"] = entry.symbol;
    out["reason"] = entry.reason;
    out["cash_delta"] = entry.cash_delta;
    out["position_delta"] = entry.position_delta;
    out["reserved_cash_delta"] = entry.reserved_cash_delta;
    out["reserved_position_delta"] = entry.reserved_position_delta;
    out["related_order_id"] = entry.related_order_id.has_value() ? py::cast(*entry.related_order_id) : py::none();
    out["related_trade_id"] = entry.related_trade_id.has_value() ? py::cast(*entry.related_trade_id) : py::none();
    return out;
}
[[nodiscard]] std::vector<py::dict> events_to_dicts(const std::vector<tes::Event>& events) {
    std::vector<py::dict> out;
    out.reserve(events.size());
    for (const tes::Event& event : events) {
        out.emplace_back(event_to_py(event));
    }
    return out;
}

[[nodiscard]] tes::TimeInForce tif_from_string(const std::string& time_in_force) {
    if (time_in_force == "GTC") {
        return tes::TimeInForce::Gtc;
    }
    if (time_in_force == "IOC") {
        return tes::TimeInForce::Ioc;
    }
    if (time_in_force == "FOK") {
        return tes::TimeInForce::Fok;
    }
    throw std::invalid_argument("time_in_force must be one of: GTC, IOC, FOK");
}

}  // namespace

PYBIND11_MODULE(tes_engine, m) {
    m.doc() = "Python bindings for TES matching engine";

    py::enum_<tes::OrderType>(m, "OrderType")
        .value("LIMIT", tes::OrderType::Limit)
        .value("MARKET", tes::OrderType::Market)
        .export_values();

    py::enum_<tes::TimeInForce>(m, "TimeInForce")
        .value("GTC", tes::TimeInForce::Gtc)
        .value("IOC", tes::TimeInForce::Ioc)
        .value("FOK", tes::TimeInForce::Fok)
        .export_values();


    py::class_<tes::MarketDataRecord>(m, "MarketDataRecord")
        .def_property_readonly("symbol", [](const tes::MarketDataRecord& self) { return self.symbol; })
        .def_property_readonly("sequence_number", [](const tes::MarketDataRecord& self) { return self.sequence_number; })
        .def_property_readonly("step", [](const tes::MarketDataRecord& self) { return self.step; })
        .def_property_readonly("timestamp", [](const tes::MarketDataRecord& self) { return self.timestamp; })
        .def_property_readonly("bids", [](const tes::MarketDataRecord& self) { py::list levels; for (const auto& level : self.bids) levels.append(py::dict("symbol"_a=level.symbol,"side"_a=(level.side==tes::Side::Bid?"BUY":"SELL"),"price"_a=level.price.ticks,"qty"_a=level.qty.value)); return levels; })
        .def_property_readonly("asks", [](const tes::MarketDataRecord& self) { py::list levels; for (const auto& level : self.asks) levels.append(py::dict("symbol"_a=level.symbol,"side"_a=(level.side==tes::Side::Bid?"BUY":"SELL"),"price"_a=level.price.ticks,"qty"_a=level.qty.value)); return levels; })
        .def_property_readonly("triggering_event_names", [](const tes::MarketDataRecord& self) { return self.triggering_event_names; });

    py::class_<tes::MarketDataSummary>(m, "MarketDataSummary")
        .def_readonly("best_bid", &tes::MarketDataSummary::best_bid)
        .def_readonly("best_ask", &tes::MarketDataSummary::best_ask)
        .def_readonly("mid_price", &tes::MarketDataSummary::mid_price)
        .def_readonly("spread", &tes::MarketDataSummary::spread)
        .def_readonly("total_bid_qty", &tes::MarketDataSummary::total_bid_qty)
        .def_readonly("total_ask_qty", &tes::MarketDataSummary::total_ask_qty)
        .def_readonly("imbalance", &tes::MarketDataSummary::imbalance);

    py::class_<tes::MarketDataRecorder>(m, "MarketDataRecorder")
        .def(py::init<std::optional<std::size_t>>(), py::arg("max_records_per_symbol") = std::nullopt)
        .def("record_snapshot", [](tes::MarketDataRecorder& self, const py::dict& raw_snapshot) {
                 tes::BookSnapshot snapshot;
                 snapshot.symbol = raw_snapshot["symbol"].cast<std::string>();
                 snapshot.sequence_number = raw_snapshot["sequence_number"].cast<std::uint64_t>();
                 for (const auto& item : raw_snapshot["bids"].cast<py::list>()) {
                     const auto level = item.cast<py::dict>();
                     snapshot.bids.push_back(tes::BookLevel{level["symbol"].cast<std::string>(), tes::Side::Bid,
                         tes::Price{level["price"].cast<std::int64_t>()}, tes::Qty{level["qty"].cast<std::int64_t>()}});
                 }
                 for (const auto& item : raw_snapshot["asks"].cast<py::list>()) {
                     const auto level = item.cast<py::dict>();
                     snapshot.asks.push_back(tes::BookLevel{level["symbol"].cast<std::string>(), tes::Side::Ask,
                         tes::Price{level["price"].cast<std::int64_t>()}, tes::Qty{level["qty"].cast<std::int64_t>()}});
                 }
                 self.record_snapshot(snapshot);
             })
        .def("history", &tes::MarketDataRecorder::history)
        .def("latest", &tes::MarketDataRecorder::latest)
        .def("clear", &tes::MarketDataRecorder::clear)
        .def("clear_all", &tes::MarketDataRecorder::clear_all)
        .def("size", &tes::MarketDataRecorder::size)
        .def("symbols", &tes::MarketDataRecorder::symbols)
        .def("summary", &tes::MarketDataRecorder::summary)
        .def("spread_series", &tes::MarketDataRecorder::spread_series)
        .def("mid_price_series", &tes::MarketDataRecorder::mid_price_series)
        .def("sequence_series", &tes::MarketDataRecorder::sequence_series)
        .def("record_to_json", &tes::MarketDataRecorder::record_to_json)
        .def("history_to_json", &tes::MarketDataRecorder::history_to_json)
        .def("all_histories_to_json", &tes::MarketDataRecorder::all_histories_to_json);
    py::class_<tes::MatchingEngine>(m, "MatchingEngine")
        .def(py::init<>())
        .def("place_limit_order",
             [](tes::MatchingEngine& self, const std::string& side, std::int64_t price_ticks, std::int64_t qty,
                const std::string& time_in_force, const std::string& symbol) {
                 const tes::Side parsed_side = side_from_string(side);
                 const tes::TimeInForce parsed_tif = tif_from_string(time_in_force);
                 const std::vector<tes::Event> events =
                     self.place_limit_order(0, symbol, parsed_side, tes::Price{price_ticks}, tes::Qty{qty}, parsed_tif);
                 return events_to_dicts(events);
             },
             py::arg("side"), py::arg("price_ticks"), py::arg("qty"), py::arg("time_in_force") = "GTC",
             py::arg("symbol") = tes::kDefaultSymbol)
        .def("place_market_order",
             [](tes::MatchingEngine& self, const std::string& side, std::int64_t qty, const std::string& symbol) {
                 const tes::Side parsed_side = side_from_string(side);
                 const std::vector<tes::Event> events = self.place_market_order(0, symbol, parsed_side, tes::Qty{qty});
                 return events_to_dicts(events);
             },
             py::arg("side"), py::arg("qty"), py::arg("symbol") = tes::kDefaultSymbol)
        .def("cancel",
             [](tes::MatchingEngine& self, std::uint64_t order_id) {
                 const std::vector<tes::Event> events = self.cancel(order_id);
                 return events_to_dicts(events);
             },
             py::arg("order_id"))
        .def("replace_order",
             [](tes::MatchingEngine& self, std::uint64_t order_id, std::int64_t price_ticks, std::int64_t qty) {
                 const std::vector<tes::Event> events =
                     self.replace_order(order_id, tes::Price{price_ticks}, tes::Qty{qty});
                 return events_to_dicts(events);
             },
             py::arg("order_id"), py::arg("price_ticks"), py::arg("qty"))
        .def("depth",
             [](const tes::MatchingEngine& self, std::size_t levels, const std::string& symbol) {
                 return depth_to_py(self.depth(symbol, levels));
             },
             py::arg("levels"), py::arg("symbol") = tes::kDefaultSymbol)
        .def("snapshot",
             [](const tes::MatchingEngine& self, std::size_t levels, const std::string& symbol) {
                 return snapshot_to_py(self.snapshot(symbol, levels));
             },
             py::arg("levels"), py::arg("symbol") = tes::kDefaultSymbol)
        
        .def("account_ledger",
             [](const tes::MatchingEngine& self, std::uint64_t account_id, const std::optional<std::string>& symbol) {
                 py::list out;
                 const auto entries = symbol.has_value() ? self.account_ledger(account_id, *symbol) : self.account_ledger(account_id);
                 for (const auto& entry : entries) out.append(ledger_entry_to_py(entry));
                 return out;
             },
             py::arg("account_id"), py::arg("symbol") = std::nullopt)
        .def("latest_account_snapshot",
             [](const tes::MatchingEngine& self, std::uint64_t account_id) {
                 return account_snapshot_to_py(self.latest_account_snapshot(account_id));
             },
             py::arg("account_id"))
.def("sequence_number",
             [](const tes::MatchingEngine& self, const std::string& symbol) { return self.sequence_number(symbol); },
             py::arg("symbol") = tes::kDefaultSymbol);
}
