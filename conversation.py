import asyncio
import websockets
import openai
import json
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


def is_failure_response(message):
    failure_keywords = [
        "cannot schedule an appointment", "failed to schedule", "unable to book", "could not schedule",
        "booking failed", "not successful", "error scheduling", "issue with the booking", "technical glitch"
    ]
    return any(keyword in message.lower() for keyword in failure_keywords)


async def collect_complete_message(websocket):
    full_message = []
    log_message = []
    session_end = False
    start_time = asyncio.get_event_loop().time()
    while True:
        elapsed_time = asyncio.get_event_loop().time() - start_time
        remaining_time = 6 - elapsed_time
        if remaining_time <= 0:
            print("Message collection timed out.")
            break
        if websocket.closed:
            print("WebSocket connection closed unexpectedly.")
            break
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=min(1, remaining_time))
            log_message.append(message)
            if 'Function called: end_call' in message:
                session_end = True
                break
            if 'Function called:' not in message:
                full_message.append(message)
        except asyncio.TimeoutError:
            print("Awaiting message timed out.")
            continue
        except websockets.exceptions.ConnectionClosed as e:
            print(f"WebSocket closed with exception: {e}")
            break

    return {"full": ' '.join(full_message), "log": ' '.join(log_message), "session_end": session_end}


async def test_bot(uri, n, user_prompt):
    data_collect = []
    conversations = []

    for i in range(n):
        chat_history = [{'role': 'system', 'content': user_prompt}]
        conversation = [{'role': 'system', 'content': user_prompt}]
        num = 0
        try:
            async with websockets.connect(uri, timeout=10) as websocket:
                if websocket.open:
                    user_message = await collect_complete_message(websocket)
                if not websocket.open:
                    conversation.append(
                        {"role": "error", "content": "websocket closed abruptly"})
                    break

                if user_message["session_end"] or 'Goodbye' in user_message["full"] or 'Have a fantastic day' in user_message["full"] or 'शुभकामनाएं' in user_message['full'] or 'शुभ हो' in user_message['full'] or 'बहुत धन्यवाद' in user_message['full'] or 'जय हिन्द' in user_message['full']:
                    print("Connection closing triggered.")
                    break

                chat_history.append(
                    {"role": "user", "content": user_message["full"]})
                conversation.append(
                    {"role": "agent", "content": user_message["log"]})

                assistant_response = ''

                while 'Goodbye' not in assistant_response and websocket.open and 'Have a fantastic day' not in assistant_response and 'शुभकामनाएं' not in assistant_response:
                    if "please wait" in user_message["log"].strip().lower():
                        user_message = await collect_complete_message(websocket)
                        chat_history.append(
                            {"role": "user", "content": user_message["full"]})
                        conversation.append(
                            {"role": "agent", "content": user_message["log"]})
                        continue
                    num += 1
                    response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=chat_history,
                        temperature=1,
                    )
                    assistant_response = response.choices[0].message.content
                    chat_history.append(
                        {"role": "assistant", "content": assistant_response})
                    conversation.append(
                        {"role": "customer", "content": assistant_response})
                    await websocket.send(json.dumps({'text': assistant_response}))
                    if websocket.open:
                        user_message = await collect_complete_message(websocket)
                    if not websocket.open:
                        conversation.append(
                            {"role": "error", "content": "websocket closed abruptly"})
                        break
                    chat_history.append(
                        {"role": "user", "content": user_message["full"]})
                    conversation.append(
                        {"role": "agent", "content": user_message["log"]})

                    if is_failure_response(user_message["log"]):
                        print(
                            f"Booking failure at attempt {num}: {user_message['log']}")
                        data_collect.append(
                            {'attempt': num, 'message': user_message["log"]})
                        break
                conversations.append(conversation)

        except asyncio.TimeoutError:
            print(f"Connection to {uri} timed out")
            continue  # Continue with the next iteration if there's a timeout
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket connection was closed with an error: {e}")
        except websockets.exceptions.ConnectionClosedOK:
            print("WebSocket connection was closed cleanly.")
        finally:
            # Close the websocket if it hasn't been closed yet
            if not websocket.closed:
                await websocket.close()
                print("WebSocket has been closed.")

    for convo in conversations:
        data_collect.append({
            'conversation': convo,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    return data_collect
