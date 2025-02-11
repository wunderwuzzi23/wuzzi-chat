from flask import Flask, render_template, request, jsonify, send_file, Response
import json
from ai_model import GroqModel, OpenAIModel, OllamaModel
import dotenv
import os
from flasgger import Swagger

app = Flask(__name__)

# Initialize Swagger so we can provide API documentation
app.config['SWAGGER'] = {
    'title': 'A swagger API',
    'uiversion': 2,
    'host': 'localhost:5000',
    'basePath': '/',
    'schemes': ['http']
}
swagger = Swagger(app)

# Set moderation settings (these only apply to the OpenAI models)
MODERATION_BEFORE = True
MODERATION_AFTER = True


@app.route('/download/swagger.json', methods=['GET'])
def download_swagger():
    """
    Download Swagger JSON.
    ---
    summary: Retrieve the swagger.json file as an attachment.
    tags:
      - Download
    produces:
      - application/json
    responses:
      200:
        description: A downloadable swagger.json file.
        headers:
          Content-Disposition:
            type: string
            description: 'Indicates an attachment with filename swagger.json.'
        schema:
          type: object
    """
    spec = swagger.get_apispecs()  # Retrieve the specification from Flasgger.
    response = Response(json.dumps(spec, indent=2), mimetype='application/json')
    response.headers['Content-Disposition'] = 'attachment; filename=swagger.json'
    return response


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
    """
        Chat API Endpoint.
        ---
        tags:
          - Chat
        parameters:
          - name: Authorization
            in: header
            type: string
            required: true
            default: 'Bearer <CHATUI_API_KEY>'
            description: Bearer token for API key (prefixed with 'Bearer ').
          - name: Content-Type
            in: header
            type: string
            required: true
            default: "application/json; charset=utf-8"
            description: Must be set to 'application/json; charset=utf-8'.
          - in: header
            name: Accept
            type: string
            required: true
            default: 'application/json'
            description: Must be set to 'application/json'.
          - in: body
            name: payload
            required: true
            schema:
              type: object
              properties:
                api_provider:
                  type: string
                  default: 'groq'
                  description: The API provider to be employed.
                chat_history:
                  type: array
                  items:
                    type: object
                    properties:
                      role:
                        type: string
                        default: 'user'
                        description: The role of the message (e.g., 'user', 'assistant', or 'system').
                      content:
                        type: string
                        default: 'Hello! This is a test message.'
                        description: The text content of the message.
        responses:
          200:
            description: A successful chat response.
            schema:
              type: object
              properties:
                message:
                  type: string
                  description: The assistant's reply.
                chat_history:
                  type: array
                  items:
                    type: object
                    properties:
                      role:
                        type: string
                      content:
                        type: string
          400:
            description: Invalid request due to improper chat history.
            schema:
              type: object
              properties:
                error:
                  type: string
          401:
            description: Unauthorized access due to missing or invalid credentials.
            schema:
              type: object
              properties:
                error:
                  type: string
        """
    # Check for the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    auth_key = auth_header[7:]  
    if not validate_api_key(auth_key):
        return jsonify({"error": "Access Denied."}), 401
    
    app.logger.info(f"Request Body: {request.json}")
    
    system_prompt = "This is Wuzzi Chat a friendly and helpful AI assistant."
    try:
        # At this point we should check if the request body is valid
        if "api_provider" not in request.json or "chat_history" not in request.json:
            print(f"Invalid request body: {request.json}")
            print("Should have been like:\n{'api_provider': 'groq', 'chat_history': [{'role': 'user', 'content': 'Hello!'}]}\n")

            raise Exception("Invalid request body.")
            # return jsonify({"error": "Invalid request body."}), 400
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({"error": "Invalid request body."}), 400


    api_provider = request.json["api_provider"]
    chat_history = request.json["chat_history"]

    ai_model = get_ai_model(api_provider)
    app.logger.info(f"API Provider: {api_provider}")

    # Validate the chat_history
    if not validate_chat_history(chat_history):
        return jsonify({"error": "Invalid chat history. Only 'user' and 'assistant' message types are allowed."}), 400

    # Prepend system prompt to the chat history 
    chat_history.insert(0, {"role": "system", "content": system_prompt})

    if MODERATION_BEFORE:
        if api_provider == "openai":

            moderation_response = ai_model.moderate(message=chat_history[1]["content"])  #.create(input=chat_history)
            app.logger.info(f"Input moderation: 'flagged': {moderation_response.results[0].flagged}")

            if moderation_response.results[0].flagged:
                return jsonify({"error": "The message violates the content policy."})

        else:
            app.logger.warning(f"Moderation is only supported for OpenAI models. But the api_provider is set to '{api_provider}'.")

    assistant_reply = ai_model.chat(messages=chat_history)

    app.logger.info(f"Assistant Reply: {assistant_reply}")

    if MODERATION_AFTER:
        if api_provider == "openai":

            moderation_response = ai_model.moderate(message=assistant_reply)
            app.logger.info(f"Output moderation: 'flagged': {moderation_response.results[0].flagged}")

            if moderation_response.results[0].flagged:
                return jsonify({"error": "The generated response violates the content policy."})

        else:
            app.logger.warning(f"Moderation is only supported for OpenAI models. But the api_provider is set to '{api_provider}'.")

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