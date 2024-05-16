from typing import Any


def define_env(env: Any) -> None:
    static_dir = "/static/"
    video_dir = "https://clan.lol/" + "videos/"
    asciinema_dir = static_dir + "asciinema-player/"

    @env.macro
    def video(name: str) -> str:
        return f"""<video loop muted autoplay id="{name}">
                <source src={video_dir + name} type="video/webm">
                Your browser does not support the video tag.
            </video>"""

    @env.macro
    def asciinema(name: str) -> str:
        return f"""<div id="{name}">
            <script src="{asciinema_dir}/asciinema-player.min.js"></script>
            <script>
                AsciinemaPlayer.create('{video_dir + name}',
                document.getElementById("{name}"), {{
                    loop: true,
                    autoPlay: true,
                    controls: false,
                    speed: 1.5,
                    theme: "alabaster-auto"
                }});
            </script>
        </div>"""
