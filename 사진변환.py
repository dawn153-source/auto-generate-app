import unicodedata
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps

from 문구생성 import make_captions

SIZE = 1080
BASE = Path(__file__).resolve().parent
SRC = BASE / "자료"
OUT = BASE / "완성"
LOGO = SRC / "로고.png"
LOGO_RATIO = 0.15  # 사진 가로 폭 대비 로고 크기
MARGIN = 40  # 가장자리에서 안쪽으로 띄울 거리
OPACITY = 0.7  # 1이면 선명, 낮을수록 투명


def load_logo():
    if not LOGO.exists():
        print("로고.png가 없어서 로고 넣기는 건너뛰어요.")
        return None
    with Image.open(LOGO) as im:
        logo = im.convert("RGBA")
    w = int(SIZE * LOGO_RATIO)
    h = round(logo.height * w / logo.width)
    logo = logo.resize((w, h), Image.LANCZOS)
    alpha = logo.getchannel("A").point(lambda a: int(a * OPACITY))
    logo.putalpha(alpha)
    return logo


def add_logo(img, logo):
    img = img.convert("RGBA")
    x = SIZE - logo.width - MARGIN
    y = SIZE - logo.height - MARGIN
    img.alpha_composite(logo, (x, y))
    return img.convert("RGB")


def new_run_dir():
    """완성/오늘날짜 폴더를 돌려준다. 없으면 만들고, 있으면 그 폴더에 이어서 쌓는다."""
    run_dir = OUT / date.today().isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def next_number(run_dir, today):
    """폴더에 이미 있는 '오늘날짜_번호.jpg' 다음 번호를 구한다."""
    nums = [
        int(p.stem.rsplit("_", 1)[1])
        for p in run_dir.glob(f"{today}_*.jpg")
        if p.stem.rsplit("_", 1)[1].isdigit()
    ]
    return max(nums, default=0) + 1


def main(run_dir):
    files = sorted(
        p for p in SRC.iterdir()
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")
        and unicodedata.normalize("NFC", p.name) != LOGO.name
    )
    if not files:
        print("자료 폴더에 jpg, png 사진이 없어요.")
        return

    logo = load_logo()
    today = date.today().isoformat()
    start = next_number(run_dir, today)
    for i, path in enumerate(files, start):
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            # 가운데 기준으로 정사각형 자르기 + 크기 맞추기 (비율 유지)
            img = ImageOps.fit(img, (SIZE, SIZE), Image.LANCZOS, centering=(0.5, 0.5))
            if logo:
                img = add_logo(img, logo)
            out_path = run_dir / f"{today}_{i:02d}.jpg"
            img.save(out_path, "JPEG", quality=95)
        print(f"{path.name} -> {out_path.name}")
    print(f"끝! {len(files)}장을 저장했어요.")


if __name__ == "__main__":
    run_dir = new_run_dir()
    main(run_dir)
    make_captions(run_dir)
    print(f"결과는 '{run_dir.relative_to(BASE)}' 폴더에 있어요.")
