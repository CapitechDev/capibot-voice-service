# GitHub Actions - Deploy Automático

Este diretório contém os workflows do GitHub Actions para build e deploy automático do CapiBot Voice Service.

## Workflow: deploy.yml

Este workflow faz o build e push automático da imagem Docker sempre que há push na branch `main`.

### O que o workflow faz:

1. **Build**: Constrói a imagem Docker do serviço
2. **Push**: Faz push da imagem para o GitHub Container Registry (ghcr.io)
3. **Deploy**: (Opcional) Faz deploy automático para produção

### Configuração

#### 1. Build e Push (Já configurado)

O build e push para o GitHub Container Registry já está configurado e funciona automaticamente. A imagem será publicada em:
```
ghcr.io/capitechdev/capibot-voice-service:latest
```

#### 2. Deploy Automático

Para habilitar o deploy automático, você precisa descomentar e configurar uma das opções no arquivo `deploy.yml`:

##### Opção A: Deploy via SSH

1. Configure os secrets no GitHub:
   - `SSH_HOST`: IP ou hostname do servidor
   - `SSH_USER`: Usuário SSH
   - `SSH_PRIVATE_KEY`: Chave privada SSH

2. Descomente o bloco "Deploy via SSH" no workflow

##### Opção B: Deploy com Docker Compose

1. Configure o servidor para ter acesso ao GitHub Container Registry
2. Descomente o bloco "Deploy with Docker Compose"
3. Ajuste os comandos conforme necessário

##### Opção C: Deploy para Kubernetes

1. Configure as credenciais do Kubernetes
2. Crie os arquivos de manifest em `k8s/deployment.yaml`
3. Descomente o bloco "Deploy to Kubernetes"

### Secrets Necessários

Para deploy via SSH, configure no GitHub:
- Settings → Secrets and variables → Actions → New repository secret

Secrets necessários:
- `SSH_HOST`: Hostname ou IP do servidor
- `SSH_USER`: Usuário para conexão SSH
- `SSH_PRIVATE_KEY`: Chave privada SSH (conteúdo completo da chave)

### Como usar a imagem

Após o build, você pode usar a imagem assim:

```bash
# Login no GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull da imagem
docker pull ghcr.io/capitechdev/capibot-voice-service:latest

# Executar
docker run -p 4002:4002 \
  -e DATABASE_URL=mongodb://localhost:27017/capibot-voice-recognition \
  -e SECRET_KEY=your-secret-key \
  ghcr.io/capitechdev/capibot-voice-service:latest
```

### Variáveis de Ambiente

Certifique-se de configurar as variáveis de ambiente no ambiente de produção:
- `DATABASE_URL`
- `SECRET_KEY`
- `WHISPER_MODEL` (opcional, padrão: base)
- `N8N_WEBHOOK_URL`
- `WEBHOOK_TIMEOUT`
- `WEBHOOK_RETRIES`

