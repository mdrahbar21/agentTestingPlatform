from flask import Flask, request, render_template, jsonify, session
import asyncio
import websockets
import json
import openai
import math
import os
from datetime import datetime
from flask_pymongo import PyMongo
from flask_cors import CORS
from dotenv import load_dotenv
from conversation import test_bot
from evaluator import evaluate_response
from singleMessage import single_message_test_bot
from function import llm_assistant, llm_user, converse
from constantHistory import converse2
from constantHistorySingle import converse3
from bson import ObjectId
from collections_firestore import fetch_agents, fetch_agent_system_prompt, fetch_conversations_analytics


load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config["MONGO_URI"] = "mongodb://127.0.0.1:27017/conversations"
mongo = PyMongo(app)

app.secret_key = os.urandom(24)


def run_async_function(uri, test_count, user_prompt, agent_name):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(test_bot(
        uri, test_count, user_prompt))
    loop.close()
    # print(results)
    for result in results:
        result.update({"agent_name": agent_name, "user_prompt": user_prompt})

    return results


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        agent_name = request.form['agent_name']
        uri = 'wss://hoomanlabs.com/api/sockets/chat?agentId='+agent_name
        test_count = int(request.form['test_count'])
        user_prompt = request.form['user_prompt']

        results = run_async_function(
            uri, test_count, user_prompt, agent_name)
        mongo.db.conversations.insert_many(results)

        result = fetch_conversations_analytics(agent_name, test_count)
        # print(results)
        if result:
            total_llm_latency = sum(
                conversation['average_llm_latency'] for conversation in result)
            total_output_tokens = sum(
                conversation['average_output_tokens'] for conversation in result)
            total_input_tokens = sum(
                conversation['average_input_tokens'] for conversation in result)
            num_conversations = len(result)

            overall_average_llm_latency = total_llm_latency / num_conversations
            overall_average_output_tokens = total_output_tokens / num_conversations
            overall_average_input_tokens = total_input_tokens / num_conversations
        else:
            overall_average_llm_latency = 0
            overall_average_output_tokens = 0
            overall_average_input_tokens = 0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        analytics = {"agent_name": agent_name, "timestamp": timestamp, "conversation_count": test_count, "average_llm_latency": overall_average_llm_latency,
                     "average_output_tokens": overall_average_output_tokens, "average_input_tokens": overall_average_input_tokens}
        mongo.db.analytics.insert_one(analytics)

        return render_template('results.html', agents=fetch_agents(), results=result,
                               agent_name=agent_name, test_count=test_count,
                               overall_average_llm_latency=overall_average_llm_latency,
                               overall_average_output_tokens=overall_average_output_tokens,
                               overall_average_input_tokens=overall_average_input_tokens)

        # return render_template('results.html', agents=fetch_agents(), results=results)

    return render_template('generateConversations.html', agents=fetch_agents())


@app.route('/evaluate', methods=['GET', 'POST'])
def evaluate():
    if request.method == 'POST':
        conversation_ids = request.form.getlist('conversation_id')
        results = []
        for conversation_id in conversation_ids:
            conversation = mongo.db.conversations.find_one(
                {'_id': ObjectId(conversation_id)}
            )
            assistant_used_prompt = request.form['assistant_used_prompt']
            evaluator_prompt = request.form['evaluator_prompt']
            convo = conversation['conversation']

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                evaluate_response(
                    convo, assistant_used_prompt, evaluator_prompt)
            )
            loop.close()

            evaluation_data = {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'assistant_used_prompt': assistant_used_prompt,
                'evaluator_prompt': evaluator_prompt,
                'result': result
            }

            mongo.db.conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$push': {'evaluations': evaluation_data}}
            )

            conversation = mongo.db.conversations.find_one(
                {'_id': ObjectId(conversation_id)}
            )

            results.append((conversation, result))
        agents = fetch_agent_system_prompt()
        return render_template('evaluation_result.html', agents=agents, results=results)

    conversations = mongo.db.conversations.find()
    conversation_id = request.args.get('conversation_id')
    selected_conversation_ids = [conversation_id] if conversation_id else []
    agents = fetch_agent_system_prompt()
    return render_template('evaluate.html', conversations=conversations, selected_conversation_ids=selected_conversation_ids, agents=agents)


# @app.route('/conversations', methods=['GET'])
# def results():
#     conversations = mongo.db.conversations.find().sort('timestamp', -1)
#     conversations_list = [conv for conv in conversations]
#     return render_template('conversations.html', conversations=conversations_list)


@app.route('/conversations', methods=['GET'])
def results():
    conversations_collection = mongo.db.conversations
    page = request.args.get('page', 1, type=int)
    per_page = 20
    total_conversations = conversations_collection.count_documents({})
    total_pages = math.ceil(total_conversations / per_page)

    conversations = conversations_collection.find().sort(
        'timestamp', -1).skip((page - 1) * per_page).limit(per_page)
    conversations_list = [conv for conv in conversations]

    return render_template(
        'conversations.html',
        conversations=conversations_list,
        page=page,
        total_pages=total_pages,
        agents=fetch_agents()
    )


@app.route('/singleTest', methods=['GET', 'POST'])
def singleTest():
    if request.method == 'POST':
        agent_name = request.form['agent_name']
        uri = f'wss://hoomanlabs.com/api/sockets/chat?agentId={agent_name}'
        test_count = int(request.form['test_count'])
        input_message = request.form['input_message']

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            single_message_test_bot(uri, test_count, input_message))
        loop.close()

        document = {
            "agent_name": agent_name,
            "input_message": input_message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "conversations": results
        }

        insert_result = mongo.db.single_conversation.insert_one(document)
        test_result_document = mongo.db.single_conversation.find_one(
            {"_id": insert_result.inserted_id})

        return render_template('result_single.html', test_result=test_result_document)

    return render_template('singleTest.html')


@app.route('/llmconvo')
def conversation():
    assistant_prompt = request.args.get('assistant_prompt')
    user_prompt = request.args.get('user_prompt')
    chat_history_assistant = [{"role": "system", "content": assistant_prompt}]
    chat_history_user = [{"role": "system", "content": user_prompt}]

    conversation_log = []
    for _ in range(10):
        assistant_response = llm_assistant(chat_history_user)
        chat_history_assistant.append(
            {"role": "user", "content": chat_history_user[-1]['content']})
        chat_history_assistant.append(
            {"role": "assistant", "content": assistant_response})

        user_response = llm_user(chat_history_assistant)
        chat_history_user.append(
            {"role": "assistant", "content": assistant_response})
        chat_history_user.append({"role": "user", "content": user_response})

        conversation_log.append(
            {"Assistant": assistant_response, "User": user_response})

        if "goodbye" in user_response.lower() or "goodbye" in assistant_response.lower():
            break

    return render_template('conversation.html', conversation_log=conversation_log)


@app.route('/converse', methods=['GET', 'POST'])
def handle_conversation():
    converse()
    return jsonify({"status": "Conversation ended successfully."})


@app.route('/converse2', methods=['GET', 'POST'])
def handle_conversation2():
    converse2()
    return jsonify({"status": "Conversation ended successfully."})


@app.route('/converse3', methods=['GET', 'POST'])
def handle_conversation3():
    converse3(4)
    return jsonify({"status": "Conversation ended successfully."})


if __name__ == '__main__':
    # app.run(host="0.0.0.0", port=8000)
    app.run(debug=True)
