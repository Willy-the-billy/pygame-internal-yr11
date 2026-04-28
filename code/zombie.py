import pygame  # game library for graphics, input, etc.
import random  # for random enemy spawning
import sys     # for exiting program
import math    # for angles, distance, movement
import json    # for saving/loading data
from pathlib import Path  # for file paths

pygame.init()  # start pygame

# ---------------- WINDOW SETUP ----------------
window_width = 480
window_height = 480

# gets your monitor resolution
max_window_width, max_window_height = pygame.display.get_desktop_sizes()[0]

FPS = 60  # frames per second

# create window (resizable)
screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
pygame.display.set_caption("Zombie Survival")  # window title
clock = pygame.time.Clock()  # controls FPS

# ---------------- BACKGROUND SETUP ----------------
# loads background image from parent folder
asset_path = Path(__file__).resolve().parent.parent / "repeating-background-1.png"
background_img = pygame.image.load(asset_path).convert()

TILE_SCALE = 2  # scale image bigger
background_img = pygame.transform.scale_by(background_img, TILE_SCALE)

# get tile size (used for repeating background)
tile_width = background_img.get_width()
tile_height = background_img.get_height()

# draws repeating scrolling background based on camera
def draw_background(surface, image, camera_x, camera_y, window_width, window_height):
    start_x = -int(camera_x) % tile_width - tile_width
    start_y = -int(camera_y) % tile_height - tile_height

    # tile image across screen
    for x in range(start_x, window_width + tile_width, tile_width):
        for y in range(start_y, window_height + tile_height, tile_height):
            surface.blit(image, (x, y))

# ---------------- PLAYER DATA ----------------
PLAYER = {
    "x": window_width / 2,   # position
    "y": window_height / 2,
    "speed": 5,              # movement speed
    "radius": 10,            # size
    "color": (60, 140, 255),
    "max_health": 100,
    "contact_damage": 20,    # damage taken when touching enemy
    "damage_cooldown_frames": 45,  # delay between damage ticks
    "health": 100,
    "damage_cooldown_timer": 0,
}

# ---------------- GUN DATA ----------------
GUN = {
    "color": (20, 20, 20),
    "length": 22,
    "width": 5,
    "angle": 0,  # direction gun is pointing
}

# ---------------- BULLET DATA ----------------
BULLET = {
    "radius": 4,
    "lifetime": 120,   # frames bullet exists
    "fire_timer": 0,   # cooldown between shots
    "speed": 10,
    "damage": 1,
    "fire_interval": 16,  # delay between shots
    "color": (185, 185, 185),
}

# ---------------- ENEMY BASE STATS ----------------
ENEMY_BASE = {
    "speed": 1.8,
    "max_health": 3,
    "spawn_interval": 90,
    "color": (220, 50, 50),
    "outline_color": (120, 20, 20),
    "radius": 12,
}

# current difficulty-adjusted enemy stats
CURRENT_ENEMY = {
    "speed": ENEMY_BASE["speed"],
    "max_health": ENEMY_BASE["max_health"],
    "spawn_interval": ENEMY_BASE["spawn_interval"],
}

# ---------------- GAME LISTS ----------------
bullets = []   # all active bullets
enemies = []   # all active enemies

left_mouse_was_down = False  # used to prevent holding click spam

# ---------------- FONTS ----------------
FONTS = {
    "small": pygame.font.SysFont(None, 24),
    "title": pygame.font.SysFont(None, 56),
    "menu": pygame.font.SysFont(None, 32),
    "panel_title": pygame.font.SysFont(None, 48),
    "option": pygame.font.SysFont(None, 34),
    "meta": pygame.font.SysFont(None, 26),
}

# save file location
SAVE_FILE_PATH = Path(__file__).resolve().parent.parent / "savegame.json"

# ---------------- COLLISION ----------------
# checks if two circles overlap (used for bullets + enemies + player)
def circles_overlap(x1, y1, radius1, x2, y2, radius2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2 <= (radius1 + radius2) ** 2

# ---------------- SPAWN ENEMY ----------------
def spawn_enemy(target_x, target_y, spawn_width, spawn_height):
    margin = ENEMY_BASE["radius"] + 24

    # half screen size
    half_w, half_h = spawn_width / 2, spawn_height / 2

    # spawn positions around edges of screen
    positions = {
        "top": (random.uniform(target_x - half_w, target_x + half_w), target_y - half_h - margin),
        "right": (target_x + half_w + margin, random.uniform(target_y - half_h, target_y + half_h)),
        "bottom": (random.uniform(target_x - half_w, target_x + half_w), target_y + half_h + margin),
        "left": (target_x - half_w - margin, random.uniform(target_y - half_h, target_y + half_h))
    }

    spawn_x, spawn_y = positions[random.choice(list(positions.keys()))]

    return {
        "x": spawn_x,
        "y": spawn_y,
        "radius": ENEMY_BASE["radius"],
        "speed": CURRENT_ENEMY["speed"],
        "health": CURRENT_ENEMY["max_health"],
        "max_health": CURRENT_ENEMY["max_health"]
    }

# ---------------- GUN + BULLETS ----------------
def get_gun_tip(player_x, player_y, gun_angle):
    # calculates end of gun barrel
    return (
        player_x + math.cos(gun_angle) * GUN["length"],
        player_y + math.sin(gun_angle) * GUN["length"]
    )

def spawn_bullets(player_x, player_y, gun_angle):
    # bullet starts at gun tip
    x, y = get_gun_tip(player_x, player_y, gun_angle)

    return [{
        "x": x,
        "y": y,
        "vx": math.cos(gun_angle) * BULLET["speed"],  # velocity X
        "vy": math.sin(gun_angle) * BULLET["speed"],  # velocity Y
        "life": BULLET["lifetime"],
        "damage": BULLET["damage"],
        "color": BULLET["color"]
    }]

# ---------------- DIFFICULTY SCALING ----------------
def get_difficulty_settings(level):
    speed_scale = 0.75 + level * 0.1
    health_bonus = level // 3
    spawn_scale = max(0.35, 1.15 - level * 0.08)

    return {
        "enemy_speed": ENEMY_BASE["speed"] * speed_scale,
        "enemy_max_health": ENEMY_BASE["max_health"] + health_bonus,
        "enemy_spawn_interval": max(18, int(ENEMY_BASE["spawn_interval"] * spawn_scale))
    }

# ---------------- RESET GAME ----------------
def reset_game_state():
    global bullets, enemies, left_mouse_was_down, enemy_spawn_timer

    # reset player
    PLAYER.update({
        "x": window_width / 2,
        "y": window_height / 2,
        "health": PLAYER["max_health"],
        "damage_cooldown_timer": 0
    })

    GUN["angle"] = 0

    bullets = []
    enemies = []

    enemy_spawn_timer = 0
    BULLET["fire_timer"] = 0
    left_mouse_was_down = False

    # apply difficulty
    settings = get_difficulty_settings(selected_difficulty)
    CURRENT_ENEMY.update(settings)

    # spawn starting enemies
    for _ in range(5):
        enemies.append(spawn_enemy(PLAYER["x"], PLAYER["y"], max_window_width, max_window_height))

# ---------------- SAVE / LOAD ----------------
def write_save_file(name, difficulty, high_score_value):
    save_data = {
        "name": name,
        "difficulty": difficulty,
        "high_score": high_score_value
    }

    with SAVE_FILE_PATH.open("w", encoding="utf-8") as save_file:
        json.dump(save_data, save_file)

def load_save_file():
    if not SAVE_FILE_PATH.exists():
        return None

    try:
        with SAVE_FILE_PATH.open("r", encoding="utf-8") as f:
            save_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    # validate save data
    if not isinstance(save_data, dict):
        return None

    name = str(save_data.get("name", "")).strip()
    difficulty = save_data.get("difficulty", 5)
    high_score = save_data.get("high_score", 0)

    # ensure valid values
    if not name or not isinstance(difficulty, int) or not (1 <= difficulty <= 10) or not isinstance(high_score, int) or high_score < 0:
        return None

    return {
        "name": name,
        "difficulty": difficulty,
        "high_score": high_score
    }

# ---------------- APPLY SAVE ----------------
def apply_save_profile(save_profile):
    global current_player_name, selected_difficulty, high_score, current_save

    current_save = save_profile
    current_player_name = save_profile["name"]
    selected_difficulty = save_profile["difficulty"]
    high_score = save_profile["high_score"]
    # ---------------- TEXT DRAWING ----------------
def draw_centered_text(surface, label, y, color=(245, 245, 245), text_font=None):
    # if no font given, use menu font
    if text_font is None:
        text_font = FONTS["menu"]

    # render text
    text = text_font.render(label, True, color)

    # draw it centered horizontally at given y position
    surface.blit(text, text.get_rect(center=(window_width // 2, y)))


# ---------------- MENU PANEL ----------------
def draw_menu_panel(surface, options, selected_index, hovered_index=-1):
    # dark transparent overlay (background dim)
    overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
    overlay.fill((8, 12, 22, 130))
    surface.blit(overlay, (0, 0))

    # panel size (auto scales with window)
    pw = min(560, max(350, window_width - 60))
    ph = min(500, max(320, window_height - 80))

    pr = pygame.Rect(0, 0, pw, ph)
    pr.center = (window_width // 2, window_height // 2)

    # panel surface
    ps = pygame.Surface((pr.width, pr.height), pygame.SRCALPHA)
    ps.fill((22, 29, 44, 214))

    # border
    pygame.draw.rect(ps, (82, 132, 200, 235), ps.get_rect(), 2, border_radius=16)

    surface.blit(ps, pr.topleft)

    # title text
    tt = FONTS["panel_title"].render("Zombie Survival", True, (240, 246, 255))
    surface.blit(tt, tt.get_rect(center=(pr.centerx, pr.top + 46)))

    # show save info
    profile_name = current_player_name if current_player_name else "(none loaded)"
    profile_difficulty = str(selected_difficulty) if current_save else "-"

    meta_y = pr.top + 80

    for meta_line in [f"Save: {profile_name}", f"Difficulty: {profile_difficulty}"]:
        mt = FONTS["meta"].render(meta_line, True, (223, 230, 242))
        surface.blit(mt, mt.get_rect(center=(pr.centerx, meta_y)))
        meta_y += 26

    # buttons
    options_start_y = meta_y + 40
    option_width = min(360, pr.width - 60)
    option_height = 42

    button_rects = []

    for index, option_label in enumerate(options):
        or_ = pygame.Rect(0, 0, option_width, option_height)
        or_.center = (pr.centerx, options_start_y + index * 52)
        button_rects.append(or_)

        # button states
        is_sel = index == selected_index
        is_hov = index == hovered_index

        # color depending on state
        if is_hov:
            bg_color = (100, 150, 220, 255)
        elif is_sel:
            bg_color = (66, 118, 184, 240)
        else:
            bg_color = (32, 43, 62, 190)

        border_color = (182, 222, 255) if is_sel else (90, 112, 140)
        text_color = (250, 252, 255) if is_sel else (208, 218, 236)

        # draw button
        os = pygame.Surface((or_.width, or_.height), pygame.SRCALPHA)
        os.fill(bg_color)
        pygame.draw.rect(os, border_color, os.get_rect(), 2, border_radius=12)
        surface.blit(os, or_.topleft)

        # button text
        ot = FONTS["option"].render(option_label, True, text_color)
        surface.blit(ot, ot.get_rect(center=or_.center))

    # bottom message
    mt = FONTS["meta"].render(menu_message, True, (240, 220, 145))
    surface.blit(mt, mt.get_rect(center=(pr.centerx, pr.bottom - 26)))

    return button_rects  # return clickable areas


# ---------------- INITIAL GAME STATE ----------------
game_state = "menu"  # current state (menu, playing, game_over, etc.)

current_player_name = ""
selected_difficulty = 5
menu_message = "Press N to create a save or L to load one"

current_save = None

menu_options = ["New Save", "Load Save", "Quit"]
selected_menu_option = -1

enemy_spawn_timer = 0

new_save_input = ["", ""]  # [name, difficulty]

menu_button_rects = []

# try load save at start
if (loaded_profile := load_save_file()):
    apply_save_profile(loaded_profile)
    menu_message = "Loaded existing save"


# ---------------- MAIN GAME LOOP ----------------
running = True
while running:
    clock.tick(FPS)  # limit FPS

    events = pygame.event.get()  # get all events

    # ---------- BASIC EVENTS ----------
    for event in events:
        if event.type == pygame.QUIT:
            running = False

        # window resize
        if event.type == pygame.VIDEORESIZE:
            window_width = max(event.w, 320)
            window_height = max(event.h, 240)
            screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)

    if not running:
        break

    # ================= MENU =================
    if game_state == "menu":
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_n:
                    new_save_input = ["", ""]
                    game_state = "new_save_name"

                elif event.key == pygame.K_l:
                    if profile := load_save_file():
                        apply_save_profile(profile)
                        reset_game_state()
                        game_state = "playing"
                    else:
                        menu_message = "No save found"

            # mouse click on buttons
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for idx, rect in enumerate(menu_button_rects):
                    if rect.collidepoint(event.pos):
                        selected_menu_option = idx
                        action = menu_options[idx]

                        if action == "New Save":
                            new_save_input = ["", ""]
                            game_state = "new_save_name"

                        elif action == "Load Save":
                            if profile := load_save_file():
                                apply_save_profile(profile)
                                reset_game_state()
                                game_state = "playing"
                            else:
                                menu_message = "No valid save found"

                        elif action == "Quit":
                            running = False

        # detect hover
        hovered_idx = -1
        mouse_pos = pygame.mouse.get_pos()

        for idx, rect in enumerate(menu_button_rects):
            if rect.collidepoint(mouse_pos):
                hovered_idx = idx
                break

        # draw menu
        screen.fill((10, 14, 24))
        menu_button_rects = draw_menu_panel(screen, menu_options, selected_menu_option, hovered_idx)
        pygame.display.flip()
        continue

    # ================= NEW SAVE =================
    elif game_state == "new_save_name":
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "menu"
                    menu_message = "Cancelled save creation"
                
                elif event.key == pygame.K_RETURN and new_save_input[0].strip():
                    # Move to difficulty selection
                    game_state = "new_save_difficulty"
                
                elif event.key == pygame.K_BACKSPACE:
                    new_save_input[0] = new_save_input[0][:-1]
                
                elif len(new_save_input[0]) < 20:
                    new_save_input[0] += event.unicode

        # Draw screen
        screen.fill((10, 14, 24))
        draw_centered_text(screen, "Enter Player Name", window_height // 2 - 60, text_font=FONTS["panel_title"])
        draw_centered_text(screen, new_save_input[0] + "_", window_height // 2, text_font=FONTS["menu"])
        draw_centered_text(screen, "Press ENTER to continue, ESC to cancel", window_height // 2 + 80, (180, 180, 180), FONTS["small"])
        pygame.display.flip()
        continue

    # ================= NEW SAVE DIFFICULTY =================
    elif game_state == "new_save_difficulty":
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "new_save_name"
                
                elif event.key == pygame.K_UP:
                    selected_difficulty = min(10, selected_difficulty + 1)
                
                elif event.key == pygame.K_DOWN:
                    selected_difficulty = max(1, selected_difficulty - 1)
                
                elif event.key == pygame.K_RETURN:
                    # Save the profile and start game
                    write_save_file(new_save_input[0], selected_difficulty, 0)
                    current_player_name = new_save_input[0]
                    current_save = {"name": current_player_name, "difficulty": selected_difficulty, "high_score": 0}
                    reset_game_state()
                    game_state = "playing"

        # Draw screen
        screen.fill((10, 14, 24))
        draw_centered_text(screen, "Select Difficulty", window_height // 2 - 100, text_font=FONTS["panel_title"])
        draw_centered_text(screen, f"← {selected_difficulty} →", window_height // 2, text_font=FONTS["menu"])
        draw_centered_text(screen, "(1 = Easy, 10 = Hard)", window_height // 2 + 50, (180, 180, 180), FONTS["small"])
        draw_centered_text(screen, "Press ENTER to start, UP/DOWN to adjust", window_height // 2 + 100, (180, 180, 180), FONTS["small"])
        pygame.display.flip()
        continue

    # ================= GAMEPLAY =================

    # reduce cooldown timers every frame
    PLAYER["damage_cooldown_timer"] = max(0, PLAYER["damage_cooldown_timer"] - 1)
    BULLET["fire_timer"] = max(0, BULLET["fire_timer"] - 1)

    # spawn enemies over time
    enemy_spawn_timer += 1
    if enemy_spawn_timer >= CURRENT_ENEMY["spawn_interval"]:
        enemies.append(spawn_enemy(PLAYER["x"], PLAYER["y"], max_window_width, max_window_height))
        enemy_spawn_timer = 0

    # ESC to return to menu
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game_state = "menu"

    # ---------- PLAYER INPUT ----------
    keys = pygame.key.get_pressed()
    mouse = pygame.mouse.get_pressed()

    # movement (WASD)
    PLAYER["x"] += PLAYER["speed"] * (keys[pygame.K_d] - keys[pygame.K_a])
    PLAYER["y"] += PLAYER["speed"] * (keys[pygame.K_s] - keys[pygame.K_w])

    # shooting (click)
    if mouse[0] and not BULLET["fire_timer"] and not left_mouse_was_down:
        bullets.extend(spawn_bullets(PLAYER["x"], PLAYER["y"], GUN["angle"]))
        BULLET["fire_timer"] = BULLET["fire_interval"]

    left_mouse_was_down = mouse[0]

    # ---------- ENEMY MOVEMENT ----------
    for enemy in enemies:
        dx = PLAYER["x"] - enemy["x"]
        dy = PLAYER["y"] - enemy["y"]

        dist = math.hypot(dx, dy) or 1  # avoid divide by 0

        # move toward player
        enemy["x"] += dx / dist * enemy["speed"]
        enemy["y"] += dy / dist * enemy["speed"]

    # ---------- CAMERA ----------
    camera_x = PLAYER["x"] - window_width / 2
    camera_y = PLAYER["y"] - window_height / 2

    # player screen position
    screen_x = int(PLAYER["x"] - camera_x)
    screen_y = int(PLAYER["y"] - camera_y)

    # rotate gun toward mouse
    GUN["angle"] = math.atan2(
        pygame.mouse.get_pos()[1] - screen_y,
        pygame.mouse.get_pos()[0] - screen_x
    )

    gun_tip = get_gun_tip(PLAYER["x"], PLAYER["y"], GUN["angle"])
    gun_screen = (int(gun_tip[0] - camera_x), int(gun_tip[1] - camera_y))

    # ---------- BULLETS ----------
    for bullet in bullets[:]:  # copy list so we can remove safely
        bullet["x"] += bullet["vx"]
        bullet["y"] += bullet["vy"]
        bullet["life"] -= 1

        # check hit on any enemy
        hit = any(
            circles_overlap(bullet["x"], bullet["y"], BULLET["radius"], e["x"], e["y"], e["radius"])
            and (e.update({"health": e["health"] - bullet["damage"]}) or True)
            for e in enemies
        )

        # remove bullet if expired or hit
        if bullet["life"] <= 0 or hit:
            bullets.remove(bullet)

    # remove dead enemies
    enemies[:] = [e for e in enemies if e["health"] > 0]

    # ---------- PLAYER DAMAGE ----------
    for enemy in enemies:
        if circles_overlap(PLAYER["x"], PLAYER["y"], PLAYER["radius"], enemy["x"], enemy["y"], enemy["radius"]):
            if PLAYER["damage_cooldown_timer"] == 0:
                PLAYER["health"] -= PLAYER["contact_damage"]
                PLAYER["damage_cooldown_timer"] = PLAYER["damage_cooldown_frames"]

                if PLAYER["health"] <= 0:
                    game_state = "game_over"
            break

    if game_state != "playing":
        continue

    # ---------- DRAWING ----------
    draw_background(screen, background_img, camera_x, camera_y, window_width, window_height)

    # draw enemies
    for e in enemies:
        ex = int(e["x"] - camera_x)
        ey = int(e["y"] - camera_y)

        pygame.draw.circle(screen, ENEMY_BASE["color"], (ex, ey), e["radius"])
        pygame.draw.circle(screen, ENEMY_BASE["outline_color"], (ex, ey), e["radius"], 1)

        # health bar
        hr = e["health"] / e["max_health"]
        hbw = e["radius"] * 2

        pygame.draw.rect(screen, (70, 20, 20), (ex - e["radius"], ey - e["radius"] - 8, hbw, 4))
        pygame.draw.rect(screen, (40, 220, 80), (ex - e["radius"], ey - e["radius"] - 8, int(hbw * hr), 4))

    # draw gun
    pygame.draw.line(screen, GUN["color"], (screen_x, screen_y), gun_screen, GUN["width"])

    # draw player
    pygame.draw.circle(screen, PLAYER["color"], (screen_x, screen_y), PLAYER["radius"])

    # draw bullets
    for b in bullets:
        pygame.draw.circle(screen, b["color"], (int(b["x"] - camera_x), int(b["y"] - camera_y)), BULLET["radius"])

    # ---------- UI ----------
    screen.blit(FONTS["small"].render(f"Player: {current_player_name}", True, (225, 225, 225)), (12, 12))
    screen.blit(FONTS["small"].render(f"Difficulty: {selected_difficulty}", True, (245, 215, 120)), (12, 36))

    # health text
    hl = FONTS["small"].render(
        f"Health: {PLAYER['health']}/{PLAYER['max_health']}",
        True,
        (245, 245, 245)
    )
    screen.blit(hl, hl.get_rect(topright=(window_width - 12, 12)))

    # health bar
    hbw, hbh = 180, 14
    hbr = pygame.Rect(window_width - 12 - hbw, 40, hbw, hbh)

    pygame.draw.rect(screen, (70, 25, 25), hbr)
    pygame.draw.rect(screen, (50, 220, 90), (hbr.x, hbr.y, int(hbw * PLAYER["health"] / PLAYER["max_health"]), hbh))
    pygame.draw.rect(screen, (20, 20, 20), hbr, 2)

    pygame.display.flip()  # update screen


# ---------------- CLEAN EXIT ----------------
pygame.quit()
sys.exit()