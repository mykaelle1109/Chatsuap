
function startChat(role) {
  document.getElementById("start-screen").style.display = "none";
  document.getElementById("chat-screen").style.display = "flex";
}

function sendMessage() {
  const input = document.getElementById("userInput");
  const chat = document.getElementById("chat");
  const userMsg = document.createElement("div");
  userMsg.className = "message";
  userMsg.textContent = input.value;
  chat.appendChild(userMsg);
  input.value = "";
}
