from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Try loading standard Windows fonts or fall back to default
try:
    font_large = ImageFont.truetype("arialbd.ttf", 52)
    font_sub = ImageFont.truetype("georgiab.ttf", 20)
except Exception:
    font_large = ImageFont.load_default()
    font_sub = ImageFont.load_default()

assets_dir = Path("src/project-source-code/assets")
assets_dir.mkdir(parents=True, exist_ok=True)

# 1. Dark Mode Logo (RGBA transparent background, Ivory + Cyan text)
img_dark = Image.new("RGBA", (400, 130), color=(0, 0, 0, 0))
draw_dark = ImageDraw.Draw(img_dark)
ivory = (245, 238, 219, 255)
cyan = (0, 229, 255, 255)

draw_dark.text((80, 15), "DC", font=font_large, fill=ivory)
draw_dark.text((165, 15), "4", font=font_large, fill=cyan)
draw_dark.text((205, 15), "X", font=font_large, fill=ivory)
sub_text = "Data Cleaning For You"
bbox = draw_dark.textbbox((0, 0), sub_text, font=font_sub)
w = bbox[2] - bbox[0]
draw_dark.text(((400 - w) // 2, 82), sub_text, font=font_sub, fill=ivory)
img_dark.save(assets_dir / "logo_dark.png", format="PNG")
img_dark.save(assets_dir / "logo.png", format="PNG")

# 2. Light Mode Logo (RGBA transparent background, Dark Slate + Sky Blue text)
img_light = Image.new("RGBA", (400, 130), color=(0, 0, 0, 0))
draw_light = ImageDraw.Draw(img_light)
slate = (15, 23, 42, 255)
blue = (2, 132, 199, 255)

draw_light.text((80, 15), "DC", font=font_large, fill=slate)
draw_light.text((165, 15), "4", font=font_large, fill=blue)
draw_light.text((205, 15), "X", font=font_large, fill=slate)
bbox_l = draw_light.textbbox((0, 0), sub_text, font=font_sub)
w_l = bbox_l[2] - bbox_l[0]
draw_light.text(((400 - w_l) // 2, 82), sub_text, font=font_sub, fill=(51, 65, 85, 255))
img_light.save(assets_dir / "logo_light.png", format="PNG")

print("Generated transparent logo_dark.png, logo_light.png, and logo.png successfully.")
