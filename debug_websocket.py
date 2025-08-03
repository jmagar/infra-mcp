#!/usr/bin/env python3
"""Debug WebSocket authentication"""

import asyncio
import json
import os
import websockets


async def debug_auth():
    api_key = os.getenv('API_KEY', 'your-api-key-for-authentication')
    print(f"Using API key: '{api_key}' (length: {len(api_key)})")
    
    uri = "ws://localhost:9101/ws/stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Send auth message
            auth_msg = {
                "type": "auth",
                "token": api_key,
                "action": "authenticate"
            }
            
            print(f"Sending: {json.dumps(auth_msg, indent=2)}")
            await websocket.send(json.dumps(auth_msg))
            
            # Get response
            response = await websocket.recv()
            print(f"Received: {response}")
            
            response_data = json.loads(response)
            print(f"Parsed: {json.dumps(response_data, indent=2)}")
            
            # If authentication successful, stay connected for a bit
            if response_data.get("type") == "auth" and response_data.get("action") == "authenticated":
                print("Authentication successful! Staying connected for 5 seconds...")
                
                # Send a subscription message
                sub_msg = {
                    "type": "subscription",
                    "action": "subscribe",
                    "topics": ["system.metrics", "containers.status"]
                }
                print(f"Sending subscription: {json.dumps(sub_msg, indent=2)}")
                await websocket.send(json.dumps(sub_msg))
                
                # Wait for subscription confirmation
                sub_response = await websocket.recv()
                print(f"Subscription response: {sub_response}")
                
                # Stay connected for 5 seconds to test heartbeat
                await asyncio.sleep(5)
                print("Disconnecting...")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(debug_auth())