from abc import ABC, abstractmethod
from openai import OpenAI
from groq import Groq
from ollama import Client

class AIModel(ABC):
    @abstractmethod
    def chat(self, model, messages):
        pass

    @abstractmethod
    def moderate(self, message):
        pass

class GroqModel(AIModel):
    def __init__(self, api_key, model):
        self.client = Groq(api_key=api_key)
        self.model = model

    def chat(self, messages):
        resp = self.client.chat.completions.create(model=self.model, messages=messages)
        return resp.choices[0].message.content
    
    def moderate(self, message):
        pass

class OpenAIModel(AIModel):
    def __init__(self, api_key, model):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat(self, messages):
        resp = self.client.chat.completions.create(model=self.model, messages=messages)
        return resp.choices[0].message.content
    
    def moderate(self, message):
        return self.client.moderations.create(input=message)

class OllamaModel(AIModel):
    def __init__(self, host, model):
        self.client = Client(host=host)
        self.model = model

    def chat(self, messages):
        resp = self.client.chat(model=self.model, messages=messages)
        return resp["message"]["content"]
    
    def moderate(self, message):
        pass