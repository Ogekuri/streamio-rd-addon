from typing import List
import sqlite3
import os
from constants import CACHE_DATABASE_FILE
from torrent.torrent_item import TorrentItem
from utils.logger import setup_logger
from datetime import datetime

TABLE_NAME = "cached_items"

TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cached_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP,
    title TEXT,
    torrent_title TEXT,
    trackers TEXT,
    magnet TEXT,
    files TEXT,
    hash TEXT,
    indexer TEXT,
    engine_name TEXT,
    quality TEXT,
    qualitySpec TEXT,
    seeders INTEGER,
    size INTEGER,
    language TEXT,
    type TEXT,
    availability TEXT,
    year INTEGER,
    season INTEGER,
    episode INTEGER,
    seasonfile BOOLEAN
)
"""

logger = setup_logger(__name__)

def search_cache(config, media):
    
    if os.path.exists(CACHE_DATABASE_FILE):
        try:
            connection = sqlite3.connect(CACHE_DATABASE_FILE)
            cursor = connection.cursor()
            # Verifica se la tabella esiste
            cursor.execute(f"""SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}';""")
        except sqlite3.Error as e:
                    logger.error(f"SQL error: {e}")
                    return None
        if cursor.fetchone() is not None:
            logger.debug("Delete expired records")
            try:
                days = config['daysCacheValid']
                cursor.execute(f"""DELETE FROM '{TABLE_NAME}' WHERE created_at < datetime('now', '-{days} days');""")
                connection.commit()
            except sqlite3.Error as e:
                logger.error(f"SQL error: {e}")
                pass

            logger.debug("Searching for cached " + media.type + " results")

            cache_items = []

            # cicla sulle lingue
            for index, language in enumerate(media.languages):

                title = media.titles[index]
                logger.info("Searchching for " + media.type + " '" + title + "' @<cache>")

                cache_search = media.__dict__
                cache_search['title'] = title
                cache_search['language'] = language

                if media.type == "movie":
                    cache_search['year'] = media.year
                elif media.type == "series":
                    cache_search['season'] = media.season
                    cache_search['episode'] = media.episode
                    cache_search['seasonfile'] = False  # I guess keep it false to not mess up results?
                
                try:
                    # Costruisci la query di filtro in base a `cache_search`
                    filters = ["title = :title", "language = :language"]
                    if media.type == "movie":
                        filters.append("year = :year")
                    elif media.type == "series":
                        filters.extend(["season = :season", "episode = :episode", "seasonfile = :seasonfile"])

                    # Genera la query dinamica
                    query = f"SELECT * FROM {TABLE_NAME} WHERE " + " AND ".join(filters)

                    # Esegui la query con i parametri
                    cursor.execute(query, cache_search)
                    rows = cursor.fetchall()

                    # Recupera i nomi delle colonne
                    cursor.execute(f"PRAGMA table_info({TABLE_NAME});")
                    columns = [info[1] for info in cursor.fetchall()]

                    # Trasforma ogni riga in un dizionario
                    for row in rows:
                        cache_item = dict(zip(columns, row))
                        cache_item['trackers'] = cache_item['trackers'].split(";") if cache_item['trackers'] else []
                        cache_item['qualitySpec'] = cache_item['qualitySpec'].split(";") if cache_item['qualitySpec'] else []
                        cache_items.append(cache_item)

                    logger.debug(f"{len(cache_items)} record found on cache database table:'{TABLE_NAME}'.")
                except sqlite3.Error as e:
                    logger.error(f"SQL error: {e}")
                    pass
            
            if cache_items is not None and len(cache_items) > 0:
                return cache_items
            else:
                return None
    return None


def cache_results(config, torrents: List[TorrentItem], media):

    if torrents is not None and len(torrents) > 0:

        # Verifica se il file esiste (opzionale, SQLite lo crea comunque)
        db_exists = os.path.exists(CACHE_DATABASE_FILE)

        # Connetti al database (crea il file se non esiste)
        connection = sqlite3.connect(CACHE_DATABASE_FILE)
        cursor = connection.cursor()

        if not db_exists:
            logger.info("Database crated: " + CACHE_DATABASE_FILE + " .")

        # Verifica se la tabella esiste, altrimenti la crea
        cursor.execute(f"""SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}';""")
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            cursor.execute(TABLE_SCHEMA)
            connection.commit()
            logger.info("Table crated: " + TABLE_NAME + " .")

        logger.debug("Started caching results")

        # crea dizionario dei titoli
        titles = dict(zip(media.languages, media.titles))

        # elenco delle entry da aggiungere
        cache_items = []

        for torrent in torrents:
            hash_already_exist = False
            try:
                # Esegui una query per verificare l'esistenza dell'hash
                cursor.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE hash = ? LIMIT 1;", (torrent.info_hash,))
                result = cursor.fetchone()

                # Restituisci True se il risultato non è None
                if result is not None:
                    hash_already_exist = True
            except sqlite3.Error as e:
                    logger.error(f"SQL error: {e}")
                    pass
            
            if not hash_already_exist:
                try:
                    # cicla sulle lingue
                    for language in torrent.languages:
                        if language in media.languages:
                            title = titles[language]
                        else:
                            title = media.titles[0]

                        cache_item = dict()

                        cache_item['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cache_item['title'] = title
                        cache_item['torrent_title'] = torrent.title
                        cache_item['trackers'] = ";".join(torrent.trackers)
                        cache_item['magnet'] = torrent.magnet
                        cache_item['files'] = ""  # I guess keep it empty?
                        cache_item['hash'] = torrent.info_hash
                        cache_item['indexer'] = torrent.indexer
                        cache_item['engine_name'] = torrent.engine_name
                        cache_item['quality'] = torrent.quality
                        cache_item['qualitySpec'] = ";".join(torrent.quality_spec)
                        cache_item['seeders'] = torrent.seeders
                        cache_item['size'] = torrent.size
                        cache_item['language'] = language
                        cache_item['type'] = media.type
                        cache_item['availability'] = torrent.availability

                        if media.type == "movie":
                            cache_item['year'] = media.year
                        elif media.type == "series":
                            cache_item['season'] = media.season
                            cache_item['episode'] = media.episode
                            cache_item['seasonfile'] = False  # I guess keep it false to not mess up results?

                        cache_items.append(cache_item)
                except:
                    logger.exception("An exception occured durring cache parsing")
                    pass
        
        # Estrai dinamicamente le colonne dalla lista di dizionari
        if cache_items is not None and len(cache_items) > 0:
            columns = cache_items[0].keys()
            placeholders = ", ".join([":" + col for col in columns])  # Placeholder per ogni colonna

            for data in cache_items:
                try:
                    cursor.execute(f"""INSERT INTO {TABLE_NAME} ({", ".join(columns)}) VALUES ({placeholders}) """, data)
                    connection.commit()
                except sqlite3.Error as e:
                    logger.error(f"SQL error: {e}")
                    pass
            
            logger.info(f"Cached {str(len(cache_items))} {media.type} results")

        if connection:
            connection.close()
