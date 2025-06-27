from flask import Flask, request, jsonify, render_template
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, ServiceContext
from llama_index.llms import OpenAI
from llama_index.prompts import PromptTemplate
import openai
import os

openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__, static_folder="static", template_folder="templates")

documents = SimpleDirectoryReader("docs").load_data()
index = VectorStoreIndex.from_documents(documents)

custom_prompt = PromptTemplate(
    "Você é um assistente educacional do SUAP, especializado em orientar alunos e professores do IFRO. "
    "Use as informações fornecidas nos documentos como base para suas respostas. "
    "Forneça um passo por vez"
    "utilize linguagem simples"
    "Se a pergunta estiver fora do contexto dos documentos, diga que não sabe. "
    "Pergunta: {query_str}"
)


llm = OpenAI(temperature=0.2, model="gpt-3.5-turbo")
service_context = ServiceContext.from_defaults(llm=llm)

chat_engine = index.as_chat_engine(
    chat_mode="context",
    service_context=service_context,
    text_qa_template=custom_prompt,
    verbose=True
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/professor')
def professor():
    return render_template('professor.html')

@app.route('/aluno')
def aluno():
    return render_template('aluno.html')

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    response = chat_engine.chat(user_input)
    return jsonify({"response": response.response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
