import asyncio
import itertools
import random
from dataclasses import dataclass, field
from typing import List, Literal, Self

from more_itertools import first_true, flatten
from PIL.Image import Image
from telegram import Message, User, constants
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


def get_user_display_name(user: User | None) -> str:
    if user is None:
        return "Unknown user"

    if user.username is not None:
        return f"@{user.username}"

    return user.full_name


def get_user_mention(user: User | None) -> str:
    display_name = get_user_display_name(user)
    if user is None:
        return display_name

    return f"[{display_name}](tg://user?id={user.id})"


def get_mentions_list(users: List[User | None]) -> str:
    user_mentions = [get_user_mention(player) for player in users]
    user_mentions.sort()

    return "\n".join(user_mentions)


class Game:
    id: str
    game_chat_id: int
    initalization_msg: Message | None
    bot_username: str
    game_creator: User
    player_ids: set[int] = set()
    player_ids_to_user: dict[int, User] = {}
    game_status: Literal["PREP"] | Literal["ACTIVE"] | Literal["FINISHED"] = "PREP"
    teams: List[Team]
    scenarios: List[Scenario]
    current_scenario_index: int = 0
    rounds: int = 3

    @classmethod
    async def new(cls, init_call_msg: Message, bot: ExtBot) -> Self:
        assert init_call_msg.from_user is not None

        self = cls()

        self.id = str(random.randint(0, 1000000))

        self.game_chat_id = init_call_msg.chat_id
        self.player_ids = set([init_call_msg.from_user.id])
        self.player_ids_to_user[init_call_msg.from_user.id] = init_call_msg.from_user

        self.bot_username = bot.username
        self.game_creator = init_call_msg.from_user

        self.initalization_msg = await init_call_msg.reply_text(
            self.status_message,
            parse_mode=constants.ParseMode.MARKDOWN_V2,
        )

        return self

    @property
    def player_count(self) -> int:
        return len(self.player_ids)

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

    @property
    def pretty_player_list(self) -> str:
        player_list = [self.player_ids_to_user.get(pid) for pid in self.player_ids]
        return get_mentions_list(player_list)

    @property
    def pretty_team_list(self) -> str:
        assert len(self.teams) > 0

        output = ""

        for team_number, team in enumerate(self.teams):
            output += f"Team {team_number + + 1}\n"
            team_players = [self.player_ids_to_user.get(p.id) for p in team.players]
            output += get_mentions_list(team_players)
            output += "\n"
            if team_number != len(self.teams) - 1:
                output += "\n"

        return output

    @property
    def status_message(self) -> str:
        match self.game_status:
            case "PREP":
                return f"""New game created\\!
        
⌛ Waiting for players to /join\\.\\.\\.

Players:
{self.pretty_player_list}

👤 {self.player_count} players joined\\!

Commands:
/join \\- join game
/start \\- start game \\({get_user_mention(self.game_creator)} only\\)"""

            case "ACTIVE":
                return f"""🖼️ Game started\\!

Teams:
{self.pretty_team_list}

[Play game](https://t.me/{self.bot_username})"""

            case "FINISHED":
                return "Game is complete! Start a new game with /new"

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
        result_msg = await bot.send_message(self.game_chat_id, "Done!")
        for player in self.players:
            await bot.send_message(
                player.id,
                f"Round finished\\! [View results \\-\\>](https://t.me/c/{str(self.game_chat_id)[3:]}/{result_msg.id})",  # todo: substringing like that doesn't work in public groups
                parse_mode=constants.ParseMode.MARKDOWN_V2,
            )

        for i, team in enumerate(self.teams):
            image = team.scenario.compose_image()
            image_bytes = pil_image_to_bytes(image)
            await bot.send_photo(
                self.game_chat_id,
                image_bytes,
                f"Submission from team {i} (continuing in 5s...)",
            )
            await asyncio.sleep(5)

        await bot.send_message(
            self.game_chat_id,
            "All submissions revealed!",
        )

        await self.next_round(bot)

    async def next_round(self, bot: ExtBot):
        self.current_scenario_index += 1

        if self.current_scenario_index >= len(self.scenarios):
            self.game_status = "FINISHED"
            await bot.send_message(
                self.game_chat_id,
                self.status_message,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
            )
            return

        for player in self.players:
            player.slots = []

        for team in self.teams:
            team.scenario = self.scenarios[self.current_scenario_index].clone()
            await self.assign_initial_prompts_to_team(team, bot)

        await bot.send_message(
            self.game_chat_id,
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
            # Scenario(scenario_definitions.copy()[0], instruction_set_index=1),
            # Scenario(scenario_definitions.copy()[0], instruction_set_index=2),
        ]

    async def start_game(self, bot: ExtBot, message: Message) -> None:
        assert self.game_status == "PREP"
        assert self.initalization_msg is not None
        assert message.from_user is not None

        if self.game_creator.id != message.from_user.id:
            await message.reply_text("Only the game creator can start the game!")
            return

        self.populate_scenarios()
        self.current_scenario_index = 0

        # todo: change to 4 for max slot count??
        max_team_size = 3

        # team logic
        # 1 => 1
        # 2 => 1 + 1
        # 3 => 1 + 1 + 1

        # 4 => 2 + 2
        # 5 => 3 + 2
        # 6 => 2 + 2 + 2
        # 7 => 3 + 2 + 2
        # 8 => 2 + 2 + 2 + 2
        # 9 => 3 + 2 + 2 + 2
        # 10 => 2 + 2 + 2 + 2 + 2

        # split into teams
        if len(self.player_ids) <= max_team_size:
            # single player teams
            self.teams = [
                Team(
                    players=[Player(id=i)],
                    scenario=self.scenarios[self.current_scenario_index].clone(),
                )
                for i in self.player_ids
            ]
        else:
            # pairs of 2 or leftover fills a 3 group
            self.teams = []

            player_pool = list(self.player_ids.copy())
            random.shuffle(player_pool)

            team_count = len(player_pool) // 2
            for _ in range(team_count):
                team_players = [
                    Player(id=player_pool.pop()),
                    Player(id=player_pool.pop()),
                ]
                self.teams += [
                    Team(
                        players=team_players,
                        scenario=self.scenarios[self.current_scenario_index].clone(),
                    ),
                ]

            if len(player_pool) > 0:
                self.teams[0].players += [Player(id=player_pool.pop())]

        self.game_status = "ACTIVE"

        await bot.edit_message_text(
            self.status_message,
            self.game_chat_id,
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

        if join_call_msg.from_user.id in self.player_ids:
            return Exception("Player already in game")

        self.player_ids.add(join_call_msg.from_user.id)
        self.player_ids_to_user[join_call_msg.from_user.id] = join_call_msg.from_user

        await bot.edit_message_text(
            self.status_message,
            self.game_chat_id,
            self.initalization_msg.id,
            parse_mode=constants.ParseMode.MARKDOWN_V2,
        )

        return None
