class PracticePlanner:

    def build(
        self,
        goal,
        knowledge
    ):

        steps = (
            knowledge.data[
                "goals"
            ].get(
                goal,
                [goal]
            )
        )

        return {

            "goal": goal,

            "environment":
                "singleplayer",

            "steps":
                steps,

            "experiments": [

                {
                    "type":
                        "baseline",

                    "description":
                        (
                            "Attempt the goal "
                            "without a learned "
                            "specialized strategy."
                        )
                },

                {
                    "type":
                        "strategy_comparison",

                    "description":
                        (
                            "Test each researched "
                            "strategy under similar "
                            "starting conditions."
                        )
                },

                {
                    "type":
                        "combined_strategy",

                    "description":
                        (
                            "Combine techniques "
                            "from successful "
                            "strategies and test again."
                        )
                }
            ],

            "repeat_until":
                "stable_success",

            "record": [

                "completion_time_seconds",

                "diamonds_found",

                "blocks_mined",

                "distance_traveled",

                "food_consumed",

                "damage_taken",

                "deaths",

                "tool_durability_used",

                "actions",

                "failure_reason"
            ]
        }