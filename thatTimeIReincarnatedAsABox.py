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

# Even Warmer Color Palette
# Warm background colors
WARM_NIGHT = (65, 25, 40)
SUNSET_PURPLE = (125, 65, 96)
DUSK_ORANGE = (198, 102, 127)
PEACH_GLOW = (255, 205, 170)

# Vibrant warm accent colors
FIRE_ORANGE = (255, 159, 10)
MOLTEN_GOLD = (255, 225, 50)
WARM_PINK = (255, 192, 203)
CORAL = (255, 137, 95)
CRIMSON = (240, 60, 80)
EMBER_RED = (255, 99, 71)

# Player colors (warm cyan-greens)
WARM_CYAN = (94, 234, 190)
MINT_GREEN = (182, 255, 172)
SPRING_GREEN = (50, 255, 157)

# Warm neutrals
WARM_BROWN = (169, 110, 63)
SAND = (248, 223, 193)
TERRACOTTA = (224, 139, 105)
WARM_GRAY = (172, 152, 128)

# Platform colors
SUNSET_BROWN = (195, 102, 62)
WARM_STONE = (208, 163, 130)
CLAY = (198, 116, 96)

# Special colors
DOOR_BURGUNDY = (183, 70, 95)
DOOR_GOLD = (255, 215, 50)
KEY_GOLD = (255, 243, 80)
SHADOW_COLOR = (35, 15, 25)
WARM_WHITE = (255, 253, 245)

class GameState(Enum):
    MENU = 1
    PLAYING = 2
    LEVEL_COMPLETE = 3
    TRANSITIONING = 4

class TransitionState:
    def __init__(self):
        self.phase = "shrink"  # shrink, swipe, grow
        self.progress = 0.0
        self.old_level_surface = None
        self.new_level_surface = None
        self.intermediate_surfaces = []  # For showing levels in between
        self.scale = 1.0
        self.offset_x = 0
        self.target_level = 0
        self.start_level = 0
        self.direction = 1  # 1 for forward, -1 for backward

class Particle:
    def __init__(self, x, y, color_palette=None, vel_x=None, vel_y=None):
        self.x = x
        self.y = y
        self.vx = vel_x if vel_x is not None else random.uniform(-0.5, 0.5)
        self.vy = vel_y if vel_y is not None else random.uniform(-1, -0.5)
        self.life = 1.0
        self.size = random.randint(2, 5)
        if color_palette:
            self.color = random.choice(color_palette)
        else:
            self.color = random.choice([MOLTEN_GOLD, FIRE_ORANGE, WARM_PINK])
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.02
        self.vy += 0.02  # Slight gravity
        
    def draw(self, surface):
        if self.life > 0:
            alpha = int(255 * self.life)
            # Add glow effect
            for i in range(3):
                glow_alpha = alpha // (i + 1)
                glow_size = self.size + i * 2
                glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                color = (*self.color, glow_alpha)
                pygame.draw.circle(glow_surf, color, (glow_size, glow_size), glow_size)
                surface.blit(glow_surf, (self.x - glow_size, self.y - glow_size))

class Fireball:
    def __init__(self, x, y, target_x, target_y):
        self.rect = pygame.Rect(x, y, 20, 20)
        # Calculate direction to mouse
        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx*dx + dy*dy)
        if distance > 0:
            self.vel_x = (dx / distance) * 10
            self.vel_y = (dy / distance) * 10
        else:
            self.vel_x = 10
            self.vel_y = 0
        self.particles = []
        self.alive = True
        self.life = 60  # frames
        
    def update(self, platforms, breakable_boxes):
        
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            return
            
        # Move
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        
        # Check platform collisions
        for platform in platforms:
            if self.rect.colliderect(platform):
                self.explode()
                return
                
        # Check box collisions
        for box in breakable_boxes:
            if self.rect.colliderect(box.rect) and not box.broken:
                box.break_box()
                self.explode()
                return
                
        # Create fire trail
        for _ in range(3):
            self.particles.append(
                Particle(self.rect.centerx + random.randint(-5, 5),
                       self.rect.centery + random.randint(-5, 5),
                       [FIRE_ORANGE, CRIMSON, MOLTEN_GOLD, EMBER_RED],
                       random.uniform(-1, 1), random.uniform(-1, 1))
            )
            
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
        # Out of bounds
        if (self.rect.x < -50 or self.rect.x > SCREEN_WIDTH + 50 or
            self.rect.y < -50 or self.rect.y > SCREEN_HEIGHT + 50):
            self.alive = False
            
    def explode(self):
        self.alive = False
        # Create explosion particles
        for _ in range(25):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 6)
            self.particles.append(
                Particle(self.rect.centerx, self.rect.centery,
                       [FIRE_ORANGE, CRIMSON, MOLTEN_GOLD, EMBER_RED],
                       math.cos(angle) * speed, math.sin(angle) * speed)
            )
            
    def draw(self, screen):
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
            
        if self.alive:
            # Draw fireball with glow
            glow_surf = pygame.Surface((50, 50), pygame.SRCALPHA)
            for i in range(15):
                alpha = 120 - i * 8
                color = (*FIRE_ORANGE, alpha)
                pygame.draw.circle(glow_surf, color, (25, 25), 12 + i)
            screen.blit(glow_surf, (self.rect.x - 15, self.rect.y - 15))
            
            # Core
            pygame.draw.circle(screen, MOLTEN_GOLD, self.rect.center, 8)
            pygame.draw.circle(screen, WARM_WHITE, (self.rect.centerx - 3, self.rect.centery - 3), 4)

class BreakableBox:
    def __init__(self, x, y, has_key=False):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.has_key = has_key
        self.broken = False
        self.particles = []
        self.key_collected = False
        self.key_y_offset = 0
        self.key_float_phase = random.uniform(0, math.pi * 2)
        
    def break_box(self):
        if not self.broken:
            self.broken = True
            # Create wood particles
            for _ in range(20):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 6)
                self.particles.append(
                    Particle(self.rect.centerx, self.rect.centery,
                           [WARM_BROWN, SUNSET_BROWN, TERRACOTTA],
                           math.cos(angle) * speed, 
                           math.sin(angle) * speed - 3)
                )
                
    def update(self):
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
        # Float key animation
        if self.broken and self.has_key and not self.key_collected:
            self.key_float_phase += 0.1
            self.key_y_offset = math.sin(self.key_float_phase) * 5
            
    def collect_key(self):
        if self.broken and self.has_key and not self.key_collected:
            self.key_collected = True
            return True
        return False
        
    def draw(self, screen):
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
            
        if not self.broken:
            # Draw box with wood texture
            # Shadow
            shadow_rect = self.rect.copy()
            shadow_rect.x += 3
            shadow_rect.y += 3
            pygame.draw.rect(screen, SHADOW_COLOR, shadow_rect, border_radius=3)
            
            # Main box
            pygame.draw.rect(screen, WARM_BROWN, self.rect, border_radius=3)
            
            # Wood grain
            for i in range(3):
                y = self.rect.y + 10 + i * 10
                pygame.draw.line(screen, SUNSET_BROWN,
                               (self.rect.x + 5, y),
                               (self.rect.x + self.rect.width - 5, y), 2)
                               
            # Highlight
            pygame.draw.line(screen, SAND,
                           (self.rect.x + 2, self.rect.y + 2),
                           (self.rect.x + self.rect.width - 2, self.rect.y + 2), 2)
                           
        elif self.has_key and not self.key_collected:
            # Draw floating key
            key_x = self.rect.centerx
            key_y = self.rect.centery - 20 + self.key_y_offset
            
            # Key glow
            glow_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            for i in range(25):
                alpha = 80 - i * 3
                color = (*KEY_GOLD, alpha)
                pygame.draw.circle(glow_surf, color, (40, 40), 20 + i)
            screen.blit(glow_surf, (key_x - 40, key_y - 40))
            
            # Key shape
            pygame.draw.circle(screen, KEY_GOLD, (key_x, key_y), 8)
            pygame.draw.rect(screen, KEY_GOLD, (key_x - 2, key_y, 4, 15))
            pygame.draw.rect(screen, KEY_GOLD, (key_x - 2, key_y + 10, 8, 3))
            pygame.draw.rect(screen, KEY_GOLD, (key_x - 2, key_y + 14, 6, 3))

class FloatingOrb:
    def __init__(self, x, y):
        self.base_x = x
        self.base_y = y
        self.x = x
        self.y = y
        self.phase = random.uniform(0, math.pi * 2)
        self.size = random.randint(3, 8)
        self.color = random.choice([PEACH_GLOW, WARM_PINK, FIRE_ORANGE])
        self.glow_phase = random.uniform(0, math.pi * 2)
        
    def update(self):
        self.phase += 0.02
        self.glow_phase += 0.03
        self.x = self.base_x + math.sin(self.phase) * 30
        self.y = self.base_y + math.cos(self.phase * 0.7) * 20
        
    def draw(self, surface):
        # Multi-layer glow effect
        glow_size = self.size + math.sin(self.glow_phase) * 3
        for i in range(5):
            alpha = 50 - i * 10
            glow_surf = pygame.Surface((int(glow_size * 6), int(glow_size * 6)), pygame.SRCALPHA)
            color = (*self.color, alpha)
            pygame.draw.circle(glow_surf, color, 
                             (int(glow_size * 3), int(glow_size * 3)), 
                             int(glow_size + i * 4))
            surface.blit(glow_surf, (self.x - glow_size * 3, self.y - glow_size * 3))
        
        # Core with color shift
        core_color = tuple(min(255, c + 50) for c in self.color)
        pygame.draw.circle(surface, core_color, (int(self.x), int(self.y)), self.size)
        
        # Inner highlight
        pygame.draw.circle(surface, WARM_WHITE, 
                         (int(self.x - self.size//3), int(self.y - self.size//3)), 
                         self.size//2)

class Player:
    def __init__(self, x, y, abilities=None):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.vel_y = 0
        self.vel_x = 0
        self.on_ground = False
        self.color = WARM_CYAN
        self.glow_color = SPRING_GREEN
        self.trail = []
        self.particles = []
        
        # Abilities
        self.abilities = abilities or {}
        self.double_jump_available = self.abilities.get('double_jump', False)
        self.can_double_jump = False
        self.jump_pressed = False  # Track if jump key was pressed
        self.can_fireball = self.abilities.get('fireball', False)
        self.fireballs = []
        self.fireball_cooldown = 0
        self.facing_right = True
        
        # Keys collected
        self.keys = 0
        
    def update(self, platforms, mouse_pos):
        # Handle input
        keys = pygame.key.get_pressed()
        self.vel_x = 0
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
            self.facing_right = True
            
        # Jumping logic with proper double jump
        jump_key = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
        
        if jump_key and not self.jump_pressed:
            if self.on_ground:
                self.vel_y = JUMP_STRENGTH
                self.can_double_jump = self.double_jump_available
                # Jump particles
                for _ in range(12):
                    self.particles.append(
                        Particle(self.rect.centerx + random.randint(-10, 10), 
                               self.rect.bottom,
                               [WARM_CYAN, SPRING_GREEN, MINT_GREEN])
                    )
            elif self.can_double_jump:
                self.vel_y = JUMP_STRENGTH * 0.85
                self.can_double_jump = False
                # Double jump particles
                """
                for _ in range(20):
                    angle = random.uniform(0, math.pi * 2)
                    speed = random.uniform(3, 5)
                    self.particles.append(
                        Particle(self.rect.centerx, self.rect.centery,
                               [MOLTEN_GOLD, FIRE_ORANGE, WARM_PINK],
                               math.cos(angle) * speed,
                               math.sin(angle) * speed)
                    )
                """
                    
        self.jump_pressed = jump_key
                    
        # Fireball ability with mouse direction
        if self.can_fireball and self.fireball_cooldown <= 0:
            if keys[pygame.K_f] or keys[pygame.K_LSHIFT]:
                fireball_x = self.rect.centerx
                fireball_y = self.rect.centery
                self.fireballs.append(Fireball(fireball_x, fireball_y, mouse_pos[0], mouse_pos[1]))
                self.fireball_cooldown = 20
                
        if self.fireball_cooldown > 0:
            self.fireball_cooldown -= 1
            
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
        self.trail.append((self.rect.centerx, self.rect.centery, self.vel_x, self.vel_y))
        if len(self.trail) > 15:
            self.trail.pop(0)
            
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
        # Update fireballs
        self.fireballs = [f for f in self.fireballs if f.alive or len(f.particles) > 0]
        for fireball in self.fireballs:
            fireball.update(platforms, [])  # Empty boxes list for now
            
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
                        # Landing particles
                        if abs(self.vel_y) > 5:
                            for _ in range(5):
                                self.particles.append(
                                    Particle(self.rect.centerx + random.randint(-15, 15), 
                                           self.rect.bottom,
                                           [WARM_CYAN, SPRING_GREEN, MINT_GREEN])
                                )
                    else:
                        self.rect.top = platform.bottom
                        self.vel_y = 0
                        
    def draw(self, screen):
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
            
        # Draw fireballs
        for fireball in self.fireballs:
            fireball.draw(screen)
            
        # Draw enhanced trail effect
        for i, (x, y, vx, vy) in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)) * 0.4)
            size = self.rect.width - (len(self.trail) - i) * 2
            if size > 0:
                trail_surf = pygame.Surface((size, size), pygame.SRCALPHA)
                # Add slight color shift based on movement
                color_shift = int(abs(vx) * 10 + abs(vy) * 5)
                trail_color = (
                    min(255, self.glow_color[0] + color_shift),
                    self.glow_color[1],
                    self.glow_color[2],
                    alpha
                )
                pygame.draw.rect(trail_surf, trail_color, (0, 0, size, size), border_radius=5)
                screen.blit(trail_surf, (x - size//2, y - size//2))
            
        # Draw player glow
        glow_surf = pygame.Surface((self.rect.width + 20, self.rect.height + 20), pygame.SRCALPHA)
        for i in range(10):
            alpha = 80 - i * 8
            glow_rect = pygame.Rect(i, i, self.rect.width + 20 - i*2, self.rect.height + 20 - i*2)
            pygame.draw.rect(glow_surf, (*self.glow_color, alpha), glow_rect, border_radius=8)
        screen.blit(glow_surf, (self.rect.x - 10, self.rect.y - 10))
            
        # Draw player with gradient
        player_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        
        # Base color
        pygame.draw.rect(player_surf, self.color, (0, 0, self.rect.width, self.rect.height), border_radius=5)
        
        # Top highlight
        highlight_rect = pygame.Rect(5, 5, self.rect.width - 10, self.rect.height // 3)
        pygame.draw.rect(player_surf, MINT_GREEN, highlight_rect, border_radius=3)
        
        # Side shadow
        shadow_rect = pygame.Rect(self.rect.width - 10, 10, 10, self.rect.height - 10)
        shadow_color = tuple(max(0, c - 50) for c in self.color)
        pygame.draw.rect(player_surf, shadow_color, shadow_rect, border_radius=3)
        
        screen.blit(player_surf, self.rect.topleft)
            
        # Draw eye (for character)
        eye_x = self.rect.x + 8 if not self.facing_right else self.rect.x + self.rect.width - 18
        eye_y = self.rect.y + 12
        pygame.draw.circle(screen, WARM_WHITE, (eye_x + 5, eye_y), 5)
        pygame.draw.circle(screen, SHADOW_COLOR, (eye_x + 5, eye_y), 3)
        
        # Draw ability indicators
        if self.double_jump_available and self.can_double_jump and not self.on_ground:
            # Double jump indicator
            indicator_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            for i in range(10):
                alpha = 120 - i * 12
                pygame.draw.circle(indicator_surf, (*MOLTEN_GOLD, alpha), (20, 20), 15 + i)
            pygame.draw.circle(indicator_surf, MOLTEN_GOLD, (20, 20), 12, 3)
            screen.blit(indicator_surf, (self.rect.centerx - 20, self.rect.y - 45))

class Door:
    def __init__(self, x, y, target_level, label=""):
        self.rect = pygame.Rect(x, y, 60, 80)
        self.target_level = target_level
        self.label = label
        self.color = DOOR_BURGUNDY
        self.glow_timer = 0
        self.particles = []
        self.locked = False
        
    def update(self):
        self.glow_timer += 0.05
        
        # Spawn magical particles
        if random.random() < 0.1:
            self.particles.append(
                Particle(self.rect.centerx + random.randint(-20, 20),
                       self.rect.y + random.randint(0, self.rect.height),
                       [DOOR_GOLD, FIRE_ORANGE, WARM_PINK])
            )
        
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            particle.vy -= 0.1  # Float upward
        
    def draw(self, screen, font):
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
            
        # Draw door glow with warm colors
        glow_surf = pygame.Surface((self.rect.width + 60, self.rect.height + 60), pygame.SRCALPHA)
        glow_intensity = (math.sin(self.glow_timer) + 1) * 0.5
        
        for i in range(30):
            alpha = int(glow_intensity * (30 - i) * 2)
            # Different color for locked doors
            if self.locked:
                color = (*CRIMSON, alpha)
            else:
                # Gradient from gold to pink
                color_ratio = i / 30
                r = int(DOOR_GOLD[0] * (1 - color_ratio) + WARM_PINK[0] * color_ratio)
                g = int(DOOR_GOLD[1] * (1 - color_ratio) + WARM_PINK[1] * color_ratio)
                b = int(DOOR_GOLD[2] * (1 - color_ratio) + WARM_PINK[2] * color_ratio)
                color = (r, g, b, alpha)
            
            pygame.draw.rect(glow_surf, color, 
                           (i, i, self.rect.width + 60 - i*2, self.rect.height + 60 - i*2),
                           border_radius=10)
        screen.blit(glow_surf, (self.rect.x - 30, self.rect.y - 30))
        
        # Draw door shadow
        shadow_rect = self.rect.copy()
        shadow_rect.x += 5
        shadow_rect.y += 5
        pygame.draw.rect(screen, SHADOW_COLOR, shadow_rect, border_radius=5)
        
        # Draw door frame
        frame_color = WARM_GRAY if self.locked else WARM_BROWN
        pygame.draw.rect(screen, frame_color, self.rect, border_radius=5)
        pygame.draw.rect(screen, self.color, self.rect.inflate(-6, -6), border_radius=5)
        
        # Draw lock or handle
        if self.locked:
            # Draw lock
            lock_x = self.rect.centerx
            lock_y = self.rect.centery
            pygame.draw.rect(screen, WARM_GRAY, (lock_x - 10, lock_y - 5, 20, 15), border_radius=3)
            pygame.draw.arc(screen, WARM_GRAY, (lock_x - 8, lock_y - 15, 16, 20), 0, math.pi, 3)
            # Keyhole
            pygame.draw.circle(screen, SHADOW_COLOR, (lock_x, lock_y + 2), 3)
            pygame.draw.rect(screen, SHADOW_COLOR, (lock_x - 1, lock_y + 2, 2, 5))
        else:
            # Draw handle
            handle_x = self.rect.x + self.rect.width - 15
            handle_y = self.rect.y + self.rect.height // 2
            pygame.draw.circle(screen, DOOR_GOLD, (handle_x, handle_y), 6)
            pygame.draw.circle(screen, MOLTEN_GOLD, (handle_x - 2, handle_y - 2), 3)
        
        # Draw decorative patterns
        pattern_color = tuple(min(255, c + 30) for c in self.color)
        for i in range(3):
            y = self.rect.y + 15 + i * 20
            pygame.draw.line(screen, pattern_color, 
                           (self.rect.x + 10, y), 
                           (self.rect.x + self.rect.width - 10, y), 2)
            
        # Draw label
        if self.label:
            label_text = font.render(self.label, True, WARM_WHITE)
            label_x = self.rect.centerx - label_text.get_width() // 2
            label_y = self.rect.y - 25
            # Label background
            label_bg = pygame.Surface((label_text.get_width() + 10, label_text.get_height() + 4), pygame.SRCALPHA)
            pygame.draw.rect(label_bg, (*SHADOW_COLOR, 180), (0, 0, label_text.get_width() + 10, label_text.get_height() + 4), border_radius=3)
            screen.blit(label_bg, (label_x - 5, label_y - 2))
            screen.blit(label_text, (label_x, label_y))

class Light:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 650
        self.flicker_timer = random.uniform(0, math.pi * 2)
        self.particles = []
        self.color_phase = random.uniform(0, math.pi * 2)
        
    def update(self):
        self.flicker_timer += 0.1
        self.color_phase += 0.02
        
        # Occasionally spawn light particles
        if random.random() < 0.15:
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(0, 40)
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
        for i in range(3):
            wire_color = tuple(max(0, c - i * 20) for c in WARM_GRAY)
            pygame.draw.line(screen, wire_color, 
                           (self.x + i, 0), 
                           (self.x + sway + i, self.y), 2 - i)
        
        # Draw bulb with warm colors
        bulb_rect = pygame.Rect(self.x - 15 + sway, self.y - 20, 30, 40)
        
        # Bulb glow
        glow_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
        for i in range(20):
            alpha = 100 - i * 5
            color = (*MOLTEN_GOLD, alpha)
            pygame.draw.ellipse(glow_surf, color, 
                              (i, i, 80 - i*2, 80 - i*2))
        screen.blit(glow_surf, (self.x - 40 + sway, self.y - 40))
        
        # Bulb base
        pygame.draw.ellipse(screen, WARM_GRAY, bulb_rect.inflate(4, 4))
        pygame.draw.ellipse(screen, MOLTEN_GOLD, bulb_rect)
        pygame.draw.ellipse(screen, WARM_WHITE, bulb_rect.inflate(-10, -10))
        
        # Metal cap
        cap_rect = pygame.Rect(self.x - 10 + sway, self.y + 15, 20, 10)
        pygame.draw.rect(screen, WARM_GRAY, cap_rect, border_radius=2)
        
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
        
        # Create very warm light gradient
        flicker = math.sin(self.flicker_timer) * 15 + math.sin(self.flicker_timer * 3) * 7
        current_radius = self.radius + flicker
        
        center_x = self.x + sway
        center_y = self.y
        
        # Extra warm light gradient
        for r in range(int(current_radius), 0, -300):
            distance_ratio = r / current_radius
            alpha = int(255 * (1 - distance_ratio) ** 1.5)
            
            # Very warm color gradient
            if distance_ratio < 0.3:
                # Core: bright warm white
                color = (255, 253, 245, alpha)
            elif distance_ratio < 0.6:
                # Middle: golden orange
                color_ratio = (distance_ratio - 0.3) / 0.3
                r_val = 255
                g_val = int(253 - color_ratio * 60)
                b_val = int(245 - color_ratio * 165)
                color = (r_val, g_val, b_val, alpha)
            else:
                # Outer: deep orange-red
                color_ratio = (distance_ratio - 0.6) / 0.4
                r_val = 255
                g_val = int(193 - color_ratio * 120)
                b_val = int(80 - color_ratio * 80)
                color = (r_val, g_val, b_val, alpha)
            
            pygame.draw.circle(light_surface, color, 
                             (int(center_x), int(center_y)), r)

class Level:
    def __init__(self, level_data, level_number):
        self.level_number = level_number
        self.platforms = []
        self.player_start = (100, 400)
        self.doors = []
        self.lights = []
        self.floating_orbs = []
        self.stars = []
        self.breakable_boxes = []
        self.player_abilities = {}
        self.keys_required = 0
        self.load_level(level_data)
        self.create_background_elements()
        
    def create_background_elements(self):
        # Create floating orbs
        for _ in range(20):
            self.floating_orbs.append(
                FloatingOrb(random.randint(50, SCREEN_WIDTH - 50),
                           random.randint(50, SCREEN_HEIGHT - 200))
            )
        
        # Create stars
        for _ in range(150):
            self.stars.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT * 2 // 3),
                'size': random.uniform(0.5, 2.5),
                'twinkle': random.uniform(0, math.pi * 2),
                'color': random.choice([WARM_WHITE, PEACH_GLOW, WARM_PINK])
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
        
        # Load doors
        for door_data in level_data.get('doors', []):
            door = Door(door_data['x'], door_data['y'], door_data['target_level'], door_data.get('label', ''))
            if door_data.get('locked', False):
                door.locked = True
                self.keys_required += 1
            self.doors.append(door)
            
        self.lights = [Light(*l) for l in level_data.get('lights', [])]
        
        # Load breakable boxes
        for box_data in level_data.get('breakable_boxes', []):
            box = BreakableBox(box_data['x'], box_data['y'], box_data.get('has_key', False))
            self.breakable_boxes.append(box)
            
        # Load player abilities
        self.player_abilities = level_data.get('abilities', {})
        
    def update(self, player):
        # Update background elements
        for orb in self.floating_orbs:
            orb.update()
            
        for star in self.stars:
            star['twinkle'] += 0.05
            
        # Update doors
        for door in self.doors:
            door.update()
        
        # Update lights
        for light in self.lights:
            light.update()
            
        # Update breakable boxes
        for box in self.breakable_boxes:
            box.update()
            
        # Update fireballs vs boxes
        if hasattr(player, 'fireballs'):
            for fireball in player.fireballs:
                if fireball.alive:
                    fireball.update(self.platforms, self.breakable_boxes)
                    
        # Check key collection
        for box in self.breakable_boxes:
            if box.broken and box.has_key and not box.key_collected:
                if (abs(player.rect.centerx - box.rect.centerx) < 30 and 
                    abs(player.rect.centery - box.rect.centery) < 30):
                    if box.collect_key():
                        player.keys += 1
                        
        # Unlock doors if player has keys
        for door in self.doors:
            if door.locked and player.keys > 0:
                door.locked = False
                player.keys -= 1
        
    def draw_background(self, screen):
        # Draw extra warm gradient background
        for y in range(SCREEN_HEIGHT):
            # Multi-layer gradient for depth
            time_offset = pygame.time.get_ticks() * 0.00003
            y_ratio = y / SCREEN_HEIGHT
            
            # Base gradient from warm night to sunset purple
            base_r = int(WARM_NIGHT[0] * (1 - y_ratio) + SUNSET_PURPLE[0] * y_ratio)
            base_g = int(WARM_NIGHT[1] * (1 - y_ratio) + SUNSET_PURPLE[1] * y_ratio)
            base_b = int(WARM_NIGHT[2] * (1 - y_ratio) + SUNSET_PURPLE[2] * y_ratio)
            
            # Add warm orange waves
            wave = math.sin(time_offset + y * 0.005) * 20
            r = max(0, min(255, base_r + int(wave * 1.5)))
            g = max(0, min(255, base_g + int(wave * 0.7)))
            b = max(0, min(255, base_b))
            
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        
        # Draw stars with warm twinkling
        for star in self.stars:
            brightness = (math.sin(star['twinkle']) + 1) * 0.5
            alpha = int(brightness * 255)
            size = star['size'] * (0.8 + brightness * 0.4)
            
            # Star glow
            glow_surf = pygame.Surface((int(size * 8), int(size * 8)), pygame.SRCALPHA)
            for i in range(3):
                glow_alpha = alpha // (i + 1)
                glow_size = size + i
                color = (*star['color'], glow_alpha)
                pygame.draw.circle(glow_surf, color, 
                                 (int(size * 4), int(size * 4)), 
                                 int(glow_size))
            screen.blit(glow_surf, (star['x'] - size * 4, star['y'] - size * 4))
        
        # Draw floating orbs
        for orb in self.floating_orbs:
            orb.draw(screen)
            
    def draw_platforms(self, screen):
        for i, platform in enumerate(self.platforms):
            # Skip drawing boundary walls (first 3 platforms)
            if i < 3:
                continue
            
            # Platform shadow for depth
            shadow_rect = platform.copy()
            shadow_rect.y += 8
            pygame.draw.rect(screen, SHADOW_COLOR, shadow_rect, border_radius=3)
            
            # Main platform with warm gradient
            # Top surface (lighter)
            top_rect = pygame.Rect(platform.x, platform.y, platform.width, platform.height // 3)
            pygame.draw.rect(screen, WARM_STONE, top_rect, border_radius=3)
            
            # Middle section
            mid_rect = pygame.Rect(platform.x, platform.y + platform.height // 3, 
                                 platform.width, platform.height // 3)
            pygame.draw.rect(screen, SUNSET_BROWN, mid_rect)
            
            # Bottom section (darker)
            bottom_rect = pygame.Rect(platform.x, platform.y + 2 * platform.height // 3, 
                                    platform.width, platform.height // 3)
            pygame.draw.rect(screen, CLAY, bottom_rect, border_radius=3)
            
            # Highlight edge
            pygame.draw.line(screen, PEACH_GLOW, 
                           (platform.x, platform.y + 2), 
                           (platform.x + platform.width, platform.y + 2), 2)
            
            # Add texture details
            for x in range(platform.x + 10, platform.x + platform.width - 10, 30):
                pygame.draw.line(screen, WARM_BROWN, 
                               (x, platform.y + 5), 
                               (x, platform.y + platform.height - 5), 1)

class Menu:
    def __init__(self):
        self.font_title = pygame.font.Font(None, 90)
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
                if random.random() < 0.4:
                    self.particles.append(
                        Particle(rect.centerx + random.randint(-50, 50),
                               rect.centery,
                               [MOLTEN_GOLD, FIRE_ORANGE, CORAL])
                    )
        
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
        self.bg_phase += 0.01
                
    def draw(self, screen):
        # Draw extra warm gradient background
        for y in range(SCREEN_HEIGHT):
            color_ratio = y / SCREEN_HEIGHT
            r = int(SUNSET_PURPLE[0] * (1 - color_ratio) + WARM_NIGHT[0] * color_ratio)
            g = int(SUNSET_PURPLE[1] * (1 - color_ratio) + WARM_NIGHT[1] * color_ratio)
            b = int(SUNSET_PURPLE[2] * (1 - color_ratio) + WARM_NIGHT[2] * color_ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        
        # Draw animated fire waves
        wave_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(5):
            wave_y = 200 + math.sin(self.bg_phase + i * 0.5) * 100
            wave_height = 200 + math.sin(self.bg_phase * 1.5 + i) * 50
            
            for y in range(int(wave_y), min(int(wave_y + wave_height), SCREEN_HEIGHT)):
                alpha = int(50 * (1 - (y - wave_y) / wave_height))
                color = random.choice([
                    (*FIRE_ORANGE, alpha),
                    (*EMBER_RED, alpha),
                    (*PEACH_GLOW, alpha)
                ])
                pygame.draw.line(wave_surf, color, 
                               (0, y), (SCREEN_WIDTH, y))
        screen.blit(wave_surf, (0, 0))
        
        # Draw floating fire orbs
        for i in range(10):
            x = SCREEN_WIDTH//2 + math.sin(self.bg_phase + i * 0.7) * 400
            y = 300 + math.cos(self.bg_phase * 0.5 + i) * 150
            size = 30 + math.sin(self.bg_phase + i) * 10
            
            # Fire orb with intense glow
            orb_surf = pygame.Surface((int(size * 5), int(size * 5)), pygame.SRCALPHA)
            for j in range(20):
                alpha = 80 - j * 4
                color = (*FIRE_ORANGE, alpha) if i % 2 else (*MOLTEN_GOLD, alpha)
                pygame.draw.circle(orb_surf, color, 
                                 (int(size * 2.5), int(size * 2.5)), 
                                 int(size + j * 2))
            screen.blit(orb_surf, (x - size * 2.5, y - size * 2.5))
        
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
                
        # Draw title with intense fire effects
        title = "LIGHT QUEST"
        
        # Outer fire glow
        for i in range(35):
            alpha = 25 - i // 1.4
            offset = i // 2
            for dx, dy in [(offset, offset), (-offset, offset), (offset, -offset), (-offset, -offset)]:
                glow_color = (*FIRE_ORANGE, int(alpha))
                glow_text = self.font_title.render(title, True, glow_color)
                screen.blit(glow_text, (SCREEN_WIDTH//2 - glow_text.get_width()//2 + dx, 150 + dy))
        
        # Main title
        text = self.font_title.render(title, True, WARM_WHITE)
        screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 150))
        
        # Inner highlight
        highlight = self.font_title.render(title, True, MOLTEN_GOLD)
        screen.blit(highlight, (SCREEN_WIDTH//2 - highlight.get_width()//2 - 2, 148))
        
        # Draw buttons
        for name, rect in self.buttons.items():
            # Button shadow
            shadow_rect = rect.copy()
            shadow_rect.x += 6
            shadow_rect.y += 6
            pygame.draw.rect(screen, SHADOW_COLOR, shadow_rect, border_radius=15)
            
            # Button glow on hover
            if self.hover == name:
                glow_surf = pygame.Surface((rect.width + 60, rect.height + 60), pygame.SRCALPHA)
                for i in range(30):
                    alpha = int(255 * (1 - i/30) * 0.5)
                    color = (*FIRE_ORANGE, alpha)
                    pygame.draw.rect(glow_surf, color,
                                   (i, i, rect.width + 60 - i*2, rect.height + 60 - i*2),
                                   border_radius=20)
                screen.blit(glow_surf, (rect.x - 30, rect.y - 30))
            
            # Button gradient
            button_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            
            if self.hover == name:
                # Hover state - intense fire gradient
                for y in range(rect.height):
                    color_ratio = y / rect.height
                    r = int(FIRE_ORANGE[0] * (1 - color_ratio) + EMBER_RED[0] * color_ratio)
                    g = int(FIRE_ORANGE[1] * (1 - color_ratio) + EMBER_RED[1] * color_ratio)
                    b = int(FIRE_ORANGE[2] * (1 - color_ratio) + EMBER_RED[2] * color_ratio)
                    pygame.draw.line(button_surf, (r, g, b), (0, y), (rect.width, y))
            else:
                # Normal state - warm gradient
                for y in range(rect.height):
                    color_ratio = y / rect.height
                    r = int(SUNSET_BROWN[0] * (1 - color_ratio) + CLAY[0] * color_ratio)
                    g = int(SUNSET_BROWN[1] * (1 - color_ratio) + CLAY[1] * color_ratio)
                    b = int(SUNSET_BROWN[2] * (1 - color_ratio) + CLAY[2] * color_ratio)
                    pygame.draw.line(button_surf, (r, g, b), (0, y), (rect.width, y))
            
            # Apply rounded corners
            rounded_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(rounded_surf, (255, 255, 255, 255), 
                           (0, 0, rect.width, rect.height), border_radius=15)
            button_surf.blit(button_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            
            screen.blit(button_surf, rect.topleft)
            
            # Button border
            border_color = MOLTEN_GOLD if self.hover == name else PEACH_GLOW
            pygame.draw.rect(screen, border_color, rect, 3, border_radius=15)
            
            # Button text
            text = "START GAME" if name == 'start' else "QUIT"
            button_text = self.font_button.render(text, True, WARM_WHITE)
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
        self.ambient_light = 40  # Warmer ambient light
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 20)
        self.transition = TransitionState()
        self.level_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        
    def load_levels(self):
        # Level data structure
        levels = [
            # Level 1 - Basic
            {
                'platforms': [
                    (0, 700, 1200, 100),
                    (200, 600, 200, 20),
                    (500, 500, 200, 20),
                    (800, 400, 200, 20),
                ],
                'player_start': (100, 600),
                'doors': [
                    {'x': 1050, 'y': 620, 'target_level': 1, 'label': 'Level 2'}
                ],
                'lights': [(600, 100), (200, 200), (1000, 150)],
                'abilities': {}
            },
            # Level 2 - Introduction to mechanics
            {
                'platforms': [
                    (0, 700, 1200, 100),
                    (100, 550, 150, 20),
                    (350, 450, 200, 20),
                    (650, 350, 150, 20),
                    (900, 450, 200, 20),
                ],
                'player_start': (100, 600),
                'doors': [
                    {'x': 550, 'y': 620, 'target_level': 0, 'label': 'Level 1'},
                    {'x': 1050, 'y': 620, 'target_level': 2, 'label': 'Level 3'}
                ],
                'lights': [(300, 150), (600, 100), (900, 150)],
                'abilities': {}
            },
            # Level 3 - Double Jump Hub
            {
                'platforms': [
                    (0, 700, 1200, 100),
                    (200, 550, 100, 20),
                    (400, 400, 100, 20),
                    (600, 250, 100, 20),
                    (800, 400, 100, 20),
                    (1000, 550, 100, 20),
                ],
                'player_start': (100, 600),
                'doors': [
                    {'x': 550, 'y': 620, 'target_level': 0, 'label': 'Back to Start'},
                    {'x': 1050, 'y': 620, 'target_level': 3, 'label': 'Level 4'}
                ],
                'lights': [(200, 100), (600, 50), (1000, 100)],
                'abilities': {'double_jump': True}
            },
            # Level 4 - Fireball and Keys
            {
                'platforms': [
                    (0, 700, 1200, 100),
                    (150, 600, 100, 20),
                    (350, 500, 100, 20),
                    (550, 600, 100, 20),
                    (750, 500, 100, 20),
                    (950, 600, 100, 20),
                ],
                'player_start': (50, 600),
                'doors': [
                    {'x': 550, 'y': 620, 'target_level': 2, 'label': 'Level 3'},
                    {'x': 1100, 'y': 620, 'target_level': 0, 'label': 'Victory!', 'locked': True}
                ],
                'lights': [(300, 100), (600, 100), (900, 100)],
                'abilities': {'double_jump': True, 'fireball': True},
                'breakable_boxes': [
                    {'x': 380, 'y': 460, 'has_key': True},
                    {'x': 580, 'y': 560, 'has_key': False},
                    {'x': 780, 'y': 460, 'has_key': False},
                ]
            }
        ]
        return levels
        
    def start_level(self, level_index):
        if level_index < len(self.levels):
            self.level = Level(self.levels[level_index], level_index)
            # Create player with level-specific abilities
            player_x, player_y = self.level.player_start
            self.player = Player(player_x, player_y, self.level.player_abilities)
            self.current_level = level_index
            self.state = GameState.PLAYING
            
    def start_transition(self, target_level):
        # Store start and target levels
        self.transition.start_level = self.current_level
        self.transition.target_level = target_level
        
        # Determine direction and intermediate levels
        self.transition.direction = 1 if target_level > self.current_level else -1
        
        # Capture current level state
        self.transition.old_level_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.draw_level_to_surface(self.transition.old_level_surface)
        
        # Capture intermediate level surfaces
        self.transition.intermediate_surfaces = []
        if abs(target_level - self.current_level) > 1:
            # Going through multiple levels
            start = min(self.current_level, target_level) + 1
            end = max(self.current_level, target_level)
            for i in range(start, end):
                # Temporarily load each intermediate level
                temp_level = Level(self.levels[i], i)
                temp_player = Player(*temp_level.player_start, temp_level.player_abilities)
                
                # Draw to surface
                intermediate_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                self.draw_intermediate_level_to_surface(intermediate_surface, temp_level, temp_player)
                self.transition.intermediate_surfaces.append(intermediate_surface)
                
            # Reverse the list if going backwards
            if self.transition.direction < 0:
                self.transition.intermediate_surfaces.reverse()
        
        # Setup new level
        self.start_level(target_level)
        
        # Capture new level state
        self.transition.new_level_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.draw_level_to_surface(self.transition.new_level_surface)
        
        # Initialize transition
        self.transition.phase = "shrink"
        self.transition.progress = 0.0
        self.transition.scale = 1.0
        self.transition.offset_x = 0
        self.state = GameState.TRANSITIONING
        
    def draw_intermediate_level_to_surface(self, surface, level, player):
        # Similar to draw_level_to_surface but for temporary levels
        level.draw_background(surface)
        level.draw_platforms(surface)
        
        for box in level.breakable_boxes:
            box.draw(surface)
            
        for door in level.doors:
            door.draw(surface, self.small_font)
            
        player.draw(surface)
        
        # Apply lighting
        self.light_surface.fill((*[self.ambient_light] * 3, 255))
        for light in level.lights:
            light.draw(surface, self.light_surface)
        surface.blit(self.light_surface, (0, 0), special_flags=pygame.BLEND_MULT)
        
    def draw_level_to_surface(self, surface):
        # Draw the current level to a surface
        self.level.draw_background(surface)
        self.level.draw_platforms(surface)
        
        # Draw breakable boxes
        for box in self.level.breakable_boxes:
            box.draw(surface)
            
        # Draw doors
        for door in self.level.doors:
            door.draw(surface, self.small_font)
            
        self.player.draw(surface)
        
        # Apply lighting
        self.light_surface.fill((*[self.ambient_light] * 3, 255))
        for light in self.level.lights:
            light.draw(surface, self.light_surface)
        surface.blit(self.light_surface, (0, 0), special_flags=pygame.BLEND_MULT)
        
    def update_transition(self):
        speed = 0.05
        
        if self.transition.phase == "shrink":
            self.transition.progress += speed
            self.transition.scale = 1.0 - (self.transition.progress * 0.25)  # Shrink to 75%
            
            if self.transition.progress >= 1.0:
                self.transition.phase = "swipe"
                self.transition.progress = 0.0
                
        elif self.transition.phase == "swipe":
            # Calculate total swipes needed (including intermediate levels)
            total_swipes = 1 + len(self.transition.intermediate_surfaces)
            swipe_speed = speed * 1.5 / total_swipes
            
            self.transition.progress += swipe_speed
            self.transition.offset_x = self.transition.progress * SCREEN_WIDTH * self.transition.direction * total_swipes
            
            if self.transition.progress >= 1.0:
                self.transition.phase = "grow"
                self.transition.progress = 0.0
                self.transition.offset_x = 0
                
        elif self.transition.phase == "grow":
            self.transition.progress += speed
            self.transition.scale = 0.75 + (self.transition.progress * 0.25)  # Grow back to 100%
            
            if self.transition.progress >= 1.0:
                self.state = GameState.PLAYING
                
    def draw_transition(self):
        # Clear screen with warm background
        self.screen.fill(WARM_NIGHT)
        
        if self.transition.phase == "shrink":
            # Draw old level shrinking
            scaled_size = (int(SCREEN_WIDTH * self.transition.scale), 
                          int(SCREEN_HEIGHT * self.transition.scale))
            scaled_surface = pygame.transform.smoothscale(self.transition.old_level_surface, scaled_size)
            
            # Center the scaled surface
            x = (SCREEN_WIDTH - scaled_size[0]) // 2
            y = (SCREEN_HEIGHT - scaled_size[1]) // 2
            
            # Add warm shadow effect
            shadow_surf = pygame.Surface(scaled_size, pygame.SRCALPHA)
            shadow_surf.fill((SHADOW_COLOR[0], SHADOW_COLOR[1], SHADOW_COLOR[2], 100))
            self.screen.blit(shadow_surf, (x + 10, y + 10))
            
            self.screen.blit(scaled_surface, (x, y))
            
        elif self.transition.phase == "swipe":
            # All levels at 75% scale
            scaled_size = (int(SCREEN_WIDTH * 0.75), int(SCREEN_HEIGHT * 0.75))
            y = (SCREEN_HEIGHT - scaled_size[1]) // 2
            
            # Calculate which levels to show based on offset
            offset_normalized = self.transition.offset_x / SCREEN_WIDTH
            
            # Draw all relevant surfaces
            surfaces_to_draw = []
            
            # Old level
            old_x = (SCREEN_WIDTH - scaled_size[0]) // 2 - self.transition.offset_x
            if abs(old_x) < SCREEN_WIDTH:
                surfaces_to_draw.append((self.transition.old_level_surface, old_x))
            
            # Intermediate levels
            for i, intermediate_surface in enumerate(self.transition.intermediate_surfaces):
                intermediate_x = (SCREEN_WIDTH - scaled_size[0]) // 2 + SCREEN_WIDTH * self.transition.direction * (i + 1) - self.transition.offset_x
                if abs(intermediate_x) < SCREEN_WIDTH:
                    surfaces_to_draw.append((intermediate_surface, intermediate_x))
            
            # New level
            total_offset = len(self.transition.intermediate_surfaces) + 1
            new_x = (SCREEN_WIDTH - scaled_size[0]) // 2 + SCREEN_WIDTH * self.transition.direction * total_offset - self.transition.offset_x
            if abs(new_x) < SCREEN_WIDTH:
                surfaces_to_draw.append((self.transition.new_level_surface, new_x))
            
            # Draw all visible surfaces
            for surface, x_pos in surfaces_to_draw:
                scaled = pygame.transform.smoothscale(surface, scaled_size)
                self.screen.blit(scaled, (x_pos, y))
                
        elif self.transition.phase == "grow":
            # Draw new level growing
            scaled_size = (int(SCREEN_WIDTH * self.transition.scale), 
                          int(SCREEN_HEIGHT * self.transition.scale))
            scaled_surface = pygame.transform.smoothscale(self.transition.new_level_surface, scaled_size)
            
            # Center the scaled surface
            x = (SCREEN_WIDTH - scaled_size[0]) // 2
            y = (SCREEN_HEIGHT - scaled_size[1]) // 2
            
            # Add intense warm glow effect as it grows
            glow_alpha = int(255 * (1 - self.transition.progress) * 0.4)
            glow_surf = pygame.Surface((scaled_size[0] + 60, scaled_size[1] + 60), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*FIRE_ORANGE, glow_alpha), 
                           (0, 0, scaled_size[0] + 60, scaled_size[1] + 60), 
                           border_radius=30)
            self.screen.blit(glow_surf, (x - 30, y - 30))
            
            self.screen.blit(scaled_surface, (x, y))
            
    def update(self):
        if self.state == GameState.MENU:
            self.menu.update()
        elif self.state == GameState.PLAYING:
            mouse_pos = pygame.mouse.get_pos()
            self.player.update(self.level.platforms, mouse_pos)
            self.level.update(self.player)
                
            # Check door collisions
            for door in self.level.doors:
                if self.player.rect.colliderect(door.rect) and not door.locked:
                    self.start_transition(door.target_level)
                    break
                    
        elif self.state == GameState.TRANSITIONING:
            self.update_transition()
                
    def draw(self):
        if self.state == GameState.MENU:
            self.menu.draw(self.screen)
        elif self.state == GameState.PLAYING:
            # Draw to level surface first
            self.draw_level_to_surface(self.screen)
            
            # Draw crosshair for fireball aiming
            if self.player.can_fireball:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                # Draw crosshair
                pygame.draw.circle(self.screen, FIRE_ORANGE, (mouse_x, mouse_y), 10, 2)
                pygame.draw.line(self.screen, FIRE_ORANGE, (mouse_x - 15, mouse_y), (mouse_x + 15, mouse_y), 2)
                pygame.draw.line(self.screen, FIRE_ORANGE, (mouse_x, mouse_y - 15), (mouse_x, mouse_y + 15), 2)
            
            # Draw UI
            ui_surf = pygame.Surface((350, 130), pygame.SRCALPHA)
            pygame.draw.rect(ui_surf, (*SHADOW_COLOR, 180), (0, 0, 350, 130), border_radius=10)
            pygame.draw.rect(ui_surf, (*PEACH_GLOW, 100), (0, 0, 350, 130), 2, border_radius=10)
            
            level_text = self.font.render(f"Level {self.current_level + 1}", True, WARM_WHITE)
            ui_surf.blit(level_text, (10, 10))
            
            # Show abilities
            ability_y = 45
            if self.player.abilities.get('double_jump'):
                ability_text = self.small_font.render("Double Jump: Jump while in air", True, MOLTEN_GOLD)
                ui_surf.blit(ability_text, (10, ability_y))
                ability_y += 25
                
            if self.player.abilities.get('fireball'):
                ability_text = self.small_font.render("Fireball: F or Shift (aim with mouse)", True, FIRE_ORANGE)
                ui_surf.blit(ability_text, (10, ability_y))
                ability_y += 25
                
            # Show keys
            if self.player.keys > 0:
                key_text = self.small_font.render(f"Keys: {self.player.keys}", True, KEY_GOLD)
                ui_surf.blit(key_text, (10, ability_y))
            
            controls_text = self.small_font.render("Arrow Keys/WASD: Move | Space: Jump", True, WARM_WHITE)
            ui_surf.blit(controls_text, (10, 105))
            
            self.screen.blit(ui_surf, (10, 10))
            
        elif self.state == GameState.TRANSITIONING:
            self.draw_transition()
            
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

# Run the game
if __name__ == "__main__":
    game = Game()
    game.run()