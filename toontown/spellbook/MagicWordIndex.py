##################################################
# The Toontown Offline Magic Word Manager
##################################################
# Author: Benjamin Frisby
# Copyright: Copyright 2020, Toontown Offline
# Credits: Benjamin Frisby, John Cote, Ruby Lord, Frank, Nick, Little Cat, Ooowoo
# License: MIT
# Version: 1.0.0
# Email: belloqzafarian@gmail.com
##################################################

import collections, types

from direct.distributed.ClockDelta import *
from direct.interval.IntervalGlobal import *

from panda3d.otp import NametagGroup, WhisperPopup

from otp.otpbase import OTPLocalizer
from otp.otpbase import OTPGlobals

from toontown.battle import SuitBattleGlobals
from toontown.char import CharDNA
from toontown.coghq import CogDisguiseGlobals
from toontown.effects import FireworkShows
from toontown.estate import GardenGlobals
from toontown.fishing import FishGlobals
from toontown.golf import GolfGlobals
from toontown.hood import ZoneUtil
from toontown.parties import PartyGlobals
from toontown.quest import Quests
from toontown.racing.KartDNA import *
from toontown.racing import RaceGlobals
from toontown.shtiker import CogPageGlobals
from toontown.toon import NPCToons
from toontown.suit import SuitDNA
from toontown.toon import Experience
from toontown.toon import ToonDNA
from toontown.toonbase import ToontownBattleGlobals
from toontown.toonbase import ToontownGlobals
from toontown.toonbase import TTLocalizer

from . import MagicWordConfig
import time, random, re, json

magicWordIndex = collections.OrderedDict()


class MagicWord:
    notify = DirectNotifyGlobal.directNotify.newCategory('MagicWord')

    # Whether this Magic word should be considered "hidden"
    # If your Toontown source has a page for Magic Words in the Sthickerbook, this will be useful for that
    hidden = False

    # Whether this Magic Word is an administrative command or not
    # Good for config settings where you want to disable cheaty Magic Words, but still want moderation ones
    administrative = False

    # List of names that will also invoke this word - a setHP magic word might have "hp", for example
    # A Magic Word will always be callable with its class name, so you don't have to put that in the aliases
    aliases = None

    # Description of the Magic Word
    # If your Toontown source has a page for Magic Words in the Sthickerbook, this will be useful for that
    desc = MagicWordConfig.MAGIC_WORD_DEFAULT_DESC

    # Advanced description that gives the user a lot more information than normal
    # If your Toontown source has a page for Magic Words in the Sthickerbook, this will be useful for that
    advancedDesc = MagicWordConfig.MAGIC_WORD_DEFAULT_ADV_DESC

    # Default example with for commands with no arguments set
    # If your Toontown source has a page for Magic Words in the Sthickerbook, this will be useful for that
    example = ""

    # The minimum access level required to use this Magic Word
    accessLevel = 'MODERATOR'

    # A restriction on the Magic Word which sets what kind or set of Distributed Objects it can be used on
    # By default, a Magic Word can affect everyone
    affectRange = [MagicWordConfig.AFFECT_SELF, MagicWordConfig.AFFECT_OTHER, MagicWordConfig.AFFECT_BOTH]

    # Where the magic word will be executed -- EXEC_LOC_CLIENT or EXEC_LOC_SERVER
    execLocation = MagicWordConfig.EXEC_LOC_INVALID

    # List of all arguments for this word, with the format [(type, isRequired), (type, isRequired)...]
    # If the parameter is not required, you must provide a default argument: (type, False, default)
    arguments = None

    def __init__(self):
        if self.__class__.__name__ != "MagicWord":
            self.aliases = self.aliases if self.aliases is not None else []
            self.aliases.insert(0, self.__class__.__name__)
            self.aliases = [x.lower() for x in self.aliases]
            self.arguments = self.arguments if self.arguments is not None else []

            if len(self.arguments) > 0:
                for arg in self.arguments:
                    argInfo = ""
                    if not arg[MagicWordConfig.ARGUMENT_REQUIRED]:
                        argInfo += "(default: {0})".format(arg[MagicWordConfig.ARGUMENT_DEFAULT])
                    self.example += "[{0}{1}] ".format(arg[MagicWordConfig.ARGUMENT_NAME], argInfo)

            self.__register()

    def __register(self):
        for wordName in self.aliases:
            if wordName in magicWordIndex:
                self.notify.error('Duplicate Magic Word name or alias detected! Invalid name: {}'. format(wordName))
            magicWordIndex[wordName] = {'class': self,
                                        'classname': self.__class__.__name__,
                                        'hidden': self.hidden,
                                        'administrative': self.administrative,
                                        'aliases': self.aliases,
                                        'desc': self.desc,
                                        'advancedDesc': self.advancedDesc,
                                        'example': self.example,
                                        'execLocation': self.execLocation,
                                        'access': self.accessLevel,
                                        'affectRange': self.affectRange,
                                        'args': self.arguments}

    def loadWord(self, air=None, cr=None, invokerId=None, targets=None, args=None):
        self.air = air
        self.cr = cr
        self.invokerId = invokerId
        self.targets = targets
        self.args = args

    def executeWord(self):
        executedWord = None
        validTargets = len(self.targets)
        for avId in self.targets:
            invoker = None
            toon = None
            if self.air:
                invoker = self.air.doId2do.get(self.invokerId)
                toon = self.air.doId2do.get(avId)
            elif self.cr:
                invoker = self.cr.doId2do.get(self.invokerId)
                toon = self.cr.doId2do.get(avId)
            if hasattr(toon, "getName"):
                name = toon.getName()
            else:
                name = avId

            if not self.validateTarget(toon):
                if len(self.targets) > 1:
                    validTargets -= 1
                    continue
                return "{} is not a valid target!".format(name)

            # TODO: Should we implement locking?
            # if toon.getLocked() and not self.administrative:
            #     if len(self.targets) > 1:
            #         validTargets -= 1
            #         continue
            #     return "{} is currently locked. You can only use administrative commands on them.".format(name)

            if invoker.getAccessLevel() <= toon.getAccessLevel() and toon != invoker:
                if len(self.targets) > 1:
                    validTargets -= 1
                    continue
                targetAccess = OTPGlobals.AccessLevelDebug2Name.get(OTPGlobals.AccessLevelInt2Name.get(toon.getAccessLevel()))
                invokerAccess = OTPGlobals.AccessLevelDebug2Name.get(OTPGlobals.AccessLevelInt2Name.get(invoker.getAccessLevel()))
                return "You don't have a high enough Access Level to target {0}! Their Access Level: {1}. Your Access Level: {2}.".format(name, targetAccess, invokerAccess)

            if self.execLocation == MagicWordConfig.EXEC_LOC_CLIENT:
                self.args = json.loads(self.args)

            executedWord = self.handleWord(invoker, avId, toon, *self.args)
        # If you're only using the Magic Word on one person and there is a response, return that response
        if executedWord and len(self.targets) == 1:
            return executedWord
        # If the amount of targets is higher than one...
        elif validTargets > 0:
            # And it's only 1, and that's yourself, return None
            if validTargets == 1 and self.invokerId in self.targets:
                return None
            # Otherwise, state how many targets you executed it on
            return "Magic Word successfully executed on %s target(s)." % validTargets
        else:
            return "Magic Word unable to execute on any targets."

    def validateTarget(self, target):
        if self.air:
            from toontown.toon.DistributedToonAI import DistributedToonAI
            return isinstance(target, DistributedToonAI)
        elif self.cr:
            from toontown.toon.DistributedToon import DistributedToon
            return isinstance(target, DistributedToon)
        return False

    def handleWord(self, invoker, avId, toon, *args):
        raise NotImplementedError


class SetHP(MagicWord):
    aliases = ["hp", "setlaff", "laff"]
    desc = "Sets the target's current laff."
    advancedDesc = "This Magic Word will change the current amount of laff points the target has to whichever " \
                   "value you specify. You are only allowed to specify a value between -1 and the target's maximum " \
                   "laff points. If you specify a value less than 1, the target will instantly go sad unless they " \
                   "are in Immortal Mode."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("hp", int, True)]

    def handleWord(self, invoker, avId, toon, *args):
        hp = args[0]

        if not -1 <= hp <= toon.getMaxHp():
            return "Can't set {0}'s laff to {1}! Specify a value between -1 and {0}'s max laff ({2}).".format(
                toon.getName(), hp, toon.getMaxHp())

        if hp <= 0 and toon.immortalMode:
            return "Can't set {0}'s laff to {1} because they are in Immortal Mode!".format(toon.getName(), hp)

        toon.b_setHp(hp)
        return "{}'s laff has been set to {}.".format(toon.getName(), hp)


class SetMaxHP(MagicWord):
    aliases = ["maxhp", "setmaxlaff", "maxlaff"]
    desc = "Sets the target's max laff."
    advancedDesc = "This Magic Word will change the maximum amount of laff points the target has to whichever value " \
                   "you specify. You are only allowed to specify a value between 15 and 137 laff points."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("maxhp", int, True)]

    def handleWord(self, invoker, avId, toon, *args):
        maxhp = args[0]

        if not 15 <= maxhp <= 137:
            return "Can't set {}'s max laff to {}! Specify a value between 15 and 137.".format(toon.getName(), maxhp)

        toon.b_setMaxHp(maxhp)
        toon.toonUp(maxhp)
        return "{}'s max laff has been set to {}.".format(toon.getName(), maxhp)


class ToggleOobe(MagicWord):
    aliases = ["oobe"]
    desc = "Toggles the out of body experience mode, which lets you move the camera freely."
    advancedDesc = "This Magic Word will toggle what is known as 'Out Of Body Experience' Mode, hence the name " \
                   "'Oobe'. When this mode is active, you are able to move the camera around with your mouse- " \
                   "though your camera will still follow your Toon."
    execLocation = MagicWordConfig.EXEC_LOC_CLIENT

    def handleWord(self, invoker, avId, toon, *args):
        base.oobe()
        return "Oobe mode has been toggled."


class ToggleRun(MagicWord):
    aliases = ["run"]
    desc = "Toggles run mode, which gives you a faster running speed."
    advancedDesc = "This Magic Word will toggle Run Mode. When this mode is active, the target can run around at a " \
                   "very fast speed."
    execLocation = MagicWordConfig.EXEC_LOC_CLIENT

    def handleWord(self, invoker, avId, toon, *args):
        from direct.showbase.InputStateGlobal import inputState
        inputState.set('debugRunning', not inputState.isSet('debugRunning'))
        return "Run mode has been toggled."

class MaxToon(MagicWord):
    aliases = ["max", "idkfa"]
    desc = "Maxes your target toon."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    accessLevel = 'ADMIN'

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.toonbase import ToontownGlobals

        # TODO: Handle this better, like giving out all awards, set the quest tier, stuff like that.
        # This is mainly copied from Anesidora just so I can better work on things.
        toon.b_setTrackAccess([1, 1, 1, 1, 1, 1, 1])

        toon.b_setMaxCarry(ToontownGlobals.MaxCarryLimit)
        toon.b_setQuestCarryLimit(ToontownGlobals.MaxQuestCarryLimit)

        toon.experience.maxOutExp()
        toon.d_setExperience(toon.experience.makeNetString())

        toon.inventory.maxOutInv()
        toon.d_setInventory(toon.inventory.makeNetString())

        toon.b_setMaxHp(ToontownGlobals.MaxHpLimit)
        toon.b_setHp(ToontownGlobals.MaxHpLimit)

        toon.b_setMaxMoney(250)
        toon.b_setMoney(toon.maxMoney)
        toon.b_setBankMoney(toon.maxBankMoney)

        return f"Successfully maxed {toon.getName()}!"

class SkipCFO(MagicWord):
    desc = "Skips to the indicated round of the CFO."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("round", str, False, "next")]
    accessLevel = "MODERATOR"

    def handleWord(self, invoker, avId, toon, *args):
        battle = args[0]

        from toontown.suit.DistributedCashbotBossAI import DistributedCashbotBossAI
        boss = None
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedCashbotBossAI):
                if invoker.doId in do.involvedToons:
                    boss = do
                    break
        if not boss:
            return "You aren't in a CFO!"

        battle = battle.lower()

        if battle == 'two':
            if boss.state in ('PrepareBattleThree', 'BattleThree'):
                return "You can not return to previous rounds!"
            else:
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleThree')
                return "Skipping to last round..."

        if battle == 'next':
            if boss.state in ('PrepareBattleOne', 'BattleOne'):
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleThree')
                return "Skipping current round..."
            elif boss.state in ('PrepareBattleThree', 'BattleThree'):
                boss.exitIntroduction()
                boss.b_setState('Victory')
                return "Skipping final round..."


class HitCFO(MagicWord):
    desc = "Hits the CFO."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("damage", int, False, 0)]
    accessLevel = "MODERATOR"

    def handleWord(self, invoker, avId, toon, *args):
        dmg = args[0]
        from toontown.suit.DistributedCashbotBossAI import DistributedCashbotBossAI
        boss = None
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedCashbotBossAI):
                if invoker.doId in do.involvedToons:
                    boss = do
                    break
        if not boss:
            return "You aren't in a CFO!"

        boss.magicWordHit(dmg, invoker.doId)


class DisableGoons(MagicWord):
    desc = "Stuns all of the goons in an area."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.suit.DistributedGoonAI import DistributedGoonAI
        for goon in simbase.air.doFindAllInstances(DistributedGoonAI):
            goon.requestStunned(0)
        return "Disabled all Goons!"


class SkipCJ(MagicWord):
    desc = "Skips to the indicated round of the CJ."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("round", str, False, "next")]
    accessLevel = "MODERATOR"

    def handleWord(self, invoker, avId, toon, *args):
        battle = args[0]
        from toontown.suit.DistributedChiefJusticeAI import DistributedChiefJusticeAI
        boss = None
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedChiefJusticeAI):
                if invoker.doId in do.involvedToons:
                    boss = do
                    break
        if not boss:
            return "You aren't in a CJ!"

        battle = battle.lower()

        if battle == 'two':
            if boss.state in ('RollToBattleTwo', 'PrepareBattleTwo', 'BattleTwo', 'PrepareBattleThree', 'BattleThree'):
                return "You can not return to previous rounds!"
            else:
                boss.exitIntroduction()
                boss.b_setState('RollToBattleTwo')
                return "Skipping to second round..."

        if battle == 'three':
            if boss.state in ('PrepareBattleThree', 'BattleThree'):
                return "You can not return to previous rounds!"
            else:
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleThree')
                return "Skipping to final round..."

        if battle == 'next':
            if boss.state in ('PrepareBattleOne', 'BattleOne'):
                boss.exitIntroduction()
                boss.b_setState('RollToBattleTwo')
                return "Skipping current round..."
            elif boss.state in ('RollToBattleTwo', 'PrepareBattleTwo', 'BattleTwo'):
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleThree')
                return "Skipping current round..."
            elif boss.state in ('PrepareBattleThree', 'BattleThree'):
                boss.exitIntroduction()
                boss.enterNearVictory()
                boss.b_setState('Victory')
                return "Skipping final round..."


class FillJury(MagicWord):
    desc = "Fills all of the chairs in the CJ's Jury Round."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    accessLevel = "MODERATOR"

    def handleWord(self, invoker, avId, toon, *args):
        boss = None
        from toontown.suit.DistributedChiefJusticeAI import DistributedChiefJusticeAI
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedChiefJusticeAI):
                if invoker.doId in do.involvedToons:
                    boss = do
                    break
        if not boss:
            return "You aren't in a CJ!"
        if not boss.state == 'BattleTwo':
            return "You aren't in the cannon round."
        for i in xrange(len(boss.chairs)):
            boss.chairs[i].b_setToonJurorIndex(0)
            boss.chairs[i].requestToonJuror()
        return "Filled chairs."


class SkipVP(MagicWord):
    desc = "Skips to the indicated round of the VP."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("round", str, False, "next")]
    accessLevel = "MODERATOR"

    def handleWord(self, invoker, avId, toon, *args):
        battle = args[0]
        from toontown.suit.DistributedSellbotBossAI import DistributedSellbotBossAI
        boss = None
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedSellbotBossAI):
                if invoker.doId in do.involvedToons:
                    boss = do
                    break
        if not boss:
            return "You aren't in a VP!"

        battle = battle.lower()

        if battle == 'three':
            if boss.state in ('PrepareBattleThree', 'BattleThree'):
                return "You can not return to previous rounds!"
            else:
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleThree')
                return "Skipping to final round..."

        if battle == 'next':
            if boss.state in ('PrepareBattleOne', 'BattleOne'):
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleThree')
                return "Skipping current round..."
            elif boss.state in ('PrepareBattleThree', 'BattleThree'):
                boss.exitIntroduction()
                boss.b_setState('Victory')
                return "Skipping final round..."

class playAnimation1(MagicWord):
    desc = "Play the Animation: Sell Off."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    accessLevel = "MODERATOR"

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.animations.DistributedSellOffAI import DistributedSellOffAI
        animation = None
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedSellOffAI):        
                animation = do
                break
        if not DistributedSellOffAI:
            return "Cannot Play Animation!"
        
        animation.startAnimation()

        
        
class StunVP(MagicWord):
    desc = "Stuns the VP in the final round of his battle."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    accessLevel = "MODERATOR"

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.suit.DistributedSellbotBossAI import DistributedSellbotBossAI
        boss = None
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedSellbotBossAI):
                if invoker.doId in do.involvedToons:
                    boss = do
                    break
        if not boss:
            return "You aren't in a VP!"
        currState = boss.getCurrentOrNextState()
        if currState != 'BattleThree':
            return "You aren't in the final round of a VP!"
        boss.b_setAttackCode(ToontownGlobals.BossCogDizzyNow)
        boss.b_setBossDamage(boss.getBossDamage(), 0, 0)


class SkipCEO(MagicWord):
    desc = "Skips to the indicated round of the CEO."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("round", str, False, "next")]
    accessLevel = "MODERATOR"

    def handleWord(self, invoker, avId, toon, *args):
        battle = args[0]
        from toontown.suit.DistributedBossbotBossAI import DistributedBossbotBossAI
        boss = None
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedBossbotBossAI):
                if invoker.doId in do.involvedToons:
                    boss = do
                    break
        if not boss:
            return "You aren't in a CEO!"

        battle = battle.lower()

        if battle == 'two':
            if boss.state in ('PrepareBattleFour', 'BattleFour', 'PrepareBattleThree', 'BattleThree', 'PrepareBattleTwo', 'BattleTwo'):
                return "You can not return to previous rounds!"
            else:
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleTwo')
                return "Skipping to second round..."

        if battle == 'three':
            if boss.state in ('PrepareBattleFour', 'BattleFour', 'PrepareBattleThree', 'BattleThree'):
                return "You can not return to previous rounds!"
            else:
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleThree')
                return "Skipping to third round..."

        if battle == 'four':
            if boss.state in ('PrepareBattleFour', 'BattleFour'):
                return "You can not return to previous rounds!"
            else:
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleFour')
                return "Skipping to last round..."

        if battle == 'next':
            if boss.state in ('PrepareBattleOne', 'BattleOne'):
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleTwo')
                return "Skipping current round..."
            elif boss.state in ('PrepareBattleTwo', 'BattleTwo'):
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleThree')
                return "Skipping current round..."
            elif boss.state in ('PrepareBattleThree', 'BattleThree'):
                boss.exitIntroduction()
                boss.b_setState('PrepareBattleFour')
                return "Skipping current round..."
            elif boss.state in ('PrepareBattleFour', 'BattleFour'):
                boss.exitIntroduction()
                boss.b_setState('Victory')
                return "Skipping final round..."


class FeedDiners(MagicWord):
    desc = "Feed the diners in the CEO battle."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER

    def handleWord(self, invoker, avId, toon, *args):
        boss = None
        from toontown.suit.DistributedBossbotBossAI import DistributedBossbotBossAI
        for do in simbase.air.doId2do.values():
            if isinstance(do, DistributedBossbotBossAI):
                if invoker.doId in do.involvedToons:
                    boss = do
                    break
        if not boss:
            return "You aren't in a CEO!"

        if boss.state != 'BattleTwo':
            return "You aren't in the waiter round!"

        for table in boss.tables:
            for chairIndex in table.dinerInfo.keys():
                dinerStatus = table.getDinerStatus(chairIndex)
                if dinerStatus in (table.HUNGRY, table.ANGRY):
                    table.foodServed(chairIndex)

        return "All diners have been fed!"

class SpawnCog(MagicWord):
    aliases = ["cog"]
    desc = "Spawns a cog with the defined level"
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("suit", str, True), ("level", int, False, 1), ("specialSuit", int, False, 0)]

    def handleWord(self, invoker, avId, toon, *args):
        name = args[0]
        level = args[1]
        specialSuit = args[2]
        zoneId = invoker.getLocation()[1]
        if name not in SuitDNA.suitHeadTypes:
            return "Suit %s is not a valid suit!" % name
        if level not in ToontownGlobals.SuitLevels:
            return "Invalid Cog Level."

        sp = simbase.air.suitPlanners.get(zoneId - (zoneId % 100))
        if not sp:
            return "Unable to spawn %s in current zone." % name
        pointmap = sp.streetPointList
        sp.createNewSuit([], pointmap, suitName=name, suitLevel=level)
        return "Spawned %s in current zone." % name

class SpawnInvasion(MagicWord):
    aliases = ["invasion"]
    desc = "Spawn an invasion on the current AI if one doesn't exist."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("command", str, True), ("suit", str, False, "f"), ("amount", int, False, 1000), ("skelecog", int, False, 0)]

    def handleWord(self, invoker, avId, toon, *args):
        cmd = args[0]
        name = args[1]
        num = args[2]
        skeleton = args[3]
        
        self.safeDistricts = [403000001]
        
        if simbase.air.districtId in self.safeDistricts:
            return "Can't Summon an invasion in a safe district."
        else:
            if not 10 <= num <= 25000:
                return "Can't the invasion amount to {}! Specify a value between 10 and 25,000.".format(num)

            invMgr = simbase.air.suitInvasionManager
            if cmd == 'start':
                if invMgr.getInvading():
                    return "There is already an invasion on the current AI!"
                if not name in SuitDNA.suitHeadTypes:
                    return "This cog does not exist!"
                invMgr.startInvasion(name, num, skeleton)
            elif cmd == 'stop':
                if not invMgr.getInvading():
                    return "There is no invasion on the current AI!"
                #elif invMgr.undergoingMegaInvasion:
                #    return "The current invasion is a mega invasion, you must stop the holiday to stop the invasion."
                invMgr.stopInvasion()
            else:
                return "You didn't enter a valid command! Commands are ~invasion start or stop."

# Instantiate all classes defined here to register them.
# A bit hacky, but better than the old system
for item in list(globals().values()):
    if isinstance(item, type) and issubclass(item, MagicWord):
        i = item()
