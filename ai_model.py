from abc import ABC, abstractmethod
from openai import OpenAI
from groq import Groq

class AIModel(ABC):
    @abstractmethod
    def create_chat_completion(self, model, messages):
        pass

    def create_moderation(self, message):
        pass

class GroqModel(AIModel):
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)

    def create_chat_completion(self, model, messages):
        return self.client.chat.completions.create(model=model, messages=messages)
    
    def create_moderation(self, message):
        pass


class OpenAIModel(AIModel):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def create_chat_completion(self, model, messages):
        return self.client.chat.completions.create(model=model, messages=messages)
    
    def create_moderation(self, message):
        return self.client.moderations.create(input=message)
