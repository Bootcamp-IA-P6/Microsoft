"""
themes.py — Paleta de la app en 3 modos.

Modo "colorblind" usa la paleta Okabe-Ito (Okabe & Ito, 2008), el estándar
de facto para paletas seguras en daltonismo — evita depender de rojo/verde
como únicos diferenciadores y usa azul/naranja, que sí se distinguen en
deuteranopia, protanopia y tritanopia.

Nombre de la app en un solo sitio — cámbialo aquí si "ParaBus" no convence.
"""

APP_TITLE = "NAVI"
APP_TAGLINE = "Tu copiloto de movilidad"
APP_USAGE = "Pregunta cuándo llega tu autobús en el centro de Madrid"

THEMES = {
    "colorblind": {
        "label_key": "theme_colorblind",
        # Paleta Okabe-Ito — máximo contraste, sin depender de rojo/verde.
        # Es el modo por defecto: además de accesible para daltonismo,
        # es el que mejor contrasta para turistas al sol, en la calle.
        "bg": "#FFFFFF",
        "bg_card": "#F5F5F5",
        "text": "#000000",
        "text_secondary": "#3D3D3D",
        "primary": "#0072B2",         # azul Okabe-Ito
        "accent": "#E69F00",          # naranja Okabe-Ito
        "border": "#000000",
        "badge_mock_bg": "#F0E442", "badge_mock_text": "#000000",   # amarillo
        "badge_local_bg": "#56B4E9", "badge_local_text": "#000000", # celeste
        "badge_azure_bg": "#009E73", "badge_azure_text": "#FFFFFF", # verde-azulado
        "border_width": "2px",  # más contraste estructural, no solo de color
    },
    "dark": {
        "label_key": "theme_dark",
        "bg": "#0F1B2D",
        "bg_card": "#1B2C46",
        "text": "#F2F3F5",
        "text_secondary": "#C7D0DC",  # antes #A9B3C2, subido para más contraste
        "primary": "#7FB3E0",
        "accent": "#F0A94E",
        "border": "#3A4D6B",          # antes #28374F, más visible
        "badge_mock_bg": "#4A3B1C", "badge_mock_text": "#F0C97A",
        "badge_local_bg": "#1E3A5C", "badge_local_text": "#9CC7F0",
        "badge_azure_bg": "#1E3D2E", "badge_azure_text": "#8FE0B0",
        "border_width": "1px",
    },
}


def get_theme(mode: str) -> dict:
    return THEMES.get(mode, THEMES["colorblind"])
