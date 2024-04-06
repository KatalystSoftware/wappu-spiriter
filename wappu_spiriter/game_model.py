import asyncio
import itertools
import random
from dataclasses import dataclass, field
from typing import List, Literal, Self

from more_itertools import first_true, flatten
from PIL.Image import Image
from telegram import Message, constants
from telegram.ext import ExtBot

from wappu_spiriter.image_related.utils import pil_image_to_bytes
from wappu_spiriter.scenario_definitions.scenario_model import (
    Scenario,
    Slot,
    scenario_definitions,
)


@dataclass
class Player:
    id: int
    slots: List[Slot] = field(default_factory=list)


@dataclass
class Team:
    players: List[Player]
    scenario: Scenario


class Game:
    id: str
    initalization_chat_id: int
    initalization_msg: Message | None
    player_id_set: set[int] = set()
    game_status: Literal["PREP"] | Literal["ACTIVE"] | Literal["FINISHED"] = "PREP"
    teams: List[Team]
    scenarios: List[Scenario]
    current_scenario_index: int = 0
    rounds: int = 3

    @classmethod
    async def new(cls, init_call_msg: Message) -> Self:
        assert init_call_msg.from_user is not None
        self = cls()
        self.initalization_chat_id = init_call_msg.chat_id
        self.id = str(random.randint(0, 1000000))
        self.player_id_set = set([init_call_msg.from_user.id])
        await self.send_initialization_msg(init_call_msg)

        return self

    @property
    def player_count(self) -> int:
        return len(self.player_id_set)

    @property
    def players(self) -> List[Player]:
        return list(flatten([team.players for team in self.teams]))

    @property
    def current_scenario(self) -> Scenario:
        assert self.current_scenario_index < len(self.scenarios)
        return self.scenarios[self.current_scenario_index]

    @property
    def empty_slots(self) -> int:
        slots = flatten([player.slots for player in self.players])
        empty_slots = list(filter(lambda slot: slot.submitted_image is None, slots))

        return len(empty_slots)

    async def send_initialization_msg(self, init_call_msg: Message):
        self.initalization_msg = await init_call_msg.reply_text(
            f"""New game created!
        
⌛ Waiting for players to /join...

👤 {1} players joined!

Commands:
/join - join game
/start - start game"""
        )

    def get_active_slot_by_user_id(self, user_id: int) -> Slot | None:
        all_players = self.players
        player = first_true(all_players, None, lambda p: p.id == user_id)
        if not player:
            return None

        first_empty_slot = first_true(
            player.slots, None, lambda slot: slot.submitted_image is None
        )
        return first_empty_slot

    async def finish_round(self, bot: ExtBot):
        result_msg = await bot.send_message(self.initalization_chat_id, "Done!")
        for player in self.players:
            await bot.send_message(
                player.id,
                f"Round finished\\! [View results \\-\\>](https://t.me/c/{str(self.initalization_chat_id)[3:]}/{result_msg.id})",  # todo: substringing like that doesn't work in public groups
                parse_mode=constants.ParseMode.MARKDOWN_V2,
            )

        for i, team in enumerate(self.teams):
            image = team.scenario.compose_image()
            image_bytes = pil_image_to_bytes(image)
            await bot.send_photo(
                self.initalization_chat_id,
                image_bytes,
                f"Submission from team {i} (continuing in 5s...)",
            )
            await asyncio.sleep(5)

        await bot.send_message(
            self.initalization_chat_id,
            "All submissions revealed!",
        )

        await self.next_round(bot)

    async def next_round(self, bot: ExtBot):
        self.current_scenario_index += 1

        if self.current_scenario_index >= len(self.scenarios):
            await bot.send_message(
                self.initalization_chat_id,
                "Game is complete! Start a new game with /new",
            )
            return

        for player in self.players:
            player.slots = []

        for team in self.teams:
            team.scenario = self.scenarios[self.current_scenario_index].clone()
            await self.assign_initial_prompts_to_team(team, bot)

        await bot.send_message(
            self.initalization_chat_id,
            f"Next round started\\!\n\n[Play game](https://t.me/{bot.username})",
            parse_mode=constants.ParseMode.MARKDOWN_V2,
        )

    async def submit_image(
        self, user_id: int, image: Image, message: Message, bot: ExtBot
    ):
        next_slot = self.get_active_slot_by_user_id(user_id)

        done_msg = "You are finished for the round, wait for others!"
        if not next_slot:
            await message.reply_text(done_msg)
            return

        next_slot.submitted_image = image
        is_instruction_sent = await self.send_next_instruction(bot, user_id)

        if not is_instruction_sent:
            await message.reply_text(done_msg)

        if self.empty_slots == 0:
            await self.finish_round(bot)

    async def send_instruction(self, bot: ExtBot, user_id: int, prompt: str) -> None:
        await bot.send_message(user_id, prompt)

    async def send_next_instruction(self, bot: ExtBot, user_id: int) -> bool:
        active_slot = self.get_active_slot_by_user_id(user_id)

        if active_slot:
            await self.send_instruction(bot, user_id, active_slot.prompt)
            return True

        return False

    def populate_scenarios(self):
        # scenario_definitions_shuffled = scenario_definitions.copy()
        # random.shuffle(scenario_definitions_shuffled)
        # self.scenarios = [
        #     Scenario(scenario_definition)
        #     for scenario_definition in scenario_definitions_shuffled
        # ]
        self.scenarios = [
            Scenario(scenario_definitions.copy()[0], instruction_set_index=0),
            Scenario(scenario_definitions.copy()[0], instruction_set_index=1),
            Scenario(scenario_definitions.copy()[0], instruction_set_index=2),
        ]

    async def start_game(self, bot: ExtBot):
        assert self.game_status == "PREP"
        assert self.initalization_msg is not None

        self.populate_scenarios()
        self.current_scenario_index = 0

        # make single player teams
        self.teams = [
            Team(
                players=[Player(id=i)],
                scenario=self.scenarios[self.current_scenario_index].clone(),
            )
            for i in self.player_id_set
        ]

        self.game_status = "ACTIVE"

        await bot.edit_message_text(
            f"""New game created\\!
        
🖼️ Game started\\!

👤 {self.player_count} players joined\\!

[Play game](https://t.me/{bot.username})""",
            self.initalization_chat_id,
            self.initalization_msg.id,
            parse_mode=constants.ParseMode.MARKDOWN_V2,
        )

        for team in self.teams:
            await self.assign_initial_prompts_to_team(team, bot)

    async def assign_initial_prompts_to_team(self, team: Team, bot: ExtBot):
        slots = team.scenario.slots
        random.shuffle(slots)
        for slot, player in zip(slots, itertools.cycle(team.players)):
            if len(player.slots) == 0:
                await self.send_instruction(bot, player.id, slot.prompt)
            player.slots += [slot]

    async def play_round(self, round_id: int):
        pass

    # return exception object if non-terminal error
    async def join_game(
        self, join_call_msg: Message, bot: ExtBot, is_admin: bool
    ) -> Exception | None:
        assert join_call_msg.from_user is not None
        assert self.initalization_msg is not None

        if is_admin:
            await join_call_msg.delete()

        if self.game_status != "PREP":
            msg = "Game has already started, wait for the next one!"
            await join_call_msg.reply_text(msg)

            return Exception(msg)

        if join_call_msg.from_user.id in self.player_id_set:
            return Exception("Player already in game")

        self.player_id_set.add(join_call_msg.from_user.id)

        await bot.edit_message_text(
            f"""New game created!
        
⌛ Waiting for players to /join...

👤 {self.player_count} players joined!

Commands:
/join - join game
/start - start game""",
            self.initalization_chat_id,
            self.initalization_msg.id,
        )

        return None
