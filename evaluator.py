import openai
import os
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


async def evaluate_response(conversation, assistant_used_prompt, evaluator_prompt):
    eval_data = []
    eval_data.append({
        "role": "system",
        "content": evaluator_prompt
    })

    eval_data.append({
        "role": "user",
        "content": "transcript: " + str(conversation)
    })
    eval_data.append({
        "role": "user",
        "content": "AI participant system prompt: " + assistant_used_prompt
    })

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=eval_data,
            temperature=0.7,
        )
        content_to_write = response.choices[0].message.content
        print(content_to_write)
        return content_to_write
    except Exception as e:
        print("Failed to get response from OpenAI:", e)
        error = "Failed to get response from OpenAI:" + str(e)
        return error
