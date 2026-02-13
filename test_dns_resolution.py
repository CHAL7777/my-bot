#!/usr/bin/env python3
"""
Test script to verify DNS resolution works in the container.
Run this inside the bot container to test connectivity.
"""

import socket
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dns_resolution(hostname, timeout=10):
    """Test DNS resolution for a given hostname."""
    try:
        start_time = time.time()
        ip_address = socket.gethostbyname(hostname)
        resolve_time = time.time() - start_time

        logger.info(f"✓ DNS resolution successful for {hostname}")
        logger.info(f"  IP Address: {ip_address}")
        logger.info(".2f")
        return True, ip_address

    except socket.gaierror as e:
        logger.error(f"✗ DNS resolution failed for {hostname}: {e}")
        return False, None
    except Exception as e:
        logger.error(f"✗ Unexpected error testing {hostname}: {e}")
        return False, None

def test_connectivity(hostname, port=443, timeout=10):
    """Test TCP connectivity to a host and port."""
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((hostname, port))
        sock.close()
        connect_time = time.time() - start_time

        logger.info(f"✓ TCP connection successful to {hostname}:{port}")
        logger.info(".2f")
        return True

    except socket.timeout:
        logger.error(f"✗ TCP connection timeout to {hostname}:{port}")
        return False
    except socket.error as e:
        logger.error(f"✗ TCP connection failed to {hostname}:{port}: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error connecting to {hostname}:{port}: {e}")
        return False

def main():
    """Main test function."""
    logger.info("Starting DNS resolution and connectivity tests...")

    # Test hosts
    test_hosts = [
        ("api.telegram.org", 443),
        ("google.com", 443),
        ("cloudflare.com", 443),
        ("github.com", 443)
    ]

    results = []

    for hostname, port in test_hosts:
        logger.info(f"\n--- Testing {hostname} ---")

        # Test DNS resolution
        dns_success, ip = test_dns_resolution(hostname)
        if not dns_success:
            results.append(False)
            continue

        # Test connectivity
        connect_success = test_connectivity(hostname, port)
        results.append(connect_success)

    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)

    total_tests = len(results)
    passed_tests = sum(results)

    logger.info(f"Total tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Failed: {total_tests - passed_tests}")

    if passed_tests == total_tests:
        logger.info("✓ All tests passed! DNS resolution and connectivity are working.")
        return 0
    else:
        logger.error("✗ Some tests failed. Check network configuration.")
        return 1

if __name__ == "__main__":
    exit(main())
