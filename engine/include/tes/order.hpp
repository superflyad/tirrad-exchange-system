#pragma once

#include <tes/types.hpp>

namespace tes {

struct Order {
    OrderId id;
    Side side;
    Price price;
    Qty qty;
};

}  // namespace tes
