"""Program entry point"""
import pygame
import os
from config import *
from game import Game
from ai import Agent
from ui import MainMenu


def human_play():
    """Human player mode"""
    game = Game()
    print("=" * 50)
    print("HUMAN PLAY MODE")
    print("Controls: WASD/Arrows=Move, SPACE=Shoot, E=Shield, Q=Ultimate, P=Pause, ESC=Menu")

    running = True
    paused = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_p:
                    paused = not paused
                if event.key == pygame.K_r and game.game_over:
                    game.reset()

        if paused:
            game.draw()
            pause_txt = game.font.render("PAUSED", True, YELLOW)
            game.screen.blit(pause_txt, pause_txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            pygame.display.flip()
            continue

        if not game.game_over:
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1

            shoot = 1 if keys[pygame.K_SPACE] else 0
            skill = 1 if (keys[pygame.K_e] or keys[pygame.K_q]) else 0

            # Encode action: dx in [-1,0,1], dy in [-1,0,1], shoot in [0,1], skill in [0,1]
            # Total 3*3*2*2 = 36 actions
            action = (dx + 1) + (dy + 1) * 3 + shoot * 9 + skill * 18
            game.step(action)

        game.draw()

        if game.game_over:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                game.reset()
            elif keys[pygame.K_m]:
                running = False


def ai_mode(trained=True):
    """AI play mode (trained or untrained)"""
    agent = Agent()

    # FIX: 改进加载逻辑，尝试多个来源获取最佳模型
    if trained:
        loaded = False
        best_info = {"episode": 0, "score": 0, "source": None}

        # 尝试 1: 加载 best_model.pth（如果存在且比之前加载的更好）
        if os.path.exists("best_model.pth"):
            temp_agent = Agent()
            if temp_agent.load("best_model.pth"):
                if temp_agent.best_score > best_info["score"]:
                    best_info = {
                        "episode": temp_agent.episode_count,
                        "score": temp_agent.best_score,
                        "source": "best_model.pth"
                    }
                    # 复制到实际使用的 agent
                    agent.policy.load_state_dict(temp_agent.policy.state_dict())
                    agent.target.load_state_dict(temp_agent.target.state_dict())
                    agent.optimizer.load_state_dict(temp_agent.optimizer.state_dict())
                    agent.epsilon = temp_agent.epsilon
                    agent.episode_count = temp_agent.episode_count
                    agent.best_score = temp_agent.best_score
                    agent.total_steps = temp_agent.total_steps
                    agent.update_count = temp_agent.update_count
                    loaded = True
                    print(f"Loaded best_model.pth: Episodes={agent.episode_count}, Best={agent.best_score}")

        # 尝试 2: 加载 final_model.pth（通常包含最终训练状态）
        if os.path.exists("final_model.pth"):
            temp_agent = Agent()
            if temp_agent.load("final_model.pth"):
                if temp_agent.best_score > best_info["score"]:
                    best_info = {
                        "episode": temp_agent.episode_count,
                        "score": temp_agent.best_score,
                        "source": "final_model.pth"
                    }
                    agent.policy.load_state_dict(temp_agent.policy.state_dict())
                    agent.target.load_state_dict(temp_agent.target.state_dict())
                    agent.optimizer.load_state_dict(temp_agent.optimizer.state_dict())
                    agent.epsilon = temp_agent.epsilon
                    agent.episode_count = temp_agent.episode_count
                    agent.best_score = temp_agent.best_score
                    agent.total_steps = temp_agent.total_steps
                    agent.update_count = temp_agent.update_count
                    loaded = True
                    print(f"Loaded final_model.pth: Episodes={agent.episode_count}, Best={agent.best_score}")

        # 尝试 3: 从 checkpoints 文件夹加载最新的检查点
        if os.path.exists('checkpoints'):
            checkpoints = [f for f in os.listdir('checkpoints') if f.startswith('checkpoint_')]
            if checkpoints:
                # 按数字排序
                def get_episode_num(filename):
                    try:
                        num_part = filename.split('_ep')[1].split('.')[0]
                        return int(num_part)
                    except (IndexError, ValueError):
                        return 0

                checkpoints.sort(key=get_episode_num)
                latest_ckpt = os.path.join('checkpoints', checkpoints[-1])

                temp_agent = Agent()
                if temp_agent.load(latest_ckpt):
                    if temp_agent.best_score > best_info["score"]:
                        best_info = {
                            "episode": temp_agent.episode_count,
                            "score": temp_agent.best_score,
                            "source": latest_ckpt
                        }
                        agent.policy.load_state_dict(temp_agent.policy.state_dict())
                        agent.target.load_state_dict(temp_agent.target.state_dict())
                        agent.optimizer.load_state_dict(temp_agent.optimizer.state_dict())
                        agent.epsilon = temp_agent.epsilon
                        agent.episode_count = temp_agent.episode_count
                        agent.best_score = temp_agent.best_score
                        agent.total_steps = temp_agent.total_steps
                        agent.update_count = temp_agent.update_count
                        loaded = True
                        print(f"Loaded {latest_ckpt}: Episodes={agent.episode_count}, Best={agent.best_score}")

        if not loaded:
            print("Warning: No trained model found, starting with random weights")
        else:
            print(f"\n✅ Final loaded model from {best_info['source']}: Episodes={agent.episode_count}, Best={agent.best_score}")

    game = Game()
    print(f"{'TRAINED' if trained else 'UNTRAINED'} AI MODE")
    print(f"Trained for {agent.episode_count} episodes, best score: {agent.best_score}")
    print("+/-: speed, P: pause, R: restart, ESC: menu")

    speed = 1
    running = True
    paused = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    game.reset()
                if event.key == pygame.K_p:
                    paused = not paused
                if event.key in [pygame.K_EQUALS, pygame.K_PLUS]:
                    speed = min(5, speed + 1)
                if event.key == pygame.K_MINUS:
                    speed = max(1, speed - 1)

        if paused:
            game.draw()
            pause_txt = game.font.render("PAUSED", True, YELLOW)
            game.screen.blit(pause_txt, pause_txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            pygame.display.flip()
            continue

        if not game.game_over:
            # Run multiple steps per frame for speedup
            for _ in range(speed):
                state = game.get_state()
                action = agent.select_action(state, training=False)
                _, _, done, _ = game.step(action)
                if done:
                    break

        game.draw()

        speed_txt = game.small_font.render(f"Speed: {speed}x", True, YELLOW)
        game.screen.blit(speed_txt, (SCREEN_WIDTH - 150, 20))
        pygame.display.flip()


def train_mode():
    """Training mode for AI"""
    print("=" * 50)
    print("TRAINING MODE")
    print("=" * 50)

    agent = Agent()
    game = Game()

    # Try to resume training from checkpoint
    resumed = False
    if os.path.exists('checkpoints'):
        checkpoints = [f for f in os.listdir('checkpoints') if f.startswith('checkpoint_')]
        if checkpoints:
            # FIX: Use numeric sorting here too
            def get_episode_num(filename):
                try:
                    num_part = filename.split('_ep')[1].split('.')[0]
                    return int(num_part)
                except (IndexError, ValueError):
                    return 0
            checkpoints.sort(key=get_episode_num)
            latest = os.path.join('checkpoints', checkpoints[-1])
            if agent.load(latest, load_memory=False):
                resumed = True
                print(f"Resumed training from episode {agent.episode_count}")

    if not resumed and agent.load("best_model.pth", load_memory=False):
        resumed = True
        print("Resumed from best_model.pth")

    if not resumed:
        print("Starting fresh training")

    print("Controls: ESC=stop & save, P=pause, S=save now")
    print("=" * 50)

    # Training parameters
    episodes = 5000  # Total target episodes
    save_interval = 100  # Auto-save every 100 episodes

    running = True
    paused = False

    start_ep = agent.episode_count

    # FIX: Restructured training loop to avoid nested while loops with event handling issues
    for ep in range(start_ep, episodes):
        if not running:
            break

        # FIX: Update episode count at the start of each episode
        agent.episode_count = ep
        state = game.reset()
        episode_reward = 0
        episode_steps = 0
        done = False

        # Inner game loop - single episode
        while not done and running:
            # Handle events without blocking
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_p:
                        paused = not paused
                    if event.key == pygame.K_s:
                        # Manual save
                        agent.save("best_model.pth", save_memory=True)
                        agent.auto_save()

            if not running:
                break

            if paused:
                game.draw()
                txt = game.font.render("TRAINING PAUSED - Press P to resume", True, YELLOW)
                game.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, 50)))

                info_txt = game.small_font.render(
                    f"Episode: {ep}/{episodes} | Best: {agent.best_score} | Epsilon: {agent.epsilon:.3f}",
                    True, WHITE
                )
                game.screen.blit(info_txt, (10, 100))
                pygame.display.flip()
                continue

            # AI selects action and performs step
            action = agent.select_action(state, training=True)
            next_state, reward, done, info = game.step(action)

            # Store transition and learn
            agent.store(state, action, reward, next_state, float(done))
            loss = agent.learn()

            state = next_state
            episode_reward += reward
            episode_steps += 1

            # Render every 10 frames for performance
            if game.frame % 10 == 0:
                game.draw()

                # Status information
                status = f"Ep {ep + 1}/{episodes}  Score:{info['score']}  Best:{agent.best_score}  Eps:{agent.epsilon:.3f}"
                txt = game.small_font.render(status, True, YELLOW)
                game.screen.blit(txt, (10, 10))

                # Training information
                train_info = f"Steps:{agent.total_steps}  Memory:{len(agent.memory)}  EpSteps:{episode_steps}"
                txt2 = game.small_font.render(train_info, True, CYAN)
                game.screen.blit(txt2, (10, 35))

                if loss:
                    loss_txt = game.small_font.render(f"Loss:{loss:.4f}", True, GREEN)
                    game.screen.blit(loss_txt, (10, 60))

                # Progress bar
                progress = (ep + 1) / episodes
                bar_w = 300
                pygame.draw.rect(game.screen, DARK_GRAY, (SCREEN_WIDTH // 2 - bar_w // 2, 100, bar_w, 20))
                pygame.draw.rect(game.screen, GREEN, (SCREEN_WIDTH // 2 - bar_w // 2, 100, int(bar_w * progress), 20))
                pygame.draw.rect(game.screen, WHITE, (SCREEN_WIDTH // 2 - bar_w // 2, 100, bar_w, 20), 2)

                pygame.display.flip()

        # Episode finished - update best score
        if info['score'] > agent.best_score:
            agent.best_score = info['score']
            agent.save("best_model.pth", save_memory=False)
            print(f"\n*** New best score: {agent.best_score} at episode {ep + 1} ***")

        # Auto-save checkpoint
        if (ep + 1) % save_interval == 0:
            agent.auto_save()
            print(f"\nAuto-saved at episode {ep + 1}")

        # Print progress
        if (ep + 1) % 10 == 0:
            avg_eps = agent.epsilon
            print(f"Ep {ep + 1}/{episodes} | Score:{info['score']} | Best:{agent.best_score} | Eps:{avg_eps:.3f} | Steps:{agent.total_steps}")

    # FIX: 训练结束时确保 best_model.pth 被更新为最佳模型
    print("\n" + "=" * 50)
    print("Training complete!")

    # 保存最终模型
    agent.save("final_model.pth", save_memory=True)
    agent.auto_save()

    # FIX: 确保 best_model.pth 包含最佳成绩
    # 如果当前 agent 的 best_score 比 best_model.pth 中的高，则更新它
    if os.path.exists("best_model.pth"):
        temp_agent = Agent()
        if temp_agent.load("best_model.pth"):
            if agent.best_score > temp_agent.best_score:
                print(f"Updating best_model.pth with new best score: {agent.best_score}")
                agent.save("best_model.pth", save_memory=False)
            else:
                print(f"best_model.pth already has best score: {temp_agent.best_score}")
        else:
            # 如果加载失败，直接保存当前最佳
            agent.save("best_model.pth", save_memory=False)
    else:
        # 如果不存在，创建它
        agent.save("best_model.pth", save_memory=False)

    print(f"Total episodes: {agent.episode_count}")
    print(f"Best score: {agent.best_score}")
    print(f"Total steps: {agent.total_steps}")
    print("=" * 50)


def main():
    """Main entry point with menu loop"""
    while True:
        menu = MainMenu()
        choice = menu.run()

        if choice == 'human':
            human_play()
        elif choice == 'untrained':
            ai_mode(trained=False)
        elif choice == 'trained':
            ai_mode(trained=True)
        elif choice == 'train':
            train_mode()
        elif choice == 'quit':
            print("Goodbye!")
            break

    pygame.quit()


if __name__ == "__main__":
    main()