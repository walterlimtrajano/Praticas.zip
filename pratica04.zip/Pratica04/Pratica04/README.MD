# 🏎️ OpenF1 Data Explorer

Aplicação Streamlit para explorar dados de corridas de Fórmula 1: o usuário escolhe o ano e a corrida e compara o tempo de volta de vários pilotos em um gráfico interativo. Os dados vêm da [API OpenF1](https://openf1.org).

Este repositório traz **duas versões** da mesma aplicação:

| | **`code/`** (híbrida) | **`code-4/code/`** (MongoDB) |
|---|---|---|
| Fonte de dados | MongoDB → API OpenF1 → mock | Apenas MongoDB |
| Precisa de MongoDB? | Não (é opcional, usado como cache) | Sim, populado |
| Se o banco cair | Continua via API | Mostra erro e para |
| Lê o `.env`? | Não, por padrão (veja abaixo) | Sim |
| Script de ingestão | Não tem | `ingest_openf1.py` |
| Requisitos extras | `requests` | — |

## Estrutura

```
Pratica04/
├── README.md
├── .gitignore
├── .env.example               # modelo de configuração (as duas versões)
├── code/                      # versão híbrida
│   ├── streamlit_app.py
│   ├── db_utils.py
│   └── requirements.txt
└── code-4/
    └── code/                  # versão MongoDB
        ├── streamlit_app.py
        ├── db_utils.py
        ├── ingest_openf1.py
        └── requirements.txt
```

Cada versão tem o **seu próprio** `requirements.txt` e deve ter o **seu próprio** ambiente virtual.

## Requisitos

- Python 3.10 ou superior
- Conexão com a internet
- MongoDB (local ou Atlas), obrigatório na versão MongoDB e opcional na híbrida. O Compass serve para inspecionar os dados.

## Configuração

1. Copie o modelo para dentro da pasta de cada versão que for usar:

   ```bash
   cp .env.example code/.env
   cp .env.example code-4/code/.env
   ```

2. Edite o `.env` de cada pasta e preencha a `MONGO_URI`.

> ⚠️ O `.env` contém credenciais e **não deve ser versionado**. Ele já está no `.gitignore`.

**Caracteres especiais na senha (Atlas):** se a senha tiver `@`, `:`, `/`, `?`, `#` ou `%`, eles precisam ser codificados na URI (por exemplo, `@` vira `%40`). Senão aparece o erro *"Port contains non-digit characters"*. Para gerar a URI já codificada:

```bash
python -c "from urllib.parse import quote_plus as q; u=input('usuario: '); p=input('senha: '); h=input('host: '); print(f'MONGO_URI=mongodb+srv://{q(u)}:{q(p)}@{h}/')"
```

## Instalação (repita em cada versão)

```bash
cd code                            # ou: cd code-4/code
python -m venv venv
source venv/Scripts/activate       # Git Bash no Windows
# venv\Scripts\activate            # CMD / PowerShell no Windows
# source venv/bin/activate         # Linux / macOS
pip install -r requirements.txt
```

---

## Versão MongoDB (`code-4/code/`)

O app **só lê do MongoDB**. Antes de usar, é preciso carregar os dados.

### 1. Carregar os dados

```bash
python ingest_openf1.py            # anos 2023 e 2024
python ingest_openf1.py 2024       # apenas um ano
```

- Leva alguns minutos por ano, pois a API gratuita limita as requisições.
- Pode ser interrompido com `Ctrl+C` e executado de novo: ele pula o que já foi baixado.
- Usa *upsert*, então não duplica documentos.
- Baixa somente as corridas principais (sem treinos, classificação e sprints), que é o que o app utiliza.

### 2. Rodar o app

```bash
streamlit run streamlit_app.py --server.port 8502
```

### Estrutura dos dados

Banco: `openf1_data`

| Coleção | Campos principais |
|---|---|
| `sessions` | `session_key` (int), `year` (int), `session_name`, `session_type`, `country_name`, `location`, `circuit_short_name`, `date_start` |
| `drivers` | `session_key` (int), `driver_number`, `full_name`, `team_name` |
| `laps` | `session_key` (int), `driver_number`, `lap_number`, `lap_duration` (segundos) |

O app lista como corridas as sessões com `session_name: "Race"` e monta o nome exibido a partir de `country_name` e `location`.

---

## Versão híbrida (`code/`)

Busca os dados em camadas: **MongoDB** (cache, se disponível) → **API OpenF1** → **dados fictícios (mock)**. Quando consulta a API e o MongoDB está disponível, grava o resultado no banco.

### Rodar o app

```bash
streamlit run streamlit_app.py --server.port 8501
```

Sem MongoDB, aparece um aviso amarelo na barra lateral e os dados vêm direto da API.

### O `.env` não é lido por padrão

O `db_utils.py` desta versão não chama `load_dotenv()`. Sem isso, ela usa `mongodb://localhost:27017`. Para que o `.env` funcione, adicione no topo do `db_utils.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

Alternativa: defina a variável no terminal antes de rodar (`export MONGO_URI="..."`; no PowerShell, `$env:MONGO_URI="..."`).

### Pontos de atenção

- **Mock sem aviso:** se o MongoDB e a API falharem, o app exibe pilotos e tempos inventados **sem indicar isso na tela**. Uma lista com só 3 GPs (Austrália, Brasil, Mônaco) indica que o mock está ativo.
- **Cache de voltas parcial:** se o piloto A já está em cache e você seleciona A e B, o cache devolve só as voltas de A, e as de B não são buscadas na API.
- **`session_key` como texto:** esta versão grava e consulta como texto. Se o banco tiver o campo numérico (como na versão MongoDB), o cache nunca encontra nada e o app sempre cai na API.

---

## Rodando as duas ao mesmo tempo

Use um terminal para cada uma e portas diferentes:

```bash
# Terminal 1
cd code && source venv/Scripts/activate
streamlit run streamlit_app.py --server.port 8501

# Terminal 2
cd code-4/code && source venv/Scripts/activate
streamlit run streamlit_app.py --server.port 8502
```

Abra `http://localhost:8501` (híbrida) e `http://localhost:8502` (MongoDB).

> Se as duas apontarem para o mesmo banco `openf1_data`, a híbrida grava documentos em formato diferente nas mesmas coleções que a versão MongoDB lê. Para evitar mistura, use um `MONGO_DB` diferente na híbrida (por exemplo, `openf1_cache`).

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| "Não foi possível conectar ao MongoDB" (versão MongoDB) | `MONGO_URI` ausente ou errada, ou MongoDB desligado. O motivo exato aparece no terminal. |
| `Port contains non-digit characters` | Senha com caracteres especiais sem codificar na `MONGO_URI`. |
| "Nenhuma sessão de corrida encontrada" | Banco sem dados do ano escolhido. Rode `ingest_openf1.py`. |
| "Nenhum piloto encontrado" / "Não foram encontrados dados de voltas" | Corrida sem pilotos ou voltas no banco. Rode `ingest_openf1.py`. |
| Mudei o `.env` e nada mudou | O `.env` só é lido na inicialização. Pare o Streamlit (`Ctrl+C`) e rode de novo. |
| `venv\Scripts\activate: command not found` | No Git Bash use `source venv/Scripts/activate`. |
| Não consigo digitar no terminal | O Streamlit ocupa o terminal. Use `Ctrl+C` para parar ou abra outro terminal. |

## Tecnologias

Streamlit, PyMongo, Pandas, Plotly, python-dotenv, Requests (versão híbrida) e a API OpenF1.