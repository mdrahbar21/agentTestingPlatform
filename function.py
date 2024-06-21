import asyncio
import websockets
import openai
import json
from flask import session
from evaluator import evaluate_response
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
