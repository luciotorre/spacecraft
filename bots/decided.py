from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from spacecraft.client_helpers import relative_angle

import spacecraft


class AbortExecutionException(Exception):
    pass


class Decition(object):
    def __init__(self, action=lambda _, __: None, value=0,
                 priority=1, condition=lambda _: True,
                 abort_condition=lambda _: False, children=None):
        self.action = (action, value)
        self.priority = priority
        self.condition = (condition,)
        self.abort_condition = (abort_condition,)
        if children is None:
            children = []
        self.children = children

    def execute(self, message):
        if self.abort_condition[0](message):
            raise AbortExecutionException()
        if self.condition[0](message):
            self.action[0](value=self.action[1], message=message)
            for child in self.children:
                child.execute(message)


class BaseDecitionTreeClient(spacecraft.server.ClientBase):
    name = 'decitiontree'

    def _define_behaviors(self):
        pass

    def _initial_behavior(self):
        self.current = []


    def throttle(self, value=0, message=""):
        self.command('throttle', value=value)

    def fire(self, value=0, message=""):
        self.command('fire')

    def turn(self, value=0, message=""):
        self.command('turn', value=value)

    def messageReceived(self, message):
        self.message = message
        if not getattr(self, 'initialized', False):
            self.initialized = True
            self._define_behaviors()
            self._initial_behavior()

        try:
            for decition in self.current:
                decition.execute(message)
        except AbortExecutionException:
            pass


class DecitionTreeClient(BaseDecitionTreeClient):

    def player_near(self, message):
        if message['type'] == 'sensor':
            if filter(lambda x: x['object_type'] == 'player', message['proximity']):
                return True
        return False

    def player_far(self, message):
        return not self.player_near(message)

    def is_healthy(self, message):
        if message['type'] == 'sensor':
            return message.get('status', {}).get('health', 100) > 50
        return True

    def is_damaged(self, message):
        return not self.is_healthy(message)

    def to_passive(self, value=0, message=""):
        self.current = self.passive

    def to_avoid(self, value=0, message=""):
        self.current = self.avoid

    def to_frenzy(self, value=0, message=""):
        self.current = self.frenzy

    def smart_turn(self):
        if self.message['type'] == 'sensor':
            currentx = self.message['gps']['position'][0]
            currenty = self.message['gps']['position'][1]
            currentangle = self.message['gps']['angle']
            for x in self.message['proximity']:
                if x['object_type'] == 'player':
                    targetx = x['position'][0]
                    targety = x['position'][1]
                    break
            return relative_angle(currentx, currenty, targetx, targety, currentangle)

    def can_smart_turn(self):
        return -0.3 < self.smart_turn() < 0.3

    def frenzy_decition(self):
          return Decition(action=self.to_frenzy, condition=self.is_damaged, children=[
            Decition(abort_condition=lambda _: True)
          ])

    def _define_behaviors(self):
        self.passive = [
          Decition(action=self.fire),
          Decition(action=self.throttle, value=.2),
          Decition(action=self.turn, value=.2),
          self.frenzy_decition(),
          Decition(action=self.to_avoid, condition=self.player_near),
        ]

        self.avoid = [
          Decition(action=self.fire),
          Decition(action=self.turn, value=self.smart_turn(), condition=self.can_smart_turn),
          Decition(action=self.turn, value=.3),
          Decition(action=self.throttle, value=1),
          self.frenzy_decition(),
          Decition(action=self.to_passive, condition=self.player_far)
        ]

        self.frenzy = [
          Decition(action=self.throttle, value=.7, condition=self.player_far),
          Decition(action=self.throttle, value=1, condition=self.player_near),
          Decition(action=self.turn, value=.1, condition=self.player_far),
          Decition(action=self.turn, value=.2, condition=self.player_near),
          Decition(action=self.fire),
        ]

    def _initial_behavior(self):
        self.current = self.passive


def main():
    factory = ClientFactory()
    factory.protocol = DecitionTreeClient
    reactor.connectTCP("localhost", 11106, factory)

if __name__ == "__main__":
    reactor.callWhenRunning(main)
    reactor.run()
