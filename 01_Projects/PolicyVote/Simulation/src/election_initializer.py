"""Custom election initializer that uses explicit memories instead of AI-generated backstories.

Unlike Concordia's FormativeMemoriesInitializer which generates fictional individual backstories
("When X was 8 years old..."), this initializer:
- Uses only explicit pre-written memories for all entities
- Treats voter segments as groups, not individuals
- Uses real historical facts for party agents
"""

from collections.abc import Mapping, Sequence
import dataclasses
import functools
import types

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import basic_associative_memory
from concordia.components import agent as actor_components
from concordia.components import game_master as gm_components
from concordia.components.agent import memory as memory_component
from concordia.components.game_master import make_observation as make_observation_component
from concordia.language_model import language_model
from concordia.typing import entity as entity_lib
from concordia.typing import entity_component
from concordia.typing import prefab as prefab_lib
from concordia.utils import concurrency


class ElectionMemoriesInitializer(
    entity_component.ContextComponent, entity_component.ComponentWithLogging
):
    """Initializer using explicit memories only - no AI backstory generation.

    This component passes explicit memories to entities without generating
    fictional backstories. Suitable for:
    - Party agents: real historical facts
    - Voter segments: group descriptions (not individual stories)
    """

    def __init__(
        self,
        next_game_master_name: str,
        player_names: Sequence[str],
        shared_memories: Sequence[str] = (),
        player_specific_memories: Mapping[str, Sequence[str]] = types.MappingProxyType({}),
        memory_component_key: str = memory_component.DEFAULT_MEMORY_COMPONENT_KEY,
        make_observation_component_key: str = (
            make_observation_component.DEFAULT_MAKE_OBSERVATION_COMPONENT_KEY
        ),
    ):
        """Initialize the election memories component.

        Args:
            next_game_master_name: Name of the game master to pass control to after init.
            player_names: Names of all player entities.
            shared_memories: Memories given to ALL entities.
            player_specific_memories: Dict mapping entity names to their specific memories.
            memory_component_key: Key for the memory component.
            make_observation_component_key: Key for the MakeObservation component.
        """
        super().__init__()

        self._next_game_master_name = next_game_master_name
        self._player_names = player_names
        self._shared_memories = shared_memories
        self._player_specific_memories = player_specific_memories
        self._memory_component_key = memory_component_key
        self._make_observation_component_key = make_observation_component_key
        self._initialized = False

    def pre_act(
        self,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        if action_spec.output_type == entity_lib.OutputType.NEXT_GAME_MASTER:
            if self._initialized:
                return self._next_game_master_name

            memory = self.get_entity().get_component(
                self._memory_component_key, type_=memory_component.Memory
            )
            make_observation = self.get_entity().get_component(
                self._make_observation_component_key,
                type_=make_observation_component.MakeObservation,
            )

            # Add shared memories to game master
            for shared_memory in self._shared_memories:
                memory.add(shared_memory)

            def _process_player(
                player_name: str,
                memory: memory_component.Memory,
                make_observation: make_observation_component.MakeObservation,
            ):
                # Add shared memories to player
                for shared_memory in self._shared_memories:
                    make_observation.add_to_queue(player_name, shared_memory)

                # Add player-specific memories (NO AI backstory generation)
                for player_memory in self._player_specific_memories.get(player_name, []):
                    make_observation.add_to_queue(player_name, player_memory)
                    memory.add(f'{player_name} knows: "{player_memory}"')

            tasks = {
                player_name: functools.partial(
                    _process_player, player_name, memory, make_observation
                )
                for player_name in self._player_names
            }

            concurrency.run_tasks(tasks)

            self._initialized = True
            return self.get_entity().name

        return ''

    def get_state(self) -> entity_component.ComponentState:
        return {'initialized': self._initialized}

    def set_state(self, state: entity_component.ComponentState) -> None:
        pass


@dataclasses.dataclass
class GameMaster(prefab_lib.Prefab):
    """A prefab for election initialization using explicit memories only.

    Unlike formative_memories_initializer, this does NOT generate AI backstories.
    All memories must be provided explicitly in player_specific_memories.
    """

    description: str = 'An initializer that uses explicit memories (no AI backstory generation).'
    params: Mapping[str, str] = dataclasses.field(
        default_factory=lambda: {
            'name': 'election setup',
            'next_game_master_name': 'deliberation rules',
            'shared_memories': [],
            'player_specific_memories': {},
        }
    )
    entities: Sequence[entity_agent_with_logging.EntityAgentWithLogging] = ()

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_agent_with_logging.EntityAgentWithLogging:
        """Build the election initializer game master."""
        name = self.params.get('name', 'election setup')
        next_game_master_name = self.params.get('next_game_master_name', 'deliberation rules')
        shared_memories = self.params.get('shared_memories', [])
        player_specific_memories = self.params.get('player_specific_memories', {})

        memory_component_key = actor_components.memory.DEFAULT_MEMORY_COMPONENT_KEY
        memory_comp = actor_components.memory.AssociativeMemory(memory_bank=memory_bank)

        instructions_key = 'instructions'
        instructions = gm_components.instructions.Instructions()

        player_names = [entity.name for entity in self.entities]
        player_characters_key = 'player_characters'
        player_characters = gm_components.instructions.PlayerCharacters(
            player_characters=player_names,
        )

        observation_to_memory_key = 'observation_to_memory'
        observation_to_memory = actor_components.observation.ObservationToMemory()

        observation_component_key = (
            actor_components.observation.DEFAULT_OBSERVATION_COMPONENT_KEY
        )
        observation = actor_components.observation.LastNObservations(history_length=1000)

        # Use our custom initializer instead of FormativeMemoriesInitializer
        next_game_master_key = (
            gm_components.next_game_master.DEFAULT_NEXT_GAME_MASTER_COMPONENT_KEY
        )
        next_game_master = ElectionMemoriesInitializer(
            next_game_master_name=next_game_master_name,
            player_names=player_names,
            shared_memories=shared_memories,
            player_specific_memories=player_specific_memories,
        )

        make_observation_key = (
            gm_components.make_observation.DEFAULT_MAKE_OBSERVATION_COMPONENT_KEY
        )
        make_observation = gm_components.make_observation.MakeObservation(
            model=model,
            player_names=player_names,
        )

        skip_next_action_spec_key = (
            gm_components.next_acting.DEFAULT_NEXT_ACTION_SPEC_COMPONENT_KEY
        )
        skip_next_action_spec = gm_components.next_acting.FixedActionSpec(
            action_spec=entity_lib.skip_this_step_action_spec(),
        )

        terminate_key = gm_components.terminate.DEFAULT_TERMINATE_COMPONENT_KEY
        terminate = gm_components.terminate.NeverTerminate()

        components_of_game_master = {
            instructions_key: instructions,
            player_characters_key: player_characters,
            observation_component_key: observation,
            observation_to_memory_key: observation_to_memory,
            memory_component_key: memory_comp,
            next_game_master_key: next_game_master,
            make_observation_key: make_observation,
            skip_next_action_spec_key: skip_next_action_spec,
            terminate_key: terminate,
        }

        component_order = list(components_of_game_master.keys())

        act_component = gm_components.switch_act.SwitchAct(
            model=model,
            entity_names=player_names,
            component_order=component_order,
        )

        game_master = entity_agent_with_logging.EntityAgentWithLogging(
            agent_name=name,
            act_component=act_component,
            context_components=components_of_game_master,
        )

        return game_master
