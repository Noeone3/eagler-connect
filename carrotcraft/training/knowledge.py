import json
import os
from datetime import datetime

class KnowledgeBase:
    def __init__(self, filename="knowledge.json"):
        self.filename = filename
        self.data = {"goals": {}, "videos": [], "video_studies": [], "strategies": [],
                     "discovered_strategies": [], "experiments": [], "combined_strategies": []}
        self.load()

    def load(self):
        if not os.path.exists(self.filename):
            return
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except Exception as exc:
            print("Warning: could not load knowledge base:", exc)

    def save(self):
        directory = os.path.dirname(os.path.abspath(self.filename))
        os.makedirs(directory, exist_ok=True)
        tmp = self.filename + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.filename)

    def add_goal(self, goal, steps):
        self.data["goals"][goal] = [
            getattr(s, "text", s.get("text", str(s)) if isinstance(s, dict) else str(s))
            for s in steps
        ]
        self.save()

    def add_videos(self, videos):
        if not isinstance(videos, list):
            return
        existing = {v.get("video_id") for v in self.data["videos"] if isinstance(v, dict)}
        for video in videos:
            if isinstance(video, dict) and video.get("video_id") and video["video_id"] not in existing:
                self.data["videos"].append(video)
                existing.add(video["video_id"])
        self.save()

    @staticmethod
    def _key(item):
        if not isinstance(item, dict):
            return None
        return (item.get("video_id"), item.get("objective_id"))

    def add_strategies(self, strategies):
        if not isinstance(strategies, list):
            return
        existing = {self._key(x) for x in self.data["strategies"] if isinstance(x, dict)}
        for strategy in strategies:
            if not isinstance(strategy, dict) or not strategy.get("video_id"):
                continue
            key = self._key(strategy)
            if key not in existing:
                self.data["strategies"].append(strategy)
                existing.add(key)
        self.save()

    def add_video_study(self, study):
        if not isinstance(study, dict) or not study.get("video_id"):
            return
        key = self._key(study)
        replaced = False
        for i, old in enumerate(self.data["video_studies"]):
            if self._key(old) == key:
                self.data["video_studies"][i] = study
                replaced = True
                break
        if not replaced:
            self.data["video_studies"].append(study)
        self.save()
        self._process_discoveries(study)

    def _find_discovered(self, name):
        return next((x for x in self.data["discovered_strategies"]
                     if isinstance(x, dict) and x.get("name") == name), None)

    def add_discovered_strategy(self, strategy, video_id=None):
        if not isinstance(strategy, dict) or not strategy.get("name"):
            return
        name = strategy["name"]
        existing = self._find_discovered(name)
        now = datetime.utcnow().isoformat()
        if existing is None:
            existing = {"name": name, "status": "candidate", "occurrences": 0,
                        "video_count": 0, "video_ids": [], "examples": [], "y_levels": [],
                        "confidence": 0.0, "created_at": now, "updated_at": now,
                        "tested": False, "experiments": [], "results": [],
                        "average_time": None, "average_diamonds": None,
                        "average_deaths": None, "success_rate": None}
            self.data["discovered_strategies"].append(existing)
        existing["occurrences"] += int(strategy.get("occurrences", 1))
        if video_id and video_id not in existing["video_ids"]:
            existing["video_ids"].append(video_id)
        existing["video_count"] = len(existing["video_ids"])
        for example in strategy.get("examples", []):
            if isinstance(example, str) and example not in existing["examples"] and len(existing["examples"]) < 10:
                existing["examples"].append(example)
        levels = set(existing.get("y_levels", []))
        for level in strategy.get("y_levels", []):
            try: levels.add(int(level))
            except (ValueError, TypeError): pass
        existing["y_levels"] = sorted(levels)
        c = float(strategy.get("confidence", 0))
        existing["confidence"] = c if not existing.get("confidence") else round((existing["confidence"] + c) / 2, 3)
        existing["updated_at"] = now
        if existing["occurrences"] >= 2 or existing["video_count"] >= 2:
            existing["status"] = "learned_candidate"
        self.save()

    def _process_discoveries(self, study):
        for item in study.get("new_strategies", []) if isinstance(study, dict) else []:
            if isinstance(item, dict):
                self.add_discovered_strategy(item, study.get("video_id"))

    def get_strategies(self):
        return list(self.data["strategies"])

    def get_strategies_for_objective(self, objective_id):
        return [x for x in self.data["strategies"]
                if isinstance(x, dict) and x.get("objective_id") == objective_id]

    def get_studies_for_objective(self, objective_id):
        return [x for x in self.data["video_studies"]
                if isinstance(x, dict) and x.get("objective_id") == objective_id]

    def get_discovered_strategies(self, include_unclassified=False):
        return [x for x in self.data["discovered_strategies"]
                if isinstance(x, dict) and (include_unclassified or x.get("status") != "unclassified")]

    def get_learned_candidates(self):
        return [x for x in self.data["discovered_strategies"]
                if isinstance(x, dict) and x.get("status") == "learned_candidate"]

    def add_experiment(self, experiment):
        if isinstance(experiment, dict):
            self.data["experiments"].append(experiment)
            self.save()

    def add_combined_strategy(self, strategy):
        if isinstance(strategy, dict):
            self.data["combined_strategies"].append(strategy)
            self.save()
