# ingest_openf1.py
"""
Popula o MongoDB (banco 'openf1_data') com sessões, pilotos e voltas
da API OpenF1, no formato que o streamlit_app.py da v2 espera.

Uso (com o venv ativo, dentro da pasta da v2):
    python ingest_openf1.py              # anos 2023 e 2024
    python ingest_openf1.py 2024         # só 2024
    python ingest_openf1.py 2023 2024

- Lê MONGO_URI do arquivo .env
- Pode ser interrompido (Ctrl+C) e rodado de novo: ele pula o que já foi baixado.
- Usa upsert, então não cria documentos duplicados.
- Respeita o limite de requisições da API (pausa entre chamadas).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv()

API_URL = os.getenv("OPENF1_API_URL", "https://api.openf1.org/v1")
DB_NAME = "openf1_data"
PAUSE_SECONDS = 2.5      # a API gratuita limita a ~30 requisições por minuto
MAX_RETRIES = 6


def fetch(endpoint, params):
    """Consulta a API OpenF1 com pausa e novas tentativas em caso de limite (429)."""
    url = f"{API_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
    for attempt in range(1, MAX_RETRIES + 1):
        time.sleep(PAUSE_SECONDS)
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:          # OpenF1 responde 404 quando não há resultados
                return []
            if e.code == 429:
                wait = 10 * attempt
                print(f"   limite de requisições atingido, aguardando {wait}s...")
                time.sleep(wait)
                continue
            print(f"   erro HTTP {e.code} em {endpoint}: {e.reason}")
            return None
        except Exception as e:
            print(f"   erro em {endpoint} (tentativa {attempt}): {e}")
            time.sleep(5)
    return None


def bulk_upsert(collection, docs, key_fields):
    if not docs:
        return 0
    ops = [
        UpdateOne({k: d[k] for k in key_fields}, {"$set": d}, upsert=True)
        for d in docs
    ]
    collection.bulk_write(ops, ordered=False)
    return len(ops)


def ingest_year(db, year):
    print(f"\n=== {year} ===")

    # 1. Sessões do ano (todas: treinos, classificação, sprint e corrida)
    sessions = fetch("sessions", {"year": year})
    if not sessions:
        print("Nenhuma sessão retornada pela API. Pulando este ano.")
        return
    docs = []
    for s in sessions:
        docs.append({
            "session_key": int(s["session_key"]),
            "meeting_key": s.get("meeting_key"),
            "circuit_key": s.get("circuit_key"),
            "circuit_short_name": s.get("circuit_short_name"),
            "country_code": s.get("country_code"),
            "country_key": s.get("country_key"),
            "country_name": s.get("country_name"),
            "location": s.get("location"),
            "date_start": s.get("date_start"),
            "date_end": s.get("date_end"),
            "gmt_offset": s.get("gmt_offset"),
            "is_cancelled": s.get("is_cancelled", False),
            "session_name": s.get("session_name"),
            "session_type": s.get("session_type"),
            "year": int(s.get("year", year)),
        })
    bulk_upsert(db.sessions, docs, ["session_key"])
    races = [d for d in docs if d["session_name"] == "Race" and not d["is_cancelled"]]
    print(f"{len(docs)} sessões salvas, {len(races)} corridas.")

    # 2. Pilotos e voltas de cada corrida
    for i, race in enumerate(races, start=1):
        sk = race["session_key"]
        label = f"{race.get('country_name')} - {race.get('location')}"
        print(f"[{i}/{len(races)}] {label} (session_key={sk})")

        # Pilotos
        if db.drivers.count_documents({"session_key": sk}) == 0:
            drivers = fetch("drivers", {"session_key": sk})
            if drivers is None:
                print("   falha ao buscar pilotos, pulando corrida.")
                continue
            ddocs = [{
                "session_key": sk,
                "driver_number": d["driver_number"],
                "full_name": d.get("full_name") or d.get("broadcast_name"),
                "team_name": d.get("team_name"),
                "name_acronym": d.get("name_acronym"),
            } for d in drivers]
            n = bulk_upsert(db.drivers, ddocs, ["session_key", "driver_number"])
            print(f"   {n} pilotos salvos.")
        else:
            print("   pilotos já existem, pulando.")

        # Voltas (uma única requisição por corrida)
        if db.laps.count_documents({"session_key": sk}) == 0:
            laps = fetch("laps", {"session_key": sk})
            if laps is None:
                print("   falha ao buscar voltas, pulando corrida.")
                continue
            ldocs = [{
                "session_key": sk,
                "driver_number": l["driver_number"],
                "lap_number": l["lap_number"],
                "lap_duration": l.get("lap_duration"),
                "is_pit_out_lap": l.get("is_pit_out_lap"),
                "date_start": l.get("date_start"),
            } for l in laps]
            n = bulk_upsert(db.laps, ldocs, ["session_key", "driver_number", "lap_number"])
            print(f"   {n} voltas salvas.")
        else:
            print("   voltas já existem, pulando.")


def main():
    uri = os.getenv("MONGO_URI")
    if not uri:
        sys.exit("MONGO_URI não encontrada. Rode este script na pasta que contém o .env.")

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]
    print(f"Conectado ao MongoDB. Banco: {DB_NAME}")

    # Índices para as consultas ficarem rápidas
    db.sessions.create_index("session_key")
    db.sessions.create_index([("year", 1), ("session_name", 1)])
    db.drivers.create_index([("session_key", 1), ("driver_number", 1)])
    db.laps.create_index([("session_key", 1), ("driver_number", 1), ("lap_number", 1)])

    years = [int(a) for a in sys.argv[1:]] or [2023, 2024]
    for year in years:
        ingest_year(db, year)

    print("\nConcluído.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido. Rode de novo para continuar de onde parou.")