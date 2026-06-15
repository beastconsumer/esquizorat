# Esquizorat - Remote Administration Tool (RAT)

Este é um projeto completo de RAT com integração ao Discord e um Painel Web via Docker. O código foi sanitizado para remoção de tokens e chaves privadas. Siga as instruções abaixo para configurar o seu ambiente.

## 🚀 Guia de Configuração (Onde inserir seus Tokens)

Para o projeto funcionar, você deve inserir seus próprios tokens nos seguintes arquivos:

### 1. Discord Bot (Controle Remoto)
No arquivo `Program.py`, procure pelas seguintes linhas no início do arquivo:
- **TOKEN**: Insira o Bot Token do seu aplicativo no [Discord Developer Portal](https://discord.com/developers/applications).
- **GUILD_ID**: Insira o ID do seu servidor (Guild) do Discord.
- **AUTHORIZED_USERS**: Coloque o seu ID de usuário do Discord na lista para que apenas você possa comandar o bot.

```python
# Program.py
TOKEN = 'SEU_TOKEN_AQUI'
GUILD_ID = 123456789012345678  # Substitua pelo ID do seu servidor
AUTHORIZED_USERS = [123456789012345678] # Substitua pelo seu ID de usuário
```

### 2. Discord Webhook (Screenshots e Logs)
No arquivo `web_api_docker.py`, insira a URL do seu Webhook:
```python
# web_api_docker.py
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
```

### 3. Painel Web (Autenticação)
No arquivo `web_api_docker.py`, você pode alterar a senha padrão (atualmente `admin`/`password`):
```python
# web_api_docker.py
if username == 'admin' and password == 'password':
```
E também a `app.secret_key`:
```python
app.secret_key = 'sua_chave_secreta_aqui'
```

### 4. Linear API (Opcional - Gestão de Tasks)
Se utilizar a integração com o Linear, insira sua chave em `fetch_linear_tasks.js`:
```javascript
// fetch_linear_tasks.js
const apiKey = 'SUA_CHAVE_LINEAR_AQUI';
```

---

## 📂 Estrutura do Projeto

### Core
- **Program.py**: RAT principal (Discord bot + controle de sistema).
- **central_client.py**: Conexão com o painel Docker.
- **builder2.py**: Script de compilação para gerar o `RAT.exe`.

### Dashboard (Docker)
- **web_api_docker.py**: Servidor Flask/SocketIO.
- **panel_docker.html**: Interface visual.
- **Dockerfile / docker-compose.yml**: Para rodar o servidor 24/7.

---

## 🛠️ Como Utilizar

### Passo 1: Compilação
Após configurar os tokens no `Program.py`, compile o executável:
```bash
python builder2.py
```
O arquivo será gerado em `dist/RAT.exe`.

### Passo 2: Servidor
Inicie o painel de controle usando Docker:
```bash
docker-compose up -d --build
```
Acesse em: `http://localhost:5000`

---

## ⚠️ Aviso Legal
Este software é fornecido apenas para fins educacionais e de pesquisa. O autor não se responsabiliza por qualquer uso indevido ou danos causados por este programa.

---
**Desenvolvido por beastconsumer**
