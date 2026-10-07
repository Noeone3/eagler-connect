class VideoStrategyExtractor:
    KEYWORDS = {
        "branch_mining": ["branch mining", "strip mining", "tunnel"],
        "cave_mining": ["cave", "caving", "cave mining"],
        "deep_mining": ["deepslate", "deep slate", "y level -59", "y-59"],
        "ore_exposure": ["exposed ore", "ore exposure", "exposed ores"],
        "water_lava": ["lava", "water bucket", "lava pool"],
        "bed_mining": ["bed mining", "bed mine"],
        "tnt_mining": ["tnt", "tnt mining"]
    }

    def extract(self, videos):
        strategies = []
        for video in videos:
            if video.get("status") != "ok":
                continue
            text = (video.get("title", "") + "\n" +
                    video.get("description", "")).lower()
            techniques = []
            for name, keywords in self.KEYWORDS.items():
                if any(k in text for k in keywords):
                    techniques.append(name)
            strategies.append({
                "video_id": video.get("video_id"),
                "title": video.get("title", ""),
                "channel": video.get("channel", ""),
                "published_at": video.get("published_at", ""),
                "techniques": techniques or ["unknown"],
                "speed_score": None,
                "reliability_score": None,
                "resource_efficiency_score": None,
                "difficulty_score": None,
                "risk_score": None,
                "tested": False
            })
        return strategies
