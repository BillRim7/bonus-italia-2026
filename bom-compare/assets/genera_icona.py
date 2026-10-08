"""Genera assets/app.ico (icona dell'eseguibile). Uso: python assets/genera_icona.py"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "app.ico"


def draw(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256
    d.rounded_rectangle([8 * s, 8 * s, 248 * s, 248 * s], radius=48 * s, fill="#1E40AF")
    rows = [("#22C55E", 150), ("#EF4444", 110), ("#60A5FA", 170), ("#E5E7EB", 130)]
    for i, (color, width) in enumerate(rows):
        y = 52 * s + i * 42 * s
        d.rounded_rectangle([44 * s, y, 70 * s, y + 26 * s], radius=6 * s, fill=color)
        d.rounded_rectangle([82 * s, y + 4 * s, (82 + width) * s, y + 22 * s],
                            radius=9 * s, fill="#FFFFFF")
    return img


if __name__ == "__main__":
    draw().save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128),
                            (256, 256)])
    print(f"Creato {OUT}")
