import random
from typing import List, Literal, Self

from telegram import Message, constants
from telegram.ext import ExtBot

from wappu_spiriter.scenario_definitions.scenario_model import (
    Scenario,
    scenario_definitions,
)


class Game:
    id: str
    initalization_chat_id: int | None = None
    player_set: set[int] = set()
    bot_is_admin: bool | None = None

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

    game_status: Literal["PREP"] | Literal["ACTIVE"] | Literal["FINISHED"] = "PREP"

    teams: List[List[int]]

    scenarios: List[Scenario]

    current_scenario_index: int = 0

    rounds: int = 3

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
        self.teams = [[i] for i in self.player_set]

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

        print("Game started")

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
