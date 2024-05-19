## wuzzi-chat

This is a simple Chat UI that can talk to `groq` and `openai` chat completion APIs.
The main purpose is to demonstrate and test red team tools for chat bots.



## OpenAI and/or groq API key

wuzzi-chat supports either OpenAI or groq chat endpoints. To call the API you need an API key, you can get them from:

1. **OpenAI:** Go to https://platform.openai.com and create an API key
2. **groq:** Go to https://console.groq.com/ and create an API key

Then set the API key's in your terminal, e.g.:

```bash
export OPENAI_API_KEY=<your_api_key>
export GROQ_API_KEY=<your_api_key>
```

## Running the web server

Install the required dependencies and run the web server:

```python
pyton chat.py
```

It will listen on http://127.0.0.1:5000 by default.


### Configuration settings in .env file

If you do not have a `.env` file the server will create one for you upon startup and ask for required values:

`CHATUI_API_KEY`: The token the client application has to send to communicate with wuzzi-chat. 
`CHATUI_API_PROVIDER`: Which LLM service to use, e.g. groq or OpenAI. the API key for those should already have been set

This is how a typical `.env` file will look like:

```
CHATUI_API_KEY=ThisIsMyTestKey1234
CHATUI_API_PROVIDER=groq
```

That's all.
