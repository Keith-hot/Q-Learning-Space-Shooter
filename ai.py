"""AI related: DQN and Agent"""
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from collections import deque
import random
import os
import pickle


class DQN(nn.Module):
    def __init__(self, input_dim=20, hidden_dim=512, output_dim=36):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2), nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim)
        )

    def forward(self, x):
        return self.net(x)


class Agent:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")

        self.policy = DQN().to(self.device)
        self.target = DQN().to(self.device)
        self.target.load_state_dict(self.policy.state_dict())
        self.target.eval()

        self.optimizer = optim.Adam(self.policy.parameters(), lr=0.0003)
        self.memory = deque(maxlen=100000)

        self.epsilon = 0.5
        self.epsilon_end = 0.05
        self.epsilon_decay = 0.99
        self.batch_size = 128
        self.gamma = 0.99
        self.update_count = 0
        self.target_update = 2000

        # Training statistics
        self.episode_count = 0  # Trained episodes
        self.best_score = 0     # Best score achieved
        self.total_steps = 0    # Total steps taken

    def select_action(self, state, training=True):
        """Select action using epsilon-greedy policy"""
        if training and random.random() < self.epsilon:
            # 70% 概率选择移动（躲避）
            if random.random() < 0.7:
                dx = random.choice([-1, 1])
                dy = random.choice([-1, 0, 1])
                shoot = random.choice([0, 1])  # 随机射击
                skill = 0 if random.random() < 0.9 else 1
                action = (dx + 1) + (dy + 1) * 3 + shoot * 9 + skill * 18
                return action
            else:
                return random.randint(0, 35)

        else:
            with torch.no_grad():
                state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                return self.policy(state).argmax().item()

    def store(self, state, action, reward, next_state, done):
        """Store transition in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
        self.total_steps += 1

    def learn(self):
        """Perform one step of learning from replay memory"""
        if len(self.memory) < self.batch_size * 4:
            return None

        batch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)

        # Current Q values
        current_q = self.policy(states).gather(1, actions.unsqueeze(1)).squeeze()

        # Double DQN: use policy net to select action, target net to evaluate
        with torch.no_grad():
            next_actions = self.policy(next_states).argmax(1)
            next_q = self.target(next_states).gather(1, next_actions.unsqueeze(1)).squeeze()
            target_q = rewards + (1 - dones) * self.gamma * next_q

        # Compute loss and update
        loss = F.smooth_l1_loss(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 10)
        self.optimizer.step()

        # Update target network periodically
        self.update_count += 1
        if self.update_count % self.target_update == 0:
            self.target.load_state_dict(self.policy.state_dict())

        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        return loss.item()

    def save(self, path, save_memory=False):
        """Save model checkpoint, optionally including replay memory"""
        checkpoint = {
            'policy_net': self.policy.state_dict(),
            'target_net': self.target.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'update_count': self.update_count,
            'episode_count': self.episode_count,
            'best_score': self.best_score,
            'total_steps': self.total_steps,
        }
        torch.save(checkpoint, path)

        # Optionally save memory (large file)
        if save_memory and len(self.memory) > 0:
            memory_path = path + '.memory'
            with open(memory_path, 'wb') as f:
                # Save only recent 50000 experiences to control file size
                memory_list = list(self.memory)[-50000:]
                pickle.dump(memory_list, f)
            print(f"Memory saved to {memory_path} ({len(memory_list)} experiences)")

        print(f"Checkpoint saved: Episodes={self.episode_count}, Best={self.best_score}, Steps={self.total_steps}")

    def load(self, path, load_memory=False):
        """Load model checkpoint, optionally including replay memory"""
        if not os.path.exists(path):
            print(f"No checkpoint found at {path}")
            return False

        try:
            ckpt = torch.load(path, map_location=self.device)

            # Load networks
            if 'policy_net' in ckpt:
                self.policy.load_state_dict(ckpt['policy_net'])
                self.target.load_state_dict(ckpt['target_net'])
            elif 'policy' in ckpt:
                # Legacy format support
                self.policy.load_state_dict(ckpt['policy'])
                self.target.load_state_dict(ckpt.get('target_net', ckpt['policy']))
            else:
                # Direct state dict (oldest format)
                self.policy.load_state_dict(ckpt)
                self.target.load_state_dict(ckpt)

            # Load optimizer
            if 'optimizer' in ckpt:
                self.optimizer.load_state_dict(ckpt['optimizer'])

            # Load training statistics
            self.epsilon = ckpt.get('epsilon', 0.05)
            self.update_count = ckpt.get('update_count', 0)
            self.episode_count = ckpt.get('episode_count', 0)
            self.best_score = ckpt.get('best_score', 0)
            self.total_steps = ckpt.get('total_steps', 0)

            print(f"Checkpoint loaded: Episodes={self.episode_count}, Best={self.best_score}, Steps={self.total_steps}")

            # Optionally load memory
            if load_memory:
                memory_path = path + '.memory'
                if os.path.exists(memory_path):
                    with open(memory_path, 'rb') as f:
                        memory_list = pickle.load(f)
                        self.memory = deque(memory_list, maxlen=100000)
                    print(f"Memory loaded: {len(self.memory)} experiences")
                else:
                    print("No memory file found, starting with empty memory")

            return True

        # FIX: Catch specific exceptions instead of broad Exception
        except (IOError, OSError, pickle.PickleError) as e:
            print(f"Failed to load {path}: File error - {e}")
            return False
        except (RuntimeError, KeyError, ValueError) as e:
            print(f"Failed to load {path}: Data error - {e}")
            return False

    def auto_save(self, save_dir='checkpoints'):
        """Auto-save checkpoint with episode number, keep only recent 5"""
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f'checkpoint_ep{self.episode_count}.pth')
        self.save(path, save_memory=False)  # Don't save memory to save space

        # Keep only recent 5 checkpoints, delete old ones
        checkpoints = sorted([f for f in os.listdir(save_dir) if f.startswith('checkpoint_')])
        for old in checkpoints[:-5]:
            os.remove(os.path.join(save_dir, old))
            print(f"Removed old checkpoint: {old}")