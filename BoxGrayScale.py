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

# Limbo Color Palette - Grayscale only
BLACK = (0, 0, 0)
DARK_GRAY = (20, 20, 20)
MEDIUM_GRAY = (40, 40, 40)
LIGHT_GRAY = (80, 80, 80)
LIGHTER_GRAY = (120, 120, 120)
FOG_GRAY = (160, 160, 160)
WHITE = (255, 255, 255)

# Silhouette colors
SILHOUETTE = BLACK
BACKGROUND = (180, 180, 180)
FOG_COLOR = (200, 200, 200)
LIGHT_COLOR = (255, 255, 255)

class GameState(Enum):
    MENU = 1
    PLAYING = 2
    LEVEL_COMPLETE = 3
    TRANSITIONING = 4

class TransitionState:
    def __init__(self):
        self.phase = "shrink"
        self.progress = 0.0
        self.old_level_surface = None
        self.new_level_surface = None
        self.intermediate_surfaces = []
        self.scale = 1.0
        self.offset_x = 0
        self.target_level = 0
        self.start_level = 0
        self.direction = 1

class FogParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = random.randint(50, 150)
        self.speed = random.uniform(0.2, 0.5)
        self.opacity = random.randint(20, 60)
        self.phase = random.uniform(0, math.pi * 2)
        
    def update(self):
        self.x += self.speed
        self.phase += 0.01
        self.y += math.sin(self.phase) * 0.3
        
        if self.x > SCREEN_WIDTH + self.size:
            self.x = -self.size
            self.y = random.randint(0, SCREEN_HEIGHT)
            
    def draw(self, surface):
        fog_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        for i in range(self.size, 0, -5):
            alpha = int(self.opacity * (i / self.size))
            color = (*FOG_COLOR, alpha)
            pygame.draw.circle(fog_surf, color, (self.size, self.size), i)
        surface.blit(fog_surf, (self.x - self.size, self.y - self.size))

class DustParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-1, -0.5)
        self.life = 1.0
        self.size = random.randint(2, 4)
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.02
        self.vy += 0.02
        
    def draw(self, surface):
        if self.life > 0:
            alpha = int(100 * self.life)
            particle_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            color = (*LIGHT_GRAY, alpha)
            pygame.draw.circle(particle_surf, color, (self.size, self.size), self.size)
            surface.blit(particle_surf, (self.x - self.size, self.y - self.size))

class Fireball:
    def __init__(self, x, y, target_x, target_y):
        self.rect = pygame.Rect(x, y, 16, 16)
        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx*dx + dy*dy)
        if distance > 0:
            self.vel_x = (dx / distance) * 12
            self.vel_y = (dy / distance) * 12
        else:
            self.vel_x = 12
            self.vel_y = 0
        self.particles = []
        self.alive = True
        self.life = 60
        
    def update(self, platforms, breakable_boxes):
        for particle in self.particles:
            particle.update()
        self.particles = [p for p in self.particles if p.life > 0]

        if not self.alive:
            return

        self.life -= 1
        if self.life <= 0:
            self.alive = False
            return
            
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        
        for platform in platforms:
            if platform.get('solid', True) and self.rect.colliderect(platform['rect']):
                self.explode()
                return
                
        for box in breakable_boxes:
            if self.rect.colliderect(box.rect) and not box.broken:
                box.break_box()
                self.explode()
                return
                
        if random.random() < 0.8:
            self.particles.append(DustParticle(
                self.rect.centerx + random.randint(-3, 3),
                self.rect.centery + random.randint(-3, 3)
            ))
            
        if (self.rect.x < -50 or self.rect.x > SCREEN_WIDTH + 50 or
            self.rect.y < -50 or self.rect.y > SCREEN_HEIGHT + 50):
            self.alive = False
            
    def explode(self):
        self.alive = False
        for _ in range(15):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 5)
            particle = DustParticle(self.rect.centerx, self.rect.centery)
            particle.vx = math.cos(angle) * speed
            particle.vy = math.sin(angle) * speed
            self.particles.append(particle)
            
    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)
            
        if self.alive:
            # White glowing orb
            glow_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            for i in range(16, 0, -2):
                alpha = int(150 * (i / 16))
                color = (*WHITE, alpha)
                pygame.draw.circle(glow_surf, color, (16, 16), i)
            screen.blit(glow_surf, (self.rect.x - 8, self.rect.y - 8))

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
            for _ in range(12):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 5)
                particle = DustParticle(self.rect.centerx, self.rect.centery)
                particle.vx = math.cos(angle) * speed
                particle.vy = math.sin(angle) * speed - 2
                self.particles.append(particle)
                
    def update(self):
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
        if self.broken and self.has_key and not self.key_collected:
            self.key_float_phase += 0.1
            self.key_y_offset = math.sin(self.key_float_phase) * 5
            
    def collect_key(self):
        if self.broken and self.has_key and not self.key_collected:
            self.key_collected = True
            return True
        return False
        
    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)
            
        if not self.broken:
            # Silhouette box
            pygame.draw.rect(screen, SILHOUETTE, self.rect)
            # Subtle highlight
            pygame.draw.rect(screen, DARK_GRAY, self.rect, 1)
                           
        elif self.has_key and not self.key_collected:
            key_x = self.rect.centerx
            key_y = self.rect.centery - 20 + self.key_y_offset
            
            # Glowing key
            glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            for i in range(20, 0, -2):
                alpha = int(120 * (i / 20))
                pygame.draw.circle(glow_surf, (*WHITE, alpha), (30, 30), i)
            screen.blit(glow_surf, (key_x - 30, key_y - 30))
            
            # Key silhouette
            pygame.draw.circle(screen, SILHOUETTE, (key_x, key_y), 6)
            pygame.draw.rect(screen, SILHOUETTE, (key_x - 2, key_y, 4, 12))
            pygame.draw.rect(screen, SILHOUETTE, (key_x - 2, key_y + 8, 6, 2))
            pygame.draw.rect(screen, SILHOUETTE, (key_x - 2, key_y + 11, 4, 2))

class NPC:
    def __init__(self, x, y, dialogues):
        self.rect = pygame.Rect(x, y - 50, 30, 50)
        self.x = x
        self.y = y
        self.dialogues = dialogues  # Dict with keys like "from_0", "from_1", "default"
        self.bob_phase = random.uniform(0, math.pi * 2)
        self.show_prompt = False
        self.current_dialogue = None
        self.dialogue_timer = 0
        
    def update(self, player_rect, from_level):
        # Bob animation
        self.bob_phase += 0.05
        self.rect.y = self.y - 50 + math.sin(self.bob_phase) * 3
        
        # Check proximity to player
        distance = math.sqrt((player_rect.centerx - self.rect.centerx)**2 + 
                           (player_rect.centery - self.rect.centery)**2)
        self.show_prompt = distance < 60
        
        # Update dialogue timer
        if self.dialogue_timer > 0:
            self.dialogue_timer -= 1
            
    def interact(self, from_level, current_level):
        # Determine which dialogue to show
        key = f"from_{from_level}" if from_level != current_level else "default"
        if key not in self.dialogues:
            key = "default"
        
        self.current_dialogue = self.dialogues.get(key, "...")
        self.dialogue_timer = 180  # 3 seconds at 60 FPS
        
    def draw(self, screen, font):
        # Draw NPC silhouette
        # Body
        body_rect = pygame.Rect(self.rect.x + 5, self.rect.y + 20, 20, 30)
        pygame.draw.ellipse(screen, SILHOUETTE, body_rect)
        
        # Head
        head_rect = pygame.Rect(self.rect.x + 8, self.rect.y + 5, 14, 18)
        pygame.draw.ellipse(screen, SILHOUETTE, head_rect)
        
        # Arms
        pygame.draw.line(screen, SILHOUETTE, 
                        (self.rect.x + 5, self.rect.y + 25),
                        (self.rect.x - 2, self.rect.y + 35), 3)
        pygame.draw.line(screen, SILHOUETTE, 
                        (self.rect.x + 25, self.rect.y + 25),
                        (self.rect.x + 32, self.rect.y + 35), 3)
        
        # Show interaction prompt
        if self.show_prompt and self.dialogue_timer <= 0:
            # E key prompt
            prompt_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.rect(prompt_surf, (*WHITE, 100), (0, 0, 30, 30), border_radius=5)
            pygame.draw.rect(prompt_surf, SILHOUETTE, (5, 5, 20, 20), border_radius=3)
            
            e_text = font.render("E", True, WHITE)
            prompt_surf.blit(e_text, (15 - e_text.get_width()//2, 15 - e_text.get_height()//2))
            
            screen.blit(prompt_surf, (self.rect.centerx - 15, self.rect.y - 40))
        
        # Show dialogue
        if self.dialogue_timer > 0 and self.current_dialogue:
            # Dialogue bubble
            dialogue_text = font.render(self.current_dialogue, True, SILHOUETTE)
            bubble_width = dialogue_text.get_width() + 20
            bubble_height = dialogue_text.get_height() + 16
            
            bubble_surf = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
            pygame.draw.rect(bubble_surf, (*WHITE, 200), (0, 0, bubble_width, bubble_height), border_radius=10)
            pygame.draw.rect(bubble_surf, SILHOUETTE, (0, 0, bubble_width, bubble_height), 2, border_radius=10)
            
            # Tail
            tail_points = [
                (20, bubble_height),
                (30, bubble_height),
                (15, bubble_height + 10)
            ]
            pygame.draw.polygon(bubble_surf, (*WHITE, 200), tail_points)
            pygame.draw.lines(bubble_surf, SILHOUETTE, False, tail_points[0:2], 2)
            pygame.draw.lines(bubble_surf, SILHOUETTE, False, tail_points[1:3], 2)
            
            bubble_surf.blit(dialogue_text, (10, 8))
            
            bubble_x = self.rect.centerx - bubble_width // 2
            bubble_y = self.rect.y - bubble_height - 20
            screen.blit(bubble_surf, (bubble_x, bubble_y))

class Player:
    def __init__(self, x, y, abilities=None):
        self.rect = pygame.Rect(x, y, 25, 40)
        self.vel_y = 0
        self.vel_x = 0
        self.on_ground = False
        self.on_drop_platform = False
        self.dropping = False
        self.drop_timer = 0
        self.drop_key_pressed = False
        self.particles = []
        
        # Abilities
        self.abilities = abilities or {}
        self.jump_available = self.abilities.get('jump', False)
        self.double_jump_available = self.abilities.get('double_jump', False)
        self.can_double_jump = False
        self.jump_pressed = False
        self.can_fireball = self.abilities.get('fireball', False)
        self.fireballs = []
        self.fireball_cooldown = 0
        self.facing_right = True
        
        # Keys collected
        self.keys = 0

    def set_position(self, x, y):
        self.rect = pygame.Rect(x, y, 25, 40)

    def set_abilities(self, abilities={}):
        for tmp in abilities:
            self.abilities[tmp] = abilities[tmp]

        self.jump_available = self.abilities.get('jump', False)
        self.double_jump_available = self.abilities.get('double_jump', False)
        self.can_fireball = self.abilities.get('fireball', False)
        
    def update(self, platforms, mouse_pos):
        keys = pygame.key.get_pressed()
        self.vel_x = 0
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
            self.facing_right = True
            
        # Drop through platforms - fixed logic
        drop_key = keys[pygame.K_s] or keys[pygame.K_DOWN]
        
        if drop_key and not self.drop_key_pressed and self.on_drop_platform:
            self.dropping = True
            self.drop_timer = 10
            self.vel_y = 2  # Small downward velocity to ensure drop
            
        self.drop_key_pressed = drop_key
            
        if self.drop_timer > 0:
            self.drop_timer -= 1
        else:
            self.dropping = False
            
        # Jumping logic
        jump_key = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
        
        if self.jump_available and jump_key and not self.jump_pressed:
            if self.on_ground:
                self.vel_y = JUMP_STRENGTH
                self.can_double_jump = self.double_jump_available
                for _ in range(8):
                    self.particles.append(DustParticle(
                        self.rect.centerx + random.randint(-8, 8), 
                        self.rect.bottom
                    ))
            elif self.can_double_jump:
                self.vel_y = JUMP_STRENGTH * 0.85
                self.can_double_jump = False
                for _ in range(12):
                    angle = random.uniform(0, math.pi * 2)
                    speed = random.uniform(2, 4)
                    particle = DustParticle(self.rect.centerx, self.rect.centery)
                    particle.vx = math.cos(angle) * speed
                    particle.vy = math.sin(angle) * speed
                    self.particles.append(particle)
                    
        self.jump_pressed = jump_key
                    
        # Fireball ability
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
            
        # Move horizontally
        self.rect.x += self.vel_x
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
        self.check_collisions(platforms, 'horizontal')
        
        # Move vertically
        self.rect.y += self.vel_y
        self.on_ground = False
        self.on_drop_platform = False
        self.check_collisions(platforms, 'vertical')
        
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
        # Update fireballs
        self.fireballs = [f for f in self.fireballs if f.alive or len(f.particles) > 0]
        for fireball in self.fireballs:
            fireball.update(platforms, [])
            
    def check_collisions(self, platforms, direction):
        for platform in platforms:
            platform_rect = platform['rect']
            is_drop_platform = not platform.get('solid', True)
            
            if self.rect.colliderect(platform_rect):
                if direction == 'horizontal':
                    if not is_drop_platform:
                        if self.vel_x > 0:
                            self.rect.right = platform_rect.left
                        else:
                            self.rect.left = platform_rect.right
                else:  # vertical
                    if is_drop_platform:
                        # Only collide with drop platforms when falling and not dropping
                        if self.vel_y > 0 and not self.dropping:
                            # Check if player was above platform
                            if self.rect.bottom - self.vel_y <= platform_rect.top + 5:
                                self.rect.bottom = platform_rect.top
                                self.vel_y = 0
                                self.on_ground = True
                                self.on_drop_platform = True
                    else:
                        # Solid platforms
                        if self.vel_y > 0:
                            self.rect.bottom = platform_rect.top
                            self.vel_y = 0
                            self.on_ground = True
                            if abs(self.vel_y) > 5:
                                for _ in range(4):
                                    self.particles.append(DustParticle(
                                        self.rect.centerx + random.randint(-10, 10), 
                                        self.rect.bottom
                                    ))
                        else:
                            self.rect.top = platform_rect.bottom
                            self.vel_y = 0
                        
    def draw(self, screen):
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
            
        # Draw fireballs
        for fireball in self.fireballs:
            fireball.draw(screen)
            
        # Draw player silhouette
        # Body
        body_rect = pygame.Rect(self.rect.x + 3, self.rect.y + 15, 19, 25)
        pygame.draw.ellipse(screen, SILHOUETTE, body_rect)
        
        # Head
        head_rect = pygame.Rect(self.rect.x + 5, self.rect.y, 15, 18)
        pygame.draw.ellipse(screen, SILHOUETTE, head_rect)
        
        # Legs with walking animation
        leg_offset = abs(int(self.vel_x)) % 10 if self.vel_x != 0 else 0
        # Left leg
        pygame.draw.line(screen, SILHOUETTE,
                        (self.rect.x + 8, self.rect.y + 35),
                        (self.rect.x + 6 - leg_offset//3, self.rect.bottom), 4)
        # Right leg
        pygame.draw.line(screen, SILHOUETTE,
                        (self.rect.x + 17, self.rect.y + 35),
                        (self.rect.x + 19 + leg_offset//3, self.rect.bottom), 4)
        
        # Arms
        pygame.draw.line(screen, SILHOUETTE,
                        (self.rect.x + 3, self.rect.y + 20),
                        (self.rect.x - 2, self.rect.y + 30), 3)
        pygame.draw.line(screen, SILHOUETTE,
                        (self.rect.x + 22, self.rect.y + 20),
                        (self.rect.x + 27, self.rect.y + 30), 3)
        
        # Double jump indicator
        if self.double_jump_available and self.can_double_jump and not self.on_ground:
            indicator_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            for i in range(15, 0, -2):
                alpha = int(100 * (i / 15))
                pygame.draw.circle(indicator_surf, (*WHITE, alpha), (15, 15), i)
            screen.blit(indicator_surf, (self.rect.centerx - 15, self.rect.y - 35))

class Door:
    def __init__(self, x, y, target_level, label=""):
        self.rect = pygame.Rect(x, y, 50, 70)
        self.target_level = target_level
        self.label = label
        self.glow_timer = 0
        self.particles = []
        self.locked = False
        
    def update(self):
        self.glow_timer += 0.05
        
        if random.random() < 0.02 and not self.locked:
            particle = DustParticle(
                self.rect.centerx + random.randint(-15, 15),
                self.rect.y + random.randint(0, self.rect.height)
            )
            particle.vy -= 0.5
            self.particles.append(particle)
        
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            particle.vy -= 0.1
        
    def draw(self, screen, font):
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
            
        # Door glow if unlocked
        if not self.locked:
            glow_intensity = (math.sin(self.glow_timer) + 1) * 0.3
            glow_surf = pygame.Surface((self.rect.width + 40, self.rect.height + 40), pygame.SRCALPHA)
            for i in range(20, 0, -2):
                alpha = int(100 * glow_intensity * (i / 20))
                pygame.draw.rect(glow_surf, (*WHITE, alpha), 
                               (20 - i, 20 - i, self.rect.width + i*2, self.rect.height + i*2),
                               border_radius=5)
            screen.blit(glow_surf, (self.rect.x - 20, self.rect.y - 20))
        
        # Door silhouette
        pygame.draw.rect(screen, SILHOUETTE, self.rect, border_radius=5)
        
        # Door details
        inner_rect = self.rect.inflate(-10, -10)
        pygame.draw.rect(screen, DARK_GRAY, inner_rect, 2, border_radius=3)
        
        # Lock or handle
        if self.locked:
            # Lock
            lock_rect = pygame.Rect(self.rect.centerx - 8, self.rect.centery - 8, 16, 16)
            pygame.draw.rect(screen, DARK_GRAY, lock_rect, border_radius=2)
            pygame.draw.circle(screen, SILHOUETTE, lock_rect.center, 3)
        else:
            # Handle
            handle_x = self.rect.x + self.rect.width - 12
            handle_y = self.rect.centery
            pygame.draw.circle(screen, DARK_GRAY, (handle_x, handle_y), 4)
            
        # Label
        if self.label:
            label_surf = pygame.Surface((100, 20), pygame.SRCALPHA)
            label_text = font.render(self.label, True, SILHOUETTE)
            label_surf.blit(label_text, (50 - label_text.get_width()//2, 10 - label_text.get_height()//2))
            screen.blit(label_surf, (self.rect.centerx - 50, self.rect.y - 25))

class Light:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 200
        self.flicker_timer = random.uniform(0, math.pi * 2)
        
    def update(self):
        self.flicker_timer += 0.03
        
    def draw(self, screen, light_surface):
        # Light source (not visible in Limbo style)
        flicker = math.sin(self.flicker_timer) * 20
        current_radius = self.radius + flicker
        
        # Dramatic light cone
        """
        for r in range(int(current_radius), 0, -100):
            distance_ratio = r / current_radius
            # More dramatic falloff
            alpha = int(255 * (1 - distance_ratio) ** 0.7)
            color = (255, 255, 255, 159)
        """
        #pygame.draw.circle(light_surface, (255, 255, 255, 70), (int(self.x), int(self.y)), self.radius)

class Level:
    def __init__(self, level_data, level_number):
        self.level_number = level_number
        self.platforms = []
        self.player_start = (100, 400)
        self.doors = []
        self.lights = []
        self.breakable_boxes = []
        self.player_abilities = {}
        self.keys_required = 0
        self.fog_particles = []
        self.npcs = []
        self.load_level(level_data)
        
        # Create fog particles
        for _ in range(10):
            self.fog_particles.append(FogParticle(
                random.randint(-200, SCREEN_WIDTH),
                random.randint(0, SCREEN_HEIGHT)
            ))
        
    def load_level(self, level_data):
        # Load platforms
        platform_data = level_data.get('platforms', [])
        for p in platform_data:
            if len(p) > 4:
                self.platforms.append({
                    'rect': pygame.Rect(p[0], p[1], p[2], p[3]),
                    'solid': p[4]
                })
            else:
                self.platforms.append({
                    'rect': pygame.Rect(p[0], p[1], p[2], p[3]),
                    'solid': True
                })
        
        self.player_start = level_data.get('player_start', (100, 400))
        
        # Load doors
        for door_data in level_data.get('doors', []):
            door = Door(door_data['x'], door_data['y'], 
                       door_data['target_level'], 
                       door_data.get('label', ''))
            if door_data.get('locked', False):
                door.locked = True
                self.keys_required += 1
            self.doors.append(door)
            
        self.lights = [Light(*l) for l in level_data.get('lights', [])]
        
        # Load breakable boxes
        for box_data in level_data.get('breakable_boxes', []):
            box = BreakableBox(box_data['x'], box_data['y'], 
                             box_data.get('has_key', False))
            self.breakable_boxes.append(box)
            
        # Load NPCs
        for npc_data in level_data.get('npcs', []):
            npc = NPC(npc_data['x'], npc_data['y'], npc_data['dialogues'])
            self.npcs.append(npc)
            
        self.player_abilities = level_data.get('abilities', {})
        
    def update(self, player, from_level):
        # Update fog
        for fog in self.fog_particles:
            fog.update()
            
        # Update doors
        for door in self.doors:
            door.update()
        
        # Update lights
        for light in self.lights:
            light.update()
            
        # Update breakable boxes
        for box in self.breakable_boxes:
            box.update()
            
        # Update NPCs
        for npc in self.npcs:
            npc.update(player.rect, from_level)
            
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
                        
        # Unlock doors
        for door in self.doors:
            if door.locked and player.keys > 0:
                door.locked = False
                player.keys -= 1
        
    def draw_background(self, screen):
        # Gradient background
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            gray = int(BACKGROUND[0] * (1 - ratio * 0.3))
            pygame.draw.line(screen, (gray, gray, gray), (0, y), (SCREEN_WIDTH, y))
            
        # Draw fog
        for fog in self.fog_particles:
            fog.draw(screen)
            
    def draw_platforms(self, screen):
        for platform in self.platforms:
            platform_rect = platform['rect']
            is_drop_platform = not platform.get('solid', True)
            
            if is_drop_platform:
                # Drop-through platforms - thinner and slightly transparent
                thin_rect = pygame.Rect(platform_rect.x, platform_rect.y, platform_rect.width, 8)
                
                # Platform surface
                platform_surf = pygame.Surface((thin_rect.width, thin_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(platform_surf, (*SILHOUETTE, 180), (0, 0, thin_rect.width, thin_rect.height))
                screen.blit(platform_surf, thin_rect.topleft)
                
                # Edge highlights
                pygame.draw.line(screen, DARK_GRAY, 
                               (thin_rect.left, thin_rect.top),
                               (thin_rect.right, thin_rect.top), 1)
            else:
                # Solid platforms - full silhouette
                pygame.draw.rect(screen, SILHOUETTE, platform_rect)
                # Top edge highlight
                pygame.draw.line(screen, DARK_GRAY, 
                               (platform_rect.left, platform_rect.top),
                               (platform_rect.right, platform_rect.top), 2)

class Menu:
    def __init__(self):
        self.font_title = pygame.font.Font(None, 100)
        self.font_button = pygame.font.Font(None, 40)
        self.buttons = {
            'start': pygame.Rect(SCREEN_WIDTH//2 - 120, 400, 240, 50),
            'quit': pygame.Rect(SCREEN_WIDTH//2 - 120, 480, 240, 50)
        }
        self.hover = None
        self.particles = []
        self.bg_phase = 0
        self.fog_particles = []
        
        # Create fog
        for _ in range(15):
            self.fog_particles.append(FogParticle(
                random.randint(-200, SCREEN_WIDTH),
                random.randint(0, SCREEN_HEIGHT)
            ))
        
    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        self.hover = None
        for name, rect in self.buttons.items():
            if rect.collidepoint(mouse_pos):
                self.hover = name
                if random.random() < 0.1:
                    self.particles.append(DustParticle(
                        rect.centerx + random.randint(-40, 40),
                        rect.centery
                    ))
        
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update()
            
        for fog in self.fog_particles:
            fog.update()
            
        self.bg_phase += 0.01
                
    def draw(self, screen):
        # Limbo-style gradient background
        for y in range(SCREEN_HEIGHT):
            gray = int(160 - (y / SCREEN_HEIGHT) * 60)
            pygame.draw.line(screen, (gray, gray, gray), (0, y), (SCREEN_WIDTH, y))
        
        # Fog effect
        for fog in self.fog_particles:
            fog.draw(screen)
        
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
                
        # Title
        title = "LIMBO"
        title_surf = pygame.Surface((600, 150), pygame.SRCALPHA)
        
        # Title shadow
        shadow_text = self.font_title.render(title, True, SILHOUETTE)
        title_surf.blit(shadow_text, (300 - shadow_text.get_width()//2 + 5, 80 + 5))
        
        # Main title
        text = self.font_title.render(title, True, DARK_GRAY)
        title_surf.blit(text, (300 - text.get_width()//2, 80))
        
        screen.blit(title_surf, (SCREEN_WIDTH//2 - 300, 100))
        
        # Draw buttons
        for name, rect in self.buttons.items():
            if self.hover == name:
                # Glow effect
                glow_surf = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*WHITE, 50), (0, 0, rect.width + 20, rect.height + 20), border_radius=5)
                screen.blit(glow_surf, (rect.x - 10, rect.y - 10))
            
            # Button
            pygame.draw.rect(screen, SILHOUETTE, rect, border_radius=5)
            pygame.draw.rect(screen, DARK_GRAY, rect, 2, border_radius=5)
            
            # Text
            text = "START" if name == 'start' else "QUIT"
            text_color = WHITE if self.hover == name else LIGHT_GRAY
            button_text = self.font_button.render(text, True, text_color)
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
        pygame.display.set_caption("Limbo")
        self.clock = pygame.time.Clock()
        self.state = GameState.MENU
        self.menu = Menu()
        self.current_level = 0
        self.from_level = 0  # Track which level we came from
        self.levels = self.load_levels()
        self.level = None
        self.player = None
        self.light_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.ambient_light = 40
        self.font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 16)
        self.transition = TransitionState()
        self.level_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        
    def load_levels(self):
        levels = [
            # Level 1 - Basic
            {
                'platforms': [
                    (0, 700, 1200, 100),
                    (200, 600, 200, 20),
                    (500, 500, 200, 20),
                    (800, 400, 200, 20),
                    (350, 450, 150, 20, False),  # Drop-through
                ],
                'player_start': (100, 600),
                'doors': [
                    {'x': 1050, 'y': 630, 'target_level': 1, 'label': 'Next'}
                ],
                'lights': [(600, 200), (200, 300), (1000, 250)],
                'npcs': [
                    {
                        'x': 600,
                        'y': 700,
                        'dialogues': {
                            'default': "You cant do anything can you? Try moving to the next door",
                            'from_1': "Back so soon? The path ahead awaits.",
                            'from_2': "You've traveled far. Rest here.",
                        }
                    }
                ],
                'abilities': {}
            },
            # Level 2
            {
                'platforms': [
                    (0, 700, 1200, 100),
                    (100, 550, 150, 20),
                    (350, 450, 200, 20),
                    (650, 350, 150, 20),
                    (900, 450, 200, 20),
                    (250, 500, 100, 20, False),
                    (750, 400, 100, 20, False),
                ],
                'player_start': (100, 600),
                'doors': [
                    {'x': 50, 'y': 630, 'target_level': 0, 'label': 'Back'},
                    {'x': 1050, 'y': 630, 'target_level': 2, 'label': 'Deeper'}
                ],
                'lights': [(300, 200), (600, 150), (900, 200)],
                'npcs': [
                    {
                        'x': 500,
                        'y': 700,
                        'dialogues': {
                            'default': "The darkness grows deeper...",
                            'from_0': "You've taken your first steps.",
                            'from_2': "Running from what lies ahead?",
                        }
                    }
                ],
                'abilities': {'jump': True}
            },
            # Level 3 - Double Jump
            {
                'platforms': [
                    (0, 700, 1200, 100),
                    (200, 550, 100, 20),
                    (400, 400, 100, 20),
                    (600, 250, 100, 20),
                    (800, 400, 100, 20),
                    (1000, 550, 100, 20),
                    (300, 475, 80, 20, False),
                    (700, 325, 80, 20, False),
                ],
                'player_start': (100, 600),
                'doors': [
                    {'x': 50, 'y': 630, 'target_level': 0, 'label': 'Beginning'},
                    {'x': 1050, 'y': 630, 'target_level': 3, 'label': 'Final'}
                ],
                'lights': [(200, 150), (600, 100), (1000, 150)],
                'npcs': [
                    {
                        'x': 600,
                        'y': 250,
                        'dialogues': {
                            'default': "You've gained new strength. Jump twice, shadow walker.",
                            'from_0': "Such a long journey from the start...",
                            'from_3': "The end was not for you... yet.",
                        }
                    }
                ],
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
                    {'x': 550, 'y': 630, 'target_level': 2, 'label': 'Return'},
                    {'x': 1100, 'y': 630, 'target_level': 0, 'label': 'End', 'locked': True}
                ],
                'lights': [(300, 200), (600, 200), (900, 200)],
                'breakable_boxes': [
                    {'x': 380, 'y': 460, 'has_key': True},
                    {'x': 580, 'y': 560, 'has_key': False},
                    {'x': 780, 'y': 460, 'has_key': False},
                ],
                'npcs': [
                    {
                        'x': 400,
                        'y': 700,
                        'dialogues': {
                            'default': "Light can shatter darkness. Press F to cast.",
                            'from_2': "You've come to face the final challenge.",
                            'from_0': "How did you get here so quickly?",
                        }
                    }
                ],
                'abilities': {'double_jump': True, 'fireball': True},
            }
        ]
        return levels
        
    def start_level(self, level_index):
        if level_index < len(self.levels):
            self.level = Level(self.levels[level_index], level_index)
            player_x, player_y = self.level.player_start
            if self.player == None:
                self.player = Player(player_x, player_y, self.level.player_abilities)
            else:
                self.player.set_position(player_x, player_y)
                self.player.set_abilities(self.level.player_abilities)
            self.current_level = level_index
            self.state = GameState.PLAYING
            
    def start_transition(self, target_level):
        self.transition.start_level = self.current_level
        self.transition.target_level = target_level
        self.transition.direction = 1 if target_level > self.current_level else -1
        
        # Update from_level for NPC dialogues
        self.from_level = self.current_level
        
        # Capture current level
        self.transition.old_level_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.draw_level_to_surface(self.transition.old_level_surface)
        
        # Capture intermediate levels
        self.transition.intermediate_surfaces = []
        if abs(target_level - self.current_level) > 1:
            start = min(self.current_level, target_level) + 1
            end = max(self.current_level, target_level)
            for i in range(start, end):
                temp_level = Level(self.levels[i], i)
                temp_player = Player(*temp_level.player_start, temp_level.player_abilities)
                
                intermediate_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                self.draw_intermediate_level_to_surface(intermediate_surface, temp_level, temp_player)
                self.transition.intermediate_surfaces.append(intermediate_surface)
                
            if self.transition.direction < 0:
                self.transition.intermediate_surfaces.reverse()
        
        # Setup new level
        self.start_level(target_level)
        
        # Capture new level
        self.transition.new_level_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.draw_level_to_surface(self.transition.new_level_surface)
        
        # Initialize transition
        self.transition.phase = "shrink"
        self.transition.progress = 0.0
        self.transition.scale = 1.0
        self.transition.offset_x = 0
        self.state = GameState.TRANSITIONING
        
    def draw_intermediate_level_to_surface(self, surface, level, player):
        level.draw_background(surface)
        level.draw_platforms(surface)
        
        for box in level.breakable_boxes:
            box.draw(surface)
            
        for door in level.doors:
            door.draw(surface, self.small_font)
            
        for npc in level.npcs:
            npc.draw(surface, self.small_font)
            
        player.draw(surface)
        
        # Apply lighting
        self.light_surface.fill((self.ambient_light, self.ambient_light, self.ambient_light, 255))
        for light in level.lights:
            light.draw(surface, self.light_surface)
        surface.blit(self.light_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        
    def draw_level_to_surface(self, surface):
        self.level.draw_background(surface)
        self.level.draw_platforms(surface)
        
        for box in self.level.breakable_boxes:
            box.draw(surface)
            
        for door in self.level.doors:
            door.draw(surface, self.small_font)
            
        for npc in self.level.npcs:
            npc.draw(surface, self.small_font)
            
        self.player.draw(surface)
        
        # Apply dramatic lighting
        self.light_surface.fill((self.ambient_light, self.ambient_light, self.ambient_light, 255))
        for light in self.level.lights:
            light.draw(surface, self.light_surface)
        surface.blit(self.light_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        
    def update_transition(self):
        speed = 0.05
        
        if self.transition.phase == "shrink":
            self.transition.progress += speed
            self.transition.scale = 1.0 - (self.transition.progress * 0.25)
            
            if self.transition.progress >= 1.0:
                self.transition.phase = "swipe"
                self.transition.progress = 0.0
                
        elif self.transition.phase == "swipe":
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
            self.transition.scale = 0.75 + (self.transition.progress * 0.25)
            
            if self.transition.progress >= 1.0:
                self.state = GameState.PLAYING
                
    def draw_transition(self):
        # Dark background
        self.screen.fill(DARK_GRAY)
        
        if self.transition.phase == "shrink":
            scaled_size = (int(SCREEN_WIDTH * self.transition.scale), 
                          int(SCREEN_HEIGHT * self.transition.scale))
            scaled_surface = pygame.transform.smoothscale(self.transition.old_level_surface, scaled_size)
            
            x = (SCREEN_WIDTH - scaled_size[0]) // 2
            y = (SCREEN_HEIGHT - scaled_size[1]) // 2
            
            self.screen.blit(scaled_surface, (x, y))
            
        elif self.transition.phase == "swipe":
            scaled_size = (int(SCREEN_WIDTH * 0.75), int(SCREEN_HEIGHT * 0.75))
            y = (SCREEN_HEIGHT - scaled_size[1]) // 2
            
            surfaces_to_draw = []
            
            old_x = (SCREEN_WIDTH - scaled_size[0]) // 2 - self.transition.offset_x
            if abs(old_x) < SCREEN_WIDTH:
                surfaces_to_draw.append((self.transition.old_level_surface, old_x))
            
            for i, intermediate_surface in enumerate(self.transition.intermediate_surfaces):
                intermediate_x = (SCREEN_WIDTH - scaled_size[0]) // 2 + SCREEN_WIDTH * self.transition.direction * (i + 1) - self.transition.offset_x
                if abs(intermediate_x) < SCREEN_WIDTH:
                    surfaces_to_draw.append((intermediate_surface, intermediate_x))
            
            total_offset = len(self.transition.intermediate_surfaces) + 1
            new_x = (SCREEN_WIDTH - scaled_size[0]) // 2 + SCREEN_WIDTH * self.transition.direction * total_offset - self.transition.offset_x
            if abs(new_x) < SCREEN_WIDTH:
                surfaces_to_draw.append((self.transition.new_level_surface, new_x))
            
            for surface, x_pos in surfaces_to_draw:
                scaled = pygame.transform.smoothscale(surface, scaled_size)
                self.screen.blit(scaled, (x_pos, y))
                
        elif self.transition.phase == "grow":
            scaled_size = (int(SCREEN_WIDTH * self.transition.scale), 
                          int(SCREEN_HEIGHT * self.transition.scale))
            scaled_surface = pygame.transform.smoothscale(self.transition.new_level_surface, scaled_size)
            
            x = (SCREEN_WIDTH - scaled_size[0]) // 2
            y = (SCREEN_HEIGHT - scaled_size[1]) // 2
            
            self.screen.blit(scaled_surface, (x, y))
            
    def update(self):
        if self.state == GameState.MENU:
            self.menu.update()
        elif self.state == GameState.PLAYING:
            mouse_pos = pygame.mouse.get_pos()
            self.player.update(self.level.platforms, mouse_pos)
            self.level.update(self.player, self.from_level)
            
            # Check NPC interactions
            keys = pygame.key.get_pressed()
            if keys[pygame.K_e]:
                for npc in self.level.npcs:
                    if npc.show_prompt and npc.dialogue_timer <= 0:
                        npc.interact(self.from_level, self.current_level)
                
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
            self.draw_level_to_surface(self.screen)
            
            # Crosshair for fireball
            if self.player.can_fireball:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                crosshair_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(crosshair_surf, (*WHITE, 100), (10, 10), 8, 2)
                pygame.draw.line(crosshair_surf, (*WHITE, 100), (0, 10), (20, 10), 2)
                pygame.draw.line(crosshair_surf, (*WHITE, 100), (10, 0), (10, 20), 2)
                self.screen.blit(crosshair_surf, (mouse_x - 10, mouse_y - 10))
            
            # Minimal UI
            ui_y = 20
            if self.player.abilities.get('double_jump'):
                text = self.font.render("Double Jump", True, LIGHT_GRAY)
                self.screen.blit(text, (20, ui_y))
                ui_y += 25
                
            if self.player.abilities.get('fireball'):
                text = self.font.render("Light: F", True, LIGHT_GRAY)
                self.screen.blit(text, (20, ui_y))
                ui_y += 25
                
            if self.player.keys > 0:
                text = self.font.render(f"Keys: {self.player.keys}", True, WHITE)
                self.screen.blit(text, (20, ui_y))
                
            # Drop platform hint (subtle)
            hint_text = self.small_font.render("S: Drop", True, (*LIGHT_GRAY, 100))
            self.screen.blit(hint_text, (20, SCREEN_HEIGHT - 30))
            
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

if __name__ == "__main__":
    game = Game()
    game.run()