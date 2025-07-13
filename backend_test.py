#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Bahis Tahmin Sistemi
Tests all API endpoints and functionality
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class BahisTahminAPITester:
    def __init__(self, base_url="https://5c3c79e0-8da1-441e-8c5e-54a6a09d48f5.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def test_api_endpoint(self, name: str, method: str, endpoint: str, expected_status: int = 200, data: Dict = None) -> tuple:
        """Test a single API endpoint"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                self.log_test(name, False, f"Unsupported method: {method}")
                return False, {}

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            if success:
                self.log_test(name, True, f"Status: {response.status_code}")
            else:
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Response: {response.text[:200]}")

            return success, response_data

        except requests.exceptions.Timeout:
            self.log_test(name, False, "Request timeout (30s)")
            return False, {}
        except requests.exceptions.ConnectionError:
            self.log_test(name, False, "Connection error")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        print("\n🔍 Testing Root Endpoint...")
        success, data = self.test_api_endpoint("Root API", "GET", "")
        
        if success:
            if "message" in data and "version" in data and "status" in data:
                print(f"   📝 Message: {data.get('message')}")
                print(f"   📝 Version: {data.get('version')}")
                print(f"   📝 Status: {data.get('status')}")
            else:
                self.log_test("Root API Response Structure", False, "Missing expected fields")

    def test_system_status(self):
        """Test system status endpoint"""
        print("\n🔍 Testing System Status...")
        success, data = self.test_api_endpoint("System Status", "GET", "system/status")
        
        if success:
            required_fields = ["status", "database", "collections", "timestamp"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                print(f"   📝 Status: {data.get('status')}")
                print(f"   📝 Database: {data.get('database')}")
                collections = data.get('collections', {})
                print(f"   📝 Collections: {collections}")
                self.log_test("System Status Response Structure", True)
            else:
                self.log_test("System Status Response Structure", False, f"Missing fields: {missing_fields}")

    def test_leagues_endpoint(self):
        """Test leagues endpoint"""
        print("\n🔍 Testing Leagues Endpoint...")
        success, data = self.test_api_endpoint("Get Leagues", "GET", "leagues")
        
        if success:
            if "leagues" in data and "count" in data:
                leagues = data.get('leagues', [])
                count = data.get('count', 0)
                print(f"   📝 Total Leagues: {count}")
                
                if leagues:
                    sample_league = leagues[0]
                    print(f"   📝 Sample League: {sample_league.get('name', 'N/A')} ({sample_league.get('country', 'N/A')})")
                    
                    # Check league structure
                    required_fields = ["name", "country", "season", "active"]
                    missing_fields = [field for field in required_fields if field not in sample_league]
                    
                    if not missing_fields:
                        self.log_test("League Data Structure", True)
                    else:
                        self.log_test("League Data Structure", False, f"Missing fields: {missing_fields}")
                else:
                    print("   ⚠️  No leagues found in response")
            else:
                self.log_test("Leagues Response Structure", False, "Missing 'leagues' or 'count' field")

    def test_predictions_today(self):
        """Test today's predictions endpoint"""
        print("\n🔍 Testing Today's Predictions...")
        success, data = self.test_api_endpoint("Today's Predictions", "GET", "predictions/today")
        
        if success:
            if "predictions" in data and "count" in data:
                predictions = data.get('predictions', [])
                count = data.get('count', 0)
                print(f"   📝 Today's Predictions: {count}")
                
                if predictions:
                    sample_prediction = predictions[0]
                    print(f"   📝 Sample Prediction: {sample_prediction.get('home_team_name', 'N/A')} vs {sample_prediction.get('away_team_name', 'N/A')}")
                    self.log_test("Predictions Data Available", True)
                else:
                    print("   ℹ️  No predictions for today (this is normal)")
                    self.log_test("Predictions Endpoint Structure", True)
            else:
                self.log_test("Predictions Response Structure", False, "Missing 'predictions' or 'count' field")

    def test_upcoming_matches(self):
        """Test upcoming matches endpoint"""
        print("\n🔍 Testing Upcoming Matches...")
        success, data = self.test_api_endpoint("Upcoming Matches", "GET", "matches/upcoming")
        
        if success:
            if "matches" in data and "count" in data:
                matches = data.get('matches', [])
                count = data.get('count', 0)
                print(f"   📝 Upcoming Matches: {count}")
                
                if matches:
                    sample_match = matches[0]
                    print(f"   📝 Sample Match: {sample_match.get('home_team_name', 'N/A')} vs {sample_match.get('away_team_name', 'N/A')}")
                    self.log_test("Matches Data Available", True)
                else:
                    print("   ℹ️  No upcoming matches found")
                    self.log_test("Matches Endpoint Structure", True)
            else:
                self.log_test("Matches Response Structure", False, "Missing 'matches' or 'count' field")

    def test_performance_stats(self):
        """Test performance stats endpoint"""
        print("\n🔍 Testing Performance Stats...")
        success, data = self.test_api_endpoint("Performance Stats", "GET", "stats/performance")
        
        if success:
            required_fields = ["period", "total_predictions", "correct_predictions", "accuracy_percentage", "timestamp"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                print(f"   📝 Period: {data.get('period')}")
                print(f"   📝 Total Predictions: {data.get('total_predictions')}")
                print(f"   📝 Correct Predictions: {data.get('correct_predictions')}")
                print(f"   📝 Accuracy: {data.get('accuracy_percentage')}%")
                self.log_test("Performance Stats Structure", True)
            else:
                self.log_test("Performance Stats Structure", False, f"Missing fields: {missing_fields}")

    def test_scraper_trigger(self):
        """Test scraper trigger endpoint"""
        print("\n🔍 Testing Scraper Trigger...")
        success, data = self.test_api_endpoint("Trigger Scraper", "POST", "scraper/run")
        
        if success:
            if "message" in data and "timestamp" in data:
                print(f"   📝 Message: {data.get('message')}")
                print(f"   📝 Timestamp: {data.get('timestamp')}")
                self.log_test("Scraper Trigger Response", True)
            else:
                self.log_test("Scraper Trigger Response", False, "Missing expected response fields")

    def test_prediction_generation(self):
        """Test prediction generation endpoint"""
        print("\n🔍 Testing Prediction Generation...")
        success, data = self.test_api_endpoint("Generate Predictions", "POST", "prediction/generate")
        
        if success:
            if "message" in data and "timestamp" in data:
                print(f"   📝 Message: {data.get('message')}")
                print(f"   📝 Timestamp: {data.get('timestamp')}")
                self.log_test("Prediction Generation Response", True)
            else:
                self.log_test("Prediction Generation Response", False, "Missing expected response fields")

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Comprehensive Backend API Testing...")
        print(f"🌐 Base URL: {self.base_url}")
        print(f"🔗 API URL: {self.api_url}")
        print("=" * 60)

        # Test all endpoints
        self.test_root_endpoint()
        self.test_system_status()
        self.test_leagues_endpoint()
        self.test_predictions_today()
        self.test_upcoming_matches()
        self.test_performance_stats()
        self.test_scraper_trigger()
        self.test_prediction_generation()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Total Tests: {self.tests_run}")
        print(f"🎯 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")

        # Print failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")

        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = BahisTahminAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())