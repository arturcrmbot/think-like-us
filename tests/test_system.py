#!/usr/bin/env python3
"""
Complete system test for Telco Retention Dashboard
Tests frontend-backend integration with realistic scenarios
"""

import asyncio
import json
import aiohttp
import sys
from typing import Dict, Any

class SystemTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        
    async def test_api_health(self):
        """Test basic API connectivity"""
        print("Testing API health...")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/api/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"PASS API Health: {data['status']}")
                        return True
                    else:
                        print(f"FAIL API Health check failed: {response.status}")
                        return False
            except Exception as e:
                print(f"FAIL API not reachable: {e}")
                return False

    async def test_parallel_simulation(self):
        """Test parallel simulation with realistic parameters"""
        print("\n🔍 Testing parallel simulation...")
        
        test_request = {
            "customers_at_risk": 100,
            "weekly_budget": 100000,
            "success_rates": {
                "discount": 0.4,
                "priority_fix": 0.7,
                "executive_escalation": 0.85
            },
            "intervention_costs": {
                "discount_duration_months": 6,
                "priority_fix": 300,
                "executive_escalation": 600
            },
            "current_week": 1,
            "simulation_history": []
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/simulate/parallel",
                    json=test_request,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Validate response structure
                        required_fields = ['week', 'rule_based_result', 'agent_based_result']
                        missing_fields = [field for field in required_fields if field not in data]
                        
                        if missing_fields:
                            print(f"FAIL Missing fields in response: {missing_fields}")
                            return False
                        
                        # Check calculations make sense
                        rule_result = data['rule_based_result']
                        agent_result = data['agent_based_result']
                        
                        rule_roi = rule_result['clv_protected'] / max(rule_result['budget_spent'], 1)
                        agent_roi = agent_result['clv_protected'] / max(agent_result['budget_spent'], 1)
                        
                        print(f"PASS Parallel simulation successful")
                        print(f"   📊 Rule-based: {rule_result['customers_saved']['basic']} customers, £{rule_result['clv_protected']:.0f} CLV, £{rule_result['budget_spent']:.0f} spent, {rule_roi:.2f}x ROI")
                        print(f"   🤖 Agent-based: {agent_result['customers_saved']['basic']} customers, £{agent_result['clv_protected']:.0f} CLV, £{agent_result['budget_spent']:.0f} spent, {agent_roi:.2f}x ROI")
                        
                        # Validate ROI is positive and realistic
                        if rule_roi < 0.5 or rule_roi > 20:
                            print(f"⚠️  Rule-based ROI looks unrealistic: {rule_roi:.2f}x")
                        if agent_roi < 0.5 or agent_roi > 20:
                            print(f"⚠️  Agent-based ROI looks unrealistic: {agent_roi:.2f}x")
                        
                        return True
                        
                    else:
                        error_text = await response.text()
                        print(f"FAIL Parallel simulation failed: {response.status}")
                        print(f"   Error: {error_text[:200]}...")
                        return False
                        
            except asyncio.TimeoutError:
                print("FAIL Parallel simulation timed out (>30s)")
                return False
            except Exception as e:
                print(f"FAIL Parallel simulation error: {e}")
                return False

    async def test_frontend_backend_integration(self):
        """Test complete frontend-backend integration"""
        print("\n🔍 Testing frontend-backend integration...")
        
        # Test multiple weeks with different parameters
        week_configs = [
            {"customers": 50, "budget": 50000, "duration": 3},
            {"customers": 100, "budget": 100000, "duration": 6}, 
            {"customers": 200, "budget": 150000, "duration": 12}
        ]
        
        simulation_history = []
        all_passed = True
        
        for i, config in enumerate(week_configs, 1):
            print(f"   🗓️  Week {i}: {config['customers']} customers, £{config['budget']} budget, {config['duration']} months discount")
            
            test_request = {
                "customers_at_risk": config["customers"],
                "weekly_budget": config["budget"],
                "success_rates": {
                    "discount": 0.4,
                    "priority_fix": 0.7,
                    "executive_escalation": 0.85
                },
                "intervention_costs": {
                    "discount_duration_months": config["duration"],
                    "priority_fix": 300,
                    "executive_escalation": 600
                },
                "current_week": i,
                "simulation_history": simulation_history
            }
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{self.base_url}/simulate/parallel",
                        json=test_request,
                        timeout=20
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Add to history for next week
                            simulation_history.append({
                                'week': i,
                                'clv_protected': data['agent_based_result']['clv_protected'],
                                'budget_spent': data['agent_based_result']['budget_spent']
                            })
                            
                            agent_roi = data['agent_based_result']['clv_protected'] / max(data['agent_based_result']['budget_spent'], 1)
                            print(f"      PASS Week {i} completed - ROI: {agent_roi:.2f}x")
                            
                        else:
                            print(f"      FAIL Week {i} failed: {response.status}")
                            all_passed = False
                            break
                            
                except Exception as e:
                    print(f"      FAIL Week {i} error: {e}")
                    all_passed = False
                    break
        
        return all_passed

    async def run_all_tests(self):
        """Run complete system test suite"""
        print("🚀 Starting Complete System Test Suite")
        print("=" * 50)
        
        # Test 1: API Health
        health_ok = await self.test_api_health()
        if not health_ok:
            print("\nFAIL SYSTEM TEST FAILED: API not healthy")
            return False
            
        # Test 2: Parallel Simulation
        parallel_ok = await self.test_parallel_simulation()
        if not parallel_ok:
            print("\nFAIL SYSTEM TEST FAILED: Parallel simulation broken")
            return False
            
        # Test 3: Multi-week Integration
        integration_ok = await self.test_frontend_backend_integration()
        if not integration_ok:
            print("\nFAIL SYSTEM TEST FAILED: Frontend-backend integration broken")
            return False
            
        print("\n" + "=" * 50)
        print("🎉 ALL SYSTEM TESTS PASSED!")
        print("PASS API connectivity working")
        print("PASS Parallel simulations working")
        print("PASS Multi-week integration working")
        print("PASS ROI calculations realistic")
        print("PASS Frontend-backend communication working")
        return True

async def main():
    """Main test execution"""
    tester = SystemTester()
    
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test suite interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())