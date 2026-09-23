# db_utils.py
import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()


def get_mongo_db():
    """
    Estabelece conexão com o MongoDB usando a URI do arquivo .env
    e retorna o objeto do banco de dados 'openf1_data'.
    """
    try:
        MONGO_URI = os.getenv("MONGO_URI")
        if not MONGO_URI:
            raise ValueError("A variável de ambiente MONGO_URI não foi definida.")

        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        # Testa a conexão para garantir que está funcionando
        client.admin.command('ping')
        print("Conexão com MongoDB bem-sucedida.")

        db = client['openf1_data']
        return db
    except Exception as e:
        print(f"Erro ao conectar com o MongoDB: {e}")
        return None


def get_race_sessions(db, year):
    """
    Busca no banco de dados todas as corridas principais ('Race') de um ano.

    Os documentos seguem o formato cru da API OpenF1 (sem 'display_name'),
    então o nome de exibição é montado aqui a partir de country_name e location.
    Sprints ficam de fora, pois têm session_name 'Sprint'.

    Args:
        db: Objeto de conexão com o banco de dados MongoDB.
        year (int): O ano para filtrar as sessões.

    Returns:
        list: Lista de dicionários com session_key e display_name.
    """
    query = {"session_name": "Race", "year": int(year)}
    projection = {
        "session_key": 1,
        "country_name": 1,
        "location": 1,
        "date_start": 1,
        "_id": 0,
    }
    sessions = list(db.sessions.find(query, projection).sort("date_start", 1))

    for s in sessions:
        country = s.get("country_name") or "GP"
        location = s.get("location") or ""
        s["display_name"] = f"{country} - {location}" if location else country

    return sessions


def get_session_details(db, session_key):
    """
    Busca os detalhes de uma sessão específica.

    Args:
        db: Objeto de conexão com o banco de dados MongoDB.
        session_key (int): A chave única da sessão.

    Returns:
        dict: Um dicionário com os detalhes da sessão.
    """
    return db.sessions.find_one({"session_key": session_key}, {"_id": 0})


def get_drivers_from_session(db, session_key):
    """
    Busca todos os pilotos que participaram de uma sessão específica.

    Args:
        db: Objeto de conexão com o banco de dados MongoDB.
        session_key (int): A chave única da sessão.

    Returns:
        list: Uma lista de dicionários, cada um representando um piloto.
    """
    query = {"session_key": session_key}
    projection = {"full_name": 1, "driver_number": 1, "team_name": 1, "_id": 0}
    # Ordena por nome completo para melhor visualização
    return list(db.drivers.find(query, projection).sort("full_name", 1))


def get_laps_for_drivers(db, session_key, driver_numbers):
    """
    Busca os dados de todas as voltas para uma lista de pilotos em uma sessão.

    Args:
        db: Objeto de conexão com o banco de dados MongoDB.
        session_key (int): A chave única da sessão.
        driver_numbers (list): Uma lista de números de pilotos.

    Returns:
        pd.DataFrame: Um DataFrame do Pandas com os dados das voltas.
    """
    query = {
        "session_key": session_key,
        "driver_number": {"$in": driver_numbers}
    }

    # Busca apenas os campos relevantes
    projection = {
        "driver_number": 1,
        "lap_number": 1,
        "lap_duration": 1,
        "_id": 0
    }

    laps_data = list(db.laps.find(query, projection))

    if not laps_data:
        return pd.DataFrame()

    return pd.DataFrame(laps_data)