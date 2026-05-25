"""
Test script for behavior prediction API endpoints.
"""
import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/predictions/behavior"


def print_response(title: str, response: requests.Response):
    """Pretty print API response."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)
    print(f"Status: {response.status_code}")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)


def test_health():
    """Test health endpoint."""
    url = f"{BASE_URL}{API_PREFIX}/health"
    response = requests.get(url)
    print_response("HEALTH CHECK", response)
    return response.status_code == 200


def test_get_models():
    """Test get available models."""
    url = f"{BASE_URL}{API_PREFIX}/models"
    response = requests.get(url)
    print_response("GET AVAILABLE MODELS", response)
    return response.status_code == 200


def test_predict_single():
    """Test single prediction."""
    url = f"{BASE_URL}{API_PREFIX}/predict"
    
    test_cases = [
        {
            "name": "Browsing User",
            "payload": {
                "user_id": 311,
                "actions": ["view", "view", "click"],
                "model_type": "bilstm"
            }
        },
        {
            "name": "High Intent User",
            "payload": {
                "user_id": 318,
                "actions": ["view", "click", "add_to_cart", "view"],
                "model_type": "lstm"
            }
        },
        {
            "name": "Searcher",
            "payload": {
                "user_id": 129,
                "actions": ["search", "view", "click"],
                "model_type": "bilstm"
            }
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        response = requests.post(url, json=test_case["payload"])
        print_response(f"PREDICT - {test_case['name']}", response)
        
        if response.status_code != 200:
            all_passed = False
    
    return all_passed


def test_predict_top_k():
    """Test top-k predictions."""
    url = f"{BASE_URL}{API_PREFIX}/predict/top-k"
    
    payload = {
        "user_id": 311,
        "actions": ["view", "click", "add_to_cart"],
        "model_type": "bilstm"
    }
    
    # Test with different k values
    for k in [3, 5]:
        response = requests.post(f"{url}?k={k}", json=payload)
        print_response(f"TOP-{k} PREDICTIONS", response)
        
        if response.status_code != 200:
            return False
    
    return True


def test_analyze_sequence():
    """Test sequence analysis."""
    url = f"{BASE_URL}{API_PREFIX}/analyze-sequence"
    
    test_cases = [
        {
            "name": "Quick Buyer",
            "payload": {
                "user_id": 311,
                "actions": ["view", "click", "purchase"]
            }
        },
        {
            "name": "Window Shopper",
            "payload": {
                "user_id": 318,
                "actions": ["view", "view", "view", "view", "view"]
            }
        },
        {
            "name": "Deliberate Buyer",
            "payload": {
                "user_id": 129,
                "actions": ["search", "view", "click", "add_to_cart", "view", "purchase"]
            }
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        response = requests.post(url, json=test_case["payload"])
        print_response(f"ANALYZE - {test_case['name']}", response)
        
        if response.status_code != 200:
            all_passed = False
    
    return all_passed


def test_batch_predict():
    """Test batch predictions."""
    url = f"{BASE_URL}{API_PREFIX}/batch-predict"
    
    payload = [
        {
            "user_id": 311,
            "actions": ["view", "click"],
            "model_type": "bilstm"
        },
        {
            "user_id": 318,
            "actions": ["view", "add_to_cart"],
            "model_type": "lstm"
        },
        {
            "user_id": 129,
            "actions": ["search", "view", "click"],
            "model_type": "rnn"
        }
    ]
    
    response = requests.post(url, json=payload)
    print_response("BATCH PREDICT", response)
    
    return response.status_code == 200


def test_error_cases():
    """Test error handling."""
    url = f"{BASE_URL}{API_PREFIX}/predict"
    
    error_cases = [
        {
            "name": "Empty Actions",
            "payload": {
                "user_id": 311,
                "actions": [],
                "model_type": "bilstm"
            }
        },
        {
            "name": "Too Few Actions",
            "payload": {
                "user_id": 311,
                "actions": ["view"],
                "model_type": "bilstm"
            }
        },
        {
            "name": "Invalid Model Type",
            "payload": {
                "user_id": 311,
                "actions": ["view", "click"],
                "model_type": "invalid_model"
            }
        }
    ]
    
    all_passed = True
    
    for test_case in error_cases:
        response = requests.post(url, json=test_case["payload"])
        print_response(f"ERROR CASE - {test_case['name']}", response)
        
        # Should return 4xx error
        if response.status_code < 400:
            print(f"❌ Expected error but got {response.status_code}")
            all_passed = False
        else:
            print(f"✓ Correctly returned error status")
    
    return all_passed


def run_all_tests():
    """Run all API tests."""
    print("\n" + "="*80)
    print("  BEHAVIOR PREDICTION API TESTS")
    print("="*80)
    
    tests = [
        ("Health Check", test_health),
        ("Get Models", test_get_models),
        ("Single Prediction", test_predict_single),
        ("Top-K Predictions", test_predict_top_k),
        ("Sequence Analysis", test_analyze_sequence),
        ("Batch Prediction", test_batch_predict),
        ("Error Handling", test_error_cases)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'─'*80}")
        print(f"Running: {test_name}")
        print(f"{'─'*80}")
        
        try:
            passed = test_func()
            results.append((test_name, passed))
            
            if passed:
                print(f"\n✓ {test_name} PASSED")
            else:
                print(f"\n✗ {test_name} FAILED")
                
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Connection Error - Is the API server running?")
            print(f"   Start server with: uvicorn main:app --reload")
            results.append((test_name, False))
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8s} - {test_name}")
    
    print(f"\n{passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        
        test_map = {
            "health": test_health,
            "models": test_get_models,
            "predict": test_predict_single,
            "topk": test_predict_top_k,
            "analyze": test_analyze_sequence,
            "batch": test_batch_predict,
            "errors": test_error_cases
        }
        
        if test_name in test_map:
            print(f"\nRunning test: {test_name}")
            test_map[test_name]()
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(test_map.keys())}")
    else:
        # Run all tests
        run_all_tests()
