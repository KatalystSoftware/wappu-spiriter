import random
from dataclasses import dataclass
from typing import List, Tuple, TypedDict


class SlotDefinition(TypedDict):
    position: Tuple[int, int]
    size: Tuple[int, int]
    prompts: List[str]


class Slot(TypedDict):
    position: Tuple[int, int]
    size: Tuple[int, int]
    prompt: str


@dataclass
class ScenarioDefinition:
    name: str
    base_img_path: str
    base_img_dimensions: Tuple[int, int]
    slot_list: List[SlotDefinition]

    @property
    def prompts_count(self):
        return len(self.slot_list[0]["prompts"])

    def __post_init__(self):
        assert len(self.slot_list) > 0
        first_slot_prompt_count = len(self.slot_list[0]["prompts"])
        assert all(
            len(slot["prompts"]) == first_slot_prompt_count for slot in self.slot_list
        )

    def get_random_instruction_set_index(self):
        return random.randint(0, self.prompts_count - 1)


class Scenario:
    instruction_set_index: int

    def __init__(
        self,
        scenario_definition: ScenarioDefinition,
        instruction_set_index: int | None = None,
    ):
        self.scenario_definition = scenario_definition

        if instruction_set_index is None:
            instruction_set_index = (
                scenario_definition.get_random_instruction_set_index()
            )

        self.instruction_set_index = instruction_set_index

    @property
    def slots(self) -> List[Slot]:
        return [
            {
                "position": slot_opts["position"],
                "size": slot_opts["size"],
                "prompt": slot_opts["prompts"][self.instruction_set_index],
            }
            for slot_opts in self.scenario_definition.slot_list
        ]


scenario_definitions = [
    ScenarioDefinition(
        name="blank",
        base_img_path="blank.webp",
        base_img_dimensions=(1024, 512),
        slot_list=[
            {
                "position": (256, 128),
                "size": (256, 256),
                "prompts": ["sticker"],
            }
        ],
    )
]
