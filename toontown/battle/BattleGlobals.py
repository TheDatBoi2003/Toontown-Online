from direct.showbase.DirectObject import DirectObject

from panda3d.core import *

from direct.directnotify.DirectNotifyGlobal import directNotify

notify = directNotify.newCategory("BattleGlobals")

BATTLE_TOWN = 0
BATTLE_BLDG = 1
BATTLE_BOSS = 2

SOAKED_DEBUFF = 30
