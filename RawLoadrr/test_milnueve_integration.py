#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MILNUEVE Integration Test Script
Verifica que todo está correctamente integrado
"""

import asyncio
import sys
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_rate_limiter():
    """Test rate limiter functionality"""
    print("\n📊 Testing Rate Limiter...")
    try:
        from src.rate_limiter import rate_limiter
        
        # Test MILNU limit
        stats = rate_limiter.get_stats('MILNU')
        assert stats['max_calls'] == 30, f"MILNU limit should be 30, got {stats['max_calls']}"
        print(f"  ✓ MILNU rate limit: {stats['max_calls']} calls/min")
        
        # Test EMU limit
        stats = rate_limiter.get_stats('EMU')
        assert stats['max_calls'] == 60, f"EMU limit should be 60, got {stats['max_calls']}"
        print(f"  ✓ EMU rate limit: {stats['max_calls']} calls/min")
        
        # Test acquire (should not wait on first call)
        wait = await rate_limiter.acquire('MILNU')
        print(f"  ✓ Rate limiter acquire works (wait={wait}s)")
        
        print("✅ Rate Limiter: OK")
        return True
    except Exception as e:
        print(f"❌ Rate Limiter: FAILED - {e}")
        return False


async def test_logger():
    """Test logger functionality"""
    print("\n📝 Testing Logger...")
    try:
        from src.logger import get_logger
        import os
        
        logger = get_logger('TEST_MILNU')
        
        # Test error logging
        logger.error("This is a test error")
        logger.warning("This is a test warning")
        logger.info("This is a test info")
        logger.debug("This is a test debug")
        
        # Check files exist
        error_log = logger.get_error_log_path()
        debug_log = logger.get_debug_log_path()
        
        assert os.path.exists(error_log), f"Error log not created: {error_log}"
        assert os.path.exists(debug_log), f"Debug log not created: {debug_log}"
        
        print(f"  ✓ Error log: {error_log}")
        print(f"  ✓ Debug log: {debug_log}")
        
        # Verify content
        with open(error_log, 'r') as f:
            content = f.read()
            assert "test error" in content.lower(), "Error not logged"
        
        print("✅ Logger: OK")
        return True
    except Exception as e:
        print(f"❌ Logger: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tracker_milnu():
    """Test MILNU tracker class"""
    print("\n🎯 Testing MILNU Tracker...")
    try:
        from data.config import config
        from src.trackers.MILNU import MILNU
        
        # Initialize tracker
        milnu = MILNU(config)
        
        assert milnu.tracker == 'MILNU', f"Tracker name should be MILNU, got {milnu.tracker}"
        assert 'milnueve.neklair.es' in milnu.upload_url, f"Upload URL incorrect: {milnu.upload_url}"
        assert milnu.logger is not None, "Logger not initialized"
        
        print(f"  ✓ Tracker: {milnu.tracker}")
        print(f"  ✓ Upload URL: {milnu.upload_url}")
        print(f"  ✓ Search URL: {milnu.search_url}")
        print(f"  ✓ Logger initialized: {type(milnu.logger).__name__}")
        
        # Test category mapping
        cat_id = await milnu.get_cat_id('MOVIE')
        assert cat_id == '1', f"MOVIE category should be 1, got {cat_id}"
        print(f"  ✓ Category mapping works")
        
        # Test type mapping
        type_id = await milnu.get_type_id('REMUX')
        assert type_id == '2', f"REMUX type should be 2, got {type_id}"
        print(f"  ✓ Type mapping works")
        
        # Test resolution mapping
        res_id = await milnu.get_res_id('1080p')
        assert res_id == '3', f"1080p resolution should be 3, got {res_id}"
        print(f"  ✓ Resolution mapping works")
        
        print("✅ MILNU Tracker: OK")
        return True
    except Exception as e:
        print(f"❌ MILNU Tracker: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tracker_emu_updated():
    """Test that EMU was properly updated"""
    print("\n🎯 Testing EMU Tracker (updated)...")
    try:
        from data.config import config
        from src.trackers.EMU import EMU
        
        # Initialize tracker
        emu = EMU(config)
        
        assert emu.logger is not None, "Logger not initialized in EMU"
        print(f"  ✓ EMU now has logger: {type(emu.logger).__name__}")
        
        print("✅ EMU Tracker: OK")
        return True
    except Exception as e:
        print(f"❌ EMU Tracker: FAILED - {e}")
        return False


async def test_config():
    """Test that config has MILNU"""
    print("\n⚙️  Testing Configuration...")
    try:
        from data.config import config
        
        assert 'MILNU' in config['TRACKERS'], "MILNU not in config TRACKERS"
        
        milnu_config = config['TRACKERS']['MILNU']
        assert 'api_key' in milnu_config, "MILNU config missing api_key"
        assert 'announce_url' in milnu_config, "MILNU config missing announce_url"
        
        print(f"  ✓ MILNU in config")
        print(f"  ✓ API Key placeholder: {milnu_config['api_key'][:20]}...")
        print(f"  ✓ Announce URL: {milnu_config['announce_url']}")
        
        print("✅ Configuration: OK")
        return True
    except Exception as e:
        print(f"❌ Configuration: FAILED - {e}")
        return False


async def test_upload_py():
    """Test that trackers_registry.json contains MILNU and that upload.py loads it dynamically"""
    print("\n📋 Testing tracker registry (trackers_registry.json)...")
    import json, os
    registry_candidates = [
        os.path.join(os.path.dirname(__file__), 'src', 'trackers', 'trackers_registry.json'),
        os.path.join('src', 'trackers', 'trackers_registry.json'),
    ]
    try:
        registry_path = next(p for p in registry_candidates if os.path.isfile(p))
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        assert 'MILNU' in registry, "MILNU not found in trackers_registry.json"
        assert registry['MILNU'] == 'api', f"MILNU type should be 'api', got '{registry['MILNU']}'"

        upload_py_path = next(
            (p for p in [
                os.path.join(os.path.dirname(__file__), 'upload.py'),
                'upload.py',
            ] if os.path.isfile(p)), None
        )
        assert upload_py_path, "upload.py not found"
        with open(upload_py_path, 'r') as f:
            upload_content = f.read()
        assert '_load_tracker_registry' in upload_content, "Dynamic loader not found in upload.py"
        assert 'trackers_registry.json' in upload_content, "Registry path reference not found in upload.py"

        print("  ✓ MILNU in trackers_registry.json (type=api)")
        print("  ✓ upload.py uses dynamic _load_tracker_registry()")
        print("✅ Tracker registry: OK")
        return True
    except Exception as e:
        print(f"❌ Tracker registry: FAILED - {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 MILNUEVE INTEGRATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(await test_rate_limiter())
    results.append(await test_logger())
    results.append(await test_config())
    results.append(await test_upload_py())
    results.append(await test_tracker_emu_updated())
    results.append(await test_tracker_milnu())
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED! MILNUEVE is ready to use.")
        print("\nNEXT STEPS:")
        print("1. Edit data/config.py - add your MILNU API key")
        print("2. Test: python3 upload.py --tracker MILNU --input <file>")
        print("3. Check logs: logs/MILNU_errors.log")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. See above for details.")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
