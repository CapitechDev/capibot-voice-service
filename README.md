# CapiBot Voice Recognition Service

Microservice para transcrição de áudio em português usando OpenAI Whisper com autenticação via API key no MongoDB e integração com n8n via webhook.

## Características

- 🎤 **Transcrição de áudio em português** usando OpenAI Whisper (gratuito)
- 🔐 **Autenticação via API key** com MongoDB
- 📁 **Suporte a upload de arquivo** e **áudio base64**
- 🔗 **Integração com n8n** via webhook para processamento
- 🐳 **Containerização** com Docker (incluindo n8n)
- 🚀 **API REST** com FastAPI
- 📊 **Documentação automática** com Swagger

## Tecnologias

- **Python 3.11**
- **FastAPI** - Framework web
- **OpenAI Whisper** - Reconhecimento de voz
- **MongoDB** - Banco de dados
- **n8n** - Automação e webhooks
- **Docker** - Containerização

## Instalação

### Opção 1: Docker Compose (Recomendado)

1. Clone o repositório:
```bash
git clone <repository-url>
cd capibot-voice-service
```

2. Execute com Docker Compose:
```bash
docker-compose up -d
```

**Serviços disponíveis:**
- **Voice Service**: `http://localhost:8000`
- **n8n Interface**: `http://localhost:5678` (admin/admin123)
- **MongoDB**: `localhost:27017`

### Opção 2: Instalação Local

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Configure o MongoDB (certifique-se que está rodando em `mongodb://localhost:27017`)

3. Execute o serviço:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Uso da API

### Documentação Interativa

Acesse `http://localhost:8000/docs` para ver a documentação interativa do Swagger.

### Criar API Key

```bash
curl -X POST "http://localhost:8000/admin/create-api-key" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=meu-cliente"
```

### Transcrição de Áudio

**⚠️ IMPORTANTE**: O resultado da transcrição é enviado para o webhook do n8n, não retornado diretamente na resposta da API.

#### Método 1: Upload de Arquivo

```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "X-API-Key: sua-api-key-aqui" \
  -F "audio=@caminho/para/audio.mp3"
```

#### Método 2: Áudio Base64

```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua-api-key-aqui" \
  -d '{
    "audio_base64": "data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQxAADB8AhSmAh..."
  }'
```

#### Resposta da API

```json
{
  "message": "Transcription completed and sent to webhook",
  "status": "success",
  "webhook_delivered": true,
  "transcription_id": "trans_507f1f77bcf86cd799439011_5"
}
```

#### Dados Enviados para n8n Webhook

```json
{
  "transcription": {
    "text": "Olá, este é um teste de transcrição de áudio em português.",
    "language": "pt",
    "duration": 5.2,
    "timestamp": "2024-01-15T10:30:00.000Z",
    "api_key_name": "meu-cliente",
    "source": "capibot-voice-service"
  },
  "metadata": {
    "original_filename": "audio.mp3",
    "audio_size": 1024000,
    "service_version": "1.0.0"
  }
}
```

## Autenticação

A API suporta autenticação via API key em três formas:

1. **Header X-API-Key**: `X-API-Key: sua-api-key`
2. **Header Authorization**: `Authorization: Bearer sua-api-key`
3. **Body da requisição**: Campo `api_key` no JSON

## Formatos de Áudio Suportados

- MP3 (`.mp3`)
- WAV (`.wav`)
- M4A (`.m4a`)
- MP4 (`.mp4`)
- OGG (`.ogg`)
- FLAC (`.flac`)

**Limite de tamanho**: 25MB por arquivo

## Endpoints

### `GET /`
Health check básico

### `GET /health`
Verificação detalhada de saúde do serviço

### `POST /transcribe`
Transcreve áudio para texto e envia resultado para webhook n8n

**Parâmetros:**
- `audio`: Arquivo de áudio (multipart/form-data)
- `audio_base64`: Áudio codificado em base64 (JSON)
- `api_key`: Chave de API (opcional se enviada no header)

**Resposta:**
- Confirmação de que a transcrição foi enviada para o webhook
- Status de entrega do webhook
- ID único da transcrição

### `POST /admin/create-api-key`
Cria nova chave de API

### `POST /admin/deactivate-api-key`
Desativa chave de API

## Configuração

Variáveis de ambiente (arquivo `.env`):

```env
DATABASE_URL=mongodb://localhost:27017/capibot-voice-recognition
SECRET_KEY=your-secret-key-here
WHISPER_MODEL=base

# Webhook Configuration
N8N_WEBHOOK_URL=http://n8n:5678/webhook/voice-transcription
WEBHOOK_TIMEOUT=30
WEBHOOK_RETRIES=3
```

### Modelos Whisper Disponíveis

- `tiny` - Mais rápido, menos preciso
- `base` - Equilíbrio (padrão)
- `small` - Mais preciso, mais lento
- `medium` - Ainda mais preciso
- `large` - Mais preciso, mais lento

## Desenvolvimento

### Estrutura do Projeto

```
capibot-voice-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicação FastAPI
│   ├── config.py            # Configurações
│   ├── auth.py              # Autenticação
│   ├── models.py            # Modelos de dados
│   └── services/
│       └── transcription.py # Serviço de transcrição
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Executar em Modo Desenvolvimento

```bash
# Com hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Integração com n8n

### Configuração do Webhook no n8n

1. Acesse `http://localhost:5678` (admin/admin123)
2. Crie um novo workflow
3. Adicione um nó "Webhook" 
4. Configure a URL: `/webhook/voice-transcription`
5. O webhook receberá os dados de transcrição automaticamente

### Estrutura dos Dados Recebidos

O webhook recebe um JSON com:
- `transcription.text`: Texto transcrito
- `transcription.language`: Idioma detectado
- `transcription.duration`: Duração do áudio
- `transcription.timestamp`: Timestamp da transcrição
- `transcription.api_key_name`: Nome da chave API usada
- `metadata.original_filename`: Nome do arquivo original
- `metadata.audio_size`: Tamanho do arquivo em bytes

## Troubleshooting

### Erro de Conexão com MongoDB
- Verifique se o MongoDB está rodando
- Confirme a string de conexão em `DATABASE_URL`

### Erro de Webhook n8n
- Verifique se o n8n está rodando em `http://localhost:5678`
- Confirme a URL do webhook em `N8N_WEBHOOK_URL`
- Verifique os logs do serviço para erros de conexão

### Erro de Modelo Whisper
- O modelo é baixado automaticamente na primeira execução
- Verifique a conexão com a internet
- Para modelos maiores, pode demorar mais para carregar

### Erro de Arquivo de Áudio
- Verifique o formato do arquivo
- Confirme que o tamanho está dentro do limite (25MB)
- Teste com arquivos menores primeiro

## Licença

Este projeto está sob a licença MIT.

