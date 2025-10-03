#!/usr/bin/env python3
"""
Полный цикл тестирования системы breakout bot с реальными данными
"""

import asyncio
import time
import json
import logging
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from breakout_bot.config.settings import SystemConfig
from breakout_bot.core.engine import OptimizedOrchestraEngine
from breakout_bot.utils.metrics_logger import get_metrics_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemTester:
    """Comprehensive system tester"""
    
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.engine = None
        self.test_results = {}
        self.metrics_logger = get_metrics_logger()
        
    async def run_full_test(self):
        """Run complete system test"""
        logger.info("🚀 Starting full system test...")
        
        try:
            # Test 1: API Health Check
            await self.test_api_health()
            
            # Test 2: Engine Initialization
            await self.test_engine_initialization()
            
            # Test 3: Preset Loading
            await self.test_preset_loading()
            
            # Test 4: Engine Start/Stop
            await self.test_engine_lifecycle()
            
            # Test 5: Scanner Functionality
            await self.test_scanner_functionality()
            
            # Test 6: Trading Simulation
            await self.test_trading_simulation()
            
            # Test 7: Metrics Collection
            await self.test_metrics_collection()
            
            # Test 8: WebSocket Connectivity
            await self.test_websocket_connectivity()
            
            # Test 9: Error Handling
            await self.test_error_handling()
            
            # Test 10: Performance Under Load
            await self.test_performance_under_load()
            
            # Generate final report
            self.generate_test_report()
            
        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")
            self.test_results['overall_status'] = 'FAILED'
            self.test_results['error'] = str(e)
    
    async def test_api_health(self):
        """Test API health endpoints"""
        logger.info("🔍 Testing API health...")
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.api_base}/api/health", timeout=10)
            assert response.status_code == 200
            
            health_data = response.json()
            assert 'status' in health_data
            assert 'engine_initialized' in health_data
            
            # Test root endpoint
            response = requests.get(f"{self.api_base}/api/", timeout=10)
            assert response.status_code == 200
            
            self.test_results['api_health'] = 'PASSED'
            logger.info("✅ API health test passed")
            
        except Exception as e:
            self.test_results['api_health'] = f'FAILED: {e}'
            logger.error(f"❌ API health test failed: {e}")
    
    async def test_engine_initialization(self):
        """Test engine initialization"""
        logger.info("🔍 Testing engine initialization...")
        
        try:
            # Create system config
            config = SystemConfig(
                trading_mode="paper",
                paper_mode=True
            )
            
            # Initialize engine
            self.engine = OptimizedOrchestraEngine("breakout_v1", config)
            assert self.engine is not None
            assert hasattr(self.engine, 'current_state')
            
            self.test_results['engine_initialization'] = 'PASSED'
            logger.info("✅ Engine initialization test passed")
            
        except Exception as e:
            self.test_results['engine_initialization'] = f'FAILED: {e}'
            logger.error(f"❌ Engine initialization test failed: {e}")
    
    async def test_preset_loading(self):
        """Test preset loading functionality"""
        logger.info("🔍 Testing preset loading...")
        
        try:
            # Test preset list endpoint
            response = requests.get(f"{self.api_base}/api/presets/", timeout=10)
            assert response.status_code == 200
            
            presets = response.json()
            assert len(presets) > 0
            assert all('name' in preset for preset in presets)
            
            # Test specific preset loading
            response = requests.get(f"{self.api_base}/api/presets/breakout_v1", timeout=10)
            assert response.status_code == 200
            
            preset_config = response.json()
            assert 'name' in preset_config
            assert 'config' in preset_config
            
            self.test_results['preset_loading'] = 'PASSED'
            logger.info("✅ Preset loading test passed")
            
        except Exception as e:
            self.test_results['preset_loading'] = f'FAILED: {e}'
            logger.error(f"❌ Preset loading test failed: {e}")
    
    async def test_engine_lifecycle(self):
        """Test engine start/stop lifecycle"""
        logger.info("🔍 Testing engine lifecycle...")
        
        try:
            # Test engine start
            start_data = {
                "preset": "breakout_v1",
                "mode": "paper"
            }
            
            response = requests.post(f"{self.api_base}/api/engine/start", 
                                   json=start_data, timeout=60)
            assert response.status_code == 200
            
            start_result = response.json()
            assert start_result.get('success') == True
            
            # Wait a bit for engine to initialize
            await asyncio.sleep(2)
            
            # Test engine status
            response = requests.get(f"{self.api_base}/api/engine/status", timeout=10)
            assert response.status_code == 200
            
            status = response.json()
            assert 'state' in status
            
            # Test engine stop
            response = requests.post(f"{self.api_base}/api/engine/stop", timeout=60)
            assert response.status_code == 200
            
            stop_result = response.json()
            assert stop_result.get('success') == True
            
            self.test_results['engine_lifecycle'] = 'PASSED'
            logger.info("✅ Engine lifecycle test passed")
            
        except Exception as e:
            self.test_results['engine_lifecycle'] = f'FAILED: {e}'
            logger.error(f"❌ Engine lifecycle test failed: {e}")
            logger.error(f"Error: {type(e).__name__}: {str(e)}")
    
    async def test_scanner_functionality(self):
        """Test scanner functionality"""
        logger.info("🔍 Testing scanner functionality...")
        
        try:
            # Test scanner scan endpoint
            scan_data = {
                "preset": "breakout_v1",
                "limit": 5
            }
            
            response = requests.post(f"{self.api_base}/api/scanner/scan", 
                                   json=scan_data, timeout=60)
            assert response.status_code == 200
            
            scan_result = response.json()
            assert 'candidates' in scan_result
            
            # Test scanner status
            response = requests.get(f"{self.api_base}/api/scanner/status", timeout=10)
            assert response.status_code == 200
            
            self.test_results['scanner_functionality'] = 'PASSED'
            logger.info("✅ Scanner functionality test passed")
            
        except Exception as e:
            self.test_results['scanner_functionality'] = f'FAILED: {e}'
            logger.error(f"❌ Scanner functionality test failed: {e}")
    
    async def test_trading_simulation(self):
        """Test trading simulation"""
        logger.info("🔍 Testing trading simulation...")
        
        try:
            # Start engine for trading test
            start_data = {
                "preset": "breakout_v1",
                "mode": "paper"
            }
            
            response = requests.post(f"{self.api_base}/api/engine/start", 
                                   json=start_data, timeout=60)
            assert response.status_code == 200
            
            # Wait for engine to run
            await asyncio.sleep(5)
            
            # Test positions endpoint
            response = requests.get(f"{self.api_base}/api/positions", timeout=10)
            assert response.status_code == 200
            
            positions = response.json()
            assert isinstance(positions, list)
            
            # Test orders endpoint
            response = requests.get(f"{self.api_base}/api/orders", timeout=10)
            assert response.status_code == 200
            
            orders = response.json()
            assert isinstance(orders, list)
            
            # Stop engine
            response = requests.post(f"{self.api_base}/api/engine/stop", timeout=60)
            assert response.status_code == 200
            
            self.test_results['trading_simulation'] = 'PASSED'
            logger.info("✅ Trading simulation test passed")
            
        except Exception as e:
            self.test_results['trading_simulation'] = f'FAILED: {e}'
            logger.error(f"❌ Trading simulation test failed: {e}")
    
    async def test_metrics_collection(self):
        """Test metrics collection"""
        logger.info("🔍 Testing metrics collection...")
        
        try:
            # Test metrics summary
            response = requests.get(f"{self.api_base}/api/metrics/summary", timeout=10)
            assert response.status_code == 200
            
            metrics = response.json()
            assert 'performance' in metrics
            assert 'engine' in metrics
            
            # Test performance metrics
            response = requests.get(f"{self.api_base}/api/metrics/performance", timeout=10)
            assert response.status_code == 200
            
            performance = response.json()
            assert 'cpu_percent' in performance
            
            # Test metrics health
            response = requests.get(f"{self.api_base}/api/metrics/health", timeout=10)
            assert response.status_code == 200
            
            health = response.json()
            assert 'status' in health
            
            self.test_results['metrics_collection'] = 'PASSED'
            logger.info("✅ Metrics collection test passed")
            
        except Exception as e:
            self.test_results['metrics_collection'] = f'FAILED: {e}'
            logger.error(f"❌ Metrics collection test failed: {e}")
    
    async def test_websocket_connectivity(self):
        """Test WebSocket connectivity"""
        logger.info("🔍 Testing WebSocket connectivity...")
        
        try:
            import websockets
            
            # Connect to WebSocket
            uri = "ws://localhost:8000/ws"
            async with websockets.connect(uri, timeout=10) as websocket:
                # Wait for heartbeat
                message = await asyncio.wait_for(websocket.recv(), timeout=15)
                data = json.loads(message)
                
                assert data.get('type') == 'HEARTBEAT'
                assert 'data' in data
                
                self.test_results['websocket_connectivity'] = 'PASSED'
                logger.info("✅ WebSocket connectivity test passed")
                
        except Exception as e:
            self.test_results['websocket_connectivity'] = f'FAILED: {e}'
            logger.error(f"❌ WebSocket connectivity test failed: {e}")
    
    async def test_error_handling(self):
        """Test error handling"""
        logger.info("🔍 Testing error handling...")
        
        try:
            # Test invalid preset
            start_data = {
                "preset": "invalid_preset",
                "mode": "paper"
            }
            
            response = requests.post(f"{self.api_base}/api/engine/start", 
                                   json=start_data, timeout=10)
            assert response.status_code == 400  # Should return error
            
            # Test invalid endpoint
            response = requests.get(f"{self.api_base}/api/invalid", timeout=10)
            assert response.status_code == 404
            
            self.test_results['error_handling'] = 'PASSED'
            logger.info("✅ Error handling test passed")
            
        except Exception as e:
            self.test_results['error_handling'] = f'FAILED: {e}'
            logger.error(f"❌ Error handling test failed: {e}")
    
    async def test_performance_under_load(self):
        """Test performance under load"""
        logger.info("🔍 Testing performance under load...")
        
        try:
            # Start engine
            start_data = {
                "preset": "breakout_v1",
                "mode": "paper"
            }
            
            response = requests.post(f"{self.api_base}/api/engine/start", 
                                   json=start_data, timeout=60)
            assert response.status_code == 200
            
            # Run multiple concurrent requests
            tasks = []
            for i in range(10):
                task = asyncio.create_task(self._make_concurrent_request(i))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check that most requests succeeded
            success_count = sum(1 for result in results if not isinstance(result, Exception))
            assert success_count >= 8  # At least 80% should succeed
            
            # Stop engine
            response = requests.post(f"{self.api_base}/api/engine/stop", timeout=60)
            assert response.status_code == 200
            
            self.test_results['performance_under_load'] = 'PASSED'
            logger.info("✅ Performance under load test passed")
            
        except Exception as e:
            self.test_results['performance_under_load'] = f'FAILED: {e}'
            logger.error(f"❌ Performance under load test failed: {e}")
    
    async def _make_concurrent_request(self, request_id: int):
        """Make a concurrent request for load testing"""
        try:
            response = requests.get(f"{self.api_base}/api/engine/status", timeout=5)
            return response.status_code == 200
        except Exception as e:
            return e
    
    def generate_test_report(self):
        """Generate final test report"""
        logger.info("📊 Generating test report...")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result == 'PASSED')
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'test_results': self.test_results
        }
        
        # Save report to file
        with open('test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        logger.info("=" * 50)
        logger.info("📊 TEST REPORT SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {report['success_rate']:.1f}%")
        logger.info("=" * 50)
        
        for test_name, result in self.test_results.items():
            status = "✅" if result == 'PASSED' else "❌"
            logger.info(f"{status} {test_name}: {result}")
        
        logger.info("=" * 50)
        logger.info(f"📄 Full report saved to: test_report.json")

async def main():
    """Main test function"""
    tester = SystemTester()
    await tester.run_full_test()

if __name__ == "__main__":
    asyncio.run(main())
