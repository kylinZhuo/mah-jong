import numpy as np 
import re
import functions as f
from collections import Counter
import itertools


COLORS = ['m', 'p', 's', 'z']
C2L = {'m': 0, 'p': 1, 's': 2, 'z': 3}
L2C = {0: 'm', 1: 'p', 2: 's', 3: 'z'}
HONBA_FEE = 300
RICHI_FEE = 1000


def generate_all_mahjong(shuffled=False, distinct=False):

    n_numbers, n_colors = range(1, 10), range(1, 8)
    all_mj = np.array([y for x in [
        map(lambda _: str(_) + ch, n_colors if ch == 'z' else n_numbers)
        for ch in COLORS] for y in x] * (1 if distinct else 4))
    if shuffled:
        np.random.shuffle(all_mj)
    return all_mj

ALL_MJ = generate_all_mahjong(distinct=False)
ALL_MJ_DIST = generate_all_mahjong(distinct=True)


class Mahjong:

    def __init__(self, string, direction='e', status=None, hold_by=1):
        self.number = int(string[0])
        self.color = string[1]
        self.direction = direction
        self.status = status
        self.hold_by = hold_by

    def __str__(self):
        return str(self.number) + self.color


# Mountain. Randomly initialized at the beginning
class Mountain:

    def __init__(self):
        self.mahjongs = generate_all_mahjong(shuffled=True)
        # treasure
        self.treasure = [self.mahjongs[-6]]
        self.pointer = 0
        self.next = self.mahjongs[self.pointer]

    def take(self, num):
        res = list(self.mahjongs[self.pointer: self.pointer + num])
        self.pointer += num
        return res


# the set at hand
class Hand:

    def __init__(self,
                 uuid="",
                 num=0,
                 is_clear=True,
                 from_str=None
                 ):
        """
        :param num: 13 or 14
        :param is_clear: has any exposure?
        :param mahjongs: total mahjongs in hand
        :param exposure: the exposed part of mahjongs
        :param hidden: the still hidden part of mahjongs
        """
        self.uuid = uuid
        self.num = num
        self.is_clear = is_clear
        self.mahjongs = []  # the part that can do the in/out
        self.exposure = []  # max length: 4
        self.hidden = []  # the part for the hidden kan
        self.mpsz = dict({'m': [], 'p': [], 's': [], 'z': []})  # the part that can do the in/out
        if from_str:
            self.from_str(from_str)

    def from_str(self, str):
        tmp = re.split(r"[mpsz]", str)[:-1]
        values = map(lambda x: map(lambda y: int(y), list(x)), tmp)
        keys = COLORS
        self.mpsz = dict(zip(keys, values))

    # Output the hand tiles in a formatted way. 123m456p789s11234z
    def __str__(self):
        return ''.join([
                ''.join(
                    [
                        m[0] for m in self.mahjongs
                        if m[1] == ch
                    ]
                )
                + ch
                for ch in COLORS])

    def can_chi(self, mj):
        # 3 possibilities for chi: [n-2,n-1], [n-1, n+1], [n+1, n+2]
        n, color = int(mj[0]), mj[1]
        s = self.mpsz[color]
        flag, res = False, []
        for p in [(n-2, n-1), (n-1, n+1), (n+1, n+2)]:
            if (p[0] in s) and (p[1] in s):
                res.append(p)
                flag = True
        return flag, res

    def can_pon(self, mj):
        n, color = int(mj[0]), mj[1]
        return sum(np.array(self.mpsz[color]) == n) >= 2

    def can_kan(self, mj, type):
        n, color = int(mj[0]), mj[1]
        if type == 1 or type == 2:
            return sum(np.array(self.mpsz[color] == n)) == 3
        else:
            return any(all(i) for i in np.array(self.exposure) == [n] * 3)

    def take(self, mjs):
        # keep track of two sources
        if type(mjs) == list:
            self.mahjongs += mjs
            for mj in mjs: self.mpsz[mj[1]].append(int(mj[0]))
            self.num += len(mjs)
        elif type(mjs) == str:
            self.mahjongs.append(mjs)
            self.mpsz[mjs[1]].append(int(mjs[0]))
            self.num += 1
        else:
            pass

    def discard(self, mjs, pool=None):
        # when pool == None: transfer from mahjongs to hidden or exposure
        # when pool exists: discard to the pool
        if type(mjs) == list:
            for mj in mjs: 
                self.mpsz[mj[1]].append(int(mj[0]))
                self.mahjongs.remove(mj)
        elif type(mjs) == str or type(mjs) == np.string_:
            self.mahjongs.remove(mjs)
            self.mpsz[mjs[1]].remove(int(mjs[0]))
            self.num -= 1
        else:
            pass
        if pool:
            pass

    def pon(self, mj):
        for _ in range(2):
            # self.mahjongs.remove(mj)
            self.discard(mj)
        self.exposure.append([mj] * 3)
        self.is_clear = False

    def chi(self, mj, mj1, mj2):
        self.discard([mj1, mj2])
        self.exposure.append([mj, mj1, mj2])
        self.is_clear = False

    def kan(self, mj, kan_type):
        # type 1->off, 2->add, 3->on
        if kan_type == 1:
            self.discard([mj] * 3)
            self.hidden.append([mj] * 4)

        elif kan_type == 2:
            self.discard([mj] * 3)
            self.exposure.append([mj] * 4)

        elif kan_type == 3:
            for ex in self.exposure:
                if ex == [mj] * 3:
                    ex.append(mj)
                    break
        else:
            pass

    # return the 
    def get_eyes(self):
        eyes = [[str(k)+ch for k, v in Counter(self.mpsz[ch]).items() if v >= 2] for ch in COLORS]
        return list(itertools.chain(*eyes))

    def remove_eye(self, eye):
        for _ in range(2):
            self.mpsz[eye[1]].remove(int(eye[0]))

    def append_eye(self, eye):
        for _ in range(2):
            self.mpsz[eye[1]].append(int(eye[0]))

    def win(self):

        # firstly not consider the special winning pattern
        # 1) find all the possibilities of doubles
        eyes = self.get_eyes()
        if not eyes:
            return False

        def func1(vals):
            for v in vals:
                if not v:
                    continue
                if len(v) % 3 != 0:
                    return False
                else:
                    if not func2(sorted(v)):
                        return False
            return True

        # a single color
        def func2(v):
            # detect the triple first
            # v = sorted(v)
            if len(v) == 0:
                return True
            elif len(v) == 3:
                return len(set(v)) == 1 or (v[0] + 1 == v[1] == v[2] - 1)

            # elif len(v) == 6:
            #     triples = [key for key, val in Counter(v).items() if val >= 3]
            #     if len(triples) == 2:
            #         return True
            #     elif len(triples) == 1 and (triples[0] in (v[0], v[-1])):
            #         for _ in range(3):
            #             v.remove(triples[0])
            #         return func2(v)
            #     else:  # no triples
            #         minv = min(v)
            #         if minv + 1 in v and minv + 2 in v:
            #             for m in minv, minv+1, minv+2:
            #                 v.remove(m)
            #             return func2(v)
            #         else:
            #             return False

            elif len(v) in (6, 9, 12):
                triples = [key for key, val in Counter(v).items() if val >= 3]
                if len(triples) == len(v) / 3:
                    return True
                else:
                    flag = False
                    for t in triples:
                        if t == v[0] or t == v[-1]:
                            flag = True
                            for _ in range(3):
                                v.remove(t)
                    if flag:
                        return func2(v)
                    else:
                        minv = min(v)
                        if minv + 1 in v and minv + 2 in v:
                            for m in minv, minv+1, minv+2:
                                v.remove(m)
                            return func2(v)
                        else:
                            return False
            else:
                return False

        for eye in eyes:
            self.remove_eye(eye)
            vals = self.mpsz.copy().values()
            if func1(vals):
                return True
            self.append_eye(eye)

        return False

    def tenpai(self):

        pass


class Player:

    def __init__(self,
                 name=None,
                 location=None,
                 is_dealer=None,
                 score=None,
                 uuid=None):
        """
        :param name
        :param location: {'e', 's', 'w', 'n'}
        :param is_dealer: boolean
        :param score: the initial score
        :param id: the uuid
        """
        self.name = name
        self.location = location
        self.is_dealer = is_dealer
        self.score = score
        self.hands = Hand(uuid=uuid)
        self.uuid = uuid
        self.next = None
        self.pool = None

    def assign_pool(self, pool):
        self.pool = pool

    def take(self, mjs):
        self.hands.take(mjs)

    def discard(self, mjs):
        self.hands.discard(mjs)

    def add_score(self, s):
        self.score += s

    # define the dynamic actions: pon, chi, kan, richi, win(tsumo, ron)
    def pon(self, mj):
        # mahjong has format '1s'
        self.hands.pon(mj)

    def chi(self, mj, mj1, mj2): 
        self.hands.chi(mj, mj1, mj2)

    def kan(self, mj):
        self.hands.kan(mj)

    def richi(self):
        self.score -= RICHI_FEE
        self.pool.n_richi += 1

    def win(self, mj=None, type='ron'):
        if not mj:
            return self.hands.win()
        else:
            self.hands.take(mj)
            ret = self.hands.win()
            self.hands.discard(mj)
            return ret

    def tenpai(self):
        return self.hands.tenpai()


class Pool:

    def __init__(self, chan=1):

        self.num = 0
        self.discard = {'e': [], 's': [], 'w': [], 'n': []}
        self.n_richi = 0
        self.score_left = 0
        self.honba = 0
        self.chan = chan

    def refresh(self, ryuukyoku=False, renchan=False):
        if ryuukyoku:
            self.score_left = self.honba * HONBA_FEE + self.n_richi * RICHI_FEE
        if renchan:
            self.honba += 1
        else:
            self.honba = 0
            self.chan = self.chan + 1 if self.chan < 4 else 1

        self.num = 0
        self.discard = {'e': [], 's': [], 'w': [], 'n': []}


def initialize_mountain():

    _mountain = Mountain()
    return _mountain


def initialize_players(score=25000):

    p1 = Player("East", 'e', True, score, uuid=1)
    p2 = Player("South", 's', False, score, uuid=2)
    p3 = Player("West", 'w', False, score, uuid=3)
    p4 = Player("North", 'n', False, score, uuid=4)

    p1.next = p2
    p2.next = p3
    p3.next = p4
    p4.next = p1

    return p1, p2, p3, p4


def distribute(_mountain, start_player):

    cp = start_player

    # take 4 mahjongs each time for 3 times
    for _x in range(3):
        for _y in range(4):
            mjs = _mountain.take(4)
            # cp = players[_y]
            cp.take(mjs)
            cp = cp.next

    # take the last few
    for _x in range(4):
        mj = _mountain.take(1)
        # cp = players[_y]
        cp.take(mj)
        cp = cp.next

    mj = _mountain.take(1)
    cp.take(mj)
    # players[0].take(mj)


if __name__ == '__main__':

    # p1, p2, p3, p4 = initialize_players()
    # mountain = initialize_mountain()
    # distribute(mountain, p1)

    # p1.discard(p1.hands.mahjongs[0])
    # print p1.hands
    # p1.take('3z')
    # print p1.hands
    # p1.discard(p1.hands.mahjongs[0])
    # print p1.hands

    print generate_all_mahjong(distinct=True, shuffled=True)

    # p1 = Player(uuid=805)
    # p1.hands.from_str('111m222p233334s22z')
    # print p1.win()