from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "app" / "static" / "images"
WIDTH = 1080
HEIGHT = 1350

TITLES = [
    "Deixe o celular mais fácil de usar",
    "Entenda sua conexão com a internet",
    "Envie mensagens e áudios",
    "Envie fotos com segurança",
    "Reconheça mensagens suspeitas",
    "Cuidado antes de clicar",
    "Proteja suas senhas e códigos",
    "Faça Pix com segurança",
    "Conheça os serviços públicos digitais",
    "Pare, pense e peça ajuda",
]

PHRASES = [
    "Ajuste o celular para o seu conforto.",
    "Saiba quando usa Wi-Fi ou dados móveis.",
    "Confira a conversa antes de enviar.",
    "Observe toda a foto antes de compartilhar.",
    "Pressa e pedido de dinheiro são sinais de alerta.",
    "Verifique antes de abrir um link.",
    "Senha e código são somente seus.",
    "Confira nome e valor antes de confirmar.",
    "Use apenas sites e aplicativos oficiais.",
    "Na dúvida, pare e procure alguém de confiança.",
]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    line_width: int,
    spacing: int,
) -> int:
    lines = wrap(text, width=line_width)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=font, fill=fill)
        y += box[3] - box[1] + spacing
    return y


def generate_image(number: int, title: str, phrase: str) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#F4F8F5")
    draw = ImageDraw.Draw(image)
    dark = "#123A2E"
    green = "#087A55"
    yellow = "#F4BD42"

    draw.rounded_rectangle((70, 65, 1010, 1285), radius=48, fill="#FFFFFF", outline="#C9D9D2", width=5)
    draw.rounded_rectangle((130, 125, 950, 285), radius=35, fill=dark)
    draw.text((175, 160), "CONECTA-ZAP 60+", font=load_font(48, True), fill="#FFFFFF")
    draw.ellipse((390, 340, 690, 640), fill=yellow)
    number_text = f"{number:02d}"
    number_font = load_font(165, True)
    box = draw.textbbox((0, 0), number_text, font=number_font)
    draw.text(((WIDTH - (box[2] - box[0])) // 2, 390), number_text, font=number_font, fill=dark)

    y = draw_centered_lines(draw, title, 710, load_font(66, True), dark, 27, 14)
    draw.line((220, y + 28, 860, y + 28), fill=green, width=8)
    draw_centered_lines(draw, phrase, y + 80, load_font(40), "#314E45", 40, 12)

    notice = "IMAGEM PROVISÓRIA"
    notice_font = load_font(30, True)
    notice_box = draw.textbbox((0, 0), notice, font=notice_font)
    draw.rounded_rectangle((330, 1185, 750, 1245), radius=20, fill="#E1F5ED")
    draw.text(((WIDTH - (notice_box[2] - notice_box[0])) // 2, 1199), notice, font=notice_font, fill=green)

    output_path = OUTPUT_DIRECTORY / f"infografico-{number:02d}.png"
    image.save(output_path, format="PNG", optimize=True)


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for index, (title, phrase) in enumerate(zip(TITLES, PHRASES, strict=True), start=1):
        generate_image(index, title, phrase)
    print(f"Generated 10 placeholder images in {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    main()
