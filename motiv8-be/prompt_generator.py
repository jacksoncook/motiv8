"""
Shared prompt generation logic for image generation
Used by both the API endpoint and batch processing
"""

from datetime import datetime
from models import User


def get_prompts_for_user(user: User):
    """
    Get the appropriate prompt and negative prompt based on user settings.

    Prompt structure: gender component + mode component + background component

    Args:
        user: User object with gender, mode settings

    Returns:
        tuple: (prompt, negative_prompt)
    """
    # Asian Cities - Cycling through iconic locations (7 cities for 7 days)
    asian_cities = [
        "Seoul, Korea with vibrant neon-lit skyscrapers, traditional hanok rooftops, and cherry blossoms along modern streets",
        "Nara, Japan with ancient wooden temples, peaceful deer roaming through gardens, and traditional Japanese architecture",
        "Tokyo, Japan with towering skyscrapers, bustling Shibuya crossing, and bright neon signs illuminating the streets",
        "Taipei, Taiwan with Taipei 101 piercing the sky, night markets glowing with lanterns, and lush mountain backdrop",
        "Beijing, China with the majestic Forbidden City, traditional imperial architecture, and red palace walls",
        "Moscow, Russia with colorful onion domes of Saint Basil's Cathedral, Red Square, and snow-dusted architecture",
        "Hiroshima, Japan with the iconic Atomic Bomb Dome by the river, Peace Memorial Park, and modern cityscape beyond"
    ]

    # Select city based on day of week (0=Monday, 6=Sunday)
    day_of_week = datetime.now().weekday()
    city_background = asian_cities[day_of_week % len(asian_cities)]

    gender_term = "female" if user.gender == "female" else "male"

    # Gender component - female always gets "two piece", male gets "in underwear"
    if user.gender == "female":
        gender_component = f"full body photo of a {gender_term} in a two piece"
    else:
        gender_component = f"full body photo of a {gender_term} in underwear"

    # Mode component based on user's selected mode
    # Fallback to anti_motivation_mode for backward compatibility
    mode = user.mode or ("shame" if user.anti_motivation_mode else ("toned" if user.gender == "female" else "ripped"))

    if mode == "shame":
        # Shame mode: demotivational, unhealthy appearance - same for all genders
        mode_component = "who is obese, overweight, hairy, unhealthy, ill-looking, out of shape, slovenly appearance"
        negative_prompt = "blurry, low quality, distorted, deformed, monochrome, lowres, worst quality, low quality, muscular, fit, healthy, athletic, nude, naked, nudity, exposed genitals"
    elif mode == "toned":
        # Toned mode: athletic, fit physique
        mode_component = "with toned athletic physique"
        negative_prompt = "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality, nude, naked, nudity, exposed genitals"
    elif mode == "ripped":
        # Ripped mode: extremely muscular, bodybuilder physique
        mode_component = "bodybuilder with extremely muscular physique"
        negative_prompt = "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality, nude, naked, nudity, exposed genitals"
    elif mode == "furry":
        # Furry mode: human with anthropomorphic furry body
        # Alternates through different animals based on day of year
        day_of_year = datetime.now().timetuple().tm_yday
        furry_animals = ["wolf", "fox", "cat"]
        animal = furry_animals[day_of_year % len(furry_animals)]
        mode_component = f"human with an anthropomorphic {animal}-style furry body"
        negative_prompt = "blurry, low quality, distorted, deformed, ugly, bad anatomy, lowres, worst quality, nude, naked, nudity, exposed genitals, animal face, animal head, snout, muzzle, whiskers, cartoon, anime, mask, helmet, human"
    else:
        # Default to toned if mode is invalid
        mode_component = "with toned athletic physique"
        negative_prompt = "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality, nude, naked, nudity, exposed genitals"

    # Background component
    background_component = f"at {city_background}, highly detailed, 8k, photorealistic"

    # Add "professional" prefix for non-shame modes
    if mode != "shame":
        prompt = f"professional {gender_component} {mode_component}, {background_component}"
    else:
        prompt = f"{gender_component} {mode_component}, {background_component}"

    return prompt, negative_prompt
