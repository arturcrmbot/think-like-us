#!/usr/bin/env python3
"""
Simple system test - no emojis for Windows compatibility
"""
import requests
import json

def test_system():
    print("Testing Telco Retention System...")
    
    # Test API health
    try:
        health = requests.get("http://localhost:8001/api/health", timeout=5)
        if health.status_code == 200:
            print("PASS: API health check")
        else:
            print(f"FAIL: API health returned {health.status_code}")
            return False
    except Exception as e:
        print(f"FAIL: API not reachable - {e}")
        return False
    
    # Test parallel simulation
    try:
        test_data = {
            "customers_at_risk": 100,
            "weekly_budget": 40000,
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
        
        response = requests.post(
            "http://localhost:8001/simulate/parallel",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check basic structure
            required = ['week', 'rule_based_result', 'agent_based_result']
            missing = [f for f in required if f not in data]
            if missing:
                print(f"FAIL: Missing fields {missing}")
                return False
            
            # Check ROI calculations
            rule_roi = data['rule_based_result']['clv_protected'] / max(data['rule_based_result']['budget_spent'], 1)
            agent_roi = data['agent_based_result']['clv_protected'] / max(data['agent_based_result']['budget_spent'], 1)
            
            print(f"PASS: Parallel simulation working")
            print(f"  Rule-based: {rule_roi:.2f}x ROI")
            print(f"  Agent-based: {agent_roi:.2f}x ROI")
            
            if 0.1 < rule_roi < 10 and 0.1 < agent_roi < 10:
                print("PASS: ROI calculations realistic")
                return True
            else:
                print(f"FAIL: ROI values unrealistic - Rule: {rule_roi}, Agent: {agent_roi}")
                return False
                
        else:
            print(f"FAIL: Parallel simulation returned {response.status_code}")
            print(f"Error: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"FAIL: Parallel simulation crashed - {e}")
        return False

if __name__ == "__main__":
    if test_system():
        print("\nSYSTEM TEST PASSED - All working fine")
    else:
        print("\nSYSTEM TEST FAILED - Issues found")