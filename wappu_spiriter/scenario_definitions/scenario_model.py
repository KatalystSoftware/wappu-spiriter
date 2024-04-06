import random
from copy import deepcopy
from dataclasses import dataclass
from typing import List, Tuple, TypedDict

from PIL import Image

from wappu_spiriter.image_related.manipulate_img import overlay_pil_image_on_base_image


class SlotDefinition(TypedDict):
    position: Tuple[int, int]
    size: Tuple[int, int]
    prompts: List[str]


@dataclass
class Slot:
    position: Tuple[int, int]
    size: Tuple[int, int]
    prompt: str
    submitted_image: Image.Image | None = None


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

        self.slots = [
            Slot(
                position=slot_opts["position"],
                size=slot_opts["size"],
                prompt=slot_opts["prompts"][instruction_set_index],
            )
            for slot_opts in self.scenario_definition.slot_list
        ]

    def all_slots_filled(self):
        return all(slot.submitted_image is not None for slot in self.slots)

    def compose_image(self):
        assert self.all_slots_filled()

        image = Image.open(self.scenario_definition.base_img_path)
        for slot in self.slots:
            assert slot.submitted_image is not None
            image = overlay_pil_image_on_base_image(
                image,
                slot.submitted_image,
                (
                    slot.position,
                    (slot.position[0] + slot.size[0], slot.position[1] + slot.size[1]),
                ),
            )

        return image

    def clone(self):
        return deepcopy(self)


scenario_definitions = [
    ScenarioDefinition(
        name="park",
        base_img_path="image_templates/IMG_1240.PNG",
        base_img_dimensions=(3508, 2480),
        slot_list=[
            {
                "position": (2239, 2),
                "size": (530, 561),
                "prompts": [
                    "someone hanging",
                    "an animal climbing something",
                    "a poster",
                ],
            },
            {
                "position": (900, 1700),
                "size": (600, 600),
                "prompts": [
                    "a person laying down",
                    "a person sittin",
                    "a person angry",
                ],
            },
            {
                "position": (2050, 2000),
                "size": (200, 200),
                "prompts": ["an item", "a drink", "an animal"],
            },
        ],
    ),
]
