import openai
import os
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def simulate_function_call(function_call):
    if function_call.name == 'book_appointment':
        return "The appointment has been booked successfully for the requested time."
    elif function_call.name == 'get_slots_date':
        return "Yes, the slots are available at the given time"
    elif function_call.name == 'get_slots':
        return "Available slots are 9:00 AM, 11:00 AM, and 3:00 PM."
    return "Function call simulation result."


def llm_assistant(chat_history):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Book appointment once you have collected and confirmed all the required details (name, email, purpose, date and time) with the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Appointment date or start date shared by the user.",
                        },
                        "email": {
                            "type": "string",
                            "description": "user's email address",
                        },
                        "name": {
                            "type": "string",
                            "description": "patient's/user's name",
                        },
                        "purpose": {
                            "type": "string",
                            "description": "purpose of the visit under one sentence.",
                        },
                        "time": {
                            "type": "string",
                            "description": "Appointment time or start time confirmed by the user.",
                        },
                    },
                    "required": ["date", "email", "name", "purpose", "time"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_slots_date",
                "description": "Get available appointment slots when the user explicitly asks for available slots for particular date(s) or date-range. The user may optionally provide a preferred time-range, which will be interpreted and converted to startTime and endTime.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "endDate": {
                            "type": "string",
                            "description": "End date when user provides a date-range with a clear and specific end date. This is an optional value.",
                        },
                        "endTime": {
                            "type": "string",
                            "description": "The end time for the preferred time-range shared by user. This must be in 12-hour HH:MM format.",
                        },
                        "startDate": {
                            "type": "string",
                            "description": "The preferred date or start date of a date range shared by the user. This must be in exactly the same form as shared by the user.",
                        },
                        "startTime": {
                            "type": "string",
                            "description": "The start time for the preferred time-range shared by user. This must be in 12-hour HH:MM format. This is an optional value.",
                        },
                    },
                    "required": ["startDate"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_slots",
                "description": "Get available appointment slots when the user asks for available slots without providing any date(s) or date range. You should only use this once the user has explicitly confirmed that they don't have a preferred date for the appointment.",
                "parameters": {
                    "type": "object",
                    "properties": {

                    },
                    "required": [],
                },
            }
        }

    ]
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history,
            tools=tools,
            tool_choice="auto",
            temperature=1,
        )
        # print(response)
        message_content = response.choices[0].message.content
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0].function
            print('Tool Call: ' + str(tool_call))
            function_result = simulate_function_call(tool_call)
            chat_history.append(
                {"role": "assistant", "name": tool_call.name, "content": function_result})
            return function_result
        return message_content
        # return response.choices[0].message.content
    except Exception as e:
        print(f"Error during LLM assistant response generation: {e}")
        return None


def llm_user(chat_history):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history,
            temperature=1,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during LLM user response generation: {e}")
        return None


def converse():
    voice_test_prompt = "## Identity You are Susan, a voice assistant working at the new appointments desk of City Hospital. You are a friendly, professional, and patient-centric assistant.  \
        ## Role Your main task is to help users book new appointments over a phone conversation using the “New Appointment Guide”. You must keep track of conversation history and collect all the required details in a friendly and efficient manner. \
        Avoid asking for the details which the user has already provided.   Additionally you may use your medical knowledge to understand user messages but never give medical advice.  ### Address:  4th Main, Indiranagar, Bangalore, India. \
        ### Working Hours:  09:00 AM - 09:00 PM, Monday to Saturday. Hospital remains closed on Sunday.  ## Response Guidelines Remember this is a phone conversation and you must follow the below guidelines in formulating all your responses.  \
            - Be Concise: Keep your responses short (under 1-2 sentences), like in a real conversation. - One question at a time: Ask only one question/detail at a time, do not pack more topics into one response. \
            - Embrace Variety: Use diverse but simple language and rephrasing to enhance clarity without repeating content. - Adapt and Guess: Try to understand transcripts that may contain transcription errors. \
        Avoid mentioning 'transcription error' in the response. - Stay in Character: Keep conversations within your role's scope, guiding them back creatively without repeating. - Always use a colloquial way of referring to the date (like 'next Friday', 'tomorrow'). - Avoid using the user's name in your responses unless it is absolutely needed. \
        - Make the interaction feel friendly and informal. - When responding with multiple options or long paragraphs, break your response into bullet points or short paragraphs. Avoid using numbered-lists.  \## New Appointment Guide You must follow the 3-step process given below.  \
        ### Step 1: Booking Details Collection You must collect all the required details one-by-one in a flexible order.  Remember, users share details in any order be it name-first or date-first or purpose-first or something else.  \
        Adapt and collect the details as the user provides them.  #### Name (Required) - Ask for the patient's/user’s name. - If unsure of the spelling, confirm by asking the user to spell it letter by letter.  \
        #### Purpose of visit (Required) - Ask about the purpose of their visit. - Show empathy. - Based on the provided information, identify the appropriate medical specialist (e.g., ''I'll book an appointment with a Dentist if the user mentions tooth pain''). \
        #### Email (Required) - Ask the user to clearly spell out their email address. - Always replace '.'' with '(dot)' in email addresses. - Confirm the email address by repeating email back letter by letter to the user.  \
        #### Date and Time (Required) - Ask the user for their preferred date and time for the appointment. - Sometimes users might share only a date or time in their messages, then you must ask again for the missing detail.    \
        - If the user provides the preferred date and time, collect any remaining details (if necessary) and then proceed to the booking details confirmation step.\
        - Else:- Check availability by following the Availability Check Guide.\
        - Share the available slots with the user and ask them to select their preferred date and time.\
        - If there are multiple available slot options, use conjunctions between each of them to ensure fluidity. Remember your response is being delivered over the phone. \
        For example: - I have available slots for [date] “from 9:00 AM to 11:30 AM” and “from 5:30 PM to 8:00 PM”.- The available slots for [date] are “from 8:00 AM to 10:30 AM”, next one “from 2:00 PM to 4:00 PM” and last one “from 7:00 PM to 7:30 PM”.- Also, if there are more than 3 available slots, only share the first 3 options. If a user asks for more, share the rest of the slot options. - Once the user selects their preferred date and time, collect any remaining details (if necessary) and then proceed to the booking details confirmation step.   ### Step 2: Booking Details Confirmation - Confirm all the collected details (name, purpose, email, date, and time) with the user.  - Listen attentively and make any necessary adjustments if the user requests changes. - Confirm the updated details again with the user. - Wait for user confirmation before proceeding to the next step.   ### Step 3: Book Appointment - Once all details are confirmed, book an appointment by calling the book_appointment function. - Respond to the user based on the function's outcome, either confirming the booking or providing further instructions if needed. - If the user requests modifications or cancellations after the appointment is booked, inform them that you can only book new appointments and suggest transferring the call to an agent who can assist.  \
        ## Availability Check Guide Users might ask for available slots with or without any date/time preference. First, you must identify the relevant case and then follow the guidelines to check availability and subsequently book appointments.  \
        ### Case 1: User gave a preferred date or date-range and asked for available slots - Consider user provided date/day or start of date-range as start date. - Use the end date only when the user provides a date range with a clear and specific end date. \
        - Make sure that the startDate and endDate are exactly in the same form as shared by the user. For example:   - If the user said “tomorrow” then startDate = “tomorrow”, endDate = “”   - If the user said “26th” then startDate = “26th”, endDate = “”   - If the user said “26th june” then startDate = “26th june”, endDate = “”   - If the user said “next week” then startDate = “next week”, endDate = “”   - If the user said “between 3rd and 7th” then startDate = “3rd”, endDate = “7th” - If the user has provided a time-range,   - Interpret and convert time-range to appropriate 12-hour AM/PM value. For example:     - If the user said “morning” then startTime = “09:00 AM”, endTime = “12:00 PM”     - If the user said “after 2” then startTime = “02:00 PM”, endTime = “08:00 PM” (end of working hours)     - If the user said “between 3 and 5” then startTime = “03:00 PM”, endTime = “05:00 PM” - Check availability by calling get_slots_date function with appropriate startDate, startTime, endTime, and endDate (optional). - If the user has not provided a time-range then check availability by calling get_slots_date function with appropriate startDate and endDate (optional).  ### Case 2: User gave no preferred date or date-range and asked for available slots Check availability by calling get_slots function.  Once you have the available slots, ask the user to select their preferred slot and then proceed appropriately. If there are multiple available slot options, use conjunctions between each of them to ensure fluidity. Remember your response is being delivered over the phone."

    user_prompt = "Your name is Rahbar. You are a patient, looking to book an appointment at city hospital over a phone call. Your job is to interact with the receptionist, provide necessary information and ensure clear communication. Here are some details about you: Email: rahbar@hoomanlabs.com Age: 21 Gender: Male - Remember this is a phone conversation so keep your responses short (under 1-2 sentences) and to-the-point. - Also, when receptionist asks for your preferred date and time, provide a specific date and time in the future"
    chat_history_assistant = [
        {"role": "system", "content": voice_test_prompt}]
    chat_history_user = [
        {"role": "system", "content": user_prompt}]

    intro_message = "Thank you for calling City Hospital. This is Susan from the appointments department. How may I assist you today?"
    chat_history_assistant.append(
        {"role": "assistant", "content": intro_message})
    chat_history_user.append(
        {"role": "user", "content": intro_message})
    print("Assistant: "+str(intro_message))

    for _ in range(15):
        user_response = llm_user(chat_history_user)
        if user_response is None or user_response.strip() == "":
            print("Received empty or invalid response from user.")
            break

        chat_history_user.append(
            {"role": "assistant", "content": user_response})
        chat_history_assistant.append({
            "role": "user", "content": user_response
        })
        print("User:", user_response)

        assistant_response = llm_assistant(chat_history_assistant)
        if assistant_response is None or assistant_response.strip() == "":
            print("Received empty or invalid response from assistant.")
            break

        chat_history_assistant.append(
            {"role": "assistant", "content": assistant_response})
        chat_history_user.append(
            {"role": "user", "content": assistant_response})
        print("Assistant:", assistant_response)

        if "goodbye" in user_response.lower() or "goodbye" in assistant_response.lower():
            break

    print("Conversation ended.")
