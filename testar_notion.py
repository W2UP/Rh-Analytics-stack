import truststore
truststore.inject_into_ssl()

from rh.sync import fetch_database
from rh.core import DB_COLABORADORES

if __name__ == "__main__":
    dados = fetch_database(DB_COLABORADORES)
    print(f"Conexão verificada: {len(dados)} registros recebidos.")
