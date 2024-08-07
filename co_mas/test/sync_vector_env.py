import traceback
from pprint import pformat

from loguru import logger
from tqdm import tqdm

from co_mas.test.utils import vector_sample_sample
from co_mas.vector import SyncVectorParallelEnv


def check_dict(info_dict, env_ids):
    for k, v in info_dict.items():
        if isinstance(v, dict):
            if all(not isinstance(_v, dict) for _v in v.values()):
                assert set(v.keys()).issuperset(env_ids), f"Dict keys {k}: {v} should contain {env_ids}"
            else:
                check_dict(v, env_ids)


def sync_vector_env_test(sync_vec_env: SyncVectorParallelEnv, num_cycles=1000):
    """
    Test whether the SyncVectorParallelEnv can run an episode.
    """
    sync_vec_env.reset(seed=42)
    # Test contents
    # 1. where the sub-environments reset correctly

    obs, info = sync_vec_env.reset()
    should_be_reset = {env_id: len(_agents) == 0 for env_id, _agents in sync_vec_env.agents.items()}

    logger.trace("agents:\n" + pformat(sync_vec_env.agents))
    logger.trace("envs_have_agents:\n" + pformat(sync_vec_env.envs_have_agents))
    logger.trace("info:\n" + pformat(info))
    for _ in tqdm(range(num_cycles)):
        action = {}
        for agent in sync_vec_env.possible_agents:
            agent_envs = sync_vec_env.envs_have_agent(agent)
            if len(agent_envs) > 0:
                action[agent] = vector_sample_sample(
                    agent, obs[agent], info[agent], sync_vec_env.action_space(agent), agent_envs
                )
        logger.trace("action:\n" + pformat(action))

        envs_have_agents = sync_vec_env.envs_have_agents

        try:
            state = sync_vec_env.state()
        except Exception:
            logger.warning(traceback.format_exc())
        else:
            if list(state.keys())[0] in sync_vec_env.env_ids:
                assert set(state.keys()).issuperset(
                    [env_id for env_id in should_be_reset if should_be_reset[env_id] is False]
                ), "State should contain all running environments"
            else:
                for agent in sync_vec_env.possible_agents:
                    envs_have_agent = envs_have_agents[agent]
                    assert set(state.get(agent, {}).keys()).issuperset(
                        envs_have_agent
                    ), f"States should contain {envs_have_agent}, while the keys are {state.get(agent, {}).keys()}"

        obs, rew, terminated, truncated, info = sync_vec_env.step(action)

        logger.trace("envs_have_agents:\n" + pformat(sync_vec_env.envs_have_agents))
        logger.trace("info:\n" + pformat(info))
        logger.trace("agents:\n" + pformat(sync_vec_env.agents))
        logger.trace("terminated:\n" + pformat(terminated))
        logger.trace("truncated:\n" + pformat(truncated))

        agents = sync_vec_env.agents
        should_be_reset = {env_id: len(_agents) == 0 for env_id, _agents in agents.items()}
        logger.trace(f"{pformat(should_be_reset)}\n==?\n{pformat(sync_vec_env.unwrapped._autoreset_envs)}")
        assert all(
            sync_vec_env.unwrapped._autoreset_envs[env_id] == should_be_reset[env_id] for env_id in sync_vec_env.env_ids
        ), "Autoreset environments should be reset"
        for agent in sync_vec_env.possible_agents:
            envs_have_agent = envs_have_agents[agent]
            assert set(obs.get(agent, {}).keys()).issuperset(
                envs_have_agent
            ), f"Observations should contain {envs_have_agent}"
            assert set(rew.get(agent, {}).keys()).issuperset(
                envs_have_agent
            ), f"Rewards should contain {envs_have_agent}"
            assert set(terminated.get(agent, {}).keys()).issuperset(
                envs_have_agent
            ), f"Terminations should contain {envs_have_agent}"
            assert set(truncated.get(agent, {}).keys()).issuperset(
                envs_have_agent
            ), f"Truncations should contain {envs_have_agent}"
            check_dict(info.get(agent, {}), envs_have_agent)

    logger.success("SyncVectorParallelEnv Test Passed!")
