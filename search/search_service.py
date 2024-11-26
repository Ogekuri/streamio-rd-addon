import sys
# serve per helpers.py e novaprinter.py che voglio tenere in quel percorso
sys.path.append("search/plugins/")

import os
import queue
import threading
import time
import xml.etree.ElementTree as ET

import requests

from search.search_indexer import SearchIndexer
from search.search_result import SearchResult
from models.movie import Movie
from models.series import Series
from utils import detection
from utils.logger import setup_logger

from search.plugins.thepiratebay_categories import thepiratebay
from search.plugins.one337x import one337x
from search.plugins.ilcorsaronero import ilcorsaronero

from urllib.parse import quote_plus
import io
from contextlib import redirect_stdout
import json
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# define if it's run in multi-thread - False for debug
MULTI_THREAD = True

class SearchService:
    def __init__(self, config):
        self.logger = setup_logger(__name__)

        self.__search = config['search']
        self.__engines = config['engines']
        self.__session = requests.Session()
        self.__language_tags = {
            'en':'ENG', 
            'fr':'FRA', 
            'es':'ESP', 
            'de':'GER', 
            'it':'ITA', 
            'pt':'POR', 
            'ru':'RUS', 
            'in':'INDIAN', 
            'nl':'NLD', 
            'hu':'HUN', 
            'la':'LATIN', 
            'multi':'MULTI',
            }


    def search(self, media):
        self.logger.debug("Started Search search for " + media.type + " " + media.titles[0])

        indexers = self.__get_indexers()
        for indexer in indexers:
            self.logger.info("Searchching for " + media.type + " '" + media.titles[0] + "' @" + indexer.engine_name)

        threads = []
        results_queue = queue.Queue()  # Create a Queue instance to hold the results

        if MULTI_THREAD:
            if isinstance(media, Movie):
                with ThreadPoolExecutor() as executor:
                    futures = [executor.submit(self.__search_movie_indexer, media, indexer) for indexer in indexers]
                    for future in futures:
                        results_queue.put(future.result())  # Raccoglie il risultato
            elif isinstance(media, Series):
                with ThreadPoolExecutor() as executor:
                    futures = [executor.submit(self.__search_series_indexer, media, indexer) for indexer in indexers]
                    for future in futures:
                        results_queue.put(future.result())  # Raccoglie il risultato
        else:
            if isinstance(media, Movie):
                for indexer in indexers:
                    result = self.__search_movie_indexer(media, indexer)
                    results_queue.put(result)  # Put the result in the queue
            elif isinstance(media, Series):
                for indexer in indexers:
                    result = self.__search_series_indexer(media, indexer)
                    results_queue.put(result)  # Put the result in the queue

        # Retrieve results from the queue and append them to the results list
        results = []
        while not results_queue.empty():
            results.extend(results_queue.get())
        flatten_results = [result for sublist in results for result in sublist]
        
        del threads, results_queue, results

        if flatten_results is not None and len(flatten_results) > 0:
            # post process results ############################################à
            results = []

            threads = []
            results_queue = queue.Queue()  # Create a Queue instance to hold the results

            if MULTI_THREAD:
                # Define a wrapper function that calls the actual target function and stores its return value in the queue
                def thread_target(result, media):
                    # Call the actual function
                    res = self.__post_process_result(result, media)
                    results_queue.put(res)  # Put the result in the queue

                for result in flatten_results:
                    # Pass the wrapper function as the target to Thread, with necessary arguments
                    threads.append(threading.Thread(target=thread_target, args=(result, media)))

                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()
            else:
                for result in flatten_results:
                    res = self.__post_process_result(result, media)
                    results_queue.put(res)  # Put the result in the queue

            # Retrieve results from the queue and append them to the results list
            while not results_queue.empty():
                results.append(results_queue.get())
        else:
            results = None

        return results


    def __get_engine(self, engine_name):
        if engine_name == 'thepiratebay':
            return thepiratebay()
        elif engine_name == 'one337x':
            return one337x()
        elif engine_name == 'ilcorsaronero':
            return ilcorsaronero()
        else:
            raise ValueError(f"Torrent Search '{engine_name}' not supported")


    def __get_engine_language(self, engine_name):
            if engine_name == 'thepiratebay':
                return "any"
            elif engine_name == 'one337x':
                return "any"
            elif engine_name == 'ilcorsaronero':
                return "it"
            else:
                raise ValueError(f"Torrent Search '{engine_name}' not supported")
    

    def __search_movie_indexer(self, movie, indexer):
        # get titles and languages
        if indexer.language == "any":
            languages = movie.languages
            titles = movie.titles
        else:
            index_of_language = [index for index, lang in enumerate(movie.languages) if lang == indexer.language]
            languages = [movie.languages[index] for index in index_of_language]
            titles = [movie.titles[index] for index in index_of_language]

        results = []

        for index, lang in enumerate(languages):
            lang_tag = self.__language_tags[languages[index]]
            search_string = str(titles[index] + ' ' + movie.year  + ' ' +  lang_tag)
            search_string = quote_plus(search_string)
            category = str(indexer.movie_search_capatabilities)

            try:
                start_time = time.time()
                list_of_dicts = indexer.engine.search(search_string, category)
                if list_of_dicts is not None and len(list_of_dicts) > 0:
                    result = self.__get_torrents_from_list_of_dicts(movie, indexer, list_of_dicts)
                    if result is not None:
                        results.append(result)
                self.logger.debug(f"Searching {search_string} @ {indexer.engine_name}/{category} in {round(time.time() - start_time, 1)} [s]")
            except Exception:
                self.logger.exception(
                    f"An exception occured while searching for a movie on Search with indexer {indexer.title} and "
                    f"language {lang}.")

        return results
    

    def __search_series_indexer(self, series, indexer):
        # get titles and languages
        if indexer.language == "any":
            languages = series.languages
            titles = series.titles
        else:
            index_of_language = [index for index, lang in enumerate(series.languages) if lang == indexer.language]
            languages = [series.languages[index] for index in index_of_language]
            titles = [series.titles[index] for index in index_of_language]

        results = []

        for index, lang in enumerate(languages):
            lang_tag = self.__language_tags[languages[index]]
            # season = str(int(series.season.replace('S', '')))
            # episode = str(int(series.episode.replace('E', '')))
            search_string = str(titles[index] + ' ' + series.season + series.episode + ' ' + lang_tag)
            search_string = quote_plus(search_string)
            category = str(indexer.tv_search_capatabilities)

            try:
                start_time = time.time()
                list_of_dicts = indexer.engine.search(search_string, category)
                if list_of_dicts is not None and len(list_of_dicts) > 0:
                    result = self.__get_torrents_from_list_of_dicts(series, indexer, list_of_dicts)
                    if result is not None:
                        results.append(result)
                self.logger.debug(f"Searching {search_string} @ {indexer.engine_name}/{category} in {round(time.time() - start_time, 1)} [s]")
            except Exception:
                self.logger.exception(
                    f"An exception occured while searching for a series on Search with indexer {indexer.title} and language {lang}.")

        return results


    def __get_indexers(self):
        try:
            indexer_list = self.__get_indexer_from_engines(self.__engines)
            return indexer_list
        except Exception:
            self.logger.exception("An exception occured while getting indexers from Search.")
            return []


    def __get_indexer_from_engines(self, engines):

        indexer_list = []
        id = 0
        for engine_name in engines:
            indexer = SearchIndexer()

            indexer.engine = self.__get_engine(engine_name)
            indexer.language = self.__get_engine_language(engine_name)

            indexer.title = indexer.engine.name
            indexer.id = id
            indexer.engine_name = engine_name

            supported_categories = indexer.engine.supported_categories
            if ('movies' in supported_categories) and (supported_categories['movies'] is not None):
                indexer.movie_search_capatabilities = 'movies'
            else:
                if ('all' in supported_categories) and (supported_categories['all'] is not None):
                    indexer.movie_search_capatabilities = 'all'
                else:
                    self.logger.info(f"Movie search not available for {indexer.title}")

            if ('tv' in supported_categories) and (supported_categories['tv'] is not None):
                indexer.tv_search_capatabilities = 'tv'
            else:
                if ('all' in supported_categories) and (supported_categories['all'] is not None):
                    indexer.movie_search_capatabilities = 'all'
                else:
                    self.logger.info(f"TV search not available for {indexer.title}")

            indexer_list.append(indexer)
            
            self.logger.debug(f"Indexer: {indexer.id} - {indexer.engine_name} - {indexer.title} - {indexer.language} - {indexer.movie_search_capatabilities} - {indexer.tv_search_capatabilities}")

            id += 1

        return indexer_list


    def __get_torrents_from_list_of_dicts(self, media, indexer, list_of_dicts):

        result_list = []
        
        for item in list_of_dicts:
            result = SearchResult()

            result.seeders = item['seeds']
            if int(result.seeders) <= 0:
                continue

            result.title = item['name']
            result.size = item['size']
            result.indexer = indexer.title              # engine name 'Il Corsaro Nero' 
            result.engine_name = indexer.engine_name    # engine type 'ilcorsaronero'
            result.type = media.type                    # series or movie
            result.privacy = 'public'                   # public or private (determina se sarà o meno salvato in cache)

            result.magnet = None        # processed on __post_process_results after getting pages
            result.link = item['link']  # shoud be content the link of magnet or .torrent file 
                                        # but NOW contain the web page or magnet, will be __post_process_results
            result.info_hash = None     # processed on __post_process_results after getting pages

            result_list.append(result)

        return result_list


    def __is_magnet_link(self, link):
        # Check if link inizia con "magnet:?"
        return link.startswith("magnet:?")


    def __extract_info_hash(self, magnet_link):
        # parse
        parsed = urlparse(magnet_link)
        
        # extract 'xt'
        params = parse_qs(parsed.query)
        xt = params.get("xt", [None])[0]
        
        if xt and xt.startswith("urn:btih:"):
            # remove prefix "urn:btih:"
            info_hash = xt.split("urn:btih:")[1]
            return info_hash
        else:
            raise ValueError("Magnet link invalid")


    def __post_process_result(self, result, media):
        if self.__is_magnet_link(result.link):
            result.magnet = result.link
        else:
            start_time = time.time()
            engine = self.__get_engine(result.engine_name)
            res_link = engine.download_torrent(result.link)
            if res_link is not None and self.__is_magnet_link(res_link):
                result.magnet = res_link
                result.link = result.magnet
            else:
                raise Exception('Error, please fill a bug report!')
            self.logger.debug(f"Download magnet of result {result.title} @ {result.engine_name} in {round(time.time() - start_time, 1)} [s]")

        result.languages = detection.detect_languages(result.title)
        result.quality = detection.detect_quality(result.title)
        result.quality_spec = detection.detect_quality_spec(result.title)
        result.type = media.type
        result.info_hash = self.__extract_info_hash(result.magnet)

        if isinstance(media, Series):
            result.season = media.season
            result.episode = media.episode

        return result
