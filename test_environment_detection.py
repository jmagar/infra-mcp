#!/usr/bin/env python3
"""Test environment detection utilities"""

from apps.backend.src.utils.environment import (
    EnvironmentDetector,
    WSL_DETECTION_COMMAND,
    EnvironmentInfo,
    should_skip_drive_health_monitoring
)

def test_wsl_detection():
    """Test WSL environment detection"""
    print("Testing WSL Detection:")
    
    # Test WSL content
    wsl_content = "Linux version 5.15.167.4-microsoft-standard-WSL2 (x86_64-msft-linux-gcc)"
    is_wsl = EnvironmentDetector.is_wsl_environment(wsl_content)
    print(f"  WSL content: {is_wsl} (expected: True)")
    
    # Test regular Linux content
    linux_content = "Linux version 5.15.0-25-generic (buildd@lgw01-amd64-038)"
    is_linux = EnvironmentDetector.is_wsl_environment(linux_content)
    print(f"  Regular Linux: {is_linux} (expected: False)")
    
    # Test empty content
    is_empty = EnvironmentDetector.is_wsl_environment("")
    print(f"  Empty content: {is_empty} (expected: False)")

def test_container_detection():
    """Test container environment detection"""
    print("\nTesting Container Detection:")
    
    # Test Docker environment
    is_docker = EnvironmentDetector.is_container_environment(dockerenv_exists=True)
    print(f"  Docker env file: {is_docker} (expected: True)")
    
    # Test cgroup detection
    cgroup_content = "12:pids:/docker/abc123"
    is_cgroup_docker = EnvironmentDetector.is_container_environment(
        dockerenv_exists=False, 
        proc_cgroup_content=cgroup_content
    )
    print(f"  Docker cgroup: {is_cgroup_docker} (expected: True)")
    
    # Test regular system
    regular_cgroup = "12:pids:/user.slice/user-1000.slice"
    is_regular = EnvironmentDetector.is_container_environment(
        dockerenv_exists=False,
        proc_cgroup_content=regular_cgroup
    )
    print(f"  Regular system: {is_regular} (expected: False)")

def test_drive_health_skipping():
    """Test drive health monitoring logic"""
    print("\nTesting Drive Health Monitoring Logic:")
    
    # WSL environment
    wsl_env = EnvironmentInfo(is_wsl=True)
    should_skip_wsl = should_skip_drive_health_monitoring(wsl_env)
    print(f"  WSL environment: skip={should_skip_wsl} (expected: True)")
    
    # Container environment
    container_env = EnvironmentInfo(is_container=True)
    should_skip_container = should_skip_drive_health_monitoring(container_env)
    print(f"  Container environment: skip={should_skip_container} (expected: True)")
    
    # Regular environment
    regular_env = EnvironmentInfo(is_wsl=False, is_container=False)
    should_skip_regular = should_skip_drive_health_monitoring(regular_env)
    print(f"  Regular environment: skip={should_skip_regular} (expected: False)")

def test_detection_commands():
    """Test detection command constants"""
    print("\nTesting Detection Commands:")
    
    commands = EnvironmentDetector.get_detection_commands()
    print(f"  WSL command: {commands['wsl']}")
    print(f"  Container command: {commands['container']}")
    print(f"  Systemd command: {commands['systemd']}")
    
    print(f"\nWSL_DETECTION_COMMAND constant: {WSL_DETECTION_COMMAND}")

if __name__ == "__main__":
    print("Environment Detection Utility Tests")
    print("=" * 40)
    
    test_wsl_detection()
    test_container_detection() 
    test_drive_health_skipping()
    test_detection_commands()
    
    print("\n✅ All tests completed!")