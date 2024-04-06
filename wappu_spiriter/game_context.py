from typing import Dict, Optional

from telegram.ext import Application, CallbackContext, ExtBot

from wappu_spiriter.game_model import Game


class BotState:
    def __init__(self) -> None:
        self.games: Dict[str, Game] = dict()

        self.user_id_to_game: dict[int, str] = dict()
        self.groupchat_id_to_game: dict[int, str] = dict()

    def exists_active_game_in_groupchat(self, groupchat_id: int) -> bool:
        if groupchat_id not in self.groupchat_id_to_game:
            return False

        game = self.games.get(self.groupchat_id_to_game[groupchat_id])

        if game is None:
            return False

        return game.game_status != "FINISHED"

    def get_game_by_groupchat_id(self, groupchat_id: int):
        game_id = self.groupchat_id_to_game.get(groupchat_id)
        game = self.games.get(game_id) if game_id else None
        return game

    def get_game_by_userid(self, userid: int):
        game_id = self.user_id_to_game.get(userid)
        game = self.games.get(game_id) if game_id else None
        return game


class GameStateContext(CallbackContext[ExtBot, dict, dict, BotState]):
    def __init__(
        self,
        application: Application,
        chat_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ):
        super().__init__(application=application, chat_id=chat_id, user_id=user_id)
        self._message_id: Optional[int] = None
