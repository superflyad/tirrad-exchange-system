#pragma once

#include <tes/types.hpp>

namespace tes {

struct Order {
    OrderId id;
    Side side;
    Price price;
    Qty qty;
    OrderVisibility visibility{OrderVisibility::Displayed};
    Qty total_qty{0};
    Qty display_qty{0};
    Qty reserve_qty{0};
};

}  // namespace tes
