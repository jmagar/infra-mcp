#!/usr/bin/env python3
"""
Simple WebSocket client test script for the infrastructor WebSocket server.

Tests basic connection, authentication, and subscription functionality.
"""

import asyncio
import json
import os
import sys
import websockets
from datetime import datetime


async def test_websocket():
    """Test WebSocket connection and basic functionality"""
    
    # Get API key from environment
    api_key = os.getenv('API_KEY', 'your-api-key-for-authentication')
    
    uri = "ws://localhost:9101/ws/stream"
    
    try:
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")
            
            # Send authentication message
            auth_message = {
                "type": "auth",
                "token": api_key,
                "action": "authenticate"
            }
            
            print("🔐 Sending authentication...")
            await websocket.send(json.dumps(auth_message))
            
            # Wait for auth response
            auth_response = await websocket.recv()
            auth_data = json.loads(auth_response)
            
            if auth_data.get("action") == "authenticated":
                print(f"✅ Authenticated as user: {auth_data.get('user_id')}")
                print(f"✅ Client ID: {auth_data.get('client_id')}")
            else:
                print(f"❌ Authentication failed: {auth_data}")
                return
            
            # Subscribe to topics
            subscription_message = {
                "type": "subscription",
                "action": "subscribe",
                "topics": ["global", "devices.*", "metrics.system_metrics"]
            }
            
            print("📡 Subscribing to topics...")
            await websocket.send(json.dumps(subscription_message))
            
            # Wait for subscription confirmation
            sub_response = await websocket.recv()
            sub_data = json.loads(sub_response)
            
            if sub_data.get("action") == "confirmed":
                print(f"✅ Subscribed to topics: {sub_data.get('topics')}")
            else:
                print(f"❌ Subscription failed: {sub_data}")
            
            # Send a heartbeat
            heartbeat_message = {
                "type": "heartbeat"
            }
            
            print("💓 Sending heartbeat...")
            await websocket.send(json.dumps(heartbeat_message))
            
            # Wait for heartbeat response
            heartbeat_response = await websocket.recv()
            heartbeat_data = json.loads(heartbeat_response)
            
            if heartbeat_data.get("type") == "heartbeat":
                print("✅ Heartbeat confirmed")
            else:
                print(f"❓ Unexpected response: {heartbeat_data}")
            
            # Listen for messages for a short time
            print("👂 Listening for real-time messages (10 seconds)...")
            
            try:
                # Set a timeout for listening
                await asyncio.wait_for(
                    listen_for_messages(websocket), 
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                print("⏰ Listening timeout reached")
            
            print("✅ WebSocket test completed successfully!")
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused - is the server running on port 9101?")
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")


async def listen_for_messages(websocket):
    """Listen for incoming WebSocket messages"""
    message_count = 0
    
    async for message in websocket:
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            timestamp = data.get("timestamp", datetime.now().isoformat())
            
            print(f"📨 Received {message_type} message at {timestamp}")
            
            # Show different message types
            if message_type == "data":
                device_id = data.get("device_id", "unknown")
                metric_type = data.get("metric_type", "unknown")
                print(f"   📊 Data from {device_id}: {metric_type}")
            elif message_type == "event":
                event_type = data.get("event_type", "unknown")
                severity = data.get("severity", "info")
                print(f"   🚨 Event: {event_type} ({severity})")
            elif message_type == "heartbeat":
                print(f"   💓 Heartbeat from server")
            else:
                print(f"   📝 {message_type}: {data}")
            
            message_count += 1
            
            # Stop after receiving a few messages
            if message_count >= 5:
                print(f"📊 Received {message_count} messages, stopping listen")
                break
                
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON received: {message}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")


if __name__ == "__main__":
    print("🚀 Starting WebSocket test...")
    print("Make sure the server is running: ./dev.sh start")
    print()
    
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)