import pygame
import random
import sys
import math
import json
from pathlib import Path

pygame.init()

window_width = 480
window_height = 480
max_window_width, max_window_height = pygame.display.get_desktop_sizes()[0]
FPS = 60

screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
pygame.display.set_caption("Zombie Survival")
clock = pygame.time.Clock()

asset_path = Path(__file__).resolve().parent.parent / "repeating-background-1.png"
background_img = pygame.image.load(asset_path).convert()
TILE_SCALE = 2
background_img = pygame.transform.scale_by(background_img, TILE_SCALE)
tile_width = background_img.get_width()
tile_height = background_img.get_height()


def draw_background(surface, image, camera_x, camera_y, window_width, window_height):
    start_x = -int(camera_x) % tile_width - tile_width
    start_y = -int(camera_y) % tile_height - tile_height

    for x in range(start_x, window_width + tile_width, tile_width):
        for y in range(start_y, window_height + tile_height, tile_height):
            surface.blit(image, (x, y))

player_x = window_width / 2
player_y = window_height / 2
player_speed = 5
player_radius = 10
player_color = (60, 140, 255)
player_max_health = 100
player_contact_damage = 20
player_damage_cooldown_frames = 45
player_health = player_max_health
player_damage_cooldown_timer = 0
gun_color = (20, 20, 20)
gun_length = 22
gun_width = 5
gun_angle = 0
gun_turn_speed = 0.35

bullet_radius = 4
bullet_lifetime = 120
bullet_fire_timer = 0
bullet_speed = 10
bullet_damage = 1
bullet_fire_interval = 16
bullets = []
left_mouse_was_down = False
bullet_color = (185, 185, 185)

enemy_color = (220, 50, 50)
enemy_outline_color = (120, 20, 20)
enemy_speed = 1.8
enemy_radius = 12
enemy_max_health = 3
enemy_spawn_interval = 90
enemy_spawn_timer = 0
enemies = []

BASE_ENEMY_SPEED = enemy_speed
BASE_ENEMY_MAX_HEALTH = enemy_max_health
BASE_ENEMY_SPAWN_INTERVAL = enemy_spawn_interval

current_enemy_speed = BASE_ENEMY_SPEED
current_enemy_max_health = BASE_ENEMY_MAX_HEALTH
current_enemy_spawn_interval = BASE_ENEMY_SPAWN_INTERVAL



font = pygame.font.SysFont(None, 24)
title_font = pygame.font.SysFont(None, 56)
menu_font = pygame.font.SysFont(None, 32)
menu_panel_title_font = pygame.font.SysFont(None, 48)
menu_option_font = pygame.font.SysFont(None, 34)
menu_meta_font = pygame.font.SysFont(None, 26)
SAVE_FILE_PATH = Path(__file__).resolve().parent.parent / "savegame.json"


def circles_overlap(x1, y1, radius1, x2, y2, radius2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2 <= (radius1 + radius2) ** 2


def spawn_enemy(target_x, target_y, spawn_width, spawn_height):
    spawn_margin = enemy_radius + 24
    half_width = spawn_width / 2
    half_height = spawn_height / 2
    side = random.choice(("top", "right", "bottom", "left"))

    if side == "top":
        spawn_x = random.uniform(target_x - half_width, target_x + half_width)
        spawn_y = target_y - half_height - spawn_margin
    elif side == "right":
        spawn_x = target_x + half_width + spawn_margin
        spawn_y = random.uniform(target_y - half_height, target_y + half_height)
    elif side == "bottom":
        spawn_x = random.uniform(target_x - half_width, target_x + half_width)
        spawn_y = target_y + half_height + spawn_margin
    else:
        spawn_x = target_x - half_width - spawn_margin
        spawn_y = random.uniform(target_y - half_height, target_y + half_height)

    return {
        "x": spawn_x,
        "y": spawn_y,
        "radius": enemy_radius,
        "speed": current_enemy_speed,
        "health": current_enemy_max_health,
        "max_health": current_enemy_max_health,
    }





def get_gun_tip(player_x, player_y, gun_angle):
    return (
        player_x + math.cos(gun_angle) * gun_length,
        player_y + math.sin(gun_angle) * gun_length,
    )


def spawn_bullets(player_x, player_y, gun_angle):
    bullet_x, bullet_y = get_gun_tip(player_x, player_y, gun_angle)
    return [{
        "x": bullet_x,
        "y": bullet_y,
        "vx": math.cos(gun_angle) * bullet_speed,
        "vy": math.sin(gun_angle) * bullet_speed,
        "life": bullet_lifetime,
        "damage": bullet_damage,
        "color": bullet_color,
    }]


def get_difficulty_settings(level):
    speed_scale = 0.75 + level * 0.1
    health_bonus = level // 3
    spawn_scale = max(0.35, 1.15 - level * 0.08)
    return {
        "enemy_speed": BASE_ENEMY_SPEED * speed_scale,
        "enemy_max_health": BASE_ENEMY_MAX_HEALTH + health_bonus,
        "enemy_spawn_interval": max(18, int(BASE_ENEMY_SPAWN_INTERVAL * spawn_scale)),
    }


def reset_game_state():
    global player_x, player_y, gun_angle, bullets, enemies
    global enemy_spawn_timer, bullet_fire_timer
    global left_mouse_was_down
    global player_health, player_damage_cooldown_timer
    global current_enemy_speed, current_enemy_max_health, current_enemy_spawn_interval

    player_x = window_width / 2
    player_y = window_height / 2
    gun_angle = 0
    bullets = []
    enemies = []

    enemy_spawn_timer = 0
    bullet_fire_timer = 0
    left_mouse_was_down = False

    player_health = player_max_health
    player_damage_cooldown_timer = 0

    difficulty_settings = get_difficulty_settings(selected_difficulty)
    current_enemy_speed = difficulty_settings["enemy_speed"]
    current_enemy_max_health = difficulty_settings["enemy_max_health"]
    current_enemy_spawn_interval = difficulty_settings["enemy_spawn_interval"]

    for _ in range(5):
        enemies.append(spawn_enemy(player_x, player_y, max_window_width, max_window_height))


def write_save_file(name, difficulty, high_score_value):
    save_data = {
        "name": name,
        "difficulty": difficulty,
        "high_score": high_score_value,
    }
    with SAVE_FILE_PATH.open("w", encoding="utf-8") as save_file:
        json.dump(save_data, save_file)


def load_save_file():
    if not SAVE_FILE_PATH.exists():
        return None

    try:
        with SAVE_FILE_PATH.open("r", encoding="utf-8") as save_file:
            save_data = json.load(save_file)
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(save_data, dict):
        return None

    name = str(save_data.get("name", "")).strip()
    difficulty = save_data.get("difficulty", 5)
    high_score_value = save_data.get("high_score", 0)

    if not name:
        return None
    if not isinstance(difficulty, int) or not (1 <= difficulty <= 10):
        return None
    if not isinstance(high_score_value, int) or high_score_value < 0:
        high_score_value = 0

    return {
        "name": name,
        "difficulty": difficulty,
        "high_score": high_score_value,
    }


def apply_save_profile(save_profile):
    global current_player_name, selected_difficulty, high_score, current_save

    current_save = save_profile
    current_player_name = save_profile["name"]
    selected_difficulty = save_profile["difficulty"]
    high_score = save_profile["high_score"]


def persist_current_profile():
    if current_save is None:
        return
    current_save["name"] = current_player_name
    current_save["difficulty"] = selected_difficulty
    current_save["high_score"] = high_score
    write_save_file(current_player_name, selected_difficulty, high_score)


def draw_centered_text(surface, label, y, color=(245, 245, 245), text_font=menu_font):
    text = text_font.render(label, True, color)
    text_rect = text.get_rect(center=(window_width // 2, y))
    surface.blit(text, text_rect)


def draw_menu_panel(surface, options, selected_index):
    overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
    overlay.fill((8, 12, 22, 130))
    surface.blit(overlay, (0, 0))

    panel_width = min(560, max(350, window_width - 60))
    panel_height = min(500, max(320, window_height - 80))
    panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
    panel_rect.center = (window_width // 2, window_height // 2)

    panel_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    panel_surface.fill((22, 29, 44, 214))
    pygame.draw.rect(panel_surface, (82, 132, 200, 235), panel_surface.get_rect(), 2, border_radius=16)
    surface.blit(panel_surface, panel_rect.topleft)

    title_text = menu_panel_title_font.render("Zombie Survival", True, (240, 246, 255))
    title_rect = title_text.get_rect(center=(panel_rect.centerx, panel_rect.top + 46))
    surface.blit(title_text, title_rect)

    subtitle = menu_meta_font.render("Use Up/Down to select", True, (168, 188, 220))
    subtitle_rect = subtitle.get_rect(center=(panel_rect.centerx, panel_rect.top + 80))
    surface.blit(subtitle, subtitle_rect)

    profile_name = current_player_name if current_player_name else "(none loaded)"
    profile_difficulty = str(selected_difficulty) if current_save is not None else "-"

    meta_lines = [
        f"Save: {profile_name}",
        f"Difficulty: {profile_difficulty}",
    ]
    meta_y = panel_rect.top + 118
    for meta_line in meta_lines:
        meta_text = menu_meta_font.render(meta_line, True, (223, 230, 242))
        meta_rect = meta_text.get_rect(center=(panel_rect.centerx, meta_y))
        surface.blit(meta_text, meta_rect)
        meta_y += 26

    options_start_y = meta_y + 22
    option_spacing = 52
    option_width = min(360, panel_rect.width - 60)
    option_height = 42
    for index, option_label in enumerate(options):
        option_rect = pygame.Rect(0, 0, option_width, option_height)
        option_rect.center = (panel_rect.centerx, options_start_y + index * option_spacing)

        is_selected = index == selected_index
        bg_color = (66, 118, 184, 240) if is_selected else (32, 43, 62, 190)
        border_color = (182, 222, 255) if is_selected else (90, 112, 140)
        text_color = (250, 252, 255) if is_selected else (208, 218, 236)

        option_surface = pygame.Surface((option_rect.width, option_rect.height), pygame.SRCALPHA)
        option_surface.fill(bg_color)
        pygame.draw.rect(option_surface, border_color, option_surface.get_rect(), 2, border_radius=12)
        surface.blit(option_surface, option_rect.topleft)

        option_text = menu_option_font.render(option_label, True, text_color)
        option_text_rect = option_text.get_rect(center=option_rect.center)
        surface.blit(option_text, option_text_rect)

    controls_text = menu_meta_font.render("Enter select  |  N new  |  L load  |  Esc quit", True, (192, 204, 224))
    controls_rect = controls_text.get_rect(center=(panel_rect.centerx, panel_rect.bottom - 56))
    surface.blit(controls_text, controls_rect)

    message_text = menu_meta_font.render(menu_message, True, (240, 220, 145))
    message_rect = message_text.get_rect(center=(panel_rect.centerx, panel_rect.bottom - 26))
    surface.blit(message_text, message_rect)


game_state = "menu"
current_player_name = ""
selected_difficulty = 5
new_save_name_input = ""
new_save_difficulty_input = ""
menu_message = "Press N to create a save or L to load one"
current_save = None
menu_options = ["Start Game", "New Save", "Load Save", "Quit"]
selected_menu_option = 0

loaded_profile = load_save_file()
if loaded_profile is not None:
    apply_save_profile(loaded_profile)
    menu_message = "Loaded existing save"

running = True
while running:
    clock.tick(FPS)
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.VIDEORESIZE:
            window_width = max(event.w, 320)
            window_height = max(event.h, 240)
            screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)

    if not running:
        break

    if game_state == "menu":
        def run_menu_action(action):
            global game_state, running, menu_message
            global new_save_name_input, new_save_difficulty_input

            if action == "Start Game":
                if current_save is not None:
                    reset_game_state()
                    game_state = "playing"
                else:
                    menu_message = "Create or load a save first"
            elif action == "New Save":
                new_save_name_input = ""
                new_save_difficulty_input = ""
                game_state = "new_save_name"
            elif action == "Load Save":
                loaded_profile = load_save_file()
                if loaded_profile is None:
                    menu_message = "No valid save file found"
                else:
                    apply_save_profile(loaded_profile)
                    menu_message = "Save loaded. Press Enter to play"
            elif action == "Quit":
                running = False

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    run_menu_action(menu_options[selected_menu_option])
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_UP:
                    selected_menu_option = (selected_menu_option - 1) % len(menu_options)
                if event.key == pygame.K_DOWN:
                    selected_menu_option = (selected_menu_option + 1) % len(menu_options)
                if event.key == pygame.K_n:
                    run_menu_action("New Save")
                if event.key == pygame.K_l:
                    run_menu_action("Load Save")

        screen.fill((10, 14, 24))
        draw_menu_panel(screen, menu_options, selected_menu_option)
        pygame.display.flip()
        continue

    if game_state == "new_save_name":
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "menu"
                    menu_message = "Save creation cancelled"
                elif event.key == pygame.K_BACKSPACE:
                    new_save_name_input = new_save_name_input[:-1]
                elif event.key == pygame.K_RETURN:
                    if new_save_name_input.strip():
                        game_state = "new_save_difficulty"
                        new_save_difficulty_input = ""
                    else:
                        menu_message = "Name cannot be empty"
                elif event.unicode and event.unicode.isprintable() and event.unicode not in "\r\n":
                    if len(new_save_name_input) < 16:
                        new_save_name_input += event.unicode

        draw_background(screen, background_img, 0, 0, window_width, window_height)
        draw_centered_text(screen, "New Save - Name", max(96, window_height // 3), (250, 250, 250), title_font)
        shown_name = new_save_name_input if new_save_name_input else "(type your name)"
        draw_centered_text(screen, shown_name, max(176, window_height // 3 + 80), (250, 220, 120))
        draw_centered_text(screen, "Press Enter to continue", max(222, window_height // 3 + 126), (220, 220, 220))
        draw_centered_text(screen, "Press Escape to cancel", max(258, window_height // 3 + 162), (220, 220, 220))
        pygame.display.flip()
        continue

    if game_state == "new_save_difficulty":
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "menu"
                    menu_message = "Save creation cancelled"
                elif event.key == pygame.K_BACKSPACE:
                    new_save_difficulty_input = new_save_difficulty_input[:-1]
                elif event.key == pygame.K_RETURN:
                    if new_save_difficulty_input.isdigit():
                        difficulty_value = int(new_save_difficulty_input)
                        if 1 <= difficulty_value <= 10:
                            current_player_name = new_save_name_input.strip()
                            selected_difficulty = difficulty_value
                            high_score = 0
                            write_save_file(current_player_name, selected_difficulty, high_score)
                            apply_save_profile({
                                "name": current_player_name,
                                "difficulty": selected_difficulty,
                                "high_score": high_score,
                            })
                            menu_message = "New save created"
                            reset_game_state()
                            game_state = "playing"
                        else:
                            menu_message = "Difficulty must be 1 to 10"
                    else:
                        menu_message = "Type a number from 1 to 10"
                elif event.unicode and event.unicode.isdigit():
                    if len(new_save_difficulty_input) < 2:
                        new_save_difficulty_input += event.unicode

        draw_background(screen, background_img, 0, 0, window_width, window_height)
        draw_centered_text(screen, "New Save - Difficulty", max(96, window_height // 3), (250, 250, 250), title_font)
        shown_difficulty = new_save_difficulty_input if new_save_difficulty_input else "(type 1-10)"
        draw_centered_text(screen, shown_difficulty, max(176, window_height // 3 + 80), (250, 220, 120))
        draw_centered_text(screen, "Press Enter to create save", max(222, window_height // 3 + 126), (220, 220, 220))
        draw_centered_text(screen, "Press Escape to cancel", max(258, window_height // 3 + 162), (220, 220, 220))
        pygame.display.flip()
        continue

    if game_state == "game_over":
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    game_state = "menu"
                if event.key == pygame.K_ESCAPE:
                    running = False

        draw_background(screen, background_img, 0, 0, window_width, window_height)
        draw_centered_text(screen, "Game Over", max(90, window_height // 3), (250, 120, 120), title_font)
        draw_centered_text(screen, f"Player: {current_player_name}", max(130, window_height // 3 + 40), (230, 230, 230))
        draw_centered_text(screen, f"Difficulty: {selected_difficulty}", max(162, window_height // 3 + 72), (245, 215, 120))
        draw_centered_text(screen, "Press Enter for Main Menu", max(235, window_height // 3 + 145), (250, 220, 120))
        draw_centered_text(screen, "Press Escape to Quit", max(275, window_height // 3 + 185), (220, 220, 220))
        pygame.display.flip()
        continue

    enemy_spawn_timer += 1
    if player_damage_cooldown_timer > 0:
        player_damage_cooldown_timer -= 1
    if bullet_fire_timer > 0:
        bullet_fire_timer -= 1

    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game_state = "menu"
    
    keys = pygame.key.get_pressed()
    mouse_buttons = pygame.mouse.get_pressed()
    if keys[pygame.K_w]:
        player_y -= player_speed
    if keys[pygame.K_s]:
        player_y += player_speed
    if keys[pygame.K_a]:
        player_x -= player_speed
    if keys[pygame.K_d]:
        player_x += player_speed

    should_fire = mouse_buttons[0] and bullet_fire_timer == 0 and not left_mouse_was_down
    if should_fire:
        bullets.extend(spawn_bullets(player_x, player_y, gun_angle))
        bullet_fire_timer = bullet_fire_interval
    left_mouse_was_down = mouse_buttons[0]

    if enemy_spawn_timer >= current_enemy_spawn_interval:
        enemies.append(spawn_enemy(player_x, player_y, max_window_width, max_window_height))
        enemy_spawn_timer = 0

    for enemy in enemies:
        dx = player_x - enemy["x"]
        dy = player_y - enemy["y"]
        distance = math.hypot(dx, dy)
        if distance > 0:
            enemy["x"] += (dx / distance) * enemy["speed"]
            enemy["y"] += (dy / distance) * enemy["speed"]

    camera_x = player_x - window_width / 2
    camera_y = player_y - window_height / 2
    screen_x = int(player_x - camera_x)
    screen_y = int(player_y - camera_y)
    
    mouse_x, mouse_y = pygame.mouse.get_pos()
    gun_angle = math.atan2(mouse_y - screen_y, mouse_x - screen_x)
    
    gun_tip_x, gun_tip_y = get_gun_tip(player_x, player_y, gun_angle)
    gun_tip_screen_x = int(gun_tip_x - camera_x)
    gun_tip_screen_y = int(gun_tip_y - camera_y)

    active_bullets = []
    for bullet in bullets:
        bullet["x"] += bullet["vx"]
        bullet["y"] += bullet["vy"]
        bullet["life"] -= 1
        hit_target = False
        for enemy in enemies:
            if circles_overlap(bullet["x"], bullet["y"], bullet_radius, enemy["x"], enemy["y"], enemy["radius"]):
                enemy["health"] -= bullet["damage"]
                hit_target = True
                break
        if bullet["life"] > 0 and not hit_target:
            active_bullets.append(bullet)
    bullets = active_bullets
    enemies = [enemy for enemy in enemies if enemy["health"] > 0]

    for enemy in enemies:
        if circles_overlap(player_x, player_y, player_radius, enemy["x"], enemy["y"], enemy["radius"]):
            if player_damage_cooldown_timer == 0:
                player_health -= player_contact_damage
                player_damage_cooldown_timer = player_damage_cooldown_frames
                if player_health <= 0:
                    player_health = 0
                    game_state = "game_over"
            break

    if game_state != "playing":
        continue
    
    draw_background(screen, background_img, camera_x, camera_y, window_width, window_height)
    for enemy in enemies:
        enemy_screen_x = int(enemy["x"] - camera_x)
        enemy_screen_y = int(enemy["y"] - camera_y)
        pygame.draw.circle(screen, enemy_color, (enemy_screen_x, enemy_screen_y), enemy["radius"])
        pygame.draw.circle(screen, enemy_outline_color, (enemy_screen_x, enemy_screen_y), enemy["radius"], 1)
        health_ratio = enemy["health"] / enemy["max_health"]
        health_bar_width = enemy["radius"] * 2
        health_bar_left = enemy_screen_x - enemy["radius"]
        health_bar_top = enemy_screen_y - enemy["radius"] - 8
        pygame.draw.rect(screen, (70, 20, 20), (health_bar_left, health_bar_top, health_bar_width, 4))
        pygame.draw.rect(screen, (40, 220, 80), (health_bar_left, health_bar_top, int(health_bar_width * health_ratio), 4))
    pygame.draw.line(screen, gun_color, (screen_x, screen_y), (gun_tip_screen_x, gun_tip_screen_y), gun_width)
    pygame.draw.circle(screen, player_color, (screen_x, screen_y), player_radius)
    for bullet in bullets:
        bullet_screen_x = int(bullet["x"] - camera_x)
        bullet_screen_y = int(bullet["y"] - camera_y)
        pygame.draw.circle(screen, bullet["color"], (bullet_screen_x, bullet_screen_y), bullet_radius)

    name_label = font.render(f"Player: {current_player_name}", True, (225, 225, 225))
    screen.blit(name_label, (12, 12))
    difficulty_label = font.render(f"Difficulty: {selected_difficulty}", True, (245, 215, 120))
    screen.blit(difficulty_label, (12, 36))

    health_label = font.render(f"Health: {player_health}/{player_max_health}", True, (245, 245, 245))
    health_label_rect = health_label.get_rect(topright=(window_width - 12, 12))
    screen.blit(health_label, health_label_rect)

    health_bar_width = 180
    health_bar_height = 14
    health_bar_rect = pygame.Rect(window_width - 12 - health_bar_width, 40, health_bar_width, health_bar_height)
    pygame.draw.rect(screen, (70, 25, 25), health_bar_rect)
    health_ratio = player_health / player_max_health
    pygame.draw.rect(
        screen,
        (50, 220, 90),
        (health_bar_rect.x, health_bar_rect.y, int(health_bar_width * health_ratio), health_bar_height),
    )
    pygame.draw.rect(screen, (20, 20, 20), health_bar_rect, 2)
    
    pygame.display.flip()

pygame.quit()
sys.exit()
