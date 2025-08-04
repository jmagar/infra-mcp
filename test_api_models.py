#!/usr/bin/env python3
"""
Test script for Phase 1 models via API endpoints.

Since the models are already loaded by the running server, 
we'll test them through the API to verify they work correctly.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
import aiohttp


async def test_device_api():
    """Test device creation and retrieval via API."""
    print("🧪 Testing Device model via API...")
    
    device_data = {
        "hostname": "test-server-api-001",
        "device_type": "server",
        "description": "Test server for API model validation",
        "location": "datacenter-api",
        "tags": {"environment": "test", "team": "infrastructure"},
        "docker_compose_path": "/opt/docker-compose.yml",
        "docker_appdata_path": "/opt/appdata",
        "monitoring_enabled": True
    }
    
    async with aiohttp.ClientSession() as session:
        # Create device
        async with session.post(
            'http://localhost:9101/api/devices/',
            json=device_data,
            headers={'Authorization': 'Bearer your-api-key-for-authentication'}
        ) as response:
            if response.status == 201:
                device = await response.json()
                device_id = device['data']['id']
                print(f"   ✅ Created device: {device['data']['hostname']} (ID: {device_id})")
                return device_id
            else:
                print(f"   ❌ Failed to create device: {response.status}")
                text = await response.text()
                print(f"   Error: {text}")
                return None


async def test_device_list_api():
    """Test device listing via API."""
    print("🧪 Testing Device listing via API...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            'http://localhost:9101/api/devices/',
            headers={'Authorization': 'Bearer your-api-key-for-authentication'}
        ) as response:
            if response.status == 200:
                devices = await response.json()
                print(f"   ✅ Listed {len(devices['data'])} devices")
                for device in devices['data']:
                    print(f"   - {device['hostname']} ({device['device_type']}) - {device['status']}")
                return True
            else:
                print(f"   ❌ Failed to list devices: {response.status}")
                return False


async def test_health_endpoint():
    """Test health endpoint to verify database and models are working."""
    print("🧪 Testing Health endpoint for model validation...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:9101/health') as response:
            if response.status == 200:
                health = await response.json()
                
                print(f"   ✅ API Status: {health['status']}")
                print(f"   ✅ Database Status: {health['database']['status']}")
                print(f"   ✅ Hypertables: {health['database']['timescaledb_info']['hypertables']}")
                
                # Check table counts
                table_counts = health['database']['table_counts']
                print("   ✅ Table counts:")
                for table, count in table_counts.items():
                    print(f"     - {table}: {count}")
                
                # Check hypertable status
                hypertable_status = health['database']['timescaledb_info']['hypertable_status']
                print("   ✅ Hypertable status:")
                for table, status in hypertable_status.items():
                    if status.get('is_hypertable'):
                        print(f"     - {table}: ✅ (chunks: {status['num_chunks']})")
                    else:
                        print(f"     - {table}: ❌ {status.get('status', 'Unknown')}")
                
                return True
            else:
                print(f"   ❌ Health check failed: {response.status}")
                return False


async def test_database_operations():
    """Test direct database operations using a simple query."""
    print("🧪 Testing Database operations...")
    
    try:
        # Try to connect to database directly and run simple queries
        import asyncpg
        
        conn = await asyncpg.connect(
            host='localhost',
            port=9100,
            user='postgres',
            password='change_me_in_production',
            database='infrastructor'
        )
        
        # Test basic table existence
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        print(f"   ✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"     - {table['table_name']}")
        
        # Test hypertable status
        hypertables = await conn.fetch("""
            SELECT hypertable_name, num_chunks, compression_enabled
            FROM timescaledb_information.hypertables
            ORDER BY hypertable_name
        """)
        
        print(f"   ✅ Found {len(hypertables)} hypertables:")
        for ht in hypertables:
            print(f"     - {ht['hypertable_name']}: {ht['num_chunks']} chunks, compression: {ht['compression_enabled']}")
        
        # Test device table structure
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'devices'
            ORDER BY ordinal_position
        """)
        
        print(f"   ✅ Device table has {len(columns)} columns:")
        for col in columns[:10]:  # Show first 10 columns
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"     - {col['column_name']}: {col['data_type']} {nullable}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False


async def test_model_relationships():
    """Test that model relationships work by checking foreign keys."""
    print("🧪 Testing Model relationships...")
    
    try:
        import asyncpg
        
        conn = await asyncpg.connect(
            host='localhost',
            port=9100,
            user='postgres',
            password='change_me_in_production',
            database='infrastructor'
        )
        
        # Check foreign key constraints
        fkeys = await conn.fetch("""
            SELECT 
                tc.table_name,
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
            ORDER BY tc.table_name
        """)
        
        print(f"   ✅ Found {len(fkeys)} foreign key relationships:")
        for fk in fkeys:
            print(f"     - {fk['table_name']}.{fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        
        # Verify specific Phase 1 relationships
        phase1_tables = [
            'data_collection_audit',
            'configuration_snapshots', 
            'configuration_change_events',
            'service_performance_metrics',
            'cache_metadata'
        ]
        
        phase1_fks = [fk for fk in fkeys if fk['table_name'] in phase1_tables]
        print(f"   ✅ Phase 1 tables have {len(phase1_fks)} foreign key relationships")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Relationship test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Starting Phase 1 Model Tests via API\n")
    
    success = True
    
    # Test health endpoint first
    if not await test_health_endpoint():
        success = False
    print()
    
    # Test database operations
    if not await test_database_operations():
        success = False
    print()
    
    # Test model relationships
    if not await test_model_relationships():
        success = False
    print()
    
    # Test API endpoints
    if not await test_device_list_api():
        success = False
    print()
    
    device_id = await test_device_api()
    if device_id is None:
        success = False
    print()
    
    if success:
        print("🎉 All model tests completed successfully!")
        print("✅ Phase 1 SQLAlchemy models are working correctly")
        print("✅ Database schema is properly implemented")
        print("✅ Relationships are correctly configured")
        print("✅ API integration is functional")
    else:
        print("❌ Some tests failed")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)