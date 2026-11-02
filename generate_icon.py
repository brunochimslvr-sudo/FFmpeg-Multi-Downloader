import math
from PIL import Image, ImageDraw

def create_app_icon(output_path="app_icon.ico"):
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Fundo Squircle com cantos arredondados e gradiente escuro
    margin = 12
    r = 52  # raio dos cantos
    box = [margin, margin, size - margin, size - margin]

    # Desenha sombra suave externa
    for shadow_offset in range(6, 0, -2):
        s_box = [box[0] - shadow_offset, box[1] - shadow_offset + 3, box[2] + shadow_offset, box[3] + shadow_offset + 3]
        draw.rounded_rectangle(s_box, radius=r + shadow_offset, fill=(0, 0, 0, 25))

    # Base escura com degradê sutil
    base_color_top = (21, 23, 27, 255)       # #15171B
    base_color_bot = (13, 14, 17, 255)       # #0D0E11

    # Cria máscara para preencher com degradê
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(box, radius=r, fill=255)

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base_draw = ImageDraw.Draw(base)
    for y in range(box[1], box[3]):
        ratio = (y - box[1]) / (box[3] - box[1])
        r_c = int(base_color_top[0] * (1 - ratio) + base_color_bot[0] * ratio)
        g_c = int(base_color_top[1] * (1 - ratio) + base_color_bot[1] * ratio)
        b_c = int(base_color_top[2] * (1 - ratio) + base_color_bot[2] * ratio)
        base_draw.line([(box[0], y), (box[2], y)], fill=(r_c, g_c, b_c, 255))

    img.paste(base, (0, 0), mask)

    # Borda fina de destaque (accent amber #F5A524 com transparência)
    draw.rounded_rectangle(box, radius=r, outline=(245, 165, 36, 120), width=3)

    # 2. Símbolo central: Download elegante com gradiente Âmbar -> Laranja vibrante
    # Seta de download central:
    cx = size // 2
    cy = size // 2 - 8

    # Haste da seta
    stem_w = 26
    stem_h = 75
    stem_box = [cx - stem_w // 2, cy - 40, cx + stem_w // 2, cy + 30]
    draw.rounded_rectangle(stem_box, radius=12, fill=(245, 165, 36, 255))

    # Ponta da seta (triângulo arredondado)
    arrow_pts = [
        (cx - 56, cy + 18),
        (cx + 56, cy + 18),
        (cx, cy + 74)
    ]
    draw.polygon(arrow_pts, fill=(255, 185, 64, 255))
    # ponta suave
    draw.ellipse([cx - 8, cy + 68, cx + 8, cy + 78], fill=(255, 185, 64, 255))

    # 3. Base do Download (bandeja inferior arredondada estilo dock)
    tray_y = size - margin - 52
    tray_h = 16
    tray_w = 120
    tray_box = [cx - tray_w // 2, tray_y, cx + tray_w // 2, tray_y + tray_h]
    draw.rounded_rectangle(tray_box, radius=8, fill=(245, 165, 36, 255))

    # 4. Pequenos ícones complementares: Nota musical e claquete discretas no topo
    # Ponto decorativo musical à direita
    draw.ellipse([cx + 60, cy - 35, cx + 78, cy - 17], fill=(245, 165, 36, 180))
    draw.rectangle([cx + 74, cy - 35, cx + 78, cy - 5], fill=(245, 165, 36, 180))

    # Ponto decorativo play à esquerda
    play_pts = [(cx - 75, cy - 32), (cx - 75, cy - 18), (cx - 62, cy - 25)]
    draw.polygon(play_pts, fill=(245, 165, 36, 180))

    # Salva múltiplos tamanhos no arquivo .ico para qualidade perfeita em qualquer DPI
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(output_path, format="ICO", sizes=sizes)
    print("Ícone gerado com sucesso:", output_path)

if __name__ == "__main__":
    create_app_icon()
