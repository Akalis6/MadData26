from flask import Flask, request, jsonify
from flask_cors import CORS

# Import your local Llama model functions from runModel.py
# (Ensure runModel.py has a function like `generate_response(prompt)` that takes a string and returns the model's text)
import runModel 

app = Flask(__name__)
CORS(app)

@app.route('/api/ask', methods=['POST'])
def ask_llama():
    data = request.json
    user_prompt = data.get('prompt', '')
    student_context = data.get('context', '')
    
    # 1. Engineer the Prompt
    # We combine the context from Convex with the user's question
    full_prompt = f"""You are an expert academic advisor for the University of Wisconsin-Madison. 
Use the following student context to answer their question accurately. 

Student Context (Courses Taken & Requirements):
{student_context}

Student Question: 
{user_prompt}

Answer helpfuly and concisely:"""
    
    # 2. Call your actual Llama model via runModel.py
    # NOTE: Adjust 'runModel.generate_response' to match whatever function 
    # actually generates the text in your runModel.py file.
    try:
        model_response = runModel.generate_response(full_prompt)
    except Exception as e:
        model_response = f"Model error: {str(e)}"
    
    return jsonify({"answer": model_response})

if __name__ == '__main__':
    app.run(port=5000)