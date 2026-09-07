class Player:
    def __init__(self, name):
        self.name = name
        self.Traitor = False
        self.isActive = True
        
class Traitor(Player):
    def __init__(self, name):
        super().__init__(name)
        self.Traitor = True

class Lobby:
    def __init__(self, host):
        self.players = []
        self.numPlayers = 0
        self.hostPlayer = host
        self.activeGame = False
        self.accessCode = self.generate_access_code()
    
    def add_player(self, player):
        self.players.append(player)
    
    def remove_player(self, player):
        self.players.remove(player)
    
    


class Message:
    def __init__(self, content, sender):
        self.content = content
        self.sender = sender
    
