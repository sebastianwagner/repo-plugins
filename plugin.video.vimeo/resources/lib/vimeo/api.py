from future import standard_library
standard_library.install_aliases()  # noqa: E402

import requests
import urllib.parse
import xbmc

from .client import VimeoClient
from .auth import GrantFailed
from .api_collection import ApiCollection
from resources.lib.models.channel import Channel
from resources.lib.models.group import Group
from resources.lib.models.user import User
from resources.lib.models.video import Video


class Api:
    """This class uses the official Vimeo API."""

    api_player = "https://player.vimeo.com"
    api_limit = 10

    # Extracted from public Vimeo Android App
    # This is a special client ID which will return playable URLs
    api_client_id = "74fa89b811a1cbb750d8528d163f48af28a2dbe1"
    api_client_secret = "VJjDTzlnL6Vm/GbUDuwCwcc1mrdFUa9XFlg4ZoMQ4xX2UWuzbBomapujUcGKLNrt" \
                        "wdtIIvy0paa7kFN0asWp2ooNSdqaEdwVkBLqau7MJFe0tSWez7HOakg/8BKtYzDe"

    # Access token of registered API app
    # Is used as a fallback if the client login request fails
    api_access_token_default = "d284acb5ed7c011ec0d79f79e3479f8c"
    api_access_token_cache_duration = 720  # 12 hours
    api_access_token_cache_key = "api-access-token"

    video_stream = ""

    def __init__(self, settings, lang, vfs, cache):
        self.settings = settings
        self.lang = lang
        self.vfs = vfs
        self.cache = cache

        self.api_limit = int(self.settings.get("search.items.size"))
        self.video_stream = self.settings.get("video.format")
        self.video_av1 = True if self.settings.get("video.codec.av1") == "true" else False

    @property
    def api_client(self):
        # It is possible to set a custom access token in the settings
        access_token_settings = self.settings.get("api.accesstoken")
        if access_token_settings:
            xbmc.log("plugin.video.vimeo::Api() Using custom access token", xbmc.LOGDEBUG)
            return VimeoClient(token=access_token_settings)

        # Check if there is a cached access token
        access_token_cached = self.cache.get(
            self.api_access_token_cache_key,
            self.api_access_token_cache_duration
        )
        if access_token_cached:
            xbmc.log("plugin.video.vimeo::Api() Using cached access token", xbmc.LOGDEBUG)
            return VimeoClient(token=access_token_cached)

        # Request an access token and cache it
        try:
            client = VimeoClient(
                key=self.api_client_id,
                secret=self.api_client_secret
            )
            access_token = client.load_client_credentials(["public"])
            self.cache.add(self.api_access_token_cache_key, str(access_token))
            xbmc.log("plugin.video.vimeo::Api() Using new access token", xbmc.LOGDEBUG)
            return client
        except GrantFailed:
            xbmc.log("plugin.video.vimeo::Api() Grant failed, using fallback", xbmc.LOGDEBUG)
            pass

        # Fallback
        return VimeoClient(token=self.api_access_token_default)

    @property
    def search_template(self):
        search_template = self.settings.get("search.template")

        if "{}" in search_template:
            return search_template

        return "{}"

    def call(self, url):
        params = self._get_default_params()
        res = self._do_api_request(url, params)
        return self._map_json_to_collection(res)

    def search(self, query, kind):
        params = self._get_default_params()
        params["query"] = self.search_template.format(query)
        res = self._do_api_request("/{kind}".format(kind=kind), params)
        return self._map_json_to_collection(res)

    def channel(self, channel):
        params = self._get_default_params()
        params["sort"] = "added"
        channel_id = urllib.parse.quote(channel)
        res = self._do_api_request("/channels/{id}/videos".format(id=channel_id), params)
        return self._map_json_to_collection(res)

    def resolve_media_url(self, uri):
        # If we have a full URL, we don't need to resolve it, because it already is
        if uri.startswith("https://"):
            xbmc.log("plugin.video.vimeo::Api() directly resolved", xbmc.LOGDEBUG)
            return uri

        # If we have a on-demand URL, we need to fetch the trailer and return the uri
        if uri.startswith("/ondemand/"):
            xbmc.log("plugin.video.vimeo::Api() resolving on-demand", xbmc.LOGDEBUG)
            return self._get_on_demand_trailer(uri)

        # Fallback
        xbmc.log("plugin.video.vimeo::Api() resolving fallback", xbmc.LOGDEBUG)
        uri = uri.replace("/videos/", "/video/")
        res = self._do_player_request(uri)

        return self._extract_url_from_video_config(res)

    def resolve_id(self, video_id):
        params = self._get_default_params()
        res = self._do_api_request("/videos/{video_id}".format(video_id=video_id), params)
        return self._map_json_to_collection(res)

    def _do_api_request(self, path, params):
        return self.api_client.get(path, params=params).json()

    def _do_player_request(self, uri):
        headers = {"Accept-Encoding": "gzip"}
        return requests.get(self.api_player + uri + "/config", headers=headers).json()

    def _map_json_to_collection(self, json_obj):
        collection = ApiCollection()
        collection.items = []  # Reset list in order to resolve problems in unit tests
        collection.next_href = json_obj.get("paging", {"next": None})["next"]

        if "type" in json_obj and json_obj["type"] == "video":
            # If we are dealing with a single video, pack it into a dict
            json_obj = {"data": [json_obj]}

        if "data" in json_obj:

            for item in json_obj["data"]:
                kind = item.get("type", None)
                is_video = kind == "video"
                is_channel = "/channels/" in item.get("uri", "")
                is_group = "/groups/" in item.get("uri", "")
                is_user = item.get("account", False)

                # Requests made with the fallback token won't include media URLs:
                contains_media_url = "play" in item and item["play"]["status"] == "playable"

                # On-demand videos don't contain playable video links:
                purchase_required = item.get("play", {}).get("status", "") == "purchase_required"

                if is_video:
                    if contains_media_url:
                        video_url = self._extract_url_from_search_response(item.get("play"))
                    elif purchase_required:
                        video_url = item["metadata"]["connections"]["trailer"]["uri"]
                    else:
                        video_url = item["uri"]

                    video = Video(id=item["resource_key"], label=item["name"])
                    video.thumb = self._get_picture(item["pictures"])
                    video.uri = video_url
                    video.info = {
                        "date": item["release_time"],
                        "description": item["description"],
                        "duration": item["duration"],
                        "picture": self._get_picture(item["pictures"], 4),
                        "playcount": item["stats"].get("plays", 0),
                        "user": item["user"]["name"],
                        "userThumb": self._get_picture(item["user"]["pictures"], 3),
                        "mediaUrlResolved": contains_media_url,
                        "onDemand": purchase_required,
                    }
                    collection.items.append(video)

                elif is_channel:
                    channel = Channel(id=item["resource_key"], label=item["name"])
                    channel.thumb = self._get_picture(item["pictures"], 3)
                    channel.uri = item["metadata"]["connections"]["videos"]["uri"]
                    channel.info = {
                        "date": item["created_time"],
                        "description": item.get("description", ""),
                    }
                    collection.items.append(channel)

                elif is_group:
                    group = Group(id=item["resource_key"], label=item["name"])
                    group.thumb = self._get_picture(item["pictures"], 3)
                    group.uri = item["metadata"]["connections"]["videos"]["uri"]
                    group.info = {
                        "date": item["created_time"],
                        "description": item.get("description", ""),
                    }
                    collection.items.append(group)

                elif is_user:
                    user = User(id=item["resource_key"], label=item["name"])
                    user.thumb = self._get_picture(item["pictures"], 3)
                    user.uri = item["metadata"]["connections"]["videos"]["uri"]
                    user.info = {
                        "country": item.get("location", ""),
                        "date": item["created_time"],
                        "description": item["bio"],
                    }
                    collection.items.append(user)

                else:
                    raise RuntimeError("Could not convert JSON kind to model...")

        else:
            raise RuntimeError("Api JSON seems to be invalid")

        return collection

    def _get_default_params(self):
        return {
            "per_page": self.api_limit,
            "total": self.api_limit,
            # Avoid rate limiting:
            # https://developer.vimeo.com/guidelines/rate-limiting#avoid-rate-limiting
            "fields": "uri,resource_key,name,description,type,duration,created_time,location,"
                      "bio,stats,user,account,release_time,pictures,metadata,play"
        }

    def _video_matches(self, video, video_format):
        video_height = video_format[1].replace("p", "")
        video_codec = self.settings.VIDEO_CODEC["AV1"] if self.video_av1 else \
            self.settings.VIDEO_CODEC["H.264"]

        return str(video["height"]) == video_height and video["codec"] == video_codec

    def _extract_url_from_search_response(self, video_files):
        video_format = self.settings.VIDEO_FORMAT[self.video_stream]
        video_format = video_format.split(":")
        video_type = video_format[0]

        if video_type == "hls":
            return video_files["hls"]["link"]

        elif video_type == "progressive":
            for video_file in video_files["progressive"]:
                if self._video_matches(video_file, video_format):
                    return video_file["link"]

            # Fallback if no matching quality was found
            return video_files["progressive"][0]["link"]

        else:
            raise RuntimeError("Could not extract video URL")

    def _get_on_demand_trailer(self, uri):
        res = self._do_api_request(uri, {"fields": "uri,type,play"})
        return self._extract_url_from_search_response(res["play"])

    def _extract_url_from_video_config(self, video_config):
        video_files = video_config["request"]["files"]
        video_format = self.settings.VIDEO_FORMAT[self.video_stream]
        video_format = video_format.split(":")
        video_type = video_format[0]
        video_type_setting = video_format[1]
        video_has_av1_codec = len(video_config["request"]["file_codecs"]["av1"]) > 0

        if video_type == "hls" or (video_has_av1_codec and not self.video_av1):
            hls_default_cdn = video_files["hls"]["default_cdn"]
            if self.video_av1:
                return video_files["hls"]["cdns"][hls_default_cdn]["av1_url"]
            else:
                return video_files["hls"]["cdns"][hls_default_cdn]["avc_url"]

        elif video_type == "progressive":
            for video_file in video_files["progressive"]:
                if video_file["quality"] == video_type_setting:
                    return video_file["url"]

            # Fallback if no matching quality was found
            return video_files["progressive"][0]["url"]

        else:
            raise RuntimeError("Could not extract video URL")

    @staticmethod
    def _get_picture(data, size=1):
        try:
            return data["sizes"][size]["link"]
        except IndexError:
            return data["sizes"][0]["link"]
