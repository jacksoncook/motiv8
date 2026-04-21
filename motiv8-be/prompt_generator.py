"""
Shared prompt generation logic for image generation
Used by both the API endpoint and batch processing
"""

from datetime import datetime
import random
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
    person_prompt, person_negative = get_person_prompt(user)
    background_prompt, background_negative = get_background_prompt(user)

    # Combined prompt for backward compatibility
    prompt = f"{person_prompt}, {background_prompt}"
    negative_prompt = person_negative

    return prompt, negative_prompt


def get_person_prompt(user: User):
    """
    Get the prompt for generating just the person (no background).

    Args:
        user: User object with gender, mode settings

    Returns:
        tuple: (person_prompt, person_negative_prompt)
    """
    gender_term = "female" if user.gender == "female" else "male"

    # Gender component - female always gets "two piece", male gets "in underwear"
    if user.gender == "female":
        gender_component = f"full body photo of a {gender_term} in a two piece"
    else:
        gender_component = f"full body photo of a {gender_term} in underwear"

    # 60 upright poses - selection alternates sets of 30 by odd/even month
    poses = [
        # Set A (indices 0-29) - used on even months
        "full sprint stride (mid-run, upright)",
        "basketball jump shot release",
        "basketball dunk mid-air",
        "soccer kick (striking the ball)",
        "tennis forehand swing",
        "tennis serve toss and strike",
        "baseball pitch windup",
        "baseball bat swing follow-through",
        "golf swing at full extension",
        "boxer throwing a punch",
        "boxer defensive guard stance",
        "MMA fighter mid-kick",
        "yoga warrior pose (Warrior II)",
        "weightlifter deadlift lockout",
        "weightlifter clean and jerk overhead",
        "rock climber reaching upward on a wall",
        "cyclist leaning into a turn",
        "skater performing a jump (mid-air spin)",
        "surfer riding a wave (balanced stance)",
        "volleyball player spiking mid-air",
        "quarterback throwing a football",
        "gymnast on balance beam, arms extended",
        "martial artist in fighting stance",
        "fencer in lunging attack",
        "yoga tree pose (Vrksasana)",
        "capoeira fighter in ginga stance",
        "hiker reaching mountain summit, arms raised",
        "snowboarder catching big air",
        "motocross rider mid-jump on dirt bike",
        "conductor leading an orchestra, baton raised",
        # Set B (indices 30-59) - used on odd months
        "librarian holding a large book open, reading aloud",
        "zookeeper with a monkey perched on their shoulder",
        "rancher leaning over a fence feeding a cow",
        "chef tossing pizza dough high in the air",
        "firefighter gripping a hose, spraying water",
        "surgeon in scrubs, gloved hands raised",
        "construction worker swinging a hammer overhead",
        "painter on a ladder, brush raised to a canvas",
        "musician playing electric guitar on stage",
        "DJ at turntables, one hand raised",
        "park ranger pointing at a trail map on a post",
        "astronaut in spacesuit standing on lunar surface",
        "scientist holding up a glowing flask",
        "teacher pointing at a chalkboard",
        "farmer throwing seeds across an open field",
        "fisherman casting a fishing line",
        "archer drawing a bow, aimed upward",
        "knight in armor holding a sword aloft",
        "samurai in ready stance gripping a katana",
        "cowboy spinning a lasso overhead on horseback",
        "explorer in jungle with machete raised",
        "circus performer juggling torches",
        "skydiver in freefall spread-eagle position",
        "bull rider gripping the rope on a bucking bull",
        "rock musician crowd surfing, arms outstretched",
        "police officer directing traffic, arm raised",
        "dancer mid-leap on stage",
        "soldier standing at attention in full uniform",
        "lifeguard standing on watchtower scanning the horizon",
        "race car driver standing beside car, helmet raised",
    ]

    # Odd months use set B (indices 30-59), even months use set A (indices 0-29)
    now = datetime.now()
    pose_index = (30 * (now.month % 2) + (now.day - 1)) % 60
    selected_pose = poses[pose_index]
    pose_component = f"in {selected_pose}"

    # Mode component based on user's selected mode
    # Fallback to anti_motivation_mode for backward compatibility
    mode = user.mode or ("shame" if user.anti_motivation_mode else ("toned" if user.gender == "female" else "ripped"))

    if mode == "shame":
        # Shame mode: demotivational, unhealthy appearance - same for all genders
        mode_component = "who is obese, overweight, hairy, unhealthy, ill-looking, out of shape, slovenly appearance"
        negative_prompt = "blurry, low quality, distorted, deformed, deformed limbs, extra limbs, missing limbs, monochrome, lowres, worst quality, muscular, fit, healthy, athletic, nude, naked, nudity, exposed genitals"
    elif mode == "toned":
        # Toned mode: athletic, fit physique
        mode_component = "with toned athletic physique"
        negative_prompt = "blurry, low quality, distorted, deformed, deformed limbs, extra limbs, missing limbs, ugly, bad anatomy, monochrome, lowres, worst quality, nude, naked, nudity, exposed genitals"
    elif mode == "ripped":
        # Ripped mode: extremely muscular, bodybuilder physique
        mode_component = "bodybuilder with extremely muscular physique"
        negative_prompt = "blurry, low quality, distorted, deformed, deformed limbs, extra limbs, missing limbs, ugly, bad anatomy, monochrome, lowres, worst quality, nude, naked, nudity, exposed genitals"
    elif mode == "furry":
        # Furry mode: human face with animal features and furry body
        # Randomly selects an animal type for variety

        # Detailed descriptions for each animal type - maintains human face structure with animal augmentations
        furry_descriptions = {
            "cat": "with human facial structure augmented by feline features including subtle whisker markings, triangular feline ears on top of head, cat-like eye makeup with slit pupils, body covered in detailed fur texture, digitigrade legs, paw-like feet, and a long tail",
            "fox": "with human facial structure augmented by vulpine features including fox ear tufts on top of head, russet and white fur coloring on body, fox-like eye makeup with bright alert eyes, body covered in detailed russet and white fur texture, digitigrade legs, paw-like feet with black toe beans, and a large bushy tail",
            "wolf": "with human facial structure augmented by lupine features including pointed wolf ears on top of head, grey and white fur coloring on body, wolf-like eye makeup with intense eyes, body covered in detailed grey and white fur texture, digitigrade legs, large paw-like feet, and a thick tail",
            "dragon": "with human facial structure augmented by dragon features including small horns, dragon ear fins, reptilian eye makeup with slit pupils, body covered in detailed scales, digitigrade legs, clawed feet, large wings folded against back, and a long powerful tail"
        }

        furry_animals = ["cat", "fox", "wolf", "dragon"]
        animal = random.choice(furry_animals)
        animal_description = furry_descriptions[animal]

        # Gender-appropriate clothing
        if user.gender == "female":
            clothing = "wearing fitted athletic two-piece designed for a furry body"
        else:
            clothing = "wearing fitted athletic briefs designed for a furry body"

        mode_component = f"{animal_description}, {clothing}, maintaining human face and facial structure, ultra-detailed fur texture on body, high-end VFX realism, cinematic lighting, shallow depth of field, 8k detail"
        negative_prompt = "blurry, low quality, distorted, deformed, deformed limbs, extra limbs, missing limbs, ugly, bad anatomy, lowres, worst quality, nude, naked, nudity, exposed genitals, cartoon, anime, animal muzzle, animal snout, full animal face, beast face"
    else:
        # Default to toned if mode is invalid
        mode_component = "with toned athletic physique"
        negative_prompt = "blurry, low quality, distorted, deformed, deformed limbs, extra limbs, missing limbs, ugly, bad anatomy, monochrome, lowres, worst quality, nude, naked, nudity, exposed genitals, background, scenery, buildings, landscape"

    # Build person prompt (no background)
    # Add "professional" prefix for non-shame modes, include "plain background" to avoid generating scenery
    if mode != "shame":
        person_prompt = f"professional {gender_component} {mode_component} {pose_component}, plain neutral background, studio lighting, highly detailed, 8k, photorealistic"
    else:
        person_prompt = f"{gender_component} {mode_component} {pose_component}, plain neutral background, studio lighting, highly detailed, 8k, photorealistic"

    return person_prompt, negative_prompt


def get_background_prompt(user: User):
    """
    Get the prompt for generating just the background (no people).

    Args:
        user: User object (used for consistency/future customization)

    Returns:
        tuple: (background_prompt, background_negative_prompt)
    """
    # Nature & Wildlife Scenes - One for each day of the month (30 total)
    backgrounds = [
        "A hyperrealistic rainforest at dawn with a jaguar silently emerging from dense mist, water droplets on leaves, cinematic lighting, ultra-detailed foliage",
        "A snowy Arctic landscape with a lone polar bear walking across cracked ice under a glowing aurora borealis, photorealistic textures",
        "A golden savanna at sunset with a pride of lions resting under an acacia tree, long shadows, dust particles in warm light",
        "A deep ocean abyss with a bioluminescent jellyfish illuminating the dark water, floating particles, highly detailed light diffusion",
        "A misty bamboo forest with a giant panda eating leaves, soft diffused light, atmospheric fog",
        "A desert canyon with a rattlesnake coiled on sunlit rocks, heat haze, sharp shadows, ultra-detailed scales",
        "A tropical beach at sunrise with sea turtles crawling toward the ocean, wet sand reflections, soft pastel sky",
        "A dense swamp with an alligator partially submerged in murky water, reflections, floating algae, moody lighting",
        "A mountain cliff with an eagle soaring through dramatic clouds, sharp wind-swept details, high contrast sky",
        "A lush meadow with a herd of deer grazing among wildflowers, morning dew, soft golden light",
        "A dark cave interior with bats hanging from the ceiling, subtle light rays entering from above, textured rock surfaces",
        "A coral reef ecosystem with colorful fish and a curious octopus blending into rocks, ultra-detailed underwater lighting",
        "A foggy forest clearing with a wolf pack moving through shadows, soft blue tones, cinematic atmosphere",
        "A frozen tundra with a snow fox camouflaged in white terrain, minimal color palette, crisp detail",
        "A riverbank at sunset with a hippo partially submerged, rippling water reflections, warm orange glow",
        "A dense jungle canopy with a toucan perched on a branch, vibrant colors, depth of field blur",
        "A rocky shoreline with seals lounging on wet stones, crashing waves, realistic water splashes",
        "A stormy grassland with a herd of elephants walking through rain, dramatic clouds, wet skin textures",
        "A night desert scene with a scorpion glowing under ultraviolet light, star-filled sky, high contrast",
        "A tranquil pond with a koi fish swimming beneath lily pads, crystal clear water, soft reflections",
        "A volcanic landscape with a Komodo dragon walking near flowing lava, heat glow, rugged terrain",
        "A snowy forest with a moose standing among frosted trees, breath visible in cold air",
        "A city rooftop garden at dusk with pigeons perched along ledges, urban skyline bokeh",
        "A mangrove forest with a crocodile gliding through shallow water, tangled roots, filtered sunlight",
        "A windswept steppe with wild horses running across open plains, motion blur, dramatic sky",
        "A cherry blossom garden with a red fox sitting among falling petals, soft pink tones, serene mood",
        "A dense rainforest river with a capybara lounging at the edge, humid atmosphere, rich greens",
        "A high-altitude Himalayan ridge with a snow leopard perched on rocks, expansive mountain backdrop",
        "A farm field at sunrise with a rooster crowing on a wooden fence, golden haze, rustic detail",
        "A mystical forest at twilight with fireflies surrounding a resting stag, glowing particles, ethereal lighting"
    ]

    # Select background based on day of month (1-30/31)
    day_of_month = datetime.now().day
    # Use modulo to handle days 31 in longer months
    selected_background = backgrounds[(day_of_month - 1) % len(backgrounds)]

    # Background-only prompt
    background_prompt = f"{selected_background}, no people, empty scene"
    background_negative_prompt = "blurry, low quality, distorted, people, person, human, face, body, character, figure"

    return background_prompt, background_negative_prompt
