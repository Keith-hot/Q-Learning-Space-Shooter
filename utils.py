"""工具类和函数"""
import pygame
import random
import math
from config import *


class Particle:
    def __init__(self, x, y, color, velocity, size=5, life=40):
        self.x, self.y = x, y
        self.color = color
        self.vx, self.vy = velocity
        self.size = size
        self.life = self.max_life = life
        self.alpha = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.life -= 1
        self.alpha = int(255 * self.life / self.max_life)
        self.size = max(1, int(self.size * 0.95))

    def draw(self, screen):
        if self.alpha > 0:
            color = (*self.color[:3], self.alpha)
            surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (self.size, self.size), self.size)
            screen.blit(surf, (int(self.x - self.size), int(self.y - self.size)))


class Star:
    def __init__(self):
        self.reset()
        self.y = random.randint(0, SCREEN_HEIGHT)

    def reset(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = -10
        self.z = random.uniform(0.5, 3)
        self.size = random.randint(1, 3)
        self.brightness = random.randint(100, 255)

    def update(self, speed):
        self.y += speed * self.z
        if self.y > SCREEN_HEIGHT:
            self.reset()

    def draw(self, screen):
        color = (self.brightness, self.brightness, self.brightness)
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.size)