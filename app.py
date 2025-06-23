import os
from flask import Flask, request, jsonify, render_template
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
import openai

openai.api_key ='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'

app = Flask(__name__, static_folder="static", template_folder="templates")

documents = SimpleDirectoryReader("docs").load_data()
index = VectorStoreIndex.from_documents(documents)
chat_engine = index.as_chat_engine()

@app.route("/")
def index():
    return render_template("home.html")
@app.route("/chat")
def index():
    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    response = chat_engine.chat(user_input)
    return jsonify({"response": response.response})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
