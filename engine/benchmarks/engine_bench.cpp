#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include <tes/events.hpp>
#include <tes/matching_engine.hpp>
#include <tes/order_book.hpp>

namespace {
using Clock = std::chrono::steady_clock;
struct BenchResult { std::string name; std::uint64_t ops; double elapsed_s; std::string notes; };
void print(const BenchResult& r){ const double ops_sec=r.elapsed_s>0?static_cast<double>(r.ops)/r.elapsed_s:0; std::cout<<r.name<<", operation_count="<<r.ops<<", elapsed_s="<<std::fixed<<std::setprecision(6)<<r.elapsed_s<<", ops_sec="<<std::setprecision(2)<<ops_sec; if(!r.notes.empty()) std::cout<<", notes="<<r.notes; std::cout<<"\n"; }
BenchResult run_cancel_positions(){ tes::MatchingEngine e; auto mk=[&](int p){return std::get<tes::OrderAccepted>(e.place_limit_order(tes::Side::Bid,tes::Price{p},tes::Qty{1}).front()).id;}; auto a=mk(100), b=mk(100), c=mk(100); auto t0=Clock::now(); (void)e.cancel(a); (void)e.cancel(b); (void)e.cancel(c); return {"cancel_same_price_first_middle_last",3,std::chrono::duration<double>(Clock::now()-t0).count(),"same_price_orders=3"}; }
BenchResult run_cancel_many_same_price(){ tes::MatchingEngine e; std::uint64_t n=40000; std::vector<tes::OrderId> ids; ids.reserve(n); for(std::uint64_t i=0;i<n;++i) ids.push_back(std::get<tes::OrderAccepted>(e.place_limit_order(tes::Side::Bid,tes::Price{100},tes::Qty{1}).front()).id); auto t0=Clock::now(); for(auto id:ids)(void)e.cancel(id); return {"cancel_many_same_price_orders",n,std::chrono::duration<double>(Clock::now()-t0).count(),"price=100"}; }
BenchResult run_find_many_same_price(){ tes::OrderBook b; std::uint64_t n=50000; std::vector<tes::OrderId> ids; ids.reserve(n); for(std::uint64_t i=0;i<n;++i){ const tes::OrderId id=static_cast<tes::OrderId>(i+1); ids.push_back(id); (void)b.add_limit_order(tes::Order{id,tes::Side::Ask,tes::Price{101},tes::Qty{1}});} auto t0=Clock::now(); for(auto id:ids){ auto o=b.find_order(id); if(!o.has_value()) std::abort(); } return {"find_many_same_price_orders",n,std::chrono::duration<double>(Clock::now()-t0).count(),"price=101"}; }
BenchResult run_replace_many(){ tes::MatchingEngine e; std::uint64_t n=20000; std::vector<tes::OrderId> ids; ids.reserve(n); for(std::uint64_t i=0;i<n;++i) ids.push_back(std::get<tes::OrderAccepted>(e.place_limit_order(tes::Side::Bid,tes::Price{100},tes::Qty{1}).front()).id); auto t0=Clock::now(); for(auto id:ids)(void)e.replace_order(id, tes::Price{101}, tes::Qty{1}); return {"replace_many_orders",n,std::chrono::duration<double>(Clock::now()-t0).count(),"100->101"}; }
BenchResult run_partial_fill_then_cancel(){ tes::MatchingEngine e; std::uint64_t n=20000; std::vector<tes::OrderId> ids; ids.reserve(n); for(std::uint64_t i=0;i<n;++i) ids.push_back(std::get<tes::OrderAccepted>(e.place_limit_order(tes::Side::Ask,tes::Price{102},tes::Qty{2}).front()).id); auto t0=Clock::now(); for(auto id:ids){ (void)e.place_market_order(tes::Side::Bid,tes::Qty{1}); (void)e.cancel(id);} return {"partial_fill_followed_by_cancel",n*2,std::chrono::duration<double>(Clock::now()-t0).count(),"ask_qty=2,taker_qty=1"}; }
BenchResult run_multi_symbol_mixed(){ tes::MatchingEngine e; const std::vector<tes::Symbol> syms={"AAPL","MSFT","GOOG","TSLA"}; std::uint64_t n=50000; std::vector<tes::OrderId> ids; ids.reserve(n/2); auto t0=Clock::now(); for(std::uint64_t i=0;i<n;++i){ const auto& s=syms[i%syms.size()]; if(i%5==0 && !ids.empty()){ (void)e.cancel(ids.back()); ids.pop_back(); continue; } auto ev=e.place_limit_order(1,s,(i%2)?tes::Side::Bid:tes::Side::Ask,tes::Price{100+static_cast<int>(i%7)},tes::Qty{1},tes::TimeInForce::Gtc); if(std::holds_alternative<tes::OrderAccepted>(ev.front())) ids.push_back(std::get<tes::OrderAccepted>(ev.front()).id);} return {"multi_symbol_mixed_add_cancel_replace",n,std::chrono::duration<double>(Clock::now()-t0).count(),"symbols=4"}; }
BenchResult run_depth_reads(){ tes::MatchingEngine e; for(int i=0;i<6000;++i){(void)e.place_limit_order(1,"AAPL",tes::Side::Bid,tes::Price{100+i%40},tes::Qty{1},tes::TimeInForce::Gtc);(void)e.place_limit_order(1,"AAPL",tes::Side::Ask,tes::Price{101+i%40},tes::Qty{1},tes::TimeInForce::Gtc);} std::uint64_t n=30000; auto t0=Clock::now(); for(std::uint64_t i=0;i<n;++i){ (void)e.depth("AAPL",20); (void)e.snapshot("AAPL",20);} return {"repeated_depth_snapshot_reads",n*2,std::chrono::duration<double>(Clock::now()-t0).count(),"levels=20"}; }
}

int main(){ for (const auto& r: std::vector<BenchResult>{run_cancel_positions(),run_cancel_many_same_price(),run_find_many_same_price(),run_replace_many(),run_partial_fill_then_cancel(),run_multi_symbol_mixed(),run_depth_reads()}) print(r); }
