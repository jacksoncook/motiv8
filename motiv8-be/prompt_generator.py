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
    backgrounds = [
        # Set A (indices 0-29) - athletic/sports contexts, matches even-month poses
        "A packed Olympic athletics stadium at night, rubber track lit by floodlights, roaring crowd in the stands, motion-blur finish line tape",
        "A professional NBA arena with hardwood court, bright overhead lights, crowd bokeh in the background, dramatic spotlight",
        "An NBA arena at peak atmosphere, rim and backboard lit from above, confetti falling, wide-angle court view",
        "A FIFA World Cup stadium at golden hour, lush green pitch, packed stands blurred, dramatic sky above",
        "A centre-court tennis stadium with manicured grass, white lines crisp, empty opponent's side, dramatic overhead lighting",
        "A grand-slam tennis court at dusk, stadium lights warming the clay surface, crowd noise implied by blurred stands",
        "A Major League Baseball diamond at twilight, infield dirt glowing under stadium lights, outfield grass vivid green",
        "A baseball stadium from the pitcher's mound perspective, batter's box lit, packed crowd blurred behind",
        "A pristine golf course fairway at sunrise, morning mist rising over manicured grass, distant flag on the green",
        "A professional boxing ring under harsh overhead lights, red and blue corner posts, crowd dark beyond the ropes",
        "A gritty boxing gym interior, speed bags hanging, worn canvas floor, single overhead lamp casting hard shadows",
        "An MMA octagon under dramatic arena lighting, chain-link fence casting grid shadows, crowd haze beyond",
        "An open-air yoga retreat at sunrise, wooden deck overlooking misty mountains, soft warm light, incense smoke curling",
        "A world-class Olympic weightlifting platform under competition lighting, scoreboard visible, silent arena",
        "A CrossFit competition floor with rubber mats, chalk dust floating in spotlight beams, industrial warehouse feel",
        "A dramatic granite cliff face in Yosemite, sheer vertical rock stretching out of frame, valley far below",
        "A winding mountain road in the Alps at dawn, pine trees flanking the descent, fresh asphalt glistening",
        "A professional skate park halfpipe at sunset, smooth concrete, graffiti murals on surrounding walls",
        "A massive ocean wave off the coast of Hawaii, deep blue water, white foam crest, horizon stretching wide",
        "A sun-drenched beach volleyball court at a professional tournament, white sand, net casting a long shadow",
        "An NFL stadium at game time, football field with yard lines vivid, end zone visible, deafening crowd blurred",
        "An Olympic gymnastics arena, balance beam lit by a single spot, blue mats below, judges' table in background",
        "A traditional Japanese dojo interior, polished wooden floor, red and white flags on the wall, paper lanterns",
        "An elegant European fencing hall, piste strip stretching into distance, high arched ceilings, soft ambient light",
        "A tranquil Japanese garden at dawn, stone path between maple trees, lantern glowing, koi pond reflecting sky",
        "A vibrant Brazilian favela courtyard with capoeira drums, colorful murals on walls, warm evening light",
        "A dramatic rocky mountain summit at sunrise, 360-degree view of peaks below, golden alpenglow on clouds",
        "A fresh powder ski slope in the Swiss Alps, pristine white snow, pine trees frosted, sky a deep electric blue",
        "A muddy motocross track with berms and jumps, roost flying, grandstand visible behind chain-link fence",
        "A grand concert hall with a full orchestra pit, gilded ceiling, tiered balconies, warm amber stage lighting",
        # Set B (indices 30-59) - occupational/character contexts, matches odd-month poses
        "A grand university library with floor-to-ceiling mahogany shelves, rolling ladders, warm reading lamp pools, dust motes in shafts of light",
        "A lush zoo enclosure with tropical foliage, rope swings, a mossy rock wall, dappled sunlight filtering through canopy",
        "A rustic cattle ranch at golden hour, weathered wooden fence posts, open prairie stretching to the horizon, dust haze",
        "A professional restaurant kitchen, gleaming stainless steel surfaces, copper pots hanging overhead, flames from a gas range",
        "A residential street engulfed in dramatic orange flames and thick smoke, fire truck lights strobing in the foreground",
        "A sterile hospital operating theatre, surgical lights overhead, blue drapes, vital-signs monitor glowing in the corner",
        "A downtown construction site at midday, steel skeleton of a skyscraper rising, crane silhouetted against blue sky",
        "A sunlit artist's studio with canvas-covered floors, paint-splattered walls, large skylights flooding the room with soft light",
        "A packed rock concert stage, laser beams cutting through haze, crowd of thousands lit by moving lights below",
        "A dark nightclub interior with glowing turntables, purple and blue LED wash, crowd of silhouettes on the dance floor",
        "A sweeping National Park trail head at dusk, old-growth trees towering, wooden signpost, mountains fading in the mist",
        "The lunar surface at night, Earth rising on the horizon, scattered moon rocks, inky black sky full of stars",
        "A high-tech research laboratory with glowing centrifuges, neon blue lighting, racks of specimen tubes, clean-room atmosphere",
        "A vintage school classroom with chalk-dusted blackboard, rows of wooden desks, afternoon light through tall windows",
        "A golden wheat field at harvest time, combine harvester tracks in the distance, dramatic cumulus clouds overhead",
        "A misty lake at dawn, wooden dock stretching into still water, reeds along the bank, soft pink sky reflecting below",
        "A dense medieval forest with archery targets tied to oak trees, shafts of light through the canopy, carpet of leaves",
        "A stone medieval castle courtyard, moss on the battlements, flags snapping in the wind, grey overcast dramatic sky",
        "A serene Japanese bamboo grove at dawn, shafts of pale light through tall stalks, stone lantern in the foreground",
        "A sweeping American western prairie at sunset, red rock buttes on the horizon, tumbleweeds, amber dust in the air",
        "A dense Amazon jungle with hanging vines, exotic birds in the canopy, a narrow overgrown path disappearing into shadow",
        "A grand circus tent interior with red and gold stripes, sawdust ring below, spotlight beams crossing in the air",
        "A clear blue sky at altitude with a patchwork of farmland visible 10,000 feet below, wispy clouds at eye level",
        "A dusty professional rodeo arena with wooden chutes, cowboy hat crowd in bleachers, dirt churned up in the ring",
        "A massive outdoor music festival crowd at night, LED stage lighting painting the sky, thousands of phones raised",
        "A busy urban intersection at midday, yellow taxi cabs, pedestrians blurred on crosswalks, glass skyscrapers reflecting sun",
        "A grand theatre stage from the wings, velvet curtains parted, spotlight illuminating the empty centre stage, orchestra pit below",
        "A ceremonial military parade ground with crisp stone paving, national flags lining the path, reviewing stand in the distance",
        "A white sand beach at midday, ocean stretching to the horizon, lifeguard tower casting a shadow on the sand",
        "A Formula 1 pit lane during a race, blurred pit crew equipment, tire marks on the tarmac, grandstand in the background",
    ]

    # Odd months use set B (indices 30-59), even months use set A (indices 0-29)
    now = datetime.now()
    bg_index = (30 * (now.month % 2) + (now.day - 1)) % 60
    selected_background = backgrounds[bg_index]

    # Background-only prompt
    background_prompt = f"{selected_background}, no people, empty scene"
    background_negative_prompt = "blurry, low quality, distorted, people, person, human, face, body, character, figure"

    return background_prompt, background_negative_prompt
