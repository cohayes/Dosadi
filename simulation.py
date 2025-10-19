from env import Environment
from agents import Agent

env = Environment(scarcity=0.4, danger=0.2)
for i in range(10):
    env.add_agent(Agent(id=i))

for _ in range(20):
    env.step()
    env.summary()
