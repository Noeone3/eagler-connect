import json
import os
import urllib.parse
import urllib.request


class YouTubeAutoSearch:
    """
    Searches YouTube using the official YouTube Data API.

    The API key is read from:

        YOUTUBE_API_KEY

    It is intentionally not stored in this source file.
    """

    API_URL = (
        "https://www.googleapis.com/youtube/v3/search"
    )

    DIAMOND_QUERIES = [
        "Minecraft 26.2 diamond mining fastest Java Bedrock",
        "Minecraft fastest way to find diamonds",
        "Minecraft diamond mining method 2026",
        "Minecraft branch mining diamonds",
        "Minecraft cave mining diamonds",
    ]

    def __init__(
        self,
        max_results=20
    ):

        self.max_results = max_results

        self.api_key = os.environ.get(
            "YOUTUBE_API_KEY"
        )

    # --------------------------------------------------
    # GENERAL SEARCH
    # --------------------------------------------------

    def search(
        self,
        query
    ):

        if not self.api_key:

            print(
                "ERROR: YOUTUBE_API_KEY is not set."
            )

            return []

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": self.max_results,
            "key": self.api_key,
        }

        url = (
            self.API_URL
            + "?"
            + urllib.parse.urlencode(
                params
            )
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "MinecraftAI/1.0"
            }
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=20
            ) as response:

                raw = response.read()

            data = json.loads(
                raw.decode("utf-8")
            )

        except Exception as exc:

            print(
                "YouTube API error:",
                exc
            )

            return []

        results = []

        for item in data.get(
            "items",
            []
        ):

            snippet = item.get(
                "snippet",
                {}
            )

            item_id = item.get(
                "id",
                {}
            )

            video_id = item_id.get(
                "videoId"
            )

            if not video_id:
                continue

            results.append(
                {
                    "status": "ok",

                    "video_id":
                        video_id,

                    "title":
                        snippet.get(
                            "title",
                            ""
                        ),

                    "description":
                        snippet.get(
                            "description",
                            ""
                        ),

                    "channel":
                        snippet.get(
                            "channelTitle",
                            ""
                        ),

                    "published_at":
                        snippet.get(
                            "publishedAt",
                            ""
                        ),

                    "url":
                        (
                            "https://www.youtube.com/"
                            "watch?v="
                            + video_id
                        ),
                }
            )

        return results

    # --------------------------------------------------
    # DIAMOND SEARCH
    # --------------------------------------------------

    def search_diamond_videos(
        self,
        max_total=None
    ):

        if max_total is None:

            max_total = self.max_results

        all_videos = []

        seen = set()

        print(
            "\nSearching YouTube for "
            "diamond strategies..."
        )

        for query in self.DIAMOND_QUERIES:

            if len(all_videos) >= max_total:
                break

            print(
                "  Query:",
                query
            )

            # Only request the number we still need.
            remaining = (
                max_total
                - len(all_videos)
            )

            old_max = self.max_results

            self.max_results = min(
                old_max,
                remaining
            )

            videos = self.search(
                query
            )

            self.max_results = old_max

            for video in videos:

                video_id = video.get(
                    "video_id"
                )

                if not video_id:
                    continue

                if video_id in seen:
                    continue

                seen.add(
                    video_id
                )

                all_videos.append(
                    video
                )

                if len(all_videos) >= max_total:
                    break

        return all_videos

    # --------------------------------------------------
    # COMPATIBILITY ALIAS
    # --------------------------------------------------

    def research_diamonds(
        self
    ):

        return self.search_diamond_videos()