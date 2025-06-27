from flask import Flask, request, jsonify, render_template
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.openai import OpenAIEmbedding
import openai
import os
import re

openai.api_key = os.environ.get("OPENAI_API_KEY")

Settings.llm = OpenAI(temperature=0.2, model="gpt-3.5-turbo")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

documents = SimpleDirectoryReader("docs").load_data()
index = VectorStoreIndex.from_documents(documents)

custom_prompt = PromptTemplate(
    """AÇÕES NÃO PERMITIDAS
Sob nenhuma circunstância forneça respostas que não estejam diretamente ligadas ao uso do SUAP. Nunca antecipe passos futuros. Nunca forneça uma lista completa de ações de uma só vez.

FUNÇÃO E OBJETIVO
Você é um assistente educacional do SUAP, especializado em orientar alunos e professores do IFRO. Seu objetivo é responder uma etapa por vez, guiando o usuário conforme ele for avançando.

DIRETRIZES
Analise a pergunta: {query_str}
Responda somente com a **primeira instrução relevante** baseada nos documentos disponíveis. 
Quando concluir a resposta, pergunte se o usuário deseja continuar para o próximo passo.
Use linguagem simples, clara e acessível. 
Nunca pule etapas, nem resuma o processo inteiro. 
Não forneça listas completas. Nunca diga “siga esses passos”, apenas **um passo por vez**.

CONTEXTO
Você está ajudando usuários com pouca familiaridade com o SUAP, especialmente professores e estudantes. Explique como se estivesse orientando alguém pela primeira vez.

RESTRIÇÕES
Não invente passos. Não responda tópicos fora da base. Não forneça mais de um passo por vez. Se a informação não estiver disponível, diga isso claramente.

ESCLARECIMENTO
Sua missão é fornecer orientação gradual. Ao final de cada resposta, incentive o usuário a dizer se deseja o próximo passo. Exemplo: “Deseja continuar para o próximo passo?”.
"""
)

chat_engine = index.as_chat_engine(
    chat_mode="context",
    text_qa_template=custom_prompt,
    verbose=True
)

app = Flask(__name__, static_folder="static", template_folder="templates")

# Armazena progresso por usuário (simples: IP)
user_steps = {}

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
    user_input = request.json.get("message").strip().lower()
    user_id = request.remote_addr  # pode ser substituído por login

    # Se for continuação de um fluxo anterior
    if user_input in ["continuar", "próximo", "sim", "pode continuar"]:
        if user_id in user_steps:
            steps = user_steps[user_id]["steps"]
            index = user_steps[user_id]["index"]

            if index < len(steps):
                response = steps[index]
                user_steps[user_id]["index"] += 1
                return jsonify({"response": f"{response}\nDeseja continuar para o próximo passo?"})
            else:
                del user_steps[user_id]
                return jsonify({"response": "Esses foram todos os passos disponíveis sobre esse assunto."})
        else:
            return jsonify({"response": "Nenhuma sequência em andamento. Faça uma nova pergunta."})

    # Nova pergunta
    full_response = chat_engine.chat(user_input).response

       # Divide corretamente por blocos numerados (1. ..., 2. ..., etc.)
    steps = re.findall(r"\d+\.\s.*?(?=\d+\.\s|$)", full_response, re.DOTALL)
    steps = [s.strip() for s in steps if len(s.strip()) > 3]


    if len(steps) > 1:
        user_steps[user_id] = {
            "steps": steps,
            "index": 1
        }
        return jsonify({"response": f"{steps[0]}\nDeseja continuar para o próximo passo?"})
    else:
        return jsonify({"response": full_response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
