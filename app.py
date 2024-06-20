from flask import Flask, request, render_template, jsonify, session
import asyncio
import websockets
import json
import openai
import os
from datetime import datetime
from flask_pymongo import PyMongo
from flask_cors import CORS
from dotenv import load_dotenv
from conversation import test_bot
from evaluator import evaluate_response
from singleMessage import single_message_test_bot
from bson import ObjectId


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
        # print(results)
        return render_template('results.html', results=results)

    return render_template('generateConversations.html')


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

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                evaluate_response(
                    conversation, assistant_used_prompt, evaluator_prompt)
            )
            loop.close()

            # Prepare the evaluation data
            evaluation_data = {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'assistant_used_prompt': assistant_used_prompt,
                'evaluator_prompt': evaluator_prompt,
                'result': result
            }

            # Update the MongoDB document to append the new evaluation
            mongo.db.conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$push': {'evaluations': evaluation_data}}
            )

            # Refresh the conversation object with the new evaluation
            conversation = mongo.db.conversations.find_one(
                {'_id': ObjectId(conversation_id)}
            )

            results.append((conversation, result))

        return render_template('evaluation_result.html', results=results)

    conversations = mongo.db.conversations.find()
    conversation_id = request.args.get('conversation_id')
    selected_conversation_ids = [conversation_id] if conversation_id else []
    return render_template('evaluate.html', conversations=conversations, selected_conversation_ids=selected_conversation_ids)


@app.route('/conversations', methods=['GET'])
def results():
    conversations = mongo.db.conversations.find().sort('timestamp', -1)
    # Convert from Cursor to a list of dicts
    conversations_list = [conv for conv in conversations]
    return render_template('conversations.html', conversations=conversations_list)


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
            "conversations": results  # Results is a list of conversations
        }

        insert_result = mongo.db.single_conversation.insert_one(document)
        test_result_document = mongo.db.single_conversation.find_one(
            {"_id": insert_result.inserted_id})

        return render_template('result_single.html', test_result=test_result_document)

    return render_template('singleTest.html')


if __name__ == '__main__':
    # app.run(host="0.0.0.0", port=8000)
    app.run(debug=True)
