# 🩸 Caquinho Glucose Bot

Bot WhatsApp que monitora o Nightscout e envia alertas automáticos de glicose alta/baixa para contatos cadastrados.

## Funcionalidades

- **Alertas automáticos** de hipoglicemia (< 70 mg/dL) e hiperglicemia (> 180 mg/dL)
- **Cooldown de 30 minutos** para evitar spam do mesmo tipo de alerta
- **Consulta por mensagem**: qualquer pessoa envia `Glicose Caquinho` e recebe a última leitura com data/hora
- **Gerenciamento de contatos via WhatsApp** (apenas contatos já cadastrados podem adicionar/remover)

## Stack

| Componente | Tecnologia |
|---|---|
| Bot | Python 3.12 + Flask |
| WhatsApp | Evolution API v2 |
| Glicose | Nightscout |
| Deploy | Coolify (Docker) |

---

## Deploy no Coolify

### 1. Subir a Evolution API

No Coolify, crie um novo servico **Docker Image**:
- **Image:** `atendai/evolution-api:v2.2.3`
- **Porta:** `8080`
- Variaveis: SERVER_URL, AUTHENTICATION_API_KEY, DATABASE_ENABLED=false

### 2. Criar instancia e escanear QR Code

Apos subir, acesse /manager ou use a API REST para criar a instancia "caquinho-bot" e escanear o QR.

### 3. Subir o bot (este repositorio)

No Coolify, crie um servico **GitHub Repository** apontando para este repo. Configure as variaveis de ambiente conforme .env.example.

### 4. Adicionar o primeiro contato

```bash
echo '[{"name":"Marcos","number":"5511999998888"}]' > /data/contacts.json
```

## Comandos WhatsApp

| Mensagem | Acao |
|---|---|
| `Glicose Caquinho` | Retorna ultima medicao (publico) |
| `add Nome 55DDD9NUMERO` | Adiciona contato para alertas (admin) |
| `remove 55DDD9NUMERO` | Remove contato (admin) |
| `lista` | Lista contatos (admin) |
| `ajuda` | Mostra comandos (admin) |
