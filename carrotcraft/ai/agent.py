from typing import Optional
from ai.objective_planner import Objective, ObjectivePlanner, WorldSnapshot
from ai.optimizer import SpeedOptimizer
from research.youtube_auto_search import YouTubeAutoSearch
from research.video_strategy_extractor import VideoStrategyExtractor
from research.video_study import VideoStudy
from training.knowledge import KnowledgeBase
from training.practice import PracticePlanner

DEFAULT_SERVER_URL = "wss://eagler.carrot-craft.org"


class MinecraftAI:
    def __init__(self, server_version="1.21.1", client_version="1.8.8", server_url=DEFAULT_SERVER_URL):
        self.server_version = server_version
        self.client_version = client_version
        self.server_url = server_url
        self.planner = ObjectivePlanner(mc_version=server_version)
        self.youtube = YouTubeAutoSearch()
        self.strategy_extractor = VideoStrategyExtractor()
        self.video_study = VideoStudy()
        self.knowledge = KnowledgeBase()
        self.practice = PracticePlanner()
        self.optimizer = SpeedOptimizer()
        self.goal = None
        self.objectives = []
        self.world = WorldSnapshot()
        self.current_objective: Optional[Objective] = None

    def prepare(self, goal):
        self.goal = goal
        self.objectives = self.planner.plan(goal)
        self.knowledge.add_goal(goal, self.objectives)
        return self.objectives

    def update_from_state(self, state):
        if not isinstance(state, dict): return
        self.world.player = state.get("player", self.world.player)
        self.world.inventory = state.get("inventory", self.world.inventory)
        self.world.blocks = state.get("blocks", self.world.blocks)
        self.world.entities = state.get("entities", self.world.entities)

    def select_next_objective(self):
        self.current_objective = self.planner.next_objective(self.objectives, self.world)
        return self.current_objective

    def mark_objective_done(self, objective_id=None):
        target = self.current_objective
        if objective_id is not None:
            target = next((x for x in self.objectives if x.id == objective_id), None)
        if target is None: return False
        target.status = "done"
        if self.current_objective and self.current_objective.id == target.id:
            self.current_objective = None
        return True

    def build_research_query(self, objective):
        return f"Minecraft {self.server_version} {objective.text} fastest strategy tutorial guide"

    def research_objective(self, objective, video_limit=3, study_videos=True):
        query = self.build_research_query(objective)
        print(f"\nOBJECTIVE: {objective.text}\nQUERY: {query}")
        videos = self.youtube.search(query)
        self.knowledge.add_videos(videos)

        raw = self.strategy_extractor.extract(videos)
        strategies = []
        for item in raw:
            item = dict(item)
            item.update(objective_id=objective.id, objective_text=objective.text,
                        server_version=self.server_version, research_query=query)
            strategies.append(item)
        self.knowledge.add_strategies(strategies)

        studies = []
        if study_videos:
            for video in videos[:max(0, video_limit)]:
                study = self.study_video(video, objective)
                if study is not None:
                    studies.append(study)

        return {"objective_id": objective.id, "objective_text": objective.text,
                "query": query, "videos": videos, "strategies": strategies, "studies": studies}

    def research_all_objectives(self, video_limit=3, study_videos=True, objective_limit=None):
        selected = self.objectives[:objective_limit] if objective_limit is not None else self.objectives
        results = []
        for i, objective in enumerate(selected, 1):
            print("\n" + "="*60)
            print(f"OBJECTIVE RESEARCH {i}/{len(selected)}")
            result = self.research_objective(objective, video_limit, study_videos)
            print("Videos:", len(result["videos"]), "Strategies:", len(result["strategies"]),
                  "Studies:", len(result["studies"]))
            results.append(result)
        return results

    def research(self, goal):
        videos = self.youtube.search(goal)
        self.knowledge.add_videos(videos)
        return videos

    def research_diamonds(self, limit=20):
        videos = self.youtube.search_diamond_videos(max_total=limit)
        self.knowledge.add_videos(videos)
        return self.extract_strategies_for_videos(videos)

    def extract_strategies_for_videos(self, videos, objective=None):
        strategies = self.strategy_extractor.extract(videos)
        if objective:
            for item in strategies:
                item["objective_id"] = objective.id
                item["objective_text"] = objective.text
                item["server_version"] = self.server_version
        self.knowledge.add_strategies(strategies)
        return strategies

    def study_video(self, video, objective=None):
        if isinstance(video, str):
            video = {"video_id": video, "title": video, "description": ""}
        if not isinstance(video, dict): return None
        video_id = video.get("video_id", "")
        print("Studying:", video.get("title", "Unknown"), "|", video_id)
        caption_text = ""
        try:
            from research.video_analyzer import YouTubeVideoAnalyzer
            result = YouTubeVideoAnalyzer().analyze(video_id, download=False)
            if isinstance(result, str): caption_text = result
            elif isinstance(result, dict):
                for key in ("caption_text","captions","transcript","text"):
                    value = result.get(key)
                    if isinstance(value, str):
                        caption_text = value; break
                    if isinstance(value, list):
                        caption_text = "\n".join(map(str, value)); break
            elif isinstance(result, list):
                caption_text = "\n".join(map(str, result))
        except Exception as exc:
            print("    Video analyzer error:", exc)

        try:
            study = self.video_study.study(video, caption_text)
            if objective:
                study["objective_id"] = objective.id
                study["objective_text"] = objective.text
                study["server_version"] = self.server_version
            self.knowledge.add_video_study(study)
            print("    Status:", study.get("status", "unknown"))
            if study.get("known_techniques"):
                print("    Techniques:", ", ".join(map(str, study["known_techniques"])))
            return study
        except Exception as exc:
            print("    Strategy study error:", exc)
            return None

    def study_videos(self, videos, limit=5, objective=None):
        return [s for v in list(videos[:max(0,limit)])
                if (s := self.study_video(v, objective)) is not None]

    def optimize(self, goal, objective_id=None):
        strategies = (self.knowledge.get_strategies_for_objective(objective_id)
                      if objective_id else self.knowledge.get_strategies())
        return self.optimizer.choose(goal, strategies)

    def combine_strategies(self):
        result = self.optimizer.combine(self.knowledge.get_strategies())
        self.knowledge.add_combined_strategy(result)
        return result

    def objective_action(self):
        if not self.current_objective: return None
        o = self.current_objective
        return {"objective_id": o.id, "objective": o.text,
                "action": o.action, "params": dict(o.params)}