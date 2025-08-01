import pygame
import sys
import math
import json
import random
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
GRAVITY = 0.8
JUMP_STRENGTH = -15
PLAYER_SPEED = 5

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (100, 149, 237)
DARK_BLUE = (25, 25, 112)
GOLD = (255, 215, 0)
BROWN = (139, 69, 19)
DARK_BROWN = (101, 67, 33)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (192, 192, 192)
PURPLE = (147, 112, 219)

class GameState(Enum):
    MENU = 1
    PLAYING = 2
    LEVEL_COMPLETE = 3

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-1, -0.5)
        self.life = 1.0
        self.size = random.randint(2, 5)
        self.color = random.choice([YELLOW, WHITE, ORANGE])
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.02
        self.vy += 0.02  # Slight gravity
        
    def draw(self, surface):
        if self.life > 0:
            alpha = int(255 * self.life)
            color = (*self.color, alpha)
            pos = (int(self.x), int(self.y))
            # Create a temporary surface for the particle with alpha
            particle_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, color, (self.size, self.size), self.size)
            surface.blit(particle_surf, (pos[0] - self.size, pos[1] - self.size))

class FloatingOrb:
    def __init__(self, x, y):
        self.base_x = x
        self.base_y = y
        self.x = x
        self.y = y
        self.phase = random.uniform(0, math.pi * 2)
        self.size = random.randint(3, 8)
        self.color = random.choice([(150, 150, 255), (255, 150, 255), (150, 255, 255)])
        self.glow_phase = random.uniform(0, math.pi * 2)
        
    def update(self):
        self.phase += 0.02
        self.glow_phase += 0.03
        self.x = self.base_x + math.sin(self.phase) * 30
        self.y = self.base_y + math.cos(self.phase * 0.7) * 20
        
    def draw(self, surface):
        # Glow effect
        glow_size = self.size + math.sin(self.glow_phase) * 3
        for i in range(5):
            alpha = 30 - i * 5
            glow_surf = pygame.Surface((int(glow_size * 4), int(glow_size * 4)), pygame.SRCALPHA)
            color = (*self.color, alpha)
            pygame.draw.circle(glow_surf, color, 
                             (int(glow_size * 2), int(glow_size * 2)), 
                             int(glow_size + i * 3))
            surface.blit(glow_surf, (self.x - glow_size * 2, self.y - glow_size * 2))
        
        # Core
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.size)

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.vel_y = 0
        self.vel_x = 0
        self.on_ground = False
        self.color = BLUE
        self.trail = []
        self.particles = []
        
    def update(self, platforms):
        # Handle input
        keys = pygame.key.get_pressed()
        self.vel_x = 0
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            # Add jump particles
            for _ in range(10):
                self.particles.append(
                    Particle(self.rect.centerx + random.randint(-10, 10), 
                           self.rect.bottom)
                )
            
        # Apply gravity
        self.vel_y += GRAVITY
        if self.vel_y > 20:
            self.vel_y = 20
            
        # Move horizontally with boundary check
        self.rect.x += self.vel_x
        # Keep player within screen bounds
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
        self.check_collisions(platforms, 'horizontal')
        
        # Move vertically
        self.rect.y += self.vel_y
        self.on_ground = False
        self.check_collisions(platforms, 'vertical')
        
        # Update trail for smooth effect
        self.trail.append((self.rect.centerx, self.rect.centery))
        if len(self.trail) > 10:
            self.trail.pop(0)
            
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
    def check_collisions(self, platforms, direction):
        for platform in platforms:
            if self.rect.colliderect(platform):
                if direction == 'horizontal':
                    if self.vel_x > 0:
                        self.rect.right = platform.left
                    else:
                        self.rect.left = platform.right
                else:
                    if self.vel_y > 0:
                        self.rect.bottom = platform.top
                        self.vel_y = 0
                        self.on_ground = True
                        # Add landing particles
                        if abs(self.vel_y) > 5:
                            for _ in range(5):
                                self.particles.append(
                                    Particle(self.rect.centerx + random.randint(-15, 15), 
                                           self.rect.bottom)
                                )
                    else:
                        self.rect.top = platform.bottom
                        self.vel_y = 0
                        
    def draw(self, screen):
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
            
        # Draw trail effect with alpha
        for i, pos in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)) * 0.3)
            trail_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            color = (*self.color, alpha)
            pygame.draw.rect(trail_surf, color, (0, 0, self.rect.width, self.rect.height), border_radius=5)
            screen.blit(trail_surf, (pos[0] - self.rect.width//2, pos[1] - self.rect.height//2))
            
        # Draw player with gradient effect
        player_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        for i in range(5):
            color = tuple(min(255, c + i * 10) for c in self.color)
            pygame.draw.rect(player_surf, color, 
                           (i*2, i*2, self.rect.width-i*4, self.rect.height-i*4), 
                           border_radius=5)
        screen.blit(player_surf, self.rect.topleft)
            
        # Draw shine effect
        shine_rect = pygame.Rect(self.rect.x + 5, self.rect.y + 5, 10, 10)
        pygame.draw.ellipse(screen, WHITE, shine_rect)

class Door:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 60, 80)
        self.color = BROWN
        self.glow_timer = 0
        
    def update(self):
        self.glow_timer += 0.05
        
    def draw(self, screen):
        # Draw door glow
        glow_surf = pygame.Surface((self.rect.width + 40, self.rect.height + 40), pygame.SRCALPHA)
        glow_intensity = (math.sin(self.glow_timer) + 1) * 0.5
        for i in range(20):
            alpha = int(glow_intensity * (20 - i) * 3)
            color = (255, 215, 0, alpha)
            pygame.draw.rect(glow_surf, color, 
                           (i, i, self.rect.width + 40 - i*2, self.rect.height + 40 - i*2),
                           border_radius=10)
        screen.blit(glow_surf, (self.rect.x - 20, self.rect.y - 20))
        
        # Draw door frame
        pygame.draw.rect(screen, DARK_BROWN, self.rect, border_radius=5)
        pygame.draw.rect(screen, self.color, self.rect.inflate(-6, -6), border_radius=5)
        
        # Draw door handle
        handle_x = self.rect.x + self.rect.width - 15
        handle_y = self.rect.y + self.rect.height // 2
        pygame.draw.circle(screen, GOLD, (handle_x, handle_y), 5)
        
        # Draw decorative lines
        for i in range(2):
            y = self.rect.y + 15 + i * 25
            pygame.draw.line(screen, DARK_BROWN, 
                           (self.rect.x + 10, y), 
                           (self.rect.x + self.rect.width - 10, y), 2)

class Light:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 200
        self.flicker_timer = random.uniform(0, math.pi * 2)
        self.particles = []
        
    def update(self):
        self.flicker_timer += 0.1
        
        # Occasionally spawn light particles
        if random.random() < 0.1:
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(0, 30)
            px = self.x + math.cos(angle) * dist
            py = self.y + math.sin(angle) * dist
            self.particles.append(Particle(px, py))
            
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
        
    def draw(self, screen, light_surface):
        # Draw hanging wire with sway
        sway = math.sin(self.flicker_timer * 0.3) * 5
        pygame.draw.line(screen, GRAY, (self.x, 0), (self.x + sway, self.y), 2)
        
        # Draw bulb
        bulb_rect = pygame.Rect(self.x - 15 + sway, self.y - 20, 30, 40)
        pygame.draw.ellipse(screen, YELLOW, bulb_rect)
        pygame.draw.ellipse(screen, WHITE, bulb_rect.inflate(-10, -10))
        
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
        
        # Create sophisticated light gradient with proper alpha blending
        flicker = math.sin(self.flicker_timer) * 10 + math.sin(self.flicker_timer * 3) * 5
        current_radius = self.radius + flicker
        
        # Draw light on the light surface (which acts as a mask)
        center_x = self.x + sway
        center_y = self.y
        
        # Create radial gradient for light
        for r in range(int(current_radius), 0, -3):
            # Calculate alpha based on distance from center
            alpha = int(255 * (1 - (r / current_radius)) ** 2)
            pygame.draw.circle(light_surface, (alpha, alpha, alpha, alpha), 
                             (int(center_x), int(center_y)), r)

class Level:
    def __init__(self, level_data):
        self.platforms = []
        self.player_start = (100, 400)
        self.door = None
        self.lights = []
        self.background_color = DARK_BLUE
        self.floating_orbs = []
        self.stars = []
        self.load_level(level_data)
        self.create_background_elements()
        
    def create_background_elements(self):
        # Create floating orbs
        for _ in range(15):
            self.floating_orbs.append(
                FloatingOrb(random.randint(50, SCREEN_WIDTH - 50),
                           random.randint(50, SCREEN_HEIGHT - 200))
            )
        
        # Create stars
        for _ in range(100):
            self.stars.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'size': random.uniform(0.5, 2),
                'twinkle': random.uniform(0, math.pi * 2)
            })
        
    def load_level(self, level_data):
        # Create boundary walls
        self.platforms = [
            # Left wall
            pygame.Rect(-10, 0, 10, SCREEN_HEIGHT),
            # Right wall
            pygame.Rect(SCREEN_WIDTH, 0, 10, SCREEN_HEIGHT),
            # Ceiling (optional)
            pygame.Rect(0, -10, SCREEN_WIDTH, 10)
        ]
        
        # Add level platforms
        self.platforms.extend([pygame.Rect(*p) for p in level_data.get('platforms', [])])
        self.player_start = level_data.get('player_start', (100, 400))
        door_pos = level_data.get('door', (1000, 620))
        self.door = Door(*door_pos)
        self.lights = [Light(*l) for l in level_data.get('lights', [])]
        
    def update(self):
        # Update background elements
        for orb in self.floating_orbs:
            orb.update()
            
        for star in self.stars:
            star['twinkle'] += 0.05
            
        # Update door
        self.door.update()
        
        # Update lights
        for light in self.lights:
            light.update()
        
    def draw_background(self, screen):
        # Draw animated gradient background
        for y in range(SCREEN_HEIGHT):
            # Add time-based color shift
            time_offset = pygame.time.get_ticks() * 0.00005
            color_ratio = y / SCREEN_HEIGHT
            
            # Create more complex gradient with purple tones
            r = int(self.background_color[0] * (1 - color_ratio) + 20 * math.sin(time_offset))
            g = int(self.background_color[1] * (1 - color_ratio))
            b = int(self.background_color[2] * (1 - color_ratio) + 30 * math.sin(time_offset * 1.5))
            
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        
        # Draw stars with twinkling effect
        star_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for star in self.stars:
            brightness = (math.sin(star['twinkle']) + 1) * 0.5
            alpha = int(brightness * 255)
            size = star['size'] * (0.8 + brightness * 0.4)
            
            star_surface = pygame.Surface((int(size * 4), int(size * 4)), pygame.SRCALPHA)
            color = (255, 255, 255, alpha)
            pygame.draw.circle(star_surface, color, 
                             (int(size * 2), int(size * 2)), int(size))
            star_surf.blit(star_surface, (star['x'] - size * 2, star['y'] - size * 2))
        
        screen.blit(star_surf, (0, 0))
        
        # Draw floating orbs
        for orb in self.floating_orbs:
            orb.draw(screen)
            
    def draw_platforms(self, screen):
        for i, platform in enumerate(self.platforms):
            # Skip drawing boundary walls (first 3 platforms)
            if i < 3:
                continue
                
            # Draw platform with 3D effect
            pygame.draw.rect(screen, DARK_BROWN, platform.move(0, 5))  # Shadow
            pygame.draw.rect(screen, BROWN, platform)
            pygame.draw.rect(screen, LIGHT_GRAY, platform, 2)  # Border
            
            # Add texture lines
            for x in range(platform.x, platform.x + platform.width, 20):
                pygame.draw.line(screen, DARK_BROWN, 
                               (x, platform.y), 
                               (x, platform.y + platform.height), 1)

class Menu:
    def __init__(self):
        self.font_title = pygame.font.Font(None, 80)
        self.font_button = pygame.font.Font(None, 50)
        self.buttons = {
            'start': pygame.Rect(SCREEN_WIDTH//2 - 150, 350, 300, 70),
            'quit': pygame.Rect(SCREEN_WIDTH//2 - 150, 450, 300, 70)
        }
        self.hover = None
        self.particles = []
        self.bg_phase = 0
        
    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        self.hover = None
        for name, rect in self.buttons.items():
            if rect.collidepoint(mouse_pos):
                self.hover = name
                # Add particles on hover
                if random.random() < 0.3:
                    self.particles.append(
                        Particle(rect.centerx + random.randint(-50, 50),
                               rect.centery)
                    )
        
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
        self.bg_phase += 0.01
                
    def draw(self, screen):
        # Draw animated procedural background
        for i in range(0, SCREEN_WIDTH, 50):
            for j in range(0, SCREEN_HEIGHT, 50):
                # Create moving wave pattern
                wave = math.sin(self.bg_phase + i * 0.01) * math.cos(self.bg_phase + j * 0.01)
                brightness = int(20 + wave * 20)
                color = (brightness, brightness, brightness + 30)
                pygame.draw.rect(screen, color, (i, j, 50, 50))
        
        # Draw floating light orbs in background
        for i in range(5):
            x = SCREEN_WIDTH//2 + math.sin(self.bg_phase + i) * 300
            y = 200 + math.cos(self.bg_phase * 0.7 + i) * 100
            
            # Glow effect
            glow_surf = pygame.Surface((200, 200), pygame.SRCALPHA)
            for r in range(100, 0, -2):
                alpha = int(255 * (1 - r/100) * 0.1)
                color = (255, 200, 100, alpha)
                pygame.draw.circle(glow_surf, color, (100, 100), r)
            screen.blit(glow_surf, (x - 100, y - 100))
        
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
                
        # Draw title with shadow and glow
        title = "LIGHT QUEST"
        
        # Title glow
        glow_surf = pygame.Surface((600, 200), pygame.SRCALPHA)
        for i in range(20):
            alpha = 10 - i // 2
            glow_color = (255, 215, 0, alpha)
            glow_text = self.font_title.render(title, True, glow_color)
            glow_surf.blit(glow_text, (300 - glow_text.get_width()//2 + i, 
                                      100 - glow_text.get_height()//2 + i))
        screen.blit(glow_surf, (SCREEN_WIDTH//2 - 300, 50))
        
        # Main title
        shadow = self.font_title.render(title, True, BLACK)
        text = self.font_title.render(title, True, GOLD)
        screen.blit(shadow, (SCREEN_WIDTH//2 - text.get_width()//2 + 5, 155))
        screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 150))
        
        # Draw buttons with enhanced effects
        for name, rect in self.buttons.items():
            # Button shadow
            shadow_rect = rect.copy()
            shadow_rect.x += 5
            shadow_rect.y += 5
            pygame.draw.rect(screen, BLACK, shadow_rect, border_radius=10)
            
            # Button glow on hover
            if self.hover == name:
                glow_surf = pygame.Surface((rect.width + 40, rect.height + 40), pygame.SRCALPHA)
                for i in range(20):
                    alpha = int(255 * (1 - i/20) * 0.3)
                    color = (255, 165, 0, alpha)
                    pygame.draw.rect(glow_surf, color,
                                   (i, i, rect.width + 40 - i*2, rect.height + 40 - i*2),
                                   border_radius=15)
                screen.blit(glow_surf, (rect.x - 20, rect.y - 20))
            
            # Button color
            color = ORANGE if self.hover == name else GOLD
            pygame.draw.rect(screen, color, rect, border_radius=10)
            pygame.draw.rect(screen, WHITE, rect, 3, border_radius=10)
            
            # Button text
            text = "START GAME" if name == 'start' else "QUIT"
            button_text = self.font_button.render(text, True, BLACK)
            text_x = rect.x + (rect.width - button_text.get_width()) // 2
            text_y = rect.y + (rect.height - button_text.get_height()) // 2
            screen.blit(button_text, (text_x, text_y))
            
    def handle_click(self, pos):
        if self.buttons['start'].collidepoint(pos):
            return 'start'
        elif self.buttons['quit'].collidepoint(pos):
            return 'quit'
        return None

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Light Quest - Platformer")
        self.clock = pygame.time.Clock()
        self.state = GameState.MENU
        self.menu = Menu()
        self.current_level = 0
        self.levels = self.load_levels()
        self.level = None
        self.player = None
        # Create light surface with per-pixel alpha
        self.light_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.ambient_light = 40  # Base ambient light level
        self.font = pygame.font.Font(None, 36)
        
    def load_levels(self):
        # Level data structure for easy editing
        levels = [
            {
                'platforms': [
                    # Ground
                    (0, 700, 1200, 100),
                    # Platforms
                    (200, 600, 200, 20),
                    (500, 500, 200, 20),
                    (800, 400, 200, 20),
                ],
                'player_start': (100, 600),
                'door': (1050, 620),
                'lights': [(600, 100), (200, 200), (1000, 150)]
            }
        ]
        return levels
        
    def start_level(self, level_index):
        if level_index < len(self.levels):
            self.level = Level(self.levels[level_index])
            self.player = Player(*self.level.player_start)
            self.current_level = level_index
            self.state = GameState.PLAYING
            
    def update(self):
        if self.state == GameState.MENU:
            self.menu.update()
        elif self.state == GameState.PLAYING:
            self.player.update(self.level.platforms)
            self.level.update()
                
            # Check door collision
            if self.player.rect.colliderect(self.level.door.rect):
                self.state = GameState.LEVEL_COMPLETE
                
    def draw(self):
        if self.state == GameState.MENU:
            self.menu.draw(self.screen)
        elif self.state == GameState.PLAYING:
            # Draw background
            self.level.draw_background(self.screen)
            
            # Draw level elements first
            self.level.draw_platforms(self.screen)
            self.level.door.draw(self.screen)
            self.player.draw(self.screen)
            
            # Create light mask
            self.light_surface.fill((self.ambient_light, self.ambient_light, self.ambient_light, 255))
            
            # Draw lights on the light surface
            for light in self.level.lights:
                light.draw(self.screen, self.light_surface)
            
            # Apply lighting as an overlay with multiply blend
            # This darkens areas not lit by lights
            darkness_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            darkness_overlay.fill((255, 255, 255))
            darkness_overlay.blit(self.light_surface, (0, 0), special_flags=pygame.BLEND_SUB)
            
            # Apply subtle lighting effect
            self.screen.blit(darkness_overlay, (0, 0), special_flags=pygame.BLEND_MULT)
            
            # Draw UI (on top of lighting)
            level_text = self.font.render(f"Level {self.current_level + 1}", True, WHITE)
            self.screen.blit(level_text, (10, 10))
            
            # Controls hint
            controls_text = pygame.font.Font(None, 20).render("Arrow Keys/WASD: Move | Space: Jump", True, WHITE)
            self.screen.blit(controls_text, (10, 40))
            
        elif self.state == GameState.LEVEL_COMPLETE:
            self.screen.fill(BLACK)
            
            # Animated completion text
            time = pygame.time.get_ticks() * 0.001
            scale = 1 + math.sin(time * 2) * 0.1
            
            font_size = int(36 * scale)
            dynamic_font = pygame.font.Font(None, font_size)
            
            complete_text = dynamic_font.render("Level Complete!", True, GOLD)
            continue_text = self.font.render("Press SPACE to continue", True, WHITE)
            
            self.screen.blit(complete_text, 
                           (SCREEN_WIDTH//2 - complete_text.get_width()//2, 300))
            self.screen.blit(continue_text, 
                           (SCREEN_WIDTH//2 - continue_text.get_width()//2, 400))
            
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
            
        if self.state == GameState.MENU:
            if event.type == pygame.MOUSEBUTTONDOWN:
                action = self.menu.handle_click(event.pos)
                if action == 'start':
                    self.start_level(0)
                elif action == 'quit':
                    return False
                    
        elif self.state == GameState.LEVEL_COMPLETE:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                # Load next level or return to menu
                if self.current_level + 1 < len(self.levels):
                    self.start_level(self.current_level + 1)
                else:
                    self.state = GameState.MENU
                    
        return True
        
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                running = self.handle_event(event)
                
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

# Level Editor Class
class LevelEditor:
    def __init__(self):
        self.platforms = []
        self.lights = []
        self.player_start = (100, 400)
        self.door_pos = (1000, 620)
        self.mode = 'platform'  # platform, light, player, door
        self.grid_size = 20
        
    def save_level(self, filename):
        level_data = {
            'platforms': [[p.x, p.y, p.width, p.height] for p in self.platforms],
            'lights': self.lights,
            'player_start': self.player_start,
            'door': self.door_pos
        }
        with open(filename, 'w') as f:
            json.dump(level_data, f, indent=2)
            
    def load_level(self, filename):
        with open(filename, 'r') as f:
            level_data = json.load(f)
        return level_data
        
    def snap_to_grid(self, pos):
        x = (pos[0] // self.grid_size) * self.grid_size
        y = (pos[1] // self.grid_size) * self.grid_size
        return (x, y)

# Run the game
if __name__ == "__main__":
    game = Game()
    game.run()