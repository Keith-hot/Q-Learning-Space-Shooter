"""Game entities: Bullets, enemies, players"""
import pygame
import random
import math
from dataclasses import dataclass
from config import *


@dataclass
class Bullet:
    x: float
    y: float
    speed: float = 12
    angle: float = -90
    active: bool = True
    is_enemy: bool = False

    def update(self):
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed
        self.y += math.sin(rad) * self.speed
        if self.x < 0 or self.x > SCREEN_WIDTH or self.y < 0 or self.y > SCREEN_HEIGHT:
            self.active = False

    def draw(self, screen):
        color = RED if self.is_enemy else YELLOW
        size = 6 if self.is_enemy else 4
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), size)

        # Draw the wake correctly and use a surface with transparency
        rad = math.radians(self.angle + 180)
        for i in range(3):
            tx = self.x + math.cos(rad) * (i + 1) * 8
            ty = self.y + math.sin(rad) * (i + 1) * 8
            # Create a temporary transparent surface to draw a wake
            trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            alpha = 128 - i * 40  # Gradient transparency
            trail_color = (*color, max(0, alpha))
            pygame.draw.circle(trail_surf, trail_color, (size, size), size - i)
            screen.blit(trail_surf, (int(tx - size), int(ty - size)))


class Enemy:
    def __init__(self, wave: int):
        self.wave = wave
        self.x = random.randint(50, SCREEN_WIDTH - 50)
        self.y = -50

        # The attribute increases with the wavenumber
        self.hp = 1 + wave // 4
        self.max_hp = self.hp
        self.speed = 1.5 + wave * 0.3
        self.shoot_cooldown = 0
        self.can_shoot = wave >= 3

        # mobility pattern
        self.move_pattern = random.choice(['straight', 'sine', 'chase'])
        self.phase = random.uniform(0, 3.14)
        self.target_y = random.randint(100, min(400, 200 + wave * 20))

        # Enemy types: 1= Normal, 2= Fast, 3= Tank
        r = random.random()
        if r < 0.1:
            self.enemy_type = 3  # Tank
        elif r < 0.3:
            self.enemy_type = 2  # Fast
        else:
            self.enemy_type = 1  # Normal

        self.size = 20 + self.hp * 3
        self.color = [RED, ORANGE, PURPLE, BLUE][min(self.hp - 1, 3)]
        self.pulse = 0

    def update(self, player_x, player_y):
        self.pulse += 0.1

        if self.move_pattern == 'straight':
            self.y += self.speed * 0.5
            if self.y < self.target_y:
                self.y += self.speed * 0.3
        elif self.move_pattern == 'sine':
            self.y += self.speed * 0.3
            self.x += math.sin(self.phase + self.y * 0.02) * 2
        else:
            dx = player_x - self.x
            self.x += math.copysign(min(abs(dx) * 0.02, self.speed), dx)
            self.y += self.speed * 0.4

        # Boundary restrictions
        if self.x < 30 or self.x > SCREEN_WIDTH - 30:
            self.x = max(30, min(SCREEN_WIDTH - 30, self.x))

        if self.can_shoot:
            self.shoot_cooldown -= 1
            if self.shoot_cooldown <= 0 and self.y > 50 and self.y < SCREEN_HEIGHT:
                self.shoot_cooldown = max(30, 120 - self.wave * 3)
                return self.shoot(player_x, player_y)
        return None

    def shoot(self, px, py):
        dx, dy = px - self.x, py - self.y
        angle = math.degrees(math.atan2(dy, dx))
        return Bullet(self.x, self.y, speed=6 + self.wave * 0.2, angle=angle, is_enemy=True)

    def draw(self, screen):
        pulse_size = self.size + math.sin(self.pulse) * 2
        points = []
        for i in range(6):
            angle = math.radians(i * 60 + 30)
            r = pulse_size if i % 2 == 0 else pulse_size * 0.6
            points.append((self.x + math.cos(angle) * r, self.y + math.sin(angle) * r))
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, WHITE, points, 2)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), 8)
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 5)

        if self.hp < self.max_hp:
            bar_w = 30
            bar_x = self.x - bar_w // 2
            bar_y = self.y - pulse_size - 10
            pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_w, 4))
            pygame.draw.rect(screen, GREEN, (bar_x, bar_y,
                                             bar_w * self.hp // self.max_hp, 4))


class Player:
    # Class variable: Pre-create shield surfaces to avoid creating them every frame
    _shield_surfs = None

    def __init__(self):
        self.x, self.y = SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100
        self.speed = 6
        self.hp = 5
        self.max_hp = 5

        self.shield_charges = 0
        self.shield_active = False
        self.shield_timer = 0
        self.shield_cooldown = 0

        self.ultimate = 0
        self.ultimate_max = 100

        self.invincible = 0
        self.shoot_cooldown = 0
        self.engine_glow = 0

        # Initialize the shield surface cache
        if Player._shield_surfs is None:
            Player._init_shield_surfs()

    @classmethod
    def _init_shield_surfs(cls):
        """Pre-create shield animation frames to optimize performance"""
        cls._shield_surfs = []
        cls._shield_rect = pygame.Rect(0, 0, 100, 100)
        for i in range(20):  # 创建20帧动画
            alpha = 100 + int(50 * math.sin(i * 0.314))  # 0.314 ≈ 2π/20
            surf = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(surf, (0, 100, 255, alpha), (50, 50), 45)
            pygame.draw.circle(surf, (100, 200, 255, 200), (50, 50), 45, 3)
            cls._shield_surfs.append(surf)

    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.x = max(20, min(SCREEN_WIDTH - 20, self.x))
        self.y = max(20, min(SCREEN_HEIGHT - 20, self.y))

    def update(self, wave):
        self.engine_glow = (self.engine_glow + 1) % 20
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.shield_cooldown > 0:
            self.shield_cooldown -= 1

        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False

        if self.invincible > 0:
            self.invincible -= 1

        self.shield_charges = min(wave // 3, 3)

        if self.ultimate < self.ultimate_max:
            self.ultimate += 0.05

    def activate_shield(self):
        if self.shield_charges > 0 and self.shield_cooldown <= 0 and not self.shield_active:
            self.shield_active = True
            self.shield_timer = 180
            self.shield_cooldown = 480
            self.shield_charges -= 1
            return True
        return False

    def activate_ultimate(self):
        if self.ultimate >= self.ultimate_max:
            self.ultimate = 0
            self.invincible = 180
            return True
        return False

    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = 6
            return [Bullet(self.x - 15, self.y - 10), Bullet(self.x + 15, self.y - 10)]
        return []

    def draw(self, screen):
        if self.invincible > 0 and self.invincible % 6 < 3:
            return

        if self.shield_active:
            # Use pre-created animation frames and select based on time
            frame = (pygame.time.get_ticks() // 50) % len(Player._shield_surfs)
            shield_surf = Player._shield_surfs[frame]
            screen.blit(shield_surf, (int(self.x - 50), int(self.y - 50)))

        flame_h = 25 + int(10 * math.sin(self.engine_glow * 0.3))
        pygame.draw.polygon(screen, ORANGE, [
            (self.x - 12, self.y + 20), (self.x, self.y + 20 + flame_h), (self.x + 12, self.y + 20)
        ])

        body = [(self.x, self.y - 25), (self.x - 20, self.y + 15), (self.x, self.y + 5), (self.x + 20, self.y + 15)]
        pygame.draw.polygon(screen, CYAN, body)
        pygame.draw.polygon(screen, BLUE, body, 2)
        pygame.draw.ellipse(screen, BLUE, (self.x - 10, self.y - 15, 20, 25))
        pygame.draw.ellipse(screen, (150, 220, 255), (self.x - 6, self.y - 10, 12, 18))