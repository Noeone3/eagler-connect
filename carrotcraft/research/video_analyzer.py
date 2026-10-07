import os
import re
import json

class YouTubeVideoAnalyzer:
    def __init__(self, output_dir="data/video_analysis"):
        self.output_dir = output_dir

    def analyze(self, video_id_or_url, download=True, interval=5):
        try:
            from pytubefix import YouTube
        except ImportError:
            return {"status": "error", "error": "Install pytubefix first."}

        url = video_id_or_url
        if not url.startswith("http"):
            url = "https://www.youtube.com/watch?v=" + video_id_or_url

        os.makedirs(self.output_dir, exist_ok=True)

        try:
            yt = YouTube(url)
            result = {
                "status": "ok",
                "video_id": yt.video_id,
                "title": yt.title,
                "channel": yt.author,
                "duration_seconds": yt.length,
                "url": url
            }

            captions_text = ""
            try:
                captions = yt.captions
                cap = captions.get_by_language_code("en")
                if cap is None and len(captions):
                    cap = list(captions)[0]
                if cap:
                    captions_text = cap.generate_srt_captions()
                    with open(os.path.join(self.output_dir, "captions.srt"), "w", encoding="utf-8") as f:
                        f.write(captions_text)
            except Exception as exc:
                result["caption_error"] = str(exc)

            # The study step reads this back out, so it has to be returned -
            # writing captions.srt alone left every video study with no text.
            result["caption_text"] = captions_text
            result["captions_available"] = bool(captions_text)

            if download:
                try:
                    stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
                    if stream:
                        result["video_file"] = stream.download(output_path=self.output_dir, filename="source_video.mp4")
                    else:
                        result["download_error"] = "No progressive MP4 stream available."
                except Exception as exc:
                    result["download_error"] = str(exc)

            report_path = os.path.join(self.output_dir, "analysis.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

            return result
        except Exception as exc:
            return {"status": "error", "error": str(exc), "url": url}