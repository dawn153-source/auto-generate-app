import re
from datetime import datetime
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC = BASE / "자료"
OUT = BASE / "완성"

# '넣음' 같은 메모 말투를 '넣었습니다' 같은 말로 바꾸는 표
ENDINGS = {"넣음": "넣었습니다", "않음": "않습니다", "있음": "있습니다", "많음": "많습니다", "없음": "없습니다"}


def find_text(name):
    """띄어쓰기가 있든 없든, 맥의 한글 저장 방식이 달라도 파일을 찾는다."""
    want = unicodedata.normalize("NFC", name).replace(" ", "")
    for p in SRC.glob("*.txt"):
        if unicodedata.normalize("NFC", p.name).replace(" ", "") == want:
            return p.read_text(encoding="utf-8")
    return None


def has_batchim(word):
    """마지막 글자에 받침이 있으면 True (조사 이/가, 은/는 고르기용)."""
    ch = word.strip("'\" ")[-1]
    return "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 != 0


def polish(text):
    text = text.strip()
    # '좌석 많음' -> '좌석이 많습니다' (앞말에 이/가를 붙인다)
    m = re.match(r"(.*?)(\S+)\s+(많|있|없)음$", text)
    if m:
        pre, noun, stem = m.groups()
        return f"{pre}{noun}{'이' if has_batchim(noun) else '가'} {stem}습니다"
    for old, new in ENDINGS.items():
        if text.endswith(old):
            return text[: -len(old)] + new
    return text


def parse_shop(text):
    info = {}
    for line in text.splitlines():
        if ":" in line and not line.strip().startswith("-"):
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    bullets = [l.strip()[1:].strip() for l in text.splitlines() if l.strip().startswith("-")]

    shop = {
        "name": info.get("가게 이름", ""),
        "loc": info.get("위치", ""),
        "features": [polish(f) for f in info.get("가게 특징", "").split(",") if f.strip()],
        "customers": info.get("주 고객층", ""),
        "menu": None,
        "discount": None,
    }
    for b in bullets:
        if "할인" in b:
            shop["discount"] = b
            continue
        m = re.search(r"'([^']+)'\s*([\d,]+원)\s*,?\s*(.*)", b)
        if m:
            shop["menu"] = {
                "name": m.group(1),
                "price": m.group(2),
                "desc": [polish(d) for d in m.group(3).split(",") if d.strip()],
            }
    return shop


def make_hashtags(shop):
    info = " ".join([shop["name"]] + shop["features"])
    regions = [w for w in shop["loc"].split() if w not in ("지구", "시", "구")]
    kinds = ["카페"]
    if "커피" in info:
        kinds.append("커피")
    tags = [r + "카페" for r in regions]
    if "스페셜티" in info:
        tags.append("스페셜티커피")
    if "로스팅" in info:
        tags.append("로스터리카페")
    if shop["menu"]:
        tags.append(shop["menu"]["name"].replace(" ", ""))
    if shop["discount"]:
        m = re.search(r"(\S+)\s*[\d,]+원\s*할인", shop["discount"])
        if m:
            tags.append(m.group(1))
    if shop["name"]:
        tags.append(shop["name"].replace(" ", ""))
    if regions:
        tags.append(regions[0] + "커피")
    tags += ["카페스타그램", "오늘의커피", "커피한잔", "카페투어"]
    result = []
    for t in tags:
        t = "#" + t
        if t not in result:
            result.append(t)
    return result[:10]


def sentences(descs):
    """설명 조각들을 '한 문장 = 한 줄'로 만든다."""
    return [d if d.endswith(".") else d + "." for d in descs]


def make_texts(shop):
    name, loc = shop["name"], shop["loc"]
    menu, discount = shop["menu"], shop["discount"]
    feats = shop["features"]
    desc = sentences(menu["desc"]) if menu else []

    emotional = []
    if menu:
        emotional.append(f"이번 주에 '{menu['name']}'을 새로 내놓습니다." if has_batchim(menu["name"])
                         else f"이번 주에 '{menu['name']}'를 새로 내놓습니다.")
        emotional += desc
        emotional.append("")
    if len(feats) > 1:
        emotional.append(f"{feats[-1]}.")
    emotional.append("천천히 쉬다 가시기 바랍니다.")
    emotional.append(f"{loc}에서 기다리겠습니다.")

    info = [f"{name} 이번 주 신메뉴를 알려드립니다.", ""]
    if menu:
        info.append(f"'{menu['name']}' {menu['price']}입니다.")
        info += desc
        info.append("")
    if feats:
        info.append(f"{', '.join(feats)}.")
    info.append(f"위치는 {loc}입니다.")

    event = []
    if discount:
        event.append("이번 주 혜택을 미리 말씀드립니다.")
        event.append(f"{discount}해 드립니다.")
        event.append("")
    if menu:
        event.append(f"신메뉴 '{menu['name']}'({menu['price']})도 준비했습니다.")
    event.append(f"{name}, {loc}에서 기다리겠습니다.")

    return {
        "감성형": "\n".join(emotional),
        "정보형": "\n".join(info),
        "이벤트형": "\n".join(event),
    }


def make_blog(shop):
    """네이버 블로그용: 500자 안팎, 해시태그 없음, 합니다체."""
    name, loc = shop["name"], shop["loc"]
    menu, discount = shop["menu"], shop["discount"]
    topic = "은" if has_batchim(name) else "는"
    paras = [f"안녕하세요, {name}입니다.\n이번 주에 새로 준비한 소식을 말씀드립니다."]
    if menu:
        lines = [f"이번 주 신메뉴는 '{menu['name']}'입니다.", f"가격은 {menu['price']}입니다."]
        lines += sentences(menu["desc"])
        lines += ["처음 드시는 분도 부담 없이 드실 수 있도록 정성껏 준비했습니다.",
                  "한 잔 천천히 드시면서 쉬다 가시기 바랍니다."]
        paras.append("\n".join(lines))
    if shop["features"]:
        lines = [f"{name}{topic} 이런 곳입니다."] + [f"- {f}" for f in shop["features"]]
        if "사무실" in shop["customers"]:
            lines.append("근처 사무실에서 일하시는 분들도, 지나가시는 분들도 모두 편하게 오시면 됩니다.")
        lines.append("바쁜 하루 중 잠깐 쉬고 싶을 때 들러 주십시오.")
        paras.append("\n".join(lines))
    if discount:
        paras.append(f"이번 주 할인도 미리 말씀드립니다.\n{discount}해 드립니다.\n오전에 들러 주시는 분들께 드리는 작은 혜택입니다.")
    paras.append(
        f"위치는 {loc}입니다.\n근처에 오실 일이 있으시면 편하게 방문해 주십시오.\n"
        f"끝까지 읽어 주셔서 감사합니다.\n다음 소식도 곧 전해드리겠습니다."
    )
    return "\n\n".join(paras)


def make_kakao(shop):
    """카카오톡 단골 공지용: 3줄 이내, 존댓말."""
    lines = [f"안녕하세요, {shop['name']}입니다."]
    if shop["menu"]:
        lines.append(f"이번 주 신메뉴는 '{shop['menu']['name']}'({shop['menu']['price']})입니다.")
    if shop["discount"]:
        lines.append(f"{shop['discount']}해 드립니다.")
    else:
        lines.append(f"{shop['loc']}에서 기다리겠습니다.")
    return "\n".join(lines[:3])


def make_captions(out_dir=OUT):
    text = find_text("가게정보.txt")
    if text is None:
        print("'자료' 폴더에 '가게 정보.txt'가 없어서 문구 만들기는 건너뛰어요.")
        return
    try:
        shop = parse_shop(text)
        if not shop["name"]:
            raise ValueError("'가게 이름:' 줄을 찾지 못했어요.")
        texts = make_texts(shop)
        tags = make_hashtags(shop)
        blog = make_blog(shop)
        kakao = make_kakao(shop)
    except Exception as e:
        print(f"문구 만들기에 실패했어요 ({type(e).__name__}): {e}")
        print("사진 변환은 그대로 진행돼요.")
        return

    parts = ["━━━━━ 인스타그램 ━━━━━"]
    parts += [f"[{i}. {k}]\n{v}" for i, (k, v) in enumerate(texts.items(), 1)]
    parts.append("[해시태그]\n" + " ".join(tags))
    parts.append("━━━━━ 네이버 블로그 ━━━━━\n" + blog)
    parts.append("━━━━━ 카카오톡 단골 공지 ━━━━━\n" + kakao)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = "\n\n".join(parts) + "\n"
    target = out_dir / "홍보문구.txt"
    if target.exists():
        # 같은 날 또 만들면 이전 문구는 두고 아래에 이어서 붙인다
        stamp = datetime.now().strftime("%H:%M")
        body = target.read_text(encoding="utf-8") + f"\n===== {stamp} 추가 =====\n\n" + body
    target.write_text(body, encoding="utf-8")
    print("홍보문구.txt를 저장했어요.")


if __name__ == "__main__":
    make_captions()
