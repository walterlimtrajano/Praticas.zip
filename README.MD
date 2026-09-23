# 📚 Práticas

Repositório com as práticas da disciplina de manipulação de dados. Cada prática fica em sua própria pasta, com código, `requirements.txt` e `.env.example` próprios. Toda a documentação está neste arquivo.

## Índice

- [Como usar qualquer prática](#como-usar-qualquer-prática)
- [Prática 04: Explorador de dados de F1 (MongoDB e API OpenF1)](#prática-04-explorador-de-dados-de-f1-mongodb-e-api-openf1)
- [Prática 05: Persistência poliglota (MongoDB e SQLite)](#prática-05-persistência-poliglota-mongodb-e-sqlite)
- [Problemas comuns](#problemas-comuns)

| Prática | Tema | Tecnologias |
|---|---|---|
| **04** | Explorador de dados de F1, com uma versão híbrida (MongoDB, API OpenF1 e mock) e outra só com MongoDB, com script de ingestão | Streamlit, MongoDB, API OpenF1, Plotly |
| **05** | Persistência poliglota: dados brutos no MongoDB e relatórios sumarizados no SQLite | Streamlit, MongoDB, SQLite, SQLAlchemy, Plotly |

## Estrutura do repositório

```
Praticas/
├── README.md
├── .gitignore
├── Pratica04/
│   ├── .env.example
│   ├── code/                  # versão híbrida (v1)
│   │   ├── streamlit_app.py
│   │   ├── db_utils.py
│   │   └── requirements.txt
│   └── code-4/
│       └── code/              # versão MongoDB (v2)
│           ├── streamlit_app.py
│           ├── db_utils.py
│           ├── ingest_openf1.py
│           └── requirements.txt
└── Pratica05/
    ├── .env.example
    ├── streamlit_app.py
    ├── db_utils.py
    ├── seed_db.py
    ├── recuperar.py
    └── requirements.txt
```

---

## Como usar qualquer prática

**Pré-requisitos gerais**

- Python 3.10 ou superior
- MongoDB (local ou Atlas). O Compass serve para inspecionar os dados.
- Git Bash, CMD ou PowerShell

**Passos**

1. Entre na pasta do projeto que vai rodar.
2. Copie o `.env.example` da prática para um arquivo `.env` na pasta do projeto e preencha os valores.
3. Crie um ambiente virtual e instale as dependências do `requirements.txt` daquele projeto:

```bash
python -m venv venv
source venv/Scripts/activate       # Git Bash no Windows
# venv\Scripts\activate            # CMD / PowerShell no Windows
# source venv/bin/activate         # Linux / macOS
pip install -r requirements.txt
```

4. Rode o app com `streamlit run streamlit_app.py`.

**Regras que valem para todas as práticas**

- Cada projeto tem o **seu próprio** `requirements.txt` e deve ter o **seu próprio** ambiente virtual.
- O `.env` contém credenciais e **não é versionado** (o `.gitignore` da raiz cobre todas as pastas). Só o `.env.example` vai para o repositório.
- Os nomes das variáveis **mudam de uma prática para outra** (`MONGO_URI` na 04, `MONGODB_URI` na 05). Use sempre o modelo da pasta correspondente. Se o nome estiver errado, o app usa o padrão (`localhost`) sem avisar.
- O `.env` só é lido quando o app inicia. Depois de editá-lo, pare o Streamlit (`Ctrl+C`) e rode de novo.
- Se a senha da URI do Atlas tiver caracteres especiais (`@`, `:`, `/`, `?`, `#`, `%`), codifique-os (por exemplo, `@` vira `%40`). Para gerar a URI já codificada:

```bash
python -c "from urllib.parse import quote_plus as q; u=input('usuario: '); p=input('senha: '); h=input('host: '); print(f'MONGO_URI=mongodb+srv://{q(u)}:{q(p)}@{h}/')"
```

- **Use bancos MongoDB com nomes diferentes** em cada prática (por exemplo, `openf1_data` na 04 e `openf1_pratica05` na 05), porque alguns scripts de povoamento **apagam coleções** do banco configurado.

---

## Prática 04: Explorador de dados de F1 (MongoDB e API OpenF1)

Aplicação Streamlit para explorar dados de corridas de Fórmula 1: o usuário escolhe o ano e a corrida e compara o tempo de volta de vários pilotos em um gráfico interativo. Os dados vêm da [API OpenF1](https://openf1.org). Há duas versões da mesma aplicação:

| | **`Pratica04/code`** (v1, híbrida) | **`Pratica04/code-4/code`** (v2, MongoDB) |
|---|---|---|
| Fonte de dados | MongoDB → API OpenF1 → mock | Apenas MongoDB |
| Precisa de MongoDB? | Não (opcional, usado como cache) | Sim, populado |
| Se o banco cair | Continua via API | Mostra erro e para |
| Lê o `.env`? | Não, por padrão (veja abaixo) | Sim |
| Script de ingestão | Não tem | `ingest_openf1.py` |
| Dependência extra | `requests` | — |

**Configuração:**

```bash
cp Pratica04/.env.example Pratica04/code/.env
cp Pratica04/.env.example Pratica04/code-4/code/.env
```

### Versão MongoDB (v2)

O app **só lê do MongoDB**. Antes de usar, é preciso carregar os dados. Dentro de `Pratica04/code-4/code`, com o ambiente virtual ativo:

```bash
python ingest_openf1.py            # anos 2023 e 2024
python ingest_openf1.py 2024       # apenas um ano
streamlit run streamlit_app.py --server.port 8502
```

O script de ingestão:

- Leva alguns minutos por ano, pois a API gratuita limita as requisições.
- Pode ser interrompido com `Ctrl+C` e executado de novo: ele pula o que já foi baixado.
- Usa *upsert*, então não duplica documentos.
- Baixa somente as corridas principais (sem treinos, classificação e sprints), que é o que o app utiliza.

**Estrutura dos dados** (banco `openf1_data`):

| Coleção | Campos principais |
|---|---|
| `sessions` | `session_key` (int), `year` (int), `session_name`, `session_type`, `country_name`, `location`, `circuit_short_name`, `date_start` |
| `drivers` | `session_key` (int), `driver_number`, `full_name`, `team_name` |
| `laps` | `session_key` (int), `driver_number`, `lap_number`, `lap_duration` (segundos) |

O app lista como corridas as sessões com `session_name: "Race"` e monta o nome exibido a partir de `country_name` e `location`.

### Versão híbrida (v1)

Busca os dados em camadas: **MongoDB** (cache, se disponível) → **API OpenF1** → **dados fictícios (mock)**. Quando consulta a API e o MongoDB está disponível, grava o resultado no banco. Dentro de `Pratica04/code`:

```bash
streamlit run streamlit_app.py --server.port 8501
```

Sem MongoDB, aparece um aviso amarelo na barra lateral e os dados vêm direto da API.

**O `.env` não é lido por padrão.** O `db_utils.py` desta versão não chama `load_dotenv()`, então ela usa `mongodb://localhost:27017`. Para o `.env` funcionar, adicione no topo do `db_utils.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

Alternativa: defina a variável no terminal antes de rodar (`export MONGO_URI="..."`; no PowerShell, `$env:MONGO_URI="..."`).

**Pontos de atenção:**

- **Mock sem aviso:** se o MongoDB e a API falharem, o app exibe pilotos e tempos inventados **sem indicar isso na tela**. Uma lista com só 3 GPs (Austrália, Brasil, Mônaco) indica que o mock está ativo.
- **Cache de voltas parcial:** se o piloto A já está em cache e você seleciona A e B, o cache devolve só as voltas de A, e as de B não são buscadas na API.
- **`session_key` como texto:** esta versão grava e consulta como texto. Se o banco tiver o campo numérico (como na v2), o cache nunca encontra nada e o app sempre cai na API.

### Rodando as duas versões ao mesmo tempo

Use um terminal para cada uma e portas diferentes:

```bash
# Terminal 1
cd Pratica04/code && source venv/Scripts/activate
streamlit run streamlit_app.py --server.port 8501

# Terminal 2
cd Pratica04/code-4/code && source venv/Scripts/activate
streamlit run streamlit_app.py --server.port 8502
```

Abra `http://localhost:8501` (v1) e `http://localhost:8502` (v2). Se as duas usarem o mesmo banco `openf1_data`, a v1 grava documentos em formato diferente nas mesmas coleções que a v2 lê. Use um `MONGO_DB` diferente na v1 (por exemplo, `openf1_cache`) para evitar mistura.

---

## Prática 05: Persistência poliglota (MongoDB e SQLite)

Aplicação Streamlit que usa **dois bancos com papéis diferentes**:

- **MongoDB:** dados brutos e semiestruturados de sessões e voltas.
- **SQLite:** relatórios sumarizados (métricas calculadas) e histórico de análises, via SQLAlchemy.

O fluxo é: consultar as voltas no MongoDB, comparar pilotos em um gráfico, calcular métricas agregadas e gravá-las no SQLite, onde o histórico pode ser consultado depois.

**Configuração** (dentro de `Pratica05`):

```bash
cp .env.example .env
```

| Variável | Padrão | Descrição |
|---|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017/` | Conexão com o MongoDB |
| `MONGODB_DB_NAME` | `openf1_data` | Nome do banco no MongoDB |
| `SQLITE_DB_PATH` | `sqlite:///analysis_reports.db` | URL do SQLite (arquivo criado na pasta onde o app é executado) |

### Populando os bancos (dados fictícios)

```bash
python seed_db.py
```

- **MongoDB:** cria 3 sessões (Monza 2023, Interlagos 2023, Silverstone 2024) e 25 voltas para 4 pilotos em cada uma, com uma volta de pit stop na volta 12.
- **SQLite:** recria a tabela `race_analysis` com 3 relatórios de exemplo.

> ⚠️ O `seed_db.py` **apaga** as coleções `sessions` e `laps` do banco definido em `MONGODB_DB_NAME` e **zera** o histórico do SQLite. Se usar o mesmo banco da Prática 04 (`openf1_data`), os dados reais seriam perdidos. Use um banco separado, como `openf1_pratica05`.

### Executando

Rode de dentro da pasta `Pratica05`:

```bash
streamlit run streamlit_app.py
```

**Aba 1, Análise de Sessão (MongoDB):**

1. Escolha o ano e a sessão.
2. Selecione os pilotos para comparar. O gráfico mostra a duração de cada volta.
3. Clique em **Gerar Resumo da Análise**: o app calcula, por piloto, a volta mais rápida, o tempo médio, o total de voltas e o desvio padrão (consistência, sem contar voltas de saída dos boxes) e grava tudo no SQLite.

**Aba 2, Histórico de Análises (SQLite):** mostra os relatórios gravados na tabela `race_analysis`, com métricas de resumo (total de análises, sessões distintas e pilotos processados).

### Estrutura dos dados

**MongoDB:**

| Coleção | Campos principais |
|---|---|
| `sessions` | `session_key`, `year`, `session_name`, `location`, `country_name`, `circuit_short_name`, `date_start` |
| `laps` | `session_key`, `driver_number`, `driver_name`, `lap_number`, `lap_duration`, `is_pit_out_lap`, `sector_1`, `sector_2`, `sector_3` |

**SQLite** (tabela `race_analysis`):

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | Integer (PK) | Identificador |
| `session_name` | String | Rótulo da sessão analisada |
| `driver_name` | String | Piloto (número ou nome) |
| `fastest_lap` | Float | Menor tempo de volta (s) |
| `average_lap_time` | Float | Tempo médio de volta (s) |
| `total_laps` | Integer | Total de voltas |
| `consistency_std_dev` | Float | Desvio padrão dos tempos (s) |
| `analysis_timestamp` | DateTime | Data e hora da análise |

### Recuperação do SQLite (`recuperar.py`)

Utilitário independente, usado só se o arquivo SQLite corromper:

```bash
python recuperar.py analysis_reports.db
```

Ele executa `PRAGMA integrity_check`. Se o banco estiver íntegro, nada acontece. Se não, gera um `backup.sql` e recria os dados em `banco_recuperado.db`. Esses arquivos ficam no `.gitignore`.

---

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| "Não foi possível conectar ao MongoDB" / "Erro ao conectar ao MongoDB" | Variável de conexão ausente ou com nome errado, ou MongoDB desligado. O motivo exato aparece no terminal. |
| `Port contains non-digit characters` | Senha com caracteres especiais sem codificar na URI. |
| "Nenhuma sessão de corrida encontrada" / "Nenhum dado de ano encontrado" | Banco sem dados. Na Prática 04 rode `ingest_openf1.py`; na 05, `seed_db.py`. |
| "Nenhum piloto encontrado" / "Não foram encontrados dados de voltas" (Prática 04) | Corrida sem pilotos ou voltas no banco. Rode `ingest_openf1.py`. |
| Mudei o `.env` e nada mudou | O `.env` só é lido na inicialização, ou o nome da variável está errado. Reinicie o Streamlit. |
| Lista com só 3 GPs (Austrália, Brasil, Mônaco) na v1 | O mock está ativo: sem internet ou API fora do ar. |
| Histórico do SQLite vazio depois de rodar o seed de novo | O `seed_db.py` recria a tabela e zera o histórico. |
| Dois `analysis_reports.db` diferentes | O SQLite é criado na pasta onde o comando foi executado. Rode sempre de dentro da pasta da prática. |
| `venv\Scripts\activate: command not found` | No Git Bash use `source venv/Scripts/activate`. |
| Não consigo digitar no terminal | O Streamlit ocupa o terminal. Use `Ctrl+C` para parar ou abra outro terminal. |