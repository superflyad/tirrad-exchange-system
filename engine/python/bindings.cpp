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

[[nodiscard]] std::string trading_phase_to_string(tes::TradingPhase phase) {
    if (phase == tes::TradingPhase::Continuous) return "Continuous";
    if (phase == tes::TradingPhase::OpeningAuction) return "OpeningAuction";
    if (phase == tes::TradingPhase::ClosingAuction) return "ClosingAuction";
    return "Halted";
}

[[nodiscard]] tes::TradingPhase trading_phase_from_string(const std::string& phase) {
    if (phase == "Continuous") return tes::TradingPhase::Continuous;
    if (phase == "OpeningAuction") return tes::TradingPhase::OpeningAuction;
    if (phase == "ClosingAuction") return tes::TradingPhase::ClosingAuction;
    if (phase == "Halted") return tes::TradingPhase::Halted;
    throw std::invalid_argument("phase must be Continuous, OpeningAuction, ClosingAuction, or Halted");
}

[[nodiscard]] std::string reject_reason_to_string(tes::RejectReason reason) {
    if (reason == tes::RejectReason::InvalidPrice) return "InvalidPrice";
    if (reason == tes::RejectReason::InvalidQuantity) return "InvalidQuantity";
    if (reason == tes::RejectReason::UnknownOrderId) return "UnknownOrderId";
    if (reason == tes::RejectReason::NoLiquidity) return "NoLiquidity";
    if (reason == tes::RejectReason::InsufficientCash) return "InsufficientCash";
    if (reason == tes::RejectReason::InsufficientPosition) return "InsufficientPosition";
    if (reason == tes::RejectReason::WrongAccount) return "WrongAccount";
    if (reason == tes::RejectReason::InsufficientBuyingPower) return "InsufficientBuyingPower";
    if (reason == tes::RejectReason::ShortSellingDisabled) return "ShortSellingDisabled";
    if (reason == tes::RejectReason::MarginRequirementFailed) return "MarginRequirementFailed";
    return "MaintenanceMarginBreached";
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
            } else if constexpr (std::is_same_v<T, tes::StopOrderAccepted>) {
                py::dict out;
                out["type"] = "StopOrderAccepted";
                py::dict data;
                data["order_id"] = evt.id;
                data["side"] = side_to_string(evt.side);
                data["stop_price"] = evt.stop_price.ticks;
                data["qty"] = evt.qty.value;
                data["limit_price"] = evt.limit_price.has_value() ? py::cast(evt.limit_price->ticks) : py::none();
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::StopOrderTriggered>) {
                py::dict out;
                out["type"] = "StopOrderTriggered";
                py::dict data;
                data["order_id"] = evt.id;
                data["resulting_order_id"] = evt.resulting_order_id;
                data["side"] = side_to_string(evt.side);
                data["stop_price"] = evt.stop_price.ticks;
                data["qty"] = evt.qty.value;
                data["limit_price"] = evt.limit_price.has_value() ? py::cast(evt.limit_price->ticks) : py::none();
                data["symbol"] = evt.symbol;
                out["data"] = data;
                return out;
            } else if constexpr (std::is_same_v<T, tes::TopOfBook>) {
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
            } else if constexpr (std::is_same_v<T, tes::AuctionStarted>) {
                py::dict out; out["type"] = "AuctionStarted"; py::dict data;
                data["symbol"] = evt.symbol; data["phase"] = trading_phase_to_string(evt.phase); out["data"] = data; return out;
            } else if constexpr (std::is_same_v<T, tes::AuctionEnded>) {
                py::dict out; out["type"] = "AuctionEnded"; py::dict data;
                data["symbol"] = evt.symbol; data["phase"] = trading_phase_to_string(evt.phase); out["data"] = data; return out;
            } else if constexpr (std::is_same_v<T, tes::AuctionUncross>) {
                py::dict out; out["type"] = "AuctionUncross"; py::dict data;
                data["symbol"] = evt.symbol; data["price"] = evt.price.ticks; data["qty"] = evt.qty.value; data["imbalance"] = evt.imbalance; out["data"] = data; return out;
            } else {
                py::dict out; out["type"] = "IndicativePriceUpdated"; py::dict data;
                data["symbol"] = evt.symbol; data["price"] = evt.price.has_value() ? py::cast(evt.price->ticks) : py::none(); data["qty"] = evt.qty.value; data["imbalance"] = evt.imbalance; out["data"] = data; return out;
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
    py::dict average_cost;
    for (const auto& [symbol, value] : snapshot.average_cost_by_symbol) average_cost[symbol.c_str()] = value;
    py::dict realized_by_symbol;
    for (const auto& [symbol, value] : snapshot.realized_pnl_by_symbol) realized_by_symbol[symbol.c_str()] = value;
    py::dict out;
    out["cash_balance"] = snapshot.cash_balance;
    out["reserved_cash"] = snapshot.reserved_cash;
    out["reserved_short_margin"] = snapshot.reserved_short_margin;
    out["positions"] = positions;
    out["reserved_positions"] = reserved_positions;
    out["average_cost"] = average_cost;
    out["realized_pnl"] = snapshot.realized_pnl;
    out["realized_pnl_by_symbol"] = realized_by_symbol;
    return out;
}

[[nodiscard]] py::dict performance_snapshot_to_py(const tes::MatchingEngine::PerformanceSnapshot& snapshot) {
    py::dict positions;
    for (const auto& [symbol, qty] : snapshot.position_qty_by_symbol) positions[symbol.c_str()] = qty;
    py::dict average_cost;
    for (const auto& [symbol, value] : snapshot.average_cost_by_symbol) average_cost[symbol.c_str()] = value;
    py::dict realized_by_symbol;
    for (const auto& [symbol, value] : snapshot.realized_pnl_by_symbol) realized_by_symbol[symbol.c_str()] = value;
    py::dict unrealized_by_symbol;
    for (const auto& [symbol, value] : snapshot.unrealized_pnl_by_symbol) unrealized_by_symbol[symbol.c_str()] = value;
    py::dict out;
    out["cash"] = snapshot.cash_balance;
    out["cash_balance"] = snapshot.cash_balance;
    out["reserved_cash"] = snapshot.reserved_cash;
    out["positions"] = positions;
    out["average_cost"] = average_cost;
    out["realized_pnl"] = snapshot.realized_pnl;
    out["realized_pnl_by_symbol"] = realized_by_symbol;
    out["unrealized_pnl"] = snapshot.unrealized_pnl;
    out["unrealized_pnl_by_symbol"] = unrealized_by_symbol;
    out["total_equity"] = snapshot.total_equity;
    return out;
}


[[nodiscard]] py::dict risk_config_to_py(const tes::MatchingEngine::AccountRiskConfig& config) {
    py::dict out;
    out["mode"] = config.mode == tes::MatchingEngine::AccountRiskMode::CashOnly ? "CashOnly" : "Margin";
    out["allow_short_selling"] = config.allow_short_selling;
    out["max_leverage"] = config.max_leverage;
    out["initial_margin_requirement"] = config.initial_margin_requirement;
    out["maintenance_margin_requirement"] = config.maintenance_margin_requirement;
    out["short_margin_requirement"] = config.short_margin_requirement;
    return out;
}

[[nodiscard]] tes::MatchingEngine::AccountRiskConfig risk_config_from_py(const py::dict& raw) {
    tes::MatchingEngine::AccountRiskConfig config;
    if (raw.contains("mode")) {
        const std::string mode = raw["mode"].cast<std::string>();
        if (mode == "CashOnly" || mode == "cash_only") config.mode = tes::MatchingEngine::AccountRiskMode::CashOnly;
        else if (mode == "Margin" || mode == "margin") config.mode = tes::MatchingEngine::AccountRiskMode::Margin;
        else throw std::invalid_argument("risk config mode must be CashOnly or Margin");
    }
    if (raw.contains("allow_short_selling")) config.allow_short_selling = raw["allow_short_selling"].cast<bool>();
    if (raw.contains("max_leverage")) config.max_leverage = raw["max_leverage"].cast<double>();
    if (raw.contains("initial_margin_requirement")) config.initial_margin_requirement = raw["initial_margin_requirement"].cast<double>();
    if (raw.contains("maintenance_margin_requirement")) config.maintenance_margin_requirement = raw["maintenance_margin_requirement"].cast<double>();
    if (raw.contains("short_margin_requirement")) config.short_margin_requirement = raw["short_margin_requirement"].cast<double>();
    return config;
}

[[nodiscard]] py::dict margin_snapshot_to_py(const tes::MatchingEngine::MarginSnapshot& snapshot) {
    py::dict out;
    out["gross_exposure"] = snapshot.gross_exposure;
    out["net_liquidation_value"] = snapshot.net_liquidation_value;
    out["equity"] = snapshot.equity;
    out["margin_used"] = snapshot.margin_used;
    out["available_buying_power"] = snapshot.available_buying_power;
    out["short_exposure"] = snapshot.short_exposure;
    out["maintenance_requirement"] = snapshot.maintenance_requirement;
    out["margin_call"] = snapshot.margin_call;
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
    out["fee_delta"] = entry.fee_delta;
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
        .value("STOP_MARKET", tes::OrderType::StopMarket)
        .value("STOP_LIMIT", tes::OrderType::StopLimit)
        .export_values();

    py::enum_<tes::TimeInForce>(m, "TimeInForce")
        .value("GTC", tes::TimeInForce::Gtc)
        .value("IOC", tes::TimeInForce::Ioc)
        .value("FOK", tes::TimeInForce::Fok)
        .export_values();

    py::enum_<tes::TradingPhase>(m, "TradingPhase")
        .value("CONTINUOUS", tes::TradingPhase::Continuous)
        .value("OPENING_AUCTION", tes::TradingPhase::OpeningAuction)
        .value("CLOSING_AUCTION", tes::TradingPhase::ClosingAuction)
        .value("HALTED", tes::TradingPhase::Halted)
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
        .def("set_fee_model",
             [](tes::MatchingEngine& self, double maker_fee_rate, double taker_fee_rate, std::optional<std::int64_t> fixed_fee) {
                 self.set_fee_model(tes::MatchingEngine::FeeModel{maker_fee_rate, taker_fee_rate, fixed_fee});
             },
             py::arg("maker_fee_rate"), py::arg("taker_fee_rate"), py::arg("fixed_fee") = std::nullopt)
        .def("fee_model",
             [](const tes::MatchingEngine& self) {
                 const auto model = self.fee_model();
                 py::dict out;
                 out["maker_fee_rate"] = model.maker_fee_rate;
                 out["taker_fee_rate"] = model.taker_fee_rate;
                 out["fixed_fee"] = model.fixed_fee.has_value() ? py::cast(*model.fixed_fee) : py::none();
                 return out;
             })
        .def("set_account_risk_config",
             [](tes::MatchingEngine& self, std::uint64_t account_id, const py::dict& config) {
                 self.set_account_risk_config(account_id, risk_config_from_py(config));
             },
             py::arg("account_id"), py::arg("config"))
        .def("account_risk_config",
             [](const tes::MatchingEngine& self, std::uint64_t account_id) { return risk_config_to_py(self.account_risk_config(account_id)); },
             py::arg("account_id"))
        .def("account_buying_power",
             [](const tes::MatchingEngine& self, std::uint64_t account_id) { return self.account_buying_power(account_id); },
             py::arg("account_id"))
        .def("account_margin_snapshot",
             [](const tes::MatchingEngine& self, std::uint64_t account_id) { return margin_snapshot_to_py(self.account_margin_snapshot(account_id)); },
             py::arg("account_id"))
        .def("set_account_state",
             [](tes::MatchingEngine& self, std::uint64_t account_id, const std::string& symbol, std::int64_t cash_balance, std::int64_t position_qty) {
                 self.set_account_state(account_id, symbol, cash_balance, position_qty);
             },
             py::arg("account_id"), py::arg("symbol"), py::arg("cash_balance"), py::arg("position_qty"))
        .def("place_limit_order",
             [](tes::MatchingEngine& self, const std::string& side, std::int64_t price_ticks, std::int64_t qty,
                const std::string& time_in_force, const std::string& symbol, std::uint64_t account_id) {
                 const tes::Side parsed_side = side_from_string(side);
                 const tes::TimeInForce parsed_tif = tif_from_string(time_in_force);
                 const std::vector<tes::Event> events =
                     self.place_limit_order(account_id, symbol, parsed_side, tes::Price{price_ticks}, tes::Qty{qty}, parsed_tif);
                 return events_to_dicts(events);
             },
             py::arg("side"), py::arg("price_ticks"), py::arg("qty"), py::arg("time_in_force") = "GTC",
             py::arg("symbol") = tes::kDefaultSymbol, py::arg("account_id") = 0)
        .def("place_market_order",
             [](tes::MatchingEngine& self, const std::string& side, std::int64_t qty, const std::string& symbol, std::uint64_t account_id) {
                 const tes::Side parsed_side = side_from_string(side);
                 const std::vector<tes::Event> events = self.place_market_order(account_id, symbol, parsed_side, tes::Qty{qty});
                 return events_to_dicts(events);
             },
             py::arg("side"), py::arg("qty"), py::arg("symbol") = tes::kDefaultSymbol, py::arg("account_id") = 0)
        .def("place_stop_order",
             [](tes::MatchingEngine& self, const std::string& side, std::int64_t stop_price_ticks, std::int64_t qty,
                const std::string& symbol, std::uint64_t account_id) {
                 const tes::Side parsed_side = side_from_string(side);
                 const std::vector<tes::Event> events =
                     self.place_stop_order(account_id, symbol, parsed_side, tes::Price{stop_price_ticks}, tes::Qty{qty});
                 return events_to_dicts(events);
             },
             py::arg("side"), py::arg("stop_price_ticks"), py::arg("qty"), py::arg("symbol") = tes::kDefaultSymbol,
             py::arg("account_id") = 0)
        .def("place_stop_limit_order",
             [](tes::MatchingEngine& self, const std::string& side, std::int64_t stop_price_ticks, std::int64_t limit_price_ticks,
                std::int64_t qty, const std::string& symbol, std::uint64_t account_id) {
                 const tes::Side parsed_side = side_from_string(side);
                 const std::vector<tes::Event> events = self.place_stop_limit_order(
                     account_id, symbol, parsed_side, tes::Price{stop_price_ticks}, tes::Price{limit_price_ticks}, tes::Qty{qty});
                 return events_to_dicts(events);
             },
             py::arg("side"), py::arg("stop_price_ticks"), py::arg("limit_price_ticks"), py::arg("qty"),
             py::arg("symbol") = tes::kDefaultSymbol, py::arg("account_id") = 0)
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
        .def("replace_stop_order",
             [](tes::MatchingEngine& self, std::uint64_t order_id, std::int64_t stop_price_ticks, std::int64_t qty,
                std::uint64_t account_id) {
                 const std::vector<tes::Event> events =
                     self.replace_stop_order(account_id, order_id, tes::Price{stop_price_ticks}, tes::Qty{qty});
                 return events_to_dicts(events);
             },
             py::arg("order_id"), py::arg("stop_price_ticks"), py::arg("qty"), py::arg("account_id") = 0)
        .def("replace_stop_limit_order",
             [](tes::MatchingEngine& self, std::uint64_t order_id, std::int64_t stop_price_ticks,
                std::int64_t limit_price_ticks, std::int64_t qty, std::uint64_t account_id) {
                 const std::vector<tes::Event> events = self.replace_stop_limit_order(
                     account_id, order_id, tes::Price{stop_price_ticks}, tes::Price{limit_price_ticks}, tes::Qty{qty});
                 return events_to_dicts(events);
             },
             py::arg("order_id"), py::arg("stop_price_ticks"), py::arg("limit_price_ticks"), py::arg("qty"),
             py::arg("account_id") = 0)
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
        .def("performance_snapshot",
             [](const tes::MatchingEngine& self, std::uint64_t account_id) {
                 return performance_snapshot_to_py(self.performance_snapshot(account_id));
             },
             py::arg("account_id"))
.def("set_trading_phase",
             [](tes::MatchingEngine& self, const std::string& symbol, const std::string& phase) {
                 return events_to_dicts(self.set_trading_phase(symbol, trading_phase_from_string(phase)));
             },
             py::arg("symbol"), py::arg("phase"))
        .def("trading_phase",
             [](const tes::MatchingEngine& self, const std::string& symbol) { return trading_phase_to_string(self.trading_phase(symbol)); },
             py::arg("symbol") = tes::kDefaultSymbol)
        .def("indicative_price",
             [](const tes::MatchingEngine& self, const std::string& symbol) { const auto price = self.indicative_price(symbol); return price.has_value() ? py::cast(price->ticks) : py::none(); },
             py::arg("symbol") = tes::kDefaultSymbol)
        .def("indicative_volume",
             [](const tes::MatchingEngine& self, const std::string& symbol) { return self.indicative_volume(symbol).value; },
             py::arg("symbol") = tes::kDefaultSymbol)
        .def("auction_imbalance",
             [](const tes::MatchingEngine& self, const std::string& symbol) { return self.auction_imbalance(symbol); },
             py::arg("symbol") = tes::kDefaultSymbol)
        .def("uncross",
             [](tes::MatchingEngine& self, const std::string& symbol) { return events_to_dicts(self.uncross(symbol)); },
             py::arg("symbol") = tes::kDefaultSymbol)
.def("sequence_number",
             [](const tes::MatchingEngine& self, const std::string& symbol) { return self.sequence_number(symbol); },
             py::arg("symbol") = tes::kDefaultSymbol);
}
