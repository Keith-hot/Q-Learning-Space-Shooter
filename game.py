"""Game main logic - Balanced evasion and attack (20D compatible)"""
import pygame
import numpy as np
import math
import random
from config import *
from entities import Player, Enemy, Bullet
from utils import Particle, Star


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Q-Shooter Pro - Balanced 20D")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 72)

        self.stars = [Star() for _ in range(200)]
        self.nebula_offset = 0
        self.shake = 0

        self.reset()

    def reset(self):
        self.player = Player()
        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.particles = []

        self.near_misses = 0
        self.shots_fired = 0
        self.hits_landed = 0
        self.enemies_killed = 0

        self.score = 0
        self.wave = 1
        self.frame = 0
        self.game_over = False
        self.victory = False

        self.spawn_wave()
        return self.get_state()

    def spawn_wave(self):
        count = min(6 + self.wave * 2, 30)
        for _ in range(count):
            self.enemies.append(Enemy(self.wave))

    def get_state(self):
        """Compatible 20-dimensional state"""
        state = np.zeros(20, dtype=np.float32)

        # [0-1]: Player position
        state[0] = self.player.x / SCREEN_WIDTH
        state[1] = self.player.y / SCREEN_HEIGHT

        # [2-7]: Nearest 3 enemies (absolute position)
        enemies = sorted(self.enemies,
                        key=lambda e: (e.x - self.player.x) ** 2 + (e.y - self.player.y) ** 2)

        for i, e in enumerate(enemies[:3]):
            state[2 + i * 2] = e.x / SCREEN_WIDTH
            state[3 + i * 2] = e.y / SCREEN_HEIGHT

        # [8-13]: Nearest 3 enemy bullets
        ebullets = sorted(self.enemy_bullets,
                         key=lambda b: (b.x - self.player.x) ** 2 + (b.y - self.player.y) ** 2)

        for i, b in enumerate(ebullets[:3]):
            state[8 + i * 2] = b.x / SCREEN_WIDTH
            state[9 + i * 2] = b.y / SCREEN_HEIGHT

        # [14-17]: Nearest 2 player bullets
        pbullets = sorted(self.bullets, key=lambda b: b.y)
        for i, b in enumerate(pbullets[:2]):
            state[14 + i * 2] = b.x / SCREEN_WIDTH
            state[15 + i * 2] = b.y / SCREEN_HEIGHT

        # [18-19]: Game info
        state[18] = len(self.enemies) / 30
        state[19] = self.wave / 20

        return state

    def step(self, action):
        self.frame += 1
        reward = 0.02

        prev_danger = self._calculate_danger_level()

        dx = (action % 3) - 1
        dy = ((action // 3) % 3) - 1
        shoot = (action // 9) % 2 == 1
        use_skill = action // 18 == 1

        self.player.move(dx, dy)
        self.player.update(self.wave)

        if dx != 0 or dy != 0:
            reward += 0.02
            if prev_danger > 0.5:
                reward += 0.03

        # BALANCED: Shooting reward 0.6
        if shoot:
            self.bullets.extend(self.player.shoot())
            self.shots_fired += 1
            reward += 0.6

        if use_skill:
            if not self.player.shield_active and self.player.shield_charges > 0:
                self.player.activate_shield()
                reward += 1.0
            elif self.player.ultimate >= self.player.ultimate_max:
                self.player.activate_ultimate()
                self.shake = 20
                for e in self.enemies:
                    self.add_explosion(e.x, e.y, e.color)
                self.enemies.clear()
                self.enemy_bullets.clear()
                reward += 50

        for b in self.bullets[:]:
            b.update()
            if not b.active:
                self.bullets.remove(b)

        for b in self.enemy_bullets[:]:
            b.update()
            if not b.active:
                self.enemy_bullets.remove(b)

        current_danger = self._calculate_danger_level()

        if current_danger < prev_danger:
            evasion_reward = (prev_danger - current_danger) * 1.0
            reward += evasion_reward
            self.near_misses += 1

        for e in self.enemies[:]:
            new_bullet = e.update(self.player.x, self.player.y)
            if new_bullet:
                self.enemy_bullets.append(new_bullet)

            if e.y > SCREEN_HEIGHT + 50:
                self.enemies.remove(e)
                self.player.hp -= 1
                reward -= 5

            dist = math.hypot(e.x - self.player.x, e.y - self.player.y)
            if dist < e.size + 20:
                if self.player.shield_active:
                    self.player.shield_active = False
                    self.add_explosion(e.x, e.y, e.color)
                    self.enemies.remove(e)
                    self.score += 10
                    reward += 5
                elif self.player.invincible <= 0:
                    self.player.hp -= 1
                    self.player.invincible = 60
                    self.shake = 10
                    reward -= 15
                    self.add_explosion(self.player.x, self.player.y, CYAN)
                    self.add_explosion(e.x, e.y, e.color)
                    self.enemies.remove(e)
                    if self.player.hp <= 0:
                        self.game_over = True
                        reward -= 80

        for b in self.bullets[:]:
            hit = False
            for e in self.enemies[:]:
                if math.hypot(b.x - e.x, b.y - e.y) < e.size + 5:
                    e.hp -= 1
                    hit = True
                    self.add_explosion(b.x, b.y, WHITE, small=True)
                    self.hits_landed += 1

                    reward += 4

                    if e.hp <= 0:
                        kill_bonus = 15 + self.wave * 3 + e.enemy_type * 8
                        self.score += e.wave * 10
                        reward += kill_bonus
                        self.enemies_killed += 1

                        self.add_explosion(e.x, e.y, e.color)
                        self.enemies.remove(e)
                        self.player.ultimate = min(self.player.ultimate_max, self.player.ultimate + 15)
                    break
            if hit and b in self.bullets:
                self.bullets.remove(b)

        for eb in self.enemy_bullets[:]:
            if math.hypot(eb.x - self.player.x, eb.y - self.player.y) < 20:
                if self.player.shield_active:
                    self.player.shield_active = False
                    self.enemy_bullets.remove(eb)
                    reward += 2
                elif self.player.invincible <= 0:
                    self.player.hp -= 1
                    self.player.invincible = 60
                    self.shake = 10
                    reward -= 12
                    self.enemy_bullets.remove(eb)
                    self.add_explosion(self.player.x, self.player.y, RED)
                    if self.player.hp <= 0:
                        self.game_over = True
                        reward -= 80

        if len(self.enemies) == 0 and not self.game_over:
            self.wave += 1
            reward += 30
            if self.wave > 20:
                self.victory = True
                self.game_over = True
                reward += 500
            else:
                self.spawn_wave()

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        if self.shake > 0:
            self.shake -= 1

        return self.get_state(), reward, self.game_over, {
            'score': self.score, 'wave': self.wave, 'hp': self.player.hp,
            'near_misses': self.near_misses,
            'shots_fired': self.shots_fired,
            'hits_landed': self.hits_landed,
            'enemies_killed': self.enemies_killed,
            'danger_level': current_danger
        }

    def _calculate_danger_level(self):
        danger = 0.0

        for e in self.enemies:
            dist = math.hypot(e.x - self.player.x, e.y - self.player.y)
            if dist < 150:
                danger += (150 - dist) / 150 * 0.5

        for b in self.enemy_bullets:
            dist = math.hypot(b.x - self.player.x, b.y - self.player.y)
            if dist < 100:
                danger += (100 - dist) / 100 * 0.5

        return min(danger, 1.0)

    def add_explosion(self, x, y, color, small=False):
        count = 8 if small else 20
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 8)
            self.particles.append(Particle(x, y, color,
                                           (math.cos(angle) * speed, math.sin(angle) * speed),
                                           size=random.randint(3, 8)))

    def draw(self):
        offset_x = random.randint(-self.shake, self.shake) if self.shake > 0 else 0
        offset_y = random.randint(-self.shake, self.shake) if self.shake > 0 else 0

        self.nebula_offset += 0.2
        for y in range(0, SCREEN_HEIGHT, 4):
            cv = int(20 + 10 * math.sin((y + self.nebula_offset) * 0.01))
            pygame.draw.line(self.screen, (cv // 3, cv // 2, cv), (0, y), (SCREEN_WIDTH, y), 4)

        for star in self.stars:
            star.update(0.5)
            star.draw(self.screen)

        for p in self.particles:
            p.draw(self.screen)
        for b in self.bullets:
            b.draw(self.screen)
        for b in self.enemy_bullets:
            b.draw(self.screen)
        for e in self.enemies:
            e.draw(self.screen)
        self.player.draw(self.screen)

        self.draw_ui()

        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))

            text = "VICTORY!" if self.victory else "GAME OVER"
            color = GOLD if self.victory else RED
            over_text = self.title_font.render(text, True, color)
            rect = over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(over_text, rect)

            score_text = self.font.render(f"Score: {self.score}", True, WHITE)
            rect2 = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
            self.screen.blit(score_text, rect2)

            stats_text = self.small_font.render(
                f"Kills: {self.enemies_killed} | Hits: {self.hits_landed} | Shots: {self.shots_fired} | Near Misses: {self.near_misses}",
                True, CYAN
            )
            rect_stats = stats_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
            self.screen.blit(stats_text, rect_stats)

            restart = self.small_font.render("Press R to restart, M for menu", True, GRAY)
            rect3 = restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80))
            self.screen.blit(restart, rect3)

        pygame.display.flip()
        self.clock.tick(FPS)

    def draw_ui(self):
        score_surf = self.font.render(f"SCORE: {self.score}", True, GOLD)
        self.screen.blit(score_surf, (20, 20))

        wave_surf = self.font.render(f"WAVE: {self.wave}/20", True, CYAN)
        self.screen.blit(wave_surf, (20, 60))

        for i in range(self.player.max_hp):
            color = RED if i < self.player.hp else DARK_BLUE
            pygame.draw.polygon(self.screen, color, [
                (200 + i * 35, 30), (215 + i * 35, 15), (230 + i * 35, 30),
                (230 + i * 35, 45), (215 + i * 35, 60), (200 + i * 35, 45)
            ])

        if self.player.shield_charges > 0:
            shield_text = self.small_font.render(f"Shield [E]: {self.player.shield_charges}", True, BLUE)
            self.screen.blit(shield_text, (20, 100))

        bar_w = 200
        pygame.draw.rect(self.screen, DARK_BLUE, (SCREEN_WIDTH // 2 - bar_w // 2, 20, bar_w, 20))
        ult_pct = self.player.ultimate / self.player.ultimate_max
        pygame.draw.rect(self.screen, PURPLE, (SCREEN_WIDTH // 2 - bar_w // 2, 20, int(bar_w * ult_pct), 20))
        pygame.draw.rect(self.screen, WHITE, (SCREEN_WIDTH // 2 - bar_w // 2, 20, bar_w, 20), 2)
        ult_text = self.small_font.render(f"ULTIMATE [Q]: {int(ult_pct * 100)}%", True, WHITE)
        self.screen.blit(ult_text, (SCREEN_WIDTH // 2 - 60, 45))

        danger = self._calculate_danger_level()
        if danger > 0.3:
            danger_color = RED if danger > 0.7 else ORANGE
            pygame.draw.rect(self.screen, danger_color, (SCREEN_WIDTH - 150, 100, int(100 * danger), 10))
            pygame.draw.rect(self.screen, WHITE, (SCREEN_WIDTH - 150, 100, 100, 10), 1)
            danger_text = self.small_font.render("DANGER", True, danger_color)
            self.screen.blit(danger_text, (SCREEN_WIDTH - 150, 85))

        combat_text = self.small_font.render(
            f"Kills:{self.enemies_killed} Hits:{self.hits_landed} Shots:{self.shots_fired}",
            True, LIGHT_GRAY
        )
        self.screen.blit(combat_text, (20, SCREEN_HEIGHT - 50))

        hint = self.small_font.render("WASD/Arrows: Move | SPACE: Shoot | E: Shield | Q: Ultimate", True, LIGHT_GRAY)
        self.screen.blit(hint, (20, SCREEN_HEIGHT - 30))