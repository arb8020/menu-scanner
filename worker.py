import threading
import base64
import redis
import json
import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

r = redis.Redis()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_CONFIGS = {
    "gpt-4o-mini": {
        "name": "gpt-4o-mini",
        "input_price": 0.00015,  # $0.150 per 1M tokens
        "output_price": 0.0006   # $0.600 per 1M tokens
    },
}

def query_gpt(prompt, image_content=None):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    
    if image_content:
        messages[0]["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_content}"}
        })
    
    data = {
        "model": "gpt-4o-mini",
        "messages": messages,
    }
    
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        return content
    else:
        return f"Error: {response.status_code}, {response.text}"

def extract_json(response):
    try:
        json_content = response.split('```json')[1].split('```')[0].strip()
        return json.loads(json_content)
    except Exception as e:
        print(f"Error extracting JSON: {e}")
        print(f"Original response: {response}")
        return {}

def process_menu(file_path):
    with open(file_path, 'rb') as file:
        image_content = base64.b64encode(file.read()).decode()
    
    prompt = "Please analyze this menu image and return the items, descriptions (if available), and prices in plain text. Be as thorough as possible, and be sure not to skip over any details."
    return query_gpt(prompt, image_content)

def generate_questions(menu_text):
    prompt = f"""
    Given the following menu analysis, create a set of insightful questions to ask a patron who is undecided about what to order. These questions should help uncover their preferences in terms of taste, dietary restrictions, mood, or any other relevant dining considerations. 

    Format the output as a JSON object where each key is a question number, and the value is an object containing the 'question' and a list of potential 'answers' the patron might give:

    {menu_text}

    Ensure the questions are diverse, covering various aspects like flavor preference, meal type, dietary needs, and adventurousness in trying new dishes. 
    Here's an example of how the JSON should look:

    {{
        "1": {{
            "question": "What type of meal are you in the mood for?",
            "answers": ["Something light", "A hearty meal", "Just a snack"]
        }},
        "2": {{
            "question": "Do you have any dietary restrictions?",
            "answers": ["Vegetarian", "Vegan", "Gluten-free", "None"]
        }}
    }}
    """
    questions = query_gpt(prompt)
    print(f"Generated questions: {questions}")  # Debug log
    return json.dumps(extract_json(questions))

def generate_recommendations(menu_text, user_preferences):
    prompt = f"""
    Based on the menu analysis:

    {menu_text}

    And considering the user preferences:

    {json.dumps(user_preferences)}

    Please recommend 3 dishes that best match these preferences. If there's no perfect match for some preferences, suggest the closest alternatives or explain why certain preferences can't be fully met.

    Structure your response in JSON format as follows:

    {{
        "recommendations": [
            {{
                "dish_name": "",
                "match_reason": "",
                "alternatives_if_not_exact": ""
            }},
            {{
                "dish_name": "",
                "match_reason": "",
                "alternatives_if_not_exact": ""
            }},
            {{
                "dish_name": "",
                "match_reason": "",
                "alternatives_if_not_exact": ""
            }}
        ],
        "notes": ""
    }}
    """
    recommendations = query_gpt(prompt)
    print(f"Generated recommendations: {recommendations}")  # Debug log
    return json.dumps(extract_json(recommendations))

def process_job(job_data):
    print(f'Processing job: {job_data["id"]}')

    # Process all menu images
    menu_text = ""
    for file_path in job_data['files']:
        menu_text += process_menu(file_path) + "\n\n"
        os.remove(file_path)

    # Generate questions
    questions = generate_questions(menu_text)
    
    # Save questions and menu text for later use
    r.set(f"questions:{job_data['id']}", questions)
    r.set(f"menu_text:{job_data['id']}", menu_text)
    
    # Set job status to 'questions_ready'
    r.set(f"status:{job_data['id']}", 'questions_ready')

    print(f'Job {job_data["id"]} processed, questions ready')

    # Wait for user preferences
    while True:
        user_preferences = r.get(f"user_preferences:{job_data['id']}")
        if user_preferences:
            user_preferences = json.loads(user_preferences)
            break
        time.sleep(5)

    # Generate recommendations
    recommendations = generate_recommendations(menu_text, user_preferences)
    
    # Save recommendations
    r.set(f"result:{job_data['id']}", recommendations)
    
    # Set job status to 'completed'
    r.set(f"status:{job_data['id']}", 'completed')

    print(f'Job {job_data["id"]} completed')

def worker():
    while True:
        print('Waiting for job...')
        job = r.brpop('menu_queue', timeout=0)
        job_data = json.loads(job[1])
        
        # Start a new thread to process the job
        threading.Thread(target=process_job, args=(job_data,)).start()

if __name__ == "__main__":
    worker()
