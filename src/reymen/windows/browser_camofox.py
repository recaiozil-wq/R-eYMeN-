# -*- coding: utf-8 -*-
"""browser_camofox.py — Tarayici Parmak Izi Korumasi.

Playwright ile tarayici acarken fingerprint'i gizler,
bot tespitini engeller. User-agent, viewport, header
ve WebGL parmak izini maskeeler.
"""

import json
import random
from pathlib import Path

# Gercelci user-agent'lar (Chrome, Firefox, Edge)
USER_AGENTLER = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/125.0.0.0 Safari/537.36",
]

VIEWPORT_COZUNURLUKLER = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
]


class Camofox:
    """Tarayici parmak izi koruyucu."""

    @staticmethod
    def rastgele_user_agent() -> str:
        return random.choice(USER_AGENTLER)

    @staticmethod
    def rastgele_viewport() -> dict:
        return random.choice(VIEWPORT_COZUNURLUKLER)

    @staticmethod
    def context_ayarlari() -> dict:
        """Playwright browser context ayarlari."""
        viewport = Camofox.rastgele_viewport()
        return {
            "user_agent": Camofox.rastgele_user_agent(),
            "viewport": viewport,
            "locale": "tr-TR",
            "timezone_id": "Europe/Istanbul",
            "geolocation": {"latitude": 41.0082, "longitude": 28.9784},
            "permissions": ["geolocation"],
            # WebGL parmak izini gizle
            "color_scheme": "light",
            "reduced_motion": "no-preference",
            "forced_colors": "none",
        }

    @staticmethod
    def gizlilik_betikleri() -> list[str]:
        """Sayfaya inject edilecek gizlilik betikleri."""
        return [
            """// WebGL parmak izini gizle
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(p) {
                if (p === 37445) return 'Intel Inc.';
                if (p === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, p);
            };""",
            """// Canvas parmak izini gurultule
            const toDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {
                const r = Math.random() * 0.01;
                return toDataURL.call(this) + r.toString(36).slice(2, 5);
            };""",
            """// Navigator bilgilerini gizle
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({ name: 'Chrome PDF Plugin' })),
            });
            Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'en-US'] });""",
        ]


if __name__ == "__main__":
    c = Camofox()
    print("User-Agent:", c.rastgele_user_agent()[:50])
    print("Viewport:", c.rastgele_viewport())
    print("Context ayarlari:", json.dumps(c.context_ayarlari(), indent=2)[:200])
