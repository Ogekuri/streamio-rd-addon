# run from this path

from thepiratebay_categories import thepiratebay
from one337x import one337x
from ilcorsaronero import ilcorsaronero

from urllib.parse import quote_plus

engines = [thepiratebay(), one337x(), ilcorsaronero()]

SEARCH_STRING=quote_plus("Wolfs (2024) ITA")

def __is_magnet_link(link):
    # Check if link inizia con "magnet:?"
    return link.startswith("magnet:?")

for engine in engines:
    print(engine.name)
    results = engine.search(SEARCH_STRING, 'movies')
    if results is not None:
        print(type(results))
        print(len(results))
        # print(results)
        for result in results:
            link = result['link'] 
            if not __is_magnet_link(link):
                print('convert:'+link)
                link = engine.download_torrent(result['link'])
            print(link)

