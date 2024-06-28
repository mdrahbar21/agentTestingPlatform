import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

cred = credentials.Certificate('hooman-labs-production-1a943c82bc2f.json')
app = firebase_admin.initialize_app(cred)
dbf = firestore.client()


# agents = dbf.collection("agents").stream()
# conversations = dbf.collection("conversations").orderBy(
#     'beginTimestamp', 'desc').where('agent', '==', 'voice-test').limit(10).stream()
# functions = dbf.collection("functions").stream()
# users = dbf.collection("users").stream()

# for doc in agents:
#     print(f"{doc.id} => {doc.to_dict().get('systemPrompt', '')}")
#     break
# for doc in functions:
#     print(f"{doc.id} ")
# for doc in users:
#     print(f"{doc.id} ")
# for doc in conversations:
#     print(f"{doc.id}  => {doc.to_dict()}")
#     break

def fetch_conversations_analytics(agent, test_count):
    conversations_ref = dbf.collection("conversations") \
        .where('agent', '==', agent) \
        .order_by('beginTimestamp', direction=firestore.Query.DESCENDING) \
        .limit(test_count)

    conversations = conversations_ref.stream()
    conversation_list = []

    for doc in conversations:
        conversation_data = doc.to_dict()
        conversation_data['id'] = doc.id
        transactions = conversation_data['transactions']

        total_llm_latency = sum(transaction['llmLatency']
                                for transaction in transactions)
        total_output_tokens = sum(
            transaction['outputTokens'] for transaction in transactions)
        total_input_tokens = sum(
            transaction['inputTokens'] for transaction in transactions)
        num_transactions = len(transactions)

        average_llm_latency = total_llm_latency / \
            num_transactions if num_transactions > 0 else 0
        average_output_tokens = total_output_tokens / \
            num_transactions if num_transactions > 0 else 0
        average_input_tokens = total_input_tokens / \
            num_transactions if num_transactions > 0 else 0

        conversation_data['average_llm_latency'] = average_llm_latency
        conversation_data['average_output_tokens'] = average_output_tokens
        conversation_data['average_input_tokens'] = average_input_tokens

        conversation_list.append(conversation_data)

    return conversation_list


def fetch_agents():
    agents = dbf.collection("agents").stream()
    return [doc.id for doc in agents]


def fetch_agent_system_prompt():
    agents = dbf.collection("agents").stream()
    return [{'name': doc.id, 'systemPrompt': doc.to_dict().get('systemPrompt', '')} for doc in agents]


def fetch_functions():
    functions = dbf.collection("functions").stream()
    return [doc.id for doc in functions]


def fetch_users():
    users = dbf.collection("users").stream()
    return [doc.id for doc in users]
