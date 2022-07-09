from direct.showbase.DirectObject import DirectObject

from .BattleGlobals import *

from direct.directnotify.DirectNotifyGlobal import directNotify

class BattleListenerAI(DirectObject):
    notify = directNotify.newCategory('BattleListenerAI')
    
    def __init__(self, battle, battleType=BATTLE_TOWN):
        DirectObject.__init__(self)
        self.battle = battle
        self.battleType = battleType