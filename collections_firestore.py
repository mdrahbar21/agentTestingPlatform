import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

cred = credentials.Certificate('hooman-labs-production-1a943c82bc2f.json')
app = firebase_admin.initialize_app(cred)
dbf = firestore.client()


agents = dbf.collection("agents").stream()
functions = dbf.collection("functions").stream()
users = dbf.collection("users").stream()

for doc in agents:
    print(f"{doc.id} => {doc.to_dict().get('systemPrompt', '')}")
    break
for doc in functions:
    print(f"{doc.id} ")
for doc in users:
    print(f"{doc.id} ")


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
