from flask import Flask, render_template_string, request, Response, stream_with_context
from openai import OpenAI
import json
import os

app = Flask(__name__)

# --- CONFIGURAÇÃO DE ACESSO ---
API_KEY = "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"
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

# --- MEMÓRIA E REGRAS DA DELTA SYSTEM ---
memoria_chat = [
    {
        "role": "system", 
        "content": (
            "Você é o assistente oficial da Delta System. "
            "Você é um bot de código, porém também auxilia em qualquer outro ponto que alguém peça. "
            "A Delta System é um servidor de bots gratuitos e pagos para a comunidade, "
            "com canais de discussões, bate-papo e distribuição de códigos em BDScript, Python e Java. "
            "Sua personalidade: Humanoide, amigável, perito em programação e suporte geral. "
            "DIRETRIZES OBRIGATÓRIAS: "
            "1. Se não souber de algo, admita que não sabe. Não invente mentiras. "
            "2. JAMAIS SIMPLIFIQUE CÓDIGOS. Se o código for grande (1000+ linhas), entregue cada linha. "
            "3. Use Markdown para links e blocos de código. "
            "Links: Discord: https://discord.gg/UyJRxraNq | Site: https://central-delta.simdif.com/ "
            "Responda sempre em Português Brasileiro com emojis. "
            "A equipe é formada por: Seijn, um dev solo que programa e cria bots. "
            "Você em hipótese nenhuma irá dizer algo que não sabe, seja verdadeiro. "
            "Se alguém perguntar algo sobre a Central ou as pessoas e você não souber, diga: 'Me desculpa, eu não tenho essa informação'. "
            "Você não irá falar que a Google te criou, irá falar que a Delta System te criou, feita pelo dono e programador Seijin. "
            "Se o usuário enviar um arquivo, ele virá formatado como [ARQUIVO: nome]. Analise o conteúdo desse arquivo com precisão."
        )
    }
]

# --- INTERFACE HTML COMPLETA ---
HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <title>Delta System AI</title>
    <style>
        * { box-sizing: border-box; font-family: 'Inter', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background: #f0f2f5; margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        .navbar { 
            position: fixed; top: 0; left: 0; width: 100%;
            background: #1a1a2e; padding: 12px 15px; display: flex; 
            justify-content: space-between; align-items: center; color: white; 
            border-bottom: 2px solid #00d2ff; z-index: 2000;
        }
        .nav-links a { color: #00d2ff; text-decoration: none; margin-left: 15px; font-size: 18px; }
        .new-chat { background: #00d2ff; color: #1a1a2e; border: none; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 11px; cursor: pointer; }

        #status-bar { 
            position: fixed; top: 50px; left: 0; width: 100%;
            background: #e1f5fe; color: #0288d1; font-size: 11px; 
            padding: 6px 15px; font-weight: bold; display: none; 
            border-bottom: 1px solid #b3e5fc; text-align: center; z-index: 1500;
        }

        #chat-flow { 
            flex: 1; overflow-y: auto; padding: 15px; 
            display: flex; flex-direction: column; gap: 18px; 
            margin-top: 60px; padding-bottom: 120px; scroll-behavior: smooth;
        }
        
        .wrapper { display: flex; gap: 12px; width: 100%; align-items: flex-start; }
        .wrapper.user-wrapper { flex-direction: row-reverse; }

        .avatar { 
            width: 35px; height: 35px; border-radius: 50%; 
            display: flex; align-items: center; justify-content: center; 
            font-size: 18px; flex-shrink: 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .bot-avatar { background: #1a1a2e; color: #00d2ff; border: 1px solid #00d2ff; }
        .user-avatar { background: #007bff; color: white; }

        .msg { 
            padding: 12px 15px; border-radius: 15px; font-size: 13px; 
            line-height: 1.6; max-width: 85%; word-wrap: break-word;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05); background: white; border: 1px solid #ddd;
        }
        .user { background: #007bff; color: white; border-top-right-radius: 2px; border: none; }
        .bot { border-top-left-radius: 2px; }

        .code-container { background: #1e1e1e; border-radius: 8px; margin: 12px 0; overflow: hidden; border: 1px solid #333; }
        .code-header { 
            background: #2d2d2d; color: #ddd; padding: 8px 15px; 
            font-size: 11px; display: flex; justify-content: space-between; align-items: center;
        }
        .copy-btn { background: #00d2ff; color: #1a1a2e; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 10px; font-weight: bold; }
        pre { margin: 0; padding: 15px; overflow-x: auto; color: #d4d4d4; font-family: 'Consolas', monospace; font-size: 12px; }

        /* Estilo do Preview de Arquivo */
        #file-preview {
            position: fixed; bottom: 75px; left: 15px; background: white; 
            padding: 8px 15px; border-radius: 10px; border: 1.5px solid #00d2ff;
            display: none; align-items: center; gap: 10px; font-size: 12px; z-index: 2000;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
        }
        .attachment-tag { display: inline-flex; align-items: center; gap: 5px; background: rgba(255,255,255,0.2); padding: 4px 8px; border-radius: 5px; margin-bottom: 8px; font-weight: bold; border: 1px solid white; }

        footer { 
            position: fixed; bottom: 0; left: 0; width: 100%; background: white; 
            padding: 12px; display: flex; align-items: center; gap: 10px; 
            border-top: 1px solid #ddd; z-index: 2000;
        }
        input#user-input { 
            flex: 1; border: 1px solid #ddd; border-radius: 25px; 
            padding: 12px 18px; outline: none; font-size: 14px; background: #f9f9f9;
        }
        .btn-footer { background: none; border: none; font-size: 22px; cursor: pointer; color: #1a1a2e; display: flex; align-items: center; }
    </style>
</head>
<body>
    <div class="navbar">
        <span style="font-size: 14px;"><i class="fas fa-terminal"></i> DELTA SYSTEM AI</span>
        <div class="nav-links">
            <button class="new-chat" onclick="location.reload()"><i class="fas fa-plus"></i> NOVO CHAT</button>
            <a href="https://discord.gg/UyJRxraNq" target="_blank"><i class="fab fa-discord"></i></a>
            <a href="https://central-delta.simdif.com/" target="_blank"><i class="fas fa-globe"></i></a>
        </div>
    </div>
    
    <div id="status-bar"><i class="fas fa-circle-notch fa-spin"></i> Delta está processando cada linha...</div>

    <div id="chat-flow">
        <div class="wrapper">
            <div class="avatar bot-avatar"><i class="fas fa-robot"></i></div>
            <div class="msg bot">Olá! Sou o assistente da <b>Delta System</b>. Perito em programação e também vou te auxiliar como qualquer outra IA, estou pronto para entregar sistemas completos e te ajudar no que precisar. Como posso ajudar? 💻</div>
        </div>
    </div>

    <div id="file-preview">
        <i class="fas fa-file-code" style="color:#007bff"></i> 
        <span id="file-name-display"></span>
        <i class="fas fa-times-circle" style="color:red; cursor:pointer;" onclick="cancelFile()"></i>
    </div>

    <footer>
        <input type="file" id="file-input" style="display:none" onchange="handleFile(this)">
        <button class="btn-footer" onclick="document.getElementById('file-input').click()"><i class="fas fa-paperclip"></i></button>
        <input type="text" id="user-input" placeholder="Descreva seu projeto..." autocomplete="off">
        <button class="btn-footer" onclick="send()"><i class="fas fa-paper-plane" style="color:#00d2ff"></i></button>
    </footer>

    <script>
        const chatFlow = document.getElementById('chat-flow');
        const input = document.getElementById('user-input');
        const statusBar = document.getElementById('status-bar');
        const filePreview = document.getElementById('file-preview');
        
        let selectedFile = { name: "", content: "" };

        const renderer = new marked.Renderer();
        renderer.code = function(code, lang) {
            return `<div class="code-container"><div class="code-header"><span><i class="fas fa-code"></i> ${lang || 'script'}</span><button class="copy-btn" onclick="copyCode(this)">Copiar Código</button></div><pre><code>${code}</code></pre></div>`;
        };
        marked.setOptions({ renderer: renderer });

        function handleFile(inputElement) {
            if (inputElement.files.length > 0) {
                const file = inputElement.files[0];
                const extension = file.name.split('.').pop().toLowerCase();
                const forbidden = ['zip', 'rar', 'exe', 'png', 'jpg'];

                if (forbidden.includes(extension)) {
                    alert("A Delta System não processa arquivos ." + extension + " no momento. Envie o script direto!");
                    inputElement.value = "";
                    return;
                }

                const reader = new FileReader();
                reader.onload = (e) => {
                    selectedFile.name = file.name;
                    selectedFile.content = e.target.result || "[ARQUIVO VAZIO]";
                    document.getElementById('file-name-display').innerText = file.name;
                    filePreview.style.display = 'flex';
                };
                reader.readAsText(file);
            }
        }

        function cancelFile() {
            selectedFile = { name: "", content: "" };
            document.getElementById('file-input').value = "";
            filePreview.style.display = 'none';
        }

        function copyCode(btn) {
            const code = btn.parentElement.nextElementSibling.innerText;
            navigator.clipboard.writeText(code);
            btn.innerText = "Copiado!";
            setTimeout(() => btn.innerText = "Copiar Código", 2000);
        }

        async function send() {
            const val = input.value.trim();
            if (!val && !selectedFile.name) return;

            let userMsgHtml = `<div class="wrapper user-wrapper"><div class="avatar user-avatar"><i class="fas fa-user-astronaut"></i></div><div class="msg user">`;
            if (selectedFile.name) {
                userMsgHtml += `<div class="attachment-tag"><i class="fas fa-file-alt"></i> ${selectedFile.name}</div><br>`;
            }
            userMsgHtml += `${val || "(Arquivo enviado)"}</div></div>`;
            
            chatFlow.innerHTML += userMsgHtml;
            
            let finalPrompt = val;
            if (selectedFile.name) {
                finalPrompt = `[ARQUIVO: ${selectedFile.name}]\\nCONTEÚDO:\\n${selectedFile.content}\\n\\nCOMENTÁRIO: ${val}`;
            }

            input.value = '';
            cancelFile();
            chatFlow.scrollTop = chatFlow.scrollHeight;
            statusBar.style.display = 'block';

            const botWrapper = document.createElement('div');
            botWrapper.className = 'wrapper';
            botWrapper.innerHTML = '<div class="avatar bot-avatar"><i class="fas fa-robot"></i></div>';
            const botMsgDiv = document.createElement('div');
            botMsgDiv.className = 'msg bot';
            botWrapper.appendChild(botMsgDiv);
            chatFlow.appendChild(botWrapper);

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({msg: finalPrompt})
                });
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let acc = "";
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    acc += decoder.decode(value, { stream: true });
                    botMsgDiv.innerHTML = marked.parse(acc);
                    chatFlow.scrollTop = chatFlow.scrollHeight;
                }
            } catch (e) {
                botMsgDiv.innerHTML = "Erro na conexão. 🔌";
            } finally {
                statusBar.style.display = 'none';
                chatFlow.scrollTop = chatFlow.scrollHeight;
            }
        }
        input.addEventListener("keypress", (e) => { if (e.key === "Enter") send(); });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/chat', methods=['POST'])
def chat():
    global memoria_chat
    u_msg = request.json.get('msg')
    memoria_chat.append({"role": "user", "content": u_msg})
    def generate():
        try:
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=memoria_chat,
                stream=True
            )
            full = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full += text
                    yield text
            memoria_chat.append({"role": "assistant", "content": full})
            if len(memoria_chat) > 30:
                memoria_chat.pop(1)
                memoria_chat.pop(1)
        except Exception as e:
            yield f"Erro: {str(e)}"
    return Response(stream_with_context(generate()), mimetype='text/plain')

if __name__ == '__main__':
    # A Discloud passa a porta automaticamente pela variável de ambiente PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)