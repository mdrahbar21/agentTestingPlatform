import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
import datetime

load_dotenv()


async def single_message_test_bot(uri, test_count, input_message):
    user_interactions = [
        {'text': input_message}
    ]
    data_collect = []

    for test_num in range(test_count):
        conversation = []
        async with websockets.connect(uri) as websocket:
            # Initial message comes when connection is made (hello, this is susan...)
            socket_response = await collect_complete_message(websocket)
            conversation.append(
                {"role": "agent", "content": socket_response['log']})

            # Sending the customer's message
            await websocket.send(json.dumps(user_interactions[0]))
            conversation.append({"role": "customer", "content": input_message})

            # Response from the agent
            socket_response = await collect_complete_message(websocket)
            conversation.append(
                {"role": "agent", "content": socket_response['log']})

        data_collect.append({
            'conversation': conversation,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    return data_collect


async def collect_complete_message(websocket):
    full_message = []
    log_message = []
    start_time = asyncio.get_event_loop().time()
    while True:
        elapsed_time = asyncio.get_event_loop().time() - start_time
        remaining_time = 5 - elapsed_time
        if remaining_time <= 0:
            break
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=min(1, remaining_time))
            log_message.append(message)
            if 'Function called:' not in message:
                full_message.append(message)
        except asyncio.TimeoutError:
            continue

    return {"full": ' '.join(full_message), "log": ' '.join(log_message)}
