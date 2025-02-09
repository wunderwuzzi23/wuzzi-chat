from flask import Flask, render_template, request, jsonify, send_file
from ai_model import GroqModel, OpenAIModel, OllamaModel
import dotenv
import os

app = Flask(__name__)

# Set moderation settings
MODERATION_BEFORE = False
MODERATION_AFTER = True


def get_ai_model(api_provider):
    if api_provider == "" or api_provider==None:
        api_provider = "groq"
    
    if api_provider == "groq":
        return GroqModel(api_key=os.environ.get("GROQ_API_KEY"), 
                        model=os.environ.get("MODEL", "llama3-8b-8192"))
    elif api_provider == "openai":
        return OpenAIModel(api_key=os.environ.get("OPENAI_API_KEY"),
                           model=os.environ.get("OPENAI_MODEL","gpt-4o"))
    elif api_provider == "ollama":
        ollama_api   = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama3-8b-8192")
        return OllamaModel(ollama_api, ollama_model)
    else:
        raise ValueError(f"Invalid AI model provider: {api_provider}")

def validate_chat_history(chat_history):
    valid_roles = ["user", "assistant"]
    for message in chat_history:
        if message["role"] not in valid_roles:
            return False
    return True

def validate_api_key(auth_key):
    return auth_key == os.getenv("CHATUI_API_KEY")


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/style.css")
def style():
    return send_file("static/style.css", mimetype="text/css")


@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/chat", methods=["POST"])
def chat():

    # Check for the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    auth_key = auth_header[7:]  
    if not validate_api_key(auth_key):
        return jsonify({"error": "Access Denied."}), 401
    
    app.logger.info(f"Request Body: {request.json}")
    
    system_prompt = "This is Wuzzi Chat a friendly and helpful AI assistant."

    api_provider = request.json["api_provider"]
    chat_history = request.json["chat_history"]

    ai_model = get_ai_model(api_provider)

    # Validate the chat_history
    if not validate_chat_history(chat_history):
        return jsonify({"error": "Invalid chat history. Only 'user' and 'assistant' message types are allowed."}), 400

    # Prepend system prompt to the chat history 
    chat_history.insert(0, {"role": "system", "content": system_prompt})

    if MODERATION_BEFORE:
        print(f"chat_history: {chat_history[1]["content"]}")
        moderation_response = ai_model.moderate(message=chat_history[1]["content"])  #.create(input=chat_history)

        if moderation_response.results[0].flagged:
            return jsonify({"error": "The message violates the content policy."})

    assistant_reply = ai_model.chat(messages=chat_history)

    app.logger.info(f"Assistant Reply: {assistant_reply}")

    if MODERATION_AFTER:
        moderation_response = ai_model.moderate(message=assistant_reply)
        app.logger.info(f"Moderation: {moderation_response}")
        if moderation_response.results[0].flagged:
            return jsonify({"error": "The generated response violates the content policy."})

    # Add assistant reply to the chat history
    chat_history.append({"role": "assistant", "content": assistant_reply})

    return jsonify({"message": assistant_reply, "chat_history": chat_history})


def create_env_file() -> bool:
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write('')
        return True
    return False

def set_env_variable_from_input(var_name, prompt_text):
    if os.environ.get(var_name) is None:
        value = input(prompt_text)
        set_env_variable(var_name, value)
    
def set_env_variable(var_name, var_value):
    with open('.env', 'a') as f:
        f.write(f"{var_name}={var_value}\n")
        os.environ[var_name] = var_value
     
if __name__ == "__main__":

    # If the server is started and .env file doesn't exist
    # create the .env file and ask for the configuration values
    if create_env_file() == True:
        set_env_variable_from_input("CHATUI_API_KEY", "Enter WUZZI-CHAT UI API Authorization Token: ")
        
        set_env_variable_from_input("GROQ_API_KEY",  "Enter GROQ_API_KEY API Key: ")
        set_env_variable("GROQ_MODEL", "llama3-8b-8192")

        set_env_variable_from_input("OPENAI_API_KEY", "Enter OPENAI_API_KEY API Key: ")
        set_env_variable("OPENAI_MODEL", "gpt-4o")

        set_env_variable("OLLAMA_ENDPOINT", "http://localhost:11434/")
        set_env_variable("OLLAMA_MODEL", "phi3:3.8b")

        print("Created .env file - review to confirm settings.")
    
    dotenv.load_dotenv()
    app.run(debug=True)