"""菜单和界面组件"""
import pygame
import random
import math
from config import *


class MenuButton:
    def __init__(self, x, y, w, h, text, color, hover_color, action):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.action = action
        self.hovered = False
        self.font = pygame.font.Font(None, 36)

    def draw(self, screen):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, self.rect, 3, border_radius=10)
        text_surf = self.font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            return self.action()
        return None


class MainMenu:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Q-Shooter Pro - Main Menu")
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 72)
        self.sub_font = pygame.font.Font(None, 36)

        # 按钮
        bw, bh = 350, 60
        bx = SCREEN_WIDTH // 2 - bw // 2
        by = 250

        self.buttons = [
            MenuButton(bx, by, bw, bh, "1. HUMAN PLAY", BLUE, (100, 150, 255), lambda: 'human'),
            MenuButton(bx, by + 80, bw, bh, "2. AI (UNTRAINED)", RED, (255, 100, 100), lambda: 'untrained'),
            MenuButton(bx, by + 160, bw, bh, "3. AI (TRAINED)", GREEN, (100, 255, 150), lambda: 'trained'),
            MenuButton(bx, by + 240, bw, bh, "4. TRAIN AI", PURPLE, (200, 100, 255), lambda: 'train'),
            MenuButton(bx, by + 320, bw, bh, "5. QUIT", DARK_GRAY, GRAY, lambda: 'quit'),
        ]

        self.stars = [(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)) for _ in range(200)]
        self.nebula = 0

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'quit'
                for btn in self.buttons:
                    result = btn.handle_event(event)
                    if result:
                        return result

            # 绘制背景
            self.nebula += 0.1
            self.screen.fill(BLACK)
            for y in range(0, SCREEN_HEIGHT, 4):
                cv = int(15 + 8 * math.sin((y + self.nebula) * 0.01))
                pygame.draw.line(self.screen, (cv // 3, cv // 2, cv), (0, y), (SCREEN_WIDTH, y), 4)

            for x, y in self.stars:
                b = random.randint(100, 255)
                pygame.draw.circle(self.screen, (b, b, b), (x, y), 1)

            # 标题
            title = self.title_font.render("Space Shooter", True, CYAN)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 120)))

            subtitle = self.sub_font.render("Creater - ZHANG Shufeng(Keith)", True, GRAY)
            self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 180)))

            # 技能说明
            skills = [
                "SKILL SYSTEM:",
                "Wave 3+: Shield [E] - Block damage",
                "Wave 6+: Shield charges increase",
                "Ultimate [Q] - Clear screen + invincible"
            ]
            y = 620
            for line in skills:
                txt = self.sub_font.render(line, True, LIGHT_GRAY)
                self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, y)))
                y += 30

            for btn in self.buttons:
                btn.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)