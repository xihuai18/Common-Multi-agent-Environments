from typing import Dict

import gymnasium as gym
from pettingzoo.utils.env import AgentID

from co_mas.vector.vector_env import BaseVectorParallelEnvWrapper, VectorParallelEnv


class AgentStateVectorParallelEnvWrapper(BaseVectorParallelEnvWrapper):
    """
    A wrapper that return 'state' for each agent, each sub-environment must return states for each agent.
    """

    single_state_spaces: Dict[AgentID, gym.Space]
    state_spaces: Dict[AgentID, gym.Space]

    def state_space(self, agent: AgentID) -> gym.spaces.Tuple:
        return self.state_spaces[agent]

    def single_state_space(self, agent: AgentID) -> gym.Space:
        return self.single_state_spaces[agent]


class SyncAgentStateVectorParallelEnvWrapper(AgentStateVectorParallelEnvWrapper):
    """
    Vectorized PettingZoo Parallel environment that serially runs multiple environments and returns 'state' for each agent.
    """

    def __init__(self, env: VectorParallelEnv):
        assert all(
            hasattr(_e, "state") and hasattr(_e, "state_spaces") and hasattr(_e, "state_space") for _e in env.envs
        )
        super().__init__(env)
        self.single_state_spaces = self.env.envs[0].state_spaces
        self.state_spaces = {
            agent: gym.spaces.Tuple([self.env.envs[0].state_space(agent)] * self.num_envs)
            for agent in self.possible_agents
        }
