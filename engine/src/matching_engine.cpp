#include <tes/matching_engine.hpp>

#include <algorithm>
#include <limits>

#include <tes/order.hpp>

namespace tes {
namespace {
constexpr AccountId kDefaultAccountId = 0;
constexpr std::int64_t kDefaultLegacyCash = std::numeric_limits<std::int64_t>::max() / 4;
constexpr std::int64_t kDefaultLegacyPosition = std::numeric_limits<std::int64_t>::max() / 4;
}

void MatchingEngine::set_account_state(AccountId account_id, std::int64_t cash_balance, std::int64_t position_qty) { set_account_state(account_id, kDefaultSymbol, cash_balance, position_qty); }
void MatchingEngine::set_account_state(AccountId account_id, const Symbol& symbol, std::int64_t cash_balance, std::int64_t position_qty) { auto& a = accounts_[account_id]; a.cash_balance = cash_balance; a.position_qty_by_symbol[symbol] = position_qty; }
MatchingEngine::AccountSnapshot MatchingEngine::account_snapshot(AccountId account_id) const { auto it=accounts_.find(account_id); return it==accounts_.end()?AccountSnapshot{}:it->second; }
std::optional<AccountId> MatchingEngine::order_owner(OrderId id) const { auto it=order_ownership_by_id_.find(id); return it==order_ownership_by_id_.end()?std::nullopt:std::optional<AccountId>{it->second.account_id}; }
OrderBook& MatchingEngine::book_for(const Symbol& symbol){ return books_[symbol]; }
const OrderBook* MatchingEngine::find_book(const Symbol& symbol) const { auto it=books_.find(symbol); return it==books_.end()?nullptr:&it->second; }
const OrderBook& MatchingEngine::book() const { return books_.at(kDefaultSymbol); }

std::vector<Event> MatchingEngine::place_limit_order(Side side, Price price, Qty qty, TimeInForce tif){ return place_limit_order(kDefaultAccountId,kDefaultSymbol,side,price,qty,tif);} 
std::vector<Event> MatchingEngine::place_limit_order(AccountId account_id, Side side, Price price, Qty qty, TimeInForce tif){ return place_limit_order(account_id,kDefaultSymbol,side,price,qty,tif);} 
std::vector<Event> MatchingEngine::place_limit_order(AccountId account_id, const Symbol& symbol, Side side, Price price, Qty qty, TimeInForce tif){ auto id=next_order_id_++; auto e=place_limit_order_with_account_and_id(account_id,symbol,id,side,price,qty,tif); track_events(e); return e; }

std::vector<Event> MatchingEngine::place_limit_order_with_account_and_id(AccountId account_id, const Symbol& symbol, OrderId taker_id, Side side, Price price, Qty qty, TimeInForce tif) {
    if (!is_valid_price(price)) return {OrderRejected{side, price, qty, RejectReason::InvalidPrice, symbol}};
    if (!is_valid_qty(qty)) return {OrderRejected{side, price, qty, RejectReason::InvalidQuantity, symbol}};
    auto& taker = accounts_[account_id];
    if (account_id == kDefaultAccountId && taker.cash_balance == 0) { taker.cash_balance = kDefaultLegacyCash; taker.position_qty_by_symbol[symbol] = kDefaultLegacyPosition; }
    const auto notional = price.ticks * qty.value;
    const auto pos = taker.position_qty_by_symbol[symbol];
    const auto rsv = taker.reserved_qty_by_symbol[symbol];
    if (side==Side::Bid && taker.cash_balance - taker.reserved_cash < notional) return {OrderRejected{side,price,qty,RejectReason::InsufficientCash,symbol}};
    if (side==Side::Ask && pos - rsv < qty.value) return {OrderRejected{side,price,qty,RejectReason::InsufficientPosition,symbol}};
    auto& book = book_for(symbol);
    std::vector<Event> events; Qty remaining=qty;
    while(remaining.value>0){
      auto pb=book.best_bid(); auto pa=book.best_ask();
      if(side==Side::Bid){ auto ba=book.best_ask(); if(!ba||ba->ticks>price.ticks) break; auto fill=book.fill_best(Side::Ask,remaining); if(!fill) break; remaining.value-=fill->qty.value; events.emplace_back(TradeExecuted{taker_id,fill->maker_id,side,fill->price,fill->qty,symbol}); auto& maker=accounts_[order_ownership_by_id_[fill->maker_id].account_id]; auto n=fill->price.ticks*fill->qty.value; taker.cash_balance-=n; taker.position_qty_by_symbol[symbol]+=fill->qty.value; maker.cash_balance+=n; maker.position_qty_by_symbol[symbol]-=fill->qty.value; maker.reserved_qty_by_symbol[symbol]-=fill->qty.value; maybe_emit_top_of_book_change(symbol,events,pb,pa);}
      else { auto bb=book.best_bid(); if(!bb||bb->ticks<price.ticks) break; auto fill=book.fill_best(Side::Bid,remaining); if(!fill) break; remaining.value-=fill->qty.value; events.emplace_back(TradeExecuted{taker_id,fill->maker_id,side,fill->price,fill->qty,symbol}); auto& maker=accounts_[order_ownership_by_id_[fill->maker_id].account_id]; auto n=fill->price.ticks*fill->qty.value; taker.cash_balance+=n; taker.position_qty_by_symbol[symbol]-=fill->qty.value; maker.cash_balance-=n; maker.position_qty_by_symbol[symbol]+=fill->qty.value; maker.reserved_cash-=n; maybe_emit_top_of_book_change(symbol,events,pb,pa);} }
    if(remaining.value>0){ if(tif==TimeInForce::Ioc) events.emplace_back(OrderExpired{taker_id,symbol}); else { auto r=book.add_limit_order(Order{taker_id,side,price,remaining}); for(auto& e:r){ if(std::holds_alternative<OrderAccepted>(e)){ auto v=std::get<OrderAccepted>(e); v.symbol=symbol; e=v;} if(std::holds_alternative<TopOfBook>(e)){ auto v=std::get<TopOfBook>(e); v.symbol=symbol; e=v; }} order_ownership_by_id_[taker_id]={account_id,symbol,side,price,remaining}; if(side==Side::Bid){ auto reserve=price.ticks*remaining.value; taker.reserved_cash+=reserve; reserved_cash_by_order_id_[taker_id]=reserve;} else { taker.reserved_qty_by_symbol[symbol]+=remaining.value; reserved_qty_by_order_id_[taker_id]=remaining.value;} events.insert(events.end(),r.begin(),r.end()); }}
    return events;
}
std::vector<Event> MatchingEngine::place_market_order(Side side, Qty qty){ return place_market_order(kDefaultAccountId,kDefaultSymbol,side,qty);} 
std::vector<Event> MatchingEngine::place_market_order(AccountId account_id, Side side, Qty qty){ return place_market_order(account_id,kDefaultSymbol,side,qty);} 
std::vector<Event> MatchingEngine::place_market_order(AccountId account_id, const Symbol& symbol, Side side, Qty qty){ auto e=place_limit_order(account_id,symbol,side, side==Side::Bid?Price{INT64_MAX/4}:Price{0}, qty, TimeInForce::Ioc); return e; }
std::vector<Event> MatchingEngine::cancel(OrderId id){ return cancel(kDefaultAccountId,id);} 
std::vector<Event> MatchingEngine::cancel(AccountId account_id, OrderId id){ auto own=order_ownership_by_id_.find(id); if(own==order_ownership_by_id_.end()) return {CancelRejected{id,RejectReason::UnknownOrderId,kDefaultSymbol}}; if(own->second.account_id!=account_id) return {CancelRejected{id,RejectReason::WrongAccount,own->second.symbol}}; auto& book=book_for(own->second.symbol); auto ev=book.cancel(id); if(ev.empty()) return {CancelRejected{id,RejectReason::UnknownOrderId,own->second.symbol}}; for(auto& e:ev){ if(std::holds_alternative<OrderCanceled>(e)){ auto v=std::get<OrderCanceled>(e); v.symbol=own->second.symbol; e=v; }} auto& acct=accounts_[account_id]; if(auto it=reserved_cash_by_order_id_.find(id); it!=reserved_cash_by_order_id_.end()){ acct.reserved_cash-=it->second; reserved_cash_by_order_id_.erase(it);} if(auto it=reserved_qty_by_order_id_.find(id); it!=reserved_qty_by_order_id_.end()){ acct.reserved_qty_by_symbol[own->second.symbol]-=it->second; reserved_qty_by_order_id_.erase(it);} order_ownership_by_id_.erase(id); track_events(ev); return ev; }
std::vector<Event> MatchingEngine::replace_order(OrderId id, Price p, Qty q){ return replace_order(kDefaultAccountId,id,p,q);} 
std::vector<Event> MatchingEngine::replace_order(AccountId account_id, OrderId id, Price p, Qty q){ auto own=order_ownership_by_id_.find(id); if(own==order_ownership_by_id_.end()) return {CancelRejected{id,RejectReason::UnknownOrderId,kDefaultSymbol}}; if(own->second.account_id!=account_id) return {CancelRejected{id,RejectReason::WrongAccount,own->second.symbol}}; auto side=own->second.side; auto sym=own->second.symbol; auto events=cancel(account_id,id); auto place=place_limit_order_with_account_and_id(account_id,sym,id,side,p,q,TimeInForce::Gtc); events.insert(events.end(),place.begin(),place.end()); track_events(place); return events; }
BookDepth MatchingEngine::depth(std::size_t levels) const { return depth(kDefaultSymbol,levels);} 
BookDepth MatchingEngine::depth(const Symbol& symbol, std::size_t levels) const { BookDepth r; auto* b=find_book(symbol); if(!b) return r; auto d=b->depth(levels); for(auto& l:d.bids) r.bids.push_back({l.price,l.qty}); for(auto& l:d.asks) r.asks.push_back({l.price,l.qty}); return r; }
void MatchingEngine::maybe_emit_top_of_book_change(const Symbol& symbol,std::vector<Event>& events,const std::optional<Price>& pb,const std::optional<Price>& pa){ auto& b=book_for(symbol); auto cb=b.best_bid(); auto ca=b.best_ask(); if(pb!=cb||pa!=ca) events.emplace_back(TopOfBook{cb,ca,symbol}); }
void MatchingEngine::track_events(const std::vector<Event>&) {}
}  // namespace tes
