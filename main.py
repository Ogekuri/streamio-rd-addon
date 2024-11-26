import asyncio
import logging
import os
import re
import shutil
import time
import zipfile

import requests
import starlette.status as status
from aiocron import crontab
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse

from debrid.get_debrid_service import get_debrid_service
from search.search_result import SearchResult
from search.search_service import SearchService
from metdata.cinemeta import Cinemeta
from metdata.tmdb import TMDB
from torrent.torrent_service import TorrentService
from torrent.torrent_smart_container import TorrentSmartContainer
from utils.cache import search_cache
from utils.filter_results import filter_items
from utils.filter_results import sort_items
from utils.logger import setup_logger
from utils.parse_config import parse_config
from utils.stremio_parser import parse_to_stremio_streams
from utils.string_encoding import decodeb64

from constants import ADDON_NAME, ADDON_SHORT, ADDON_VERSION

load_dotenv()

root_path = os.environ.get("ROOT_PATH", None)
if root_path and not root_path.startswith("/"):
    root_path = "/" + root_path

app = FastAPI(root_path=root_path)

VERSION = ADDON_VERSION

environment = os.getenv("NODE_ENV", "DEVELOPMENT")

# class LogFilterMiddleware:
#     def __init__(self, app):
#         self.app = app

#     async def __call__(self, scope, receive, send):
#         print("Scope:", scope)
#         print("Receive:", receive)
#         request = Request(scope, receive)
#         path = request.url.path
#         sensible_path = re.sub(r'/ey.*?/', '/<SENSITIVE_DATA>/', path)
#         logger.info(f"{request.method} - {sensible_path}")
#         return await self.app(scope, receive, send)
# if not isDev:
#     app.add_middleware(LogFilterMiddleware)


# abilita CORSMiddleware per le chiamate OPTIONS e il redirect
# probailmente posso filtrare meglio
# Configura le origini consentite
# origins = [
#     "https://web.stremio.com",  # Specifica l'origine consentita
#     "http://localhost",        # Durante lo sviluppo
#     "http://localhost:8000",   # Durante lo sviluppo
# ]

# # Aggiungi il middleware CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,  # Origini consentite
#     allow_credentials=True, # Consente l'invio di credenziali (es. cookie)
#     allow_methods=["*"],    # Consente tutti i metodi (GET, POST, OPTIONS, ecc.)
#     allow_headers=["*"],    # Consente tutti gli header
# )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


templates = Jinja2Templates(directory="templates")

logger = setup_logger(__name__)

@app.get("/")
async def root():
    return RedirectResponse(url="/configure")


@app.get("/configure")
@app.get("/{config}/configure")
async def configure(request: Request):
    print(request.headers.get("X-Real-IP"))
    print(request.headers.get("X-Forwarded-For"))
    return templates.TemplateResponse(
        "index.html",
        {"request": request },
    )


@app.get("/favicon.ico")
async def get_favicon():
    response = FileResponse(f"templates/images/favicon.ico")
    return response

@app.get("/static/{file_path:path}")
async def function(file_path: str):
    response = FileResponse(f"templates/{file_path}")
    return response


@app.get("/manifest.json")
@app.get("/{params}/manifest.json")
async def get_manifest():
    return {
        "id": "com.stremio.rd.addon",
        "background": "/static/images/background.jpg",
        "logo": "/static/images/logo.png",
        "version": VERSION,
        "catalogs": [],
        "resources": ["stream"],
        "types": ["movie", "series"],
        "name": "StremioRDAddon",
        "description": "Stremio RD Addon",
        "behaviorHints": {
            "configurable": True,
            "configurationRequired": False,
        }
    }


formatter = logging.Formatter('[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                              '%m-%d %H:%M:%S')

logger.info(f"Started {ADDON_NAME} ({environment})")

@app.get("/{config}/stream/{stream_type}/{stream_id}")
async def get_results(config: str, stream_type: str, stream_id: str, request: Request):
    start = time.time()
    stream_id = stream_id.replace(".json", "")

    config = parse_config(config)
    logger.debug(stream_type + " request")

    logger.debug(f"Getting media from {config['metadataProvider']}")
    if config['metadataProvider'] == "tmdb" and config['tmdbApi']:
        metadata_provider = TMDB(config)
    else:
        metadata_provider = Cinemeta(config)
    media = metadata_provider.get_metadata(stream_id, stream_type)
    logger.info("Got media and properties: " + str(media.titles))

    debrid_service = get_debrid_service(config)

    search_results = []
    if config['cache']:
        logger.debug("Getting cached results")
        cached_results = search_cache(config, media)
        if cached_results is not None and len(cached_results) > 0:
            cached_results = [SearchResult().from_cached_item(torrent, media) for torrent in cached_results]
            logger.debug("Got " + str(len(cached_results)) + " cached results")

            if len(cached_results) > 0:
                logger.debug("Filtering cached results")
                search_results = filter_items(cached_results, media, config=config)
                logger.debug("Filtered cached results")

    # se la cache non ritorna abbastanza risultati
    if config['search'] and len(search_results) < int(config['minCacheResults']):
        if len(search_results) > 0 and config['cache']:
            logger.debug("Not enough cached results found (results: " + str(len(search_results)) + ")")
        elif config['cache']:
            logger.debug("No cached results found")

        logger.debug("Searching for results direct with Torrent Search (Engines)")
        search_service = SearchService(config)
        engine_results = search_service.search(media)
        if engine_results is not None:
            logger.debug("Got " + str(len(engine_results)) + " results from Torrent Search (Engines)")

            logger.debug("Filtering Torrent Search (Engines) results")
            filtered_engine_search_results = filter_items(engine_results, media, config=config)
            logger.debug("Filtered Torrent Search (Engines) results")

            search_results.extend(filtered_engine_search_results)

    if search_results is not None:
        logger.debug("Converting result to TorrentItems (results: " + str(len(search_results)) + ")")
        torrent_service = TorrentService()
        torrent_results = torrent_service.convert_and_process(search_results)
        logger.debug("Converted result to TorrentItems (results: " + str(len(torrent_results)) + ")")

        torrent_smart_container = TorrentSmartContainer(config, torrent_results, media)

        if config['debrid']:
            logger.debug("Checking availability")
            hashes = torrent_smart_container.get_hashes()
            ip = request.client.host
            result = debrid_service.get_availability_bulk(hashes, ip)
            if result is not None:
                torrent_smart_container.update_availability(result, type(debrid_service))
                logger.debug("Checked availability (results: " + str(len(result.items())) + ")")
            else:
                logger.error("Unable to checked availability")


        # TODO: Maybe add an if to only save to cache if caching is enabled?
        torrent_smart_container.cache_container_items()

        logger.debug("Getting best matching results")
        best_matching_results = torrent_smart_container.get_best_matching()
        best_matching_results = sort_items(best_matching_results, config)
        logger.debug("Got best matching results (results: " + str(len(best_matching_results)) + ")")

        logger.debug("Processing results")
        stream_list = parse_to_stremio_streams(best_matching_results, config)
        logger.info("Processed results (results: " + str(len(stream_list)) + ")")

        logger.info("Total time: " + str(time.time() - start) + "s")

        return {"streams": stream_list}


@app.get("/playback/{config}/{query}")
async def get_playback(config: str, query: str, request: Request):
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Query required.")
        config = parse_config(config)
        logger.info("Decoding query")
        query = decodeb64(query)
        logger.info(query)
        logger.info("Decoded query")
        ip = request.client.host
        debrid_service = get_debrid_service(config)
        link = debrid_service.get_stream_link(query, ip)

        logger.info("Got link: " + link)
        return RedirectResponse(url=link, status_code=status.HTTP_301_MOVED_PERMANENTLY)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

@app.head("/playback/{config}/{query}")
async def get_playback(config: str, query: str, request: Request):
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Query required.")
        config = parse_config(config)
        logger.info("Decoding query")
        query = decodeb64(query)
        logger.info(query)
        logger.info("Decoded query")
        ip = request.client.host
        debrid_service = get_debrid_service(config)
        link = debrid_service.get_stream_link(query, ip)

        logger.info("Got link: " + link)
        return RedirectResponse(url=link, status_code=status.HTTP_301_MOVED_PERMANENTLY)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")


async def update_app():
    try:
        current_version = "v" + VERSION
        url = "https://api.github.com/repos/Ogekuri/streamio-rd-addon/releases/latest"
        response = requests.get(url)
        data = response.json()
        latest_version = data['tag_name']
        if latest_version != current_version:
            logger.info("New version available: " + latest_version)
            logger.info("Updating...")
            logger.info("Getting update zip...")
            update_zip = requests.get(data['zipball_url'])
            with open("update.zip", "wb") as file:
                file.write(update_zip.content)
            logger.info("Update zip downloaded")
            logger.info("Extracting update...")
            with zipfile.ZipFile("update.zip", 'r') as zip_ref:
                zip_ref.extractall("update")
            logger.info("Update extracted")

            extracted_folder = os.listdir("update")[0]
            extracted_folder_path = os.path.join("update", extracted_folder)
            for item in os.listdir(extracted_folder_path):
                s = os.path.join(extracted_folder_path, item)
                d = os.path.join(".", item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            logger.info("Files copied")

            logger.info("Cleaning up...")
            shutil.rmtree("update")
            os.remove("update.zip")
            logger.info("Cleaned up")
            logger.info("Updated !")
    except Exception as e:
        logger.error(f"Error during update: {e}")

# gestione dell'auto-update
# @crontab("* * * * *", start=not isDev)
# async def schedule_task():
#     await update_app()


async def main():
#     await asyncio.gather(
#         schedule_task()
#     )
    return


if __name__ == "__main__":
    asyncio.run(main())
