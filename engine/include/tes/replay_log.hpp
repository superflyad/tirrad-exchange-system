#pragma once

#include <cstddef>
#include <optional>
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
    ReplayCommand command;
    std::vector<Event> events;
};

class ReplayLog {
  public:
    void record(ReplayCommand command, std::vector<Event> events) {
        entries_.push_back(ReplayEntry{std::move(command), std::move(events)});
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
    }

  private:
    std::vector<ReplayEntry> entries_;
};

}  // namespace tes
