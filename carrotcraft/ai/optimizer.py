class SpeedOptimizer:

    def __init__(self):

        self.weights = {

            "speed_score": 0.45,

            "reliability_score": 0.25,

            "resource_efficiency_score":
                0.15,

            "difficulty_score": 0.10,

            "risk_score": 0.05
        }

    def calculate_score(
        self,
        strategy
    ):

        # Do not score a strategy until
        # real experiment results exist.

        for key in self.weights:

            if strategy.get(key) is None:

                return None

        score = 0.0

        for key, weight in (
            self.weights.items()
        ):

            score += (
                strategy[key]
                * weight
            )

        return score

    def rank(
        self,
        strategies
    ):

        scored = []

        for strategy in strategies:

            score = (
                self.calculate_score(
                    strategy
                )
            )

            if score is None:
                continue

            item = dict(strategy)

            item["score"] = score

            scored.append(item)

        return sorted(
            scored,
            key=lambda item:
                item["score"],
            reverse=True
        )

    def choose(
        self,
        goal,
        strategies
    ):

        ranked = self.rank(
            strategies
        )

        if ranked:

            return ranked[0]

        return {

            "goal": goal,

            "strategy": "baseline",

            "reason": (
                "No experimentally "
                "scored strategies yet."
            )
        }

    def combine(
        self,
        strategies
    ):

        ranked = self.rank(
            strategies
        )[:3]

        techniques = []

        source_videos = []

        for strategy in ranked:

            video_id = strategy.get(
                "video_id"
            )

            if video_id:

                source_videos.append(
                    video_id
                )

            for technique in (
                strategy.get(
                    "techniques",
                    []
                )
            ):

                if technique not in techniques:

                    techniques.append(
                        technique
                    )

        return {

            "techniques": techniques,

            "source_videos":
                source_videos,

            "status":
                "needs_experiment"
        }