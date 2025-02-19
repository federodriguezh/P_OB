import asyncio
import websockets
import json
import os
from datetime import datetime

# Set parameters
ENVIRONMENT = "www"
CHANNELS = [
    "book.BTC-PERPETUAL.none.20.100ms"
]
MAX_FILE_SIZE_MB = 95  # GitHub has 100MB file size limit, keeping buffer

def get_new_filename():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    return os.path.join('data', f'updates_{timestamp}.json') # git rm *.json to remove al json files

async def save_orderbook_data(runtime_minutes=300):  # ~5 hours
    msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "public/subscribe",
        "params": {
            "channels": CHANNELS
        }
    }

    start_time = datetime.now()
    current_filename = get_new_filename()

    async with websockets.connect(f'wss://{ENVIRONMENT}.deribit.com/ws/api/v2') as websocket:
        await websocket.send(json.dumps(msg))
        
        try:
            while True:
                # Check runtime
                if (datetime.now() - start_time).total_seconds() > runtime_minutes * 60:
                    print("Runtime limit reached")
                    break

                response = await websocket.recv()
                
                # Check file size and rotate if needed
                if os.path.exists(current_filename) and os.path.getsize(current_filename) > MAX_FILE_SIZE_MB * 1024 * 1024:
                    current_filename = get_new_filename()

                # Append to file
                with open(current_filename, 'a') as f:
                    json.dump(json.loads(response), f)
                    f.write('\n')
                        
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")

def main():
    try:
        asyncio.run(save_orderbook_data())

    except KeyboardInterrupt:
        print("\nData collection stopped by user")

if __name__ == "__main__":
    main()
