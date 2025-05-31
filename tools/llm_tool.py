import litellm
from litellm import completion
from google.generativeai.agent import Tool
from typing import List, Dict, Any

class LLMTool(Tool):
    def __init__(self, model_name: str, base_url: str):
        super().__init__(
            name="LLM_Tool",
            description="A powerful language model for generating text, classifying, and converting questions.",
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The prompt to send to the LLM."},
                    "max_tokens": {"type": "integer", "description": "Maximum tokens in the response.", "default": 1024},
                    "temperature": {"type": "number", "description": "Controls randomness. Lower is more deterministic.", "default": 0.7},
                },
                "required": ["prompt"],
            },
        )
        self.model_name = model_name
        self.base_url = base_url
        # Configure LiteLLM to use Ollama API base
        litellm.set_custom_api_base({"ollama": base_url})

    def run(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        try:
            response = completion(
                model=f"ollama/{self.model_name}",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            # The structure returned by litellm completion matches OpenAI chat completion schema
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return f"LLM_ERROR: {e}"

# Example usage when running this script directly:
if __name__ == "__main__":
    import config  # Your config file with OLLAMA_MODEL_NAME and OLLAMA_BASE_URL
    llm_tool = LLMTool(model_name=config.OLLAMA_MODEL_NAME, base_url=config.OLLAMA_BASE_URL)
    test_prompt = "Explain Newton's first law in simple terms."
    print(f"LLM Response: {llm_tool.run(prompt=test_prompt)}")
