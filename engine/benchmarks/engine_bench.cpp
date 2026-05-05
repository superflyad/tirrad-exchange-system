#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include <tes/matching_engine.hpp>
#include <tes/events.hpp>

namespace {
using Clock = std::chrono::steady_clock;
struct BenchResult { std::string name; std::uint64_t ops; double elapsed_s; };
void print(const BenchResult& r){ double ops_sec=r.elapsed_s>0?static_cast<double>(r.ops)/r.elapsed_s:0; std::cout<<r.name<<", operation_count="<<r.ops<<", elapsed_s="<<std::fixed<<std::setprecision(6)<<r.elapsed_s<<", ops_sec="<<std::setprecision(2)<<ops_sec<<"\n"; }
BenchResult run_add_resting(){ tes::MatchingEngine e; std::uint64_t n=50000; auto t0=Clock::now(); for(std::uint64_t i=0;i<n;++i) (void)e.place_limit_order(tes::Side::Bid, tes::Price{100+static_cast<int>(i%50)}, tes::Qty{1}); return {"add_many_resting_limit_orders",n,std::chrono::duration<double>(Clock::now()-t0).count()}; }
BenchResult run_sweep_one(){ tes::MatchingEngine e; std::uint64_t n=20000; for(std::uint64_t i=0;i<n;++i) (void)e.place_limit_order(tes::Side::Ask, tes::Price{100}, tes::Qty{1}); auto t0=Clock::now(); (void)e.place_market_order(tes::Side::Bid, tes::Qty{static_cast<int>(n)}); return {"sweep_one_price_level",n,std::chrono::duration<double>(Clock::now()-t0).count()}; }
BenchResult run_sweep_many(){ tes::MatchingEngine e; std::uint64_t levels=200, per=100; for(std::uint64_t p=0;p<levels;++p) for(std::uint64_t i=0;i<per;++i) (void)e.place_limit_order(tes::Side::Ask, tes::Price{100+static_cast<int>(p)}, tes::Qty{1}); auto t0=Clock::now(); (void)e.place_market_order(tes::Side::Bid, tes::Qty{static_cast<int>(levels*per)}); return {"sweep_many_price_levels",levels*per,std::chrono::duration<double>(Clock::now()-t0).count()}; }
BenchResult run_cancel_many(){ tes::MatchingEngine e; std::uint64_t n=30000; std::vector<tes::OrderId> ids; ids.reserve(n); for(std::uint64_t i=0;i<n;++i){ auto ev=e.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{1}); ids.push_back(std::get<tes::OrderAccepted>(ev.front()).id);} auto t0=Clock::now(); for(auto id:ids)(void)e.cancel(id); return {"cancel_many_orders",n,std::chrono::duration<double>(Clock::now()-t0).count()}; }
BenchResult run_replace_many(){ tes::MatchingEngine e; std::uint64_t n=15000; std::vector<tes::OrderId> ids; ids.reserve(n); for(std::uint64_t i=0;i<n;++i){ auto ev=e.place_limit_order(tes::Side::Bid, tes::Price{100}, tes::Qty{1}); ids.push_back(std::get<tes::OrderAccepted>(ev.front()).id);} auto t0=Clock::now(); for(auto id:ids)(void)e.replace_order(id, tes::Price{101}, tes::Qty{1}); return {"replace_many_orders",n,std::chrono::duration<double>(Clock::now()-t0).count()}; }
BenchResult run_multi_symbol(){ tes::MatchingEngine e; const std::vector<tes::Symbol> syms={"AAPL","MSFT","GOOG","TSLA"}; std::uint64_t n=40000; auto t0=Clock::now(); for(std::uint64_t i=0;i<n;++i){const auto& s=syms[i%syms.size()]; (void)e.place_limit_order(1,s,(i%2)?tes::Side::Bid:tes::Side::Ask,tes::Price{100+static_cast<int>(i%10)},tes::Qty{1},tes::TimeInForce::Gtc);} return {"multi_symbol_mixed_order_flow",n,std::chrono::duration<double>(Clock::now()-t0).count()}; }
BenchResult run_depth_reads(){ tes::MatchingEngine e; for(int i=0;i<5000;++i){(void)e.place_limit_order(1,"AAPL",tes::Side::Bid,tes::Price{100+i%40},tes::Qty{1},tes::TimeInForce::Gtc);(void)e.place_limit_order(1,"AAPL",tes::Side::Ask,tes::Price{101+i%40},tes::Qty{1},tes::TimeInForce::Gtc);} std::uint64_t n=20000; auto t0=Clock::now(); for(std::uint64_t i=0;i<n;++i){(void)e.depth("AAPL",20);(void)e.snapshot("AAPL",20);} return {"snapshot_depth_repeated_reads",n*2,std::chrono::duration<double>(Clock::now()-t0).count()}; }
}
int main(){ for (const auto& r: std::vector<BenchResult>{run_add_resting(),run_sweep_one(),run_sweep_many(),run_cancel_many(),run_replace_many(),run_multi_symbol(),run_depth_reads()}) print(r); }
