"""
Palette extractor – derives dominant colours from an image.

Uses KMeans clustering on down-sampled pixel data to quickly identify
the most prominent colours, returned as hex strings for CSS consumption.
"""

import random
from typing import List

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


# Pre-defined pleasant fallback palettes used when extraction fails
_FALLBACK_PALETTES: List[List[str]] = [
    ['#e8d5b7', '#d4a574'],
    ['#a8d8ea', '#aa96da'],
    ['#fcbad3', '#ffffd2'],
    ['#c3aed6', '#f9e4c8'],
    ['#b5eaea', '#edf6e5'],
    ['#f5b7b1', '#f9e79f'],
    ['#aed6f1', '#a3e4d7'],
    ['#d5dbdb', '#f0b27a'],
]


def extract_palette(image_path: str, num_colors: int = 2) -> List[str]:
    """
    Extract the dominant colours from an image file.

    The image is resized to 100×100 for speed before running KMeans
    clustering on its RGB pixel values.

    Args:
        image_path: Absolute or relative path to the image file.
        num_colors: Number of dominant colours to extract (default 2).

    Returns:
        A list of hex colour strings, e.g. ``['#e8d5b7', '#d4a574']``.
        Falls back to a random pleasant palette if processing fails.
    """
    try:
        img = Image.open(image_path)
        img = img.resize((100, 100))
        img = img.convert('RGB')

        # Reshape to (10000, 3) array of RGB pixels
        pixels = np.array(img).reshape(-1, 3)

        kmeans = KMeans(n_clusters=num_colors, n_init=10, random_state=42)
        kmeans.fit(pixels)

        # Convert cluster centres to hex strings
        colours: List[str] = []
        for centre in kmeans.cluster_centers_:
            r, g, b = int(centre[0]), int(centre[1]), int(centre[2])
            colours.append(f'#{r:02x}{g:02x}{b:02x}')

        return colours

    except Exception:
        # Return a random pleasant palette as a graceful fallback
        return random.choice(_FALLBACK_PALETTES)[:num_colors]
