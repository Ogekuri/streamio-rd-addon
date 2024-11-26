from models.series import Series
from torrent.torrent_item import TorrentItem
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SearchResult:
    def __init__(self):
        self.title = None  # Title of the torrent
        self.size = None  # Size of the torrent
        self.link = None  # Download link for the torrent file or magnet url
        self.indexer = None  # Indexer
        self.engine_name = None  # Indexer Name
        self.seeders = None  # Seeders count
        self.magnet = None  # Magnet url
        self.info_hash = None  # infoHash by Search
        self.privacy = None  # public or private (determina se sarà o meno salvato in cache)

        # Extra processed details for further filtering
        self.languages = None  # Language of the torrent
        self.quality = None  # Quality of the torrent
        self.quality_spec = None  # Quality specifications of the torrent
        self.type = None  # series or movie

        # Not sure about these
        self.season = None  # Season, if the media is a series
        self.episode = None  # Episode, if the media is a series

        # from cache?
        self.from_cache = False

    def convert_to_torrent_item(self):
        return TorrentItem(
            self.title,
            self.size,
            self.magnet,
            self.info_hash.lower() if self.info_hash is not None else None,
            self.link,
            self.seeders,
            self.languages,
            self.quality,
            self.quality_spec,
            self.indexer,       # ilCorSaRoNeRo
            self.engine_name,   # ilcorsaronero
            self.privacy,
            self.episode,
            self.season,
            self.type,
            self.from_cache
        )

    def from_cached_item(self, cached_item, media):
        if type(cached_item) is not dict:
            logger.error(cached_item)
        self.title = cached_item['torrent_title']
        self.indexer = cached_item['indexer']
        self.magnet = cached_item['magnet']
        self.link = cached_item['magnet']
        self.info_hash = cached_item['hash']
        self.languages = [ cached_item['language'] ]
        self.quality = cached_item['quality']
        self.quality_spec = cached_item['qualitySpec']
        self.seeders = cached_item['seeders']
        self.size = cached_item['size']
        self.type = cached_item['type']
        if self.type == "series":
            self.season = cached_item['season']
            self.episode = cached_item['episode']
        self.from_cache = True

        return self
