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
    base_img_dimensions: Tuple[int, int]
    slot_list: List[SlotDefinition]
    background_img_path: str
    foreground_img_path: str | None = None

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

        image = Image.open(self.scenario_definition.background_img_path)
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
        if self.scenario_definition.foreground_img_path:
            image = overlay_pil_image_on_base_image(
                image,
                Image.open(self.scenario_definition.foreground_img_path),
                ((0, 0), self.scenario_definition.base_img_dimensions),
            )

        return image

    def clone(self):
        return deepcopy(self)


jail_scenario = ScenarioDefinition(
    name="The day after wappu",
    background_img_path="image_templates/jail.png",
    foreground_img_path="image_templates/jail_overlay.png",
    base_img_dimensions=(3508, 2480),
    slot_list=[
        {
            "position": (666, 111),
            "size": (777, 444),
            "prompts": ["a decoration hanging on a wall"],
        },
        {
            "position": (222, 666),
            "size": (333, 333),
            "prompts": ["a person sitting down not feeling so good"],
        },
        {
            "position": (333, 1665),
            "size": (2220, 444),
            "prompts": ["a person laying down"],
        },
        {
            "position": (2664, 222),
            "size": (555, 1332),
            "prompts": ["a person standing up"],
        },
    ],
)

sauna_scenario = ScenarioDefinition(
    name="A traditional Finnish sauna",
    background_img_path="image_templates/sauna.png",
    base_img_dimensions=(3508, 2480),
    slot_list=[
        {
            "position": (666, 333),
            "size": (222, 333),
            "prompts": ["a supernatural being"],
        },
        {"position": (1110, 777), "size": (333, 444), "prompts": ["a person floating"]},
        {
            "position": (1998, 444),
            "size": (333, 333),
            "prompts": ["a person sitting down"],
        },
        {
            "position": (2664, 555),
            "size": (333, 444),
            "prompts": [
                "a person sitting down",
            ],
        },
    ],
)

seagull_scenario = ScenarioDefinition(
    name="Taking a ride on a seagull",
    background_img_path="image_templates/seagull.png",
    base_img_dimensions=(3508, 2480),
    slot_list=[
        {
            "position": (888, 666),
            "size": (222, 222),
            "prompts": ["a person hanging on a bar"],
        },
        {
            "position": (2442, 888),
            "size": (444, 777),
            "prompts": ["a person standing up"],
        },
        {
            "position": (2997, 888),
            "size": (333, 777),
            "prompts": [
                "a person standing up",
            ],
        },
    ],
)

psychedelic_scenario = ScenarioDefinition(
    name="Fever dream",
    background_img_path="image_templates/psychedelic.png",
    base_img_dimensions=(3508, 2480),
    slot_list=[
        {
            "position": (777, 777),
            "size": (444, 888),
            "prompts": ["a person falling down"],
        },
        {
            "position": (1443, 111),
            "size": (333, 444),
            "prompts": ["the king of the hill"],
        },
        {
            "position": (1665, 1887),
            "size": (222, 222),
            "prompts": [
                "a funny face",
            ],
        },
        {
            "position": (2553, 222),
            "size": (777, 444),
            "prompts": [
                "a flying object",
            ],
        },
    ],
)

ullis_grilling_scenario = ScenarioDefinition(
    name="A traditional Ullis sillis",
    background_img_path="image_templates/grill.png",
    base_img_dimensions=(3508, 2480),
    slot_list=[
        {
            "position": (666, 140),
            "size": (222, 222),
            "prompts": [
                "a wappu balloon flying in the wind",
                "an animal on a leash",
                "a child who lost their parents",
            ],
        },
        {
            "position": (1443, 333),
            "size": (555, 444),
            "prompts": [
                "a person grilling some tasty meals",
                "a very serious guard staring at a prisoner",
                "an animal standing very firmly",
            ],
        },
        {
            "position": (2553, 333),
            "size": (555, 666),
            "prompts": [
                "a person who lost their air balloon and are chasing it",
                "a person trying to swat a fly",
                "one of your favourite drinks ",
            ],
        },
        {
            "position": (1665, 1665),
            "size": (1554, 666),
            "prompts": [
                "a tired person sleeping on the grass",
                "a person that is not feeling so good",
                "an inspirational quote",
            ],
        },
    ],
)


ullis_tree_scenario = ScenarioDefinition(
    name="Picnic under a tree at Kaivopuisto",
    background_img_path="image_templates/tree.png",
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
)

scenario_definitions = [
    jail_scenario,
    sauna_scenario,
    seagull_scenario,
    psychedelic_scenario,
    ullis_grilling_scenario,
    ullis_tree_scenario,
]
