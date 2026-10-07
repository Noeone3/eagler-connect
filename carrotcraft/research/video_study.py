import re


class VideoStudy:

    KNOWN_TECHNIQUES = {
        "branch_mining": [
            "branch mining",
            "branch mine",
            "strip mining",
            "strip mine",
            "tunnel",
            "tunneling",
            "mine tunnels",
        ],

        "cave_mining": [
            "cave mining",
            "cave mine",
            "caving",
            "explore caves",
            "exploring caves",
            "cave",
        ],

        "deep_slate_mining": [
            "deepslate",
            "deep slate",
            "deep-slate",
        ],

        "exploration": [
            "explore",
            "exploring",
            "exploration",
        ],

        "ore_exposure": [
            "exposed ore",
            "expose ore",
            "ore exposure",
            "exposed diamonds",
            "visible diamonds",
        ],

        "water_lava": [
            "lava",
            "lava pool",
            "water bucket",
            "water",
        ],

        "bed_mining": [
            "bed mining",
            "bed mine",
            "beds",
        ],

        "tnt_mining": [
            "tnt mining",
            "tnt mine",
            "tnt tunnel",
            "tnt tunnel bore",
            "tnt",
        ],
    }

    ACTION_WORDS = [
        "mine",
        "mining",
        "dig",
        "digging",
        "find",
        "finding",
        "search",
        "searching",
        "explore",
        "exploring",
        "use",
        "using",
        "place",
        "placing",
        "walk",
        "walking",
        "run",
        "running",
        "travel",
        "traveling",
        "tunnel",
        "tunneling",
        "craft",
        "crafting",
        "break",
        "breaking",
    ]

    RESOURCE_WORDS = [
        "diamond",
        "diamonds",
        "ore",
        "lava",
        "water",
        "tnt",
        "bed",
        "pickaxe",
        "deepslate",
        "stone",
        "iron",
        "gold",
    ]

    def _safe_text(self, value):
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            parts = []

            for key in [
                "text",
                "caption_text",
                "transcript",
                "description",
                "title",
            ]:
                item = value.get(key)

                if isinstance(item, str):
                    parts.append(item)

            return "\n".join(parts)

        if isinstance(value, list):
            parts = []

            for item in value:
                parts.append(
                    self._safe_text(item)
                )

            return "\n".join(parts)

        return str(value)

    def _clean_text(self, text):
        text = self._safe_text(text)

        text = text.replace(
            "&amp;",
            "&"
        )

        text = text.replace(
            "&#39;",
            "'"
        )

        text = text.replace(
            "&quot;",
            '"'
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    def _split_sentences(self, text):
        text = self._clean_text(text)

        if not text:
            return []

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text
        )

        return [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

    def _detect_known_techniques(self, text):
        text = self._clean_text(
            text
        ).lower()

        techniques = []

        for technique, keywords in self.KNOWN_TECHNIQUES.items():

            for keyword in keywords:

                if keyword in text:
                    techniques.append(
                        technique
                    )

                    break

        return sorted(
            set(techniques)
        )

    def _extract_y_levels(self, text):
        text = self._clean_text(
            text
        )

        levels = []

        patterns = [
            r"\by\s*[=:]\s*(-?\d+)",
            r"\by[- ](-?\d+)\b",
            r"\bat\s+y\s+(-?\d+)",
            r"\by\s+level\s+(-?\d+)",
            r"\blevel\s+(-?\d+)",
        ]

        for pattern in patterns:

            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE
            ):

                try:
                    levels.append(
                        int(match.group(1))
                    )
                except (
                    ValueError,
                    IndexError
                ):
                    pass

        return sorted(
            set(levels)
        )

    def _is_strategy_sentence(
        self,
        sentence
    ):
        text = sentence.lower()

        has_action = any(
            word in text
            for word in self.ACTION_WORDS
        )

        has_resource = any(
            word in text
            for word in self.RESOURCE_WORDS
        )

        return (
            has_action
            and has_resource
        )

    def _contains_known_technique(
        self,
        sentence
    ):
        return bool(
            self._detect_known_techniques(
                sentence
            )
        )

    def _strategy_confidence(
        self,
        sentence
    ):
        text = sentence.lower()

        score = 0

        if any(
            word in text
            for word in self.ACTION_WORDS
        ):
            score += 1

        if any(
            word in text
            for word in self.RESOURCE_WORDS
        ):
            score += 1

        if re.search(
            r"\by\s*(?:=|level)?\s*-?\d+",
            text
        ):
            score += 1

        if any(
            word in text
            for word in [
                "fast",
                "faster",
                "best",
                "efficient",
                "efficiently",
                "quick",
                "quickly",
                "avoid",
                "instead",
                "method",
                "strategy",
            ]
        ):
            score += 1

        return min(
            score / 4.0,
            1.0
        )

    def _normalize_strategy(
        self,
        sentence
    ):
        text = self._clean_text(
            sentence
        ).lower()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        text = re.sub(
            r"[^\w\s\-=:]",
            "",
            text
        )

        return text

    def _make_strategy_name(
        self,
        sentence
    ):
        text = self._clean_text(
            sentence
        ).lower()

        y_levels = (
            self._extract_y_levels(
                sentence
            )
        )

        if y_levels:

            y = y_levels[0]

            if (
                "branch" in text
                or "tunnel" in text
            ):
                return (
                    f"branch_mining_at_y_{y}"
                )

            if (
                "mine" in text
                and "deepslate" in text
            ):
                return (
                    f"deepslate_mining_at_y_{y}"
                )

            if "diamond" in text:
                return (
                    f"diamond_mining_at_y_{y}"
                )

        if "tnt" in text:
            return "tnt_mining"

        if (
            "bed" in text
            and "mine" in text
        ):
            return "bed_mining"

        if "lava" in text:

            if "pool" in text:
                return "lava_pool_strategy"

            return "lava_exploration_strategy"

        if (
            "water" in text
            and "lava" in text
        ):
            return "water_lava_strategy"

        if "cave" in text:

            if "explore" in text:
                return (
                    "cave_exploration_strategy"
                )

            return "cave_ore_exposure"

        if (
            "exposed" in text
            or "visible" in text
        ) and "ore" in text:
            return "exposed_ore_mining"

        if "diamond" in text:

            if (
                "fast" in text
                or "quick" in text
            ):
                return "fast_diamond_search"

            return "diamond_search_strategy"

        words = re.findall(
            r"[a-z0-9]+",
            text
        )

        words = [
            word
            for word in words
            if len(word) > 2
        ]

        words = words[:6]

        if not words:
            return "unknown_strategy"

        return (
            "strategy_"
            + "_".join(words)
        )

    def _detect_new_strategies(
        self,
        text
    ):
        sentences = (
            self._split_sentences(
                text
            )
        )

        discoveries = []

        for sentence in sentences:

            if not self._is_strategy_sentence(
                sentence
            ):
                continue

            if self._contains_known_technique(
                sentence
            ):
                continue

            confidence = (
                self._strategy_confidence(
                    sentence
                )
            )

            if confidence < 0.50:
                continue

            discoveries.append({
                "name":
                    self._make_strategy_name(
                        sentence
                    ),

                "sentence":
                    sentence,

                "normalized":
                    self._normalize_strategy(
                        sentence
                    ),

                "confidence":
                    round(
                        confidence,
                        3
                    ),

                "y_levels":
                    self._extract_y_levels(
                        sentence
                    ),
            })

        return discoveries

    def _group_new_strategies(
        self,
        discoveries
    ):
        groups = {}

        for discovery in discoveries:

            if not isinstance(
                discovery,
                dict
            ):
                continue

            name = discovery.get(
                "name"
            )

            if not name:
                continue

            if name not in groups:
                groups[name] = {
                    "name": name,
                    "occurrences": 0,
                    "examples": [],
                    "y_levels": [],
                    "confidence_values": [],
                }

            group = groups[name]

            group[
                "occurrences"
            ] += 1

            sentence = discovery.get(
                "sentence"
            )

            if (
                sentence
                and sentence
                not in group["examples"]
                and len(
                    group["examples"]
                ) < 5
            ):
                group[
                    "examples"
                ].append(
                    sentence
                )

            group[
                "y_levels"
            ].extend(
                discovery.get(
                    "y_levels",
                    []
                )
            )

            group[
                "confidence_values"
            ].append(
                discovery.get(
                    "confidence",
                    0
                )
            )

        results = []

        for group in groups.values():

            confidence_values = (
                group[
                    "confidence_values"
                ]
            )

            average_confidence = (
                sum(
                    confidence_values
                )
                / len(
                    confidence_values
                )
                if confidence_values
                else 0
            )

            results.append({
                "name":
                    group["name"],

                "occurrences":
                    group["occurrences"],

                "examples":
                    group["examples"],

                "y_levels":
                    sorted(
                        set(
                            group[
                                "y_levels"
                            ]
                        )
                    ),

                "confidence":
                    round(
                        average_confidence,
                        3
                    ),
            })

        results.sort(
            key=lambda item: (
                item["occurrences"],
                item["confidence"]
            ),
            reverse=True
        )

        return results

    def study(
        self,
        video,
        caption_text
    ):
        # -----------------------------------------------------
        # Make sure video is always a dictionary
        # -----------------------------------------------------

        if isinstance(
            video,
            str
        ):
            video = {
                "video_id": video,
                "title": video,
                "description": "",
            }

        if not isinstance(
            video,
            dict
        ):
            video = {
                "video_id": "",
                "title": str(video),
                "description": "",
            }

        title = video.get(
            "title",
            ""
        )

        description = video.get(
            "description",
            ""
        )

        caption_text = (
            self._safe_text(
                caption_text
            )
        )

        combined_text = (
            self._safe_text(
                title
            )
            + "\n"
            + self._safe_text(
                description
            )
            + "\n"
            + caption_text
        )

        known = (
            self._detect_known_techniques(
                combined_text
            )
        )

        y_levels = (
            self._extract_y_levels(
                combined_text
            )
        )

        new_raw = (
            self._detect_new_strategies(
                combined_text
            )
        )

        new_strategies = (
            self._group_new_strategies(
                new_raw
            )
        )

        return {
            "status": "studied",

            "video_id":
                video.get(
                    "video_id",
                    ""
                ),

            "title":
                title,

            "channel":
                video.get(
                    "channel",
                    ""
                ),

            "known_techniques":
                known,

            "y_levels":
                y_levels,

            "new_strategies":
                new_strategies,

            "caption_length":
                len(caption_text),

            "summary":
                self._build_summary(
                    known,
                    y_levels,
                    new_strategies
                ),
        }

    def _build_summary(
        self,
        known,
        y_levels,
        new_strategies
    ):
        parts = []

        if known:
            parts.append(
                "Known techniques: "
                + ", ".join(known)
                + "."
            )

        if y_levels:
            parts.append(
                "Mentioned Y levels: "
                + ", ".join(
                    str(level)
                    for level in y_levels
                )
                + "."
            )

        if new_strategies:

            names = [
                item["name"]
                for item in new_strategies
                if isinstance(
                    item,
                    dict
                )
            ]

            if names:
                parts.append(
                    "New strategies discovered: "
                    + ", ".join(names)
                    + "."
                )

        if not parts:
            return (
                "No reliable mining strategies "
                "were extracted."
            )

        return " ".join(parts)