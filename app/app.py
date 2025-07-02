from flask import Flask, request, jsonify, render_template
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.chat_engine.types import ChatMessage
from dotenv import load_dotenv
import openai
import random
import os
import redis
import urllib.parse
import json

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.jinja_env.globals['random'] = lambda: random.randint(0, 99999)

redis_url = os.environ.get("REDIS_URL")
parsed = urllib.parse.urlparse(redis_url)
redis_client = redis.Redis(
    host=parsed.hostname,
    port=parsed.port,
    password=parsed.password,
    ssl=True,
    decode_responses=True
)
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
Responda com **apenas uma etapa por vez**, formatada de forma clara. Utilize **listas numeradas ou quebras de linha** para facilitar a leitura. Evite blocos longos e use sempre linguagem simples e direta.

Quando concluir a etapa, pergunte:
**Deseja continuar para o próximo passo?**

CONTEXTO
Você está ajudando usuários com pouca familiaridade com o SUAP, especialmente professores e estudantes. Explique como se estivesse orientando alguém pela primeira vez, com calma e clareza.

RESTRIÇÕES
Não invente passos. Não responda tópicos fora da base. Nunca responda perguntas que não estejam claramente ligadas ao sistema SUAP. Se a pergunta for sobre outro assunto (como compras, carros, redes sociais, política, etc), informe que isso foge do seu domínio e recuse-se a responder.

ESCLARECIMENTO
Sua missão é fornecer orientação gradual. Formate sempre de forma limpa e visual. Exemplo de formatação ideal:

1. Acesse o menu Administração → Salas.
2. Selecione o campus.
3. Clique em “Filtrar”.

Após cada etapa, finalize com:  
**Deseja continuar para o próximo passo?**
"""
)

chat_engine = index.as_chat_engine(
    chat_mode="context",
    text_qa_template=custom_prompt,
    similarity_top_k=5,
    verbose=True,
    response_mode="refine"
)

def get_history(user_id):
    key = f"chat_history:{user_id}"
    raw = redis_client.get(key)
    if not raw:
        return []
    try:
        return [ChatMessage(**json.loads(msg)) for msg in json.loads(raw)]
    except Exception:
        return []


def save_history(user_id, history):
    key = f"chat_history:{user_id}"
    redis_client.set(
        key,
        json.dumps([msg.json() for msg in history]),  # 👈 isso resolve
        ex=3600
    )

def clear_history(user_id):
    redis_client.delete(f"chat_history:{user_id}")

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
    user_input = request.json.get("message", "").strip()
    user_id = request.remote_addr

    if user_input.lower() in ["reiniciar", "resetar", "começar de novo", "limpar"]:
        clear_history(user_id)
        return jsonify({"response": "Conversa reiniciada. Como posso te ajudar?"})

    history = get_history(user_id)
    response_obj = chat_engine.chat(user_input, chat_history=history)
    full_response = response_obj.response

    history.append(ChatMessage(role="user", content=user_input))
    history.append(ChatMessage(role="assistant", content=full_response))
    save_history(user_id, history)

    return jsonify({"response": full_response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
