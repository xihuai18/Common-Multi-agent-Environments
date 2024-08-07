from __future__ import annotations

import warnings

from loguru import logger
from pettingzoo.test.api_test import missing_attr_warning
from pettingzoo.utils.conversions import (
    aec_to_parallel_wrapper,
    parallel_to_aec_wrapper,
    turn_based_aec_to_parallel_wrapper,
)
from pettingzoo.utils.wrappers import BaseWrapper

from co_mas.env import ParallelEnv
from co_mas.test.utils import sample_action


def parallel_api_test(par_env: ParallelEnv, num_cycles=1000, agent_state: bool = False):
    par_env.max_cycles = num_cycles

    if not hasattr(par_env, "possible_agents"):
        warnings.warn(missing_attr_warning.format(name="possible_agents"))

    assert not isinstance(par_env.unwrapped, aec_to_parallel_wrapper)
    assert not isinstance(par_env.unwrapped, parallel_to_aec_wrapper)
    assert not isinstance(par_env.unwrapped, turn_based_aec_to_parallel_wrapper)
    assert not isinstance(par_env.unwrapped, BaseWrapper)

    # checks that reset takes arguments seed and options
    par_env.reset(seed=0, options={"options": 1})

    MAX_RESETS = 2
    for _ in range(MAX_RESETS):
        obs, info = par_env.reset()

        assert isinstance(obs, dict)
        assert isinstance(info, dict)
        # Note: obs and info dicts must contain all AgentIDs, but can also have other additional keys (e.g., "common")
        assert set(par_env.agents).issubset(set(obs.keys()))
        assert set(par_env.agents).issubset(set(info.keys()))
        terminated = {agent: False for agent in par_env.agents}
        truncated = {agent: False for agent in par_env.agents}
        live_agents = set(par_env.agents[:])
        has_finished = set()
        for step in range(num_cycles):
            actions = {
                agent: sample_action(agent, obs[agent], info[agent], par_env.action_space(agent))
                for agent in par_env.agents
            }
            obs, rew, terminated, truncated, info = par_env.step(actions)
            if agent_state:
                state = par_env.state()
            for agent in par_env.agents:
                assert agent not in has_finished, "agent cannot be revived once dead"

                if agent not in live_agents:
                    live_agents.add(agent)

            assert isinstance(obs, dict)
            assert isinstance(rew, dict)
            assert isinstance(terminated, dict)
            assert isinstance(truncated, dict)
            assert isinstance(info, dict)
            if agent_state:
                assert isinstance(state, dict)

            if agent_state:
                keys = "observation reward terminated truncated info state".split()
                vals = [obs, rew, terminated, truncated, info, state]
            else:
                keys = "observation reward terminated truncated info".split()
                vals = [obs, rew, terminated, truncated, info]

            for k, v in zip(keys, vals):
                key_set = set(v.keys())
                if key_set == live_agents:
                    continue
                if len(key_set) < len(live_agents):
                    logger.warning(
                        f"Step {step}: Live agent was not given {k}.\nLive agents {live_agents}\nGiven {key_set}"
                    )
                else:
                    logger.warning(f"Agent was given {k} but was dead last turn")

            if hasattr(par_env, "possible_agents"):
                assert set(par_env.agents).issubset(
                    set(par_env.possible_agents)
                ), "possible_agents defined but does not contain all agents"

                has_finished |= {agent for agent in live_agents if terminated[agent] or truncated[agent]}
                if not par_env.agents and has_finished != set(par_env.possible_agents):
                    warnings.warn("No agents present but not all possible_agents are terminated or truncated")
            elif not par_env.agents:
                warnings.warn("No agents present")

            for agent in par_env.agents:
                assert par_env.observation_space(agent) is par_env.observation_space(
                    agent
                ), "observation_space should return the exact same space object (not a copy) for an agent. Consider decorating your observation_space(self, agent) method with @functools.lru_cache(maxsize=None)"
                assert par_env.action_space(agent) is par_env.action_space(
                    agent
                ), "action_space should return the exact same space object (not a copy) for an agent (ensures that action space seeding works as expected). Consider decorating your action_space(self, agent) method with @functools.lru_cache(maxsize=None)"

            agents_to_remove = {agent for agent in live_agents if terminated[agent] or truncated[agent]}
            live_agents -= agents_to_remove

            assert set(par_env.agents) == live_agents, f"{par_env.agents} != {live_agents}"

            if len(live_agents) == 0:
                break
    logger.success("Parallel API Test!")
