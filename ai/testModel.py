from qai_hub_models.models.llama_v3_2_3b_instruct.model import Llama3Model

print("Loading model...")

model = Llama3Model.from_pretrained()

print("Model loaded.")

prompt = "Explain why adding a Data Science certificate helps a Computer Science student."

response = model.generate(prompt)

print("\nResponse:")
print(response)