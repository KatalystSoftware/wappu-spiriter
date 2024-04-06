import itertools
import random
from dataclasses import dataclass, field
from typing import List, Literal, Self

from more_itertools import first_true, flatten
from telegram import Message, constants
from telegram.ext import ExtBot

from wappu_spiriter.scenario_definitions.scenario_model import (
    Scenario,
    Slot,
    scenario_definitions,
)


@dataclass
class Player:
    id: int
    slots: List[Slot] = field(default_factory=list)


class Game:
    id: str
    initalization_chat_id: int | None = None
    player_set: set[int] = set()
    bot_is_admin: bool | None = None
    game_status: Literal["PREP"] | Literal["ACTIVE"] | Literal["FINISHED"] = "PREP"
    teams: List[List[Player]]
    scenarios: List[Scenario]
    current_scenario_index: int = 0
    rounds: int = 3

    @classmethod
    async def new(cls, init_call_msg: Message, bot: ExtBot) -> Self:
        assert init_call_msg.from_user is not None
        self = cls()
        self.id = str(random.randint(0, 1000000))
        self.player_set = set([init_call_msg.from_user.id])
        self.bot_is_admin = bot.id in [
            admin.user.id for admin in await init_call_msg.chat.get_administrators()
        ]

        await self.send_initialization_msg(init_call_msg)

        return self

    @property
    def player_count(self) -> int:
        return len(self.player_set)

    @property
    def current_scenario(self) -> Scenario:
        assert self.current_scenario_index < len(self.scenarios)
        return self.scenarios[self.current_scenario_index]

    async def send_initialization_msg(self, init_call_msg: Message):
        self.initalization_msg = await init_call_msg.reply_text(
            f"""New game created!
        
⌛ Waiting for players to /join...

👤 {1} players joined!

Commands:
/join - join game
/start - start game"""
        )
        self.initalization_chat_id = init_call_msg.chat_id

    def get_active_slot_by_user_id(self, user_id: int) -> Slot | None:
        all_players = flatten(self.teams)
        player = first_true(all_players, None, lambda p: p.id == user_id)
        if not player:
            return None

        first_empty_slot = first_true(
            player.slots, None, lambda slot: slot.submitted_image is None
        )
        return first_empty_slot

    async def send_instruction(self, bot: ExtBot, user_id: int, prompt: str) -> None:
        await bot.send_message(user_id, prompt)

    async def send_next_instruction(self, bot: ExtBot, user_id: int) -> bool:
        active_slot = self.get_active_slot_by_user_id(user_id)

        if active_slot:
            await self.send_instruction(bot, user_id, active_slot.prompt)
            return True

        return False

    def populate_scenarios(self):
        scenario_definitions_shuffled = scenario_definitions.copy()
        random.shuffle(scenario_definitions_shuffled)
        self.scenarios = [
            Scenario(scenario_definition)
            for scenario_definition in scenario_definitions_shuffled
        ]

    async def start_game(self, bot: ExtBot):
        assert self.game_status == "PREP"

        self.populate_scenarios()

        # make single player teams
        self.teams = [[Player(id=i)] for i in self.player_set]

        self.game_status = "ACTIVE"

        self.current_scenario_index = 0

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
            slots = self.current_scenario.slots.copy()
            random.shuffle(slots)
            for slot, player in zip(slots, itertools.cycle(team)):
                if len(player.slots) == 0:
                    await self.send_instruction(bot, player.id, slot.prompt)
                player.slots += [slot]

    async def play_round(self, round_id: int):
        pass

    # return exception object if non-terminal error
    async def join_game(self, join_call_msg: Message, bot: ExtBot) -> Exception | None:
        assert join_call_msg.from_user is not None

        if self.bot_is_admin:
            await join_call_msg.delete()

        if self.game_status != "PREP":
            msg = "Game has already started, wait for the next one!"
            await join_call_msg.reply_text(msg)

            return Exception(msg)

        if join_call_msg.from_user.id in self.player_set:
            return Exception("Player already in game")

        self.player_set.add(join_call_msg.from_user.id)

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
