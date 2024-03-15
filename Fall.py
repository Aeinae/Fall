from winsound import PlaySound, SND_FILENAME as FILE, SND_ASYNC as ASYNC, SND_LOOP as LOOP, SND_NODEFAULT as NODEFAULT
from sys import stdout
from marshal import load, dump
from msvcrt import getch, kbhit
from time import sleep
from os import system, get_terminal_size as size
from collections.abc import Iterable







class level:

    '''Class for level layout.'''

    __slots__ = ('width',
                 'movables',
                 'layout',
                 'npc',
                 'coordinates')

    gravity = 1
    lives = 2

    def __init__(self,
                 layout_file,
                 movables,
                 npc = (),
                 /, *,
                 rev = False,
                 alt = False):

        self.width = size().columns - 1
        if not isinstance(movables, str): raise TypeError('movables must be a string')
        self.__class__.movables = movables
        if not isinstance(layout_file, str): raise TypeError('level layout must be a file name')
        if alt: layout_file = layout_file.replace('lvl', 'rlvl')
        layout_list = open(layout_file, encoding='utf-16-be').readlines()
        self.npc = npc
        if self.npc: self.layout = resize(layout_list, coordinates = self.npc)
        else: self.layout = resize(layout_list)
        if not rev:
            if not alt: self.coordinates = [((self.layout.find('←') + self.layout.find('↑') + 1) % self.width) + 1, (self.layout.find('←') + self.layout.find('↑') + 1) // self.width]
            else:
                x = self.layout.find('↔')
                if x % self.width < 5:
                    self.coordinates = [(x % self.width) + 1, x // self.width]
                else:
                    self.coordinates = [(x % self.width) - 1, x // self.width]
        else: self.coordinates = [((self.layout.find('→') + self.layout.find('↓') + 1) % self.width) - 1, (self.layout.find('→') + self.layout.find('↓') + 1) // self.width]

    def __str__(self, /):

        '''Return str(self).'''

        string = self.layout

        for i in self.npc:
            if None in i.coordinates: continue
            string = string[:i.coordinates[1]*self.width + i.coordinates[0]] \
                     + repr(i)*i.is_alive \
                     + string[(i.coordinates[1]*self.width + i.coordinates[0])]*(not i.is_alive) \
                     + string[(i.coordinates[1]*self.width + i.coordinates[0]) + 1:]

        string = string[:self.coordinates[1]*self.width + self.coordinates[0]] \
                 + '■' \
                 + string[(self.coordinates[1]*self.width + self.coordinates[0]) + 1:]

        return string.replace('↔', '║')

    def __repr__(self, /):

        '''Return repr(self).'''

        return self.layout

    def tile(self, coord=None, /, *, xoffset=0, yoffset=0):
        if coord is None: coord = self.coordinates
        if xoffset or yoffset:
            coord = list(coord)
            coord[0] += xoffset
            coord[1] += yoffset
        return self.layout[coord[1]*self.width + coord[0]]

    def display(self, /, *, file=stdout, end='\r\n'):

        '''To display self in the given file (standard output file by default).'''

        system('cls')
        file.write(str(layout))
        file.write('\nx: %s, y: %s' % (*layout.coordinates,))
        file.write(end)
        

    def movable(self, coordinates, /):

        '''Check if a coordinate is accessible by the player.'''

        for i in coordinates:
            if i < 0: return False
        if self.tile(coordinates).casefold() in self.movables: return True
        return False

    def move(self, key: bytes, /):

        '''Move the player (or any NPC) according to the button pressed.'''

        match key:
            case b'\xe0':
                match getch():
                    case b'H': key = b'w'
                    case b'P': key = b's'
                    case b'K': key = b'a'
                    case b'M': key = b'd'
                    case b's': key = b'\x01'
                    case b't': key = b'\x04'

        match key:
            case b'd' | b'.' | b'>' | b'D':
                if self.movable((self.coordinates[0]+1, self.coordinates[1])):
                    self.coordinates[0] += 1
                    return True

            case b'a' | b',' | b'<' | b'A':
                if self.movable((self.coordinates[0]-1, self.coordinates[1])):
                    self.coordinates[0] -= 1
                    return True

            case b'\x01':
                m1 = self.move(b'a')
                if self.tile() in '→←↔↑↓': return m1
                m2 = self.move(b'a')
                return m1 or m2

            case b'\x04':
                m1 = self.move(b'd')
                if self.tile() in '→←↔↑↓': return m1
                m2 = self.move(b'd')
                return m1 or m2

            case b' ': self.__class__.gravity *= -1

            case b'w' | b'W': self.__class__.gravity = -1

            case b's' | b'S': self.__class__.gravity = 1

            case b'\x1b':
                system('cls')
                match menu(ingame=True):
                    case 'paused': return 'paused'
                    case 'restart': return 'restart'
                return True

        return False

    def floating(self, /):

        '''Checks if the player is floating mid-air and moves the player \none step towards the ground.'''

        A = False
        if self.npc:
            for i in self.npc:
                if i.can_fall:
                    if self.movable((i.coordinates[0], i.coordinates[1] + self.gravity)):
                        i.coordinates[1] += self.gravity
                        A = True
        if self.movable((self.coordinates[0], self.coordinates[1] + self.gravity)):
            self.coordinates[1] += self.gravity
            A = True
        if A: return True
        return False

    def isfloating(self, npc=None, /):

        '''Checks if the player (or an NPC) is floating mid-air.'''

        if npc is not None:
            if npc not in self.npc: raise ValueError('NPC is not a character of this level')
            if self.movable((npc.coordinates[0], npc.coordinates[1] + self.gravity)): return True
        if self.movable((self.coordinates[0], self.coordinates[1] + self.gravity)): return True
        return False

    def over(self, /):

        '''Check game over status.'''

        if self.tile(yoffset = self.gravity) in '█':
            level.lives -= 1
            level.gravity *= -1
        for i in self.npc:
            if i.is_alive and i.can_damage and i.coordinates == self.coordinates:
                level.lives -= 1
                level.gravity *= -1
        if level.lives < 1:
            level.gravity *= -1
            return True
        return False

    def nextlvl(self, /):

        '''Check if character should advance to the next level.'''

        if self.tile() in '→↓': return True
        if self.tile() in '↔' and self.coordinates[0] > 7: return True
        return False

    def prevlvl(self, /):

        '''Check if character should advance to the previous level.'''

        if self.tile() in '←↑': return True
        if self.tile() in '↔' and self.coordinates[0] < 7: return True
        return False

    def altpass(self, /):

        '''Check if character has discovered an alternate passage.'''

        if self.tile() == '↔': return True
        return False

    def special(self, /):

        '''Check if a special effect has been obtained.'''

        if self.tile() == '⃝': return True
        return False







class npc:

    '''Class for non-playable characters.

    The representation argument must be a string that can have multiple characters; each index will have the following values:
        [0]    : Character when gravity acts downwards.
        [1]    : Character when gravity acts upwards.
    The x and y arguments take the respective coordinates of the NPC.
    The can_fall argument determines whether the npc is affected by gravity.
    The motion argument takes a function that describes the motion of the NPC.'''

    __slots__ = ('coordinates', 'repr', 'can_fall', 'can_damage', 'can_die', 'is_alive', '_move', '_move_args')

    def __init__(self, representation, x, y, /, *, can_fall=False, can_damage=False, can_die=False, motion=None, motion_args=[]):

        self.coordinates = [x, y]
        self.repr = representation
        if len(self.repr) == 1: self.repr *= 2
        self.can_fall = can_fall
        self.can_damage = can_damage
        self.can_die = can_die
        self.is_alive = True
        self._move = motion
        self._move_args = motion_args

    def __repr__(self, /):

        '''Implement repr(self).'''

        if level.gravity < 0: return self.repr[1]
        return self.repr[0]

    def move(self, /):

        '''Move the NPC.'''

        if self._move is None: return False
        return self._move(*self._move_args)

    def configure(self, **kwargs):

        '''Reinitialize any of the arguments.'''

        if 'representation' in kwargs: self.repr = kwargs['representation']
        if 'x' in kwargs: self.coordinates[0] = kwargs['x']
        if 'y' in kwargs: self.coordinates[1] = kwargs['y']
        if 'can_fall' in kwargs: self.can_fall = kwargs['can_fall']
        if 'can_damage' in kwargs: self.can_fall = kwargs['can_damage']
        if 'motion' in kwargs:
            self._move = kwargs['motion']
            self._move_args = ()
        if 'motion_args' in kwargs: self._move_args = kwargs['motion_args']

        return kwargs

    def kill(self, /):

        '''Called when the NPC is killed.'''

        if self.can_die: self.is_alive = False









def menu(*, ingame=False):

    '''Menu operations.'''

    PlaySound('.\Data\Sounds\Abstract Vision #9 (Looped).wav', FILE | ASYNC | LOOP | NODEFAULT)
    layout_list = open(r'.\Data\Main Menu.menu', encoding='utf-16-be').readlines()

    c = 1
    while True:
        layout = resize(layout_list)

        c %= 3

        match c:
            case 2:
                printf(layout.replace('   NEW GAME   ', '-- NEW GAME --'))
            case 1:
                printf(layout.replace('   CONTINUE   ', '-- CONTINUE --'))
            case 0:
                printf(layout.replace('     EXIT     ', '--   EXIT   --'))

        k = getch()

        match k:
            case b'\xe0':
                match getch():
                    case b'H': k = b'w'
                    case b'K': k = b'a'
                    case b'P': k = b's'
                    case b'M': k = b'd'

        match k:
            case b'\r' | b'\n' | b' ':
                match c:
                    case 2:
                        intro()
                        if ingame: return 'restart'
                        return 1, ' abcdefghijklmnopqrstuvwxyz,;.:\'"/1234567890-↑↓→←↔░⃝', False, False, 2
                    case 1:
                        if not ingame:
                            try:
                                with open(r'.\Data\savefile', 'rb') as F:
                                    lvl = load(F)
                                    movables = load(F)
                                    rev = load(F)
                                    alt = load(F)
                                    lives = load(F)
                                    flags = load(F)
                                    return lvl, movables, rev, alt, lives, *flags
                            except FileNotFoundError:
                                intro()
                                return 1, ' abcdefghijklmnopqrstuvwxyz,;.:\'"/1234567890-↑↓→←↔░⃝', False, False, 2
                        else: return 'paused'
                    case 0:
                        exit("Thank you for playing!")
            case b'w' | b'W' | b'^' | b'a' | b'A': c -= 1
            case b's' | b'S' | b'd' | b'D': c += 1
            case b'\x1b':
                if ingame: return 'paused'

        system('cls')







def gameover(layout, /):

    '''Game Over Screen'''

    layout_list = layout.layout.split('\n')
    if level.gravity < 0: end = 0
    else: end = len(layout_list) - 1
    for i in range(layout.coordinates[1], end, level.gravity):
        layout_list[i] = layout_list[i][:layout.coordinates[0] - 1] + "   " + layout_list[i][layout.coordinates[0] + 2:]
    layout.layout = '\n'.join(layout_list)
    while layout.floating():
        system('cls')
        printf(str(layout))
        sleep(0.1)

    layout = level(r'.\Data\Game Over.lvl', ' abcdefghijklmnopqrstuvwxyz', rev = (level.gravity < 0))
    layout.layout = layout.layout.replace('←', '═').replace('→', '═')
    PlaySound(None, FILE | ASYNC | LOOP | NODEFAULT)
    while layout.floating():
        system('cls')
        printf(str(layout))
        sleep(0.1)

    layout.layout = layout.layout.replace('░   ░', '░░░░░').replace('▒   ▒', '▒▒▒▒▒').replace('▓   ▓', '▓▓▓▓▓')

    cls = True
    ckb()
    while True:

#        if layout.coordinates[0] < layout.layout.find('╗')//2 + 1: message = 'Retry?'
#        else: message = 'Quit?'

        message = 'Quit?'

        if cls:
            system('cls')
            printf(convey(layout, message))

        if layout.floating():
            sleep(0.1)
            if not kbhit(): continue

        inp = getch()

        if not inp in b'\x1b\n\r': cls = layout.move(inp)
        sleep(0.1)
        if inp in b'\n\r':
            if message == 'Retry?':
                try:
                    with open(r'.\Data\savefile', 'rb') as F:
                        load(F)
                        level.movables = load(F)
                        load(F)
                        load(F)
                        level.lives = load(F)
                except FileNotFoundError:
                    level.movables = ' abcdefghijklmnopqrstuvwxyz,;.:\'"/1234567890-↑↓→←↔░⃝'
                    level.lives = 2
                break
            elif message == 'Quit?': raise SystemExit("Thank you for playing!")
                

        if layout.isfloating(): cls = True
        
    
    







def resize(layout_list, /, *, coordinates=None):

    '''Resize the display field.'''

    t_size = [*size()]
    t_size[0] -= 1
    t_size[1] -= 1
    t_size = (*t_size,)
    c = 1
    while len(layout_list) < t_size[1]:
        if c < 0:
            layout_list.insert(3, layout_list[2])
            if coordinates:
                if isinstance(coordinates, Iterable):
                    for i in coordinates: i.coordinates[1] += 1                 # i must be a tuple of NPCs, not their coordinates.
                else: coordinates[1] += 1                                       # coordinates must be a coordinate tuple.
        else: layout_list.insert(-2, layout_list[-3])
        c *= -1
    c = t_size[0] - len(layout_list[-1]) - 1
    for i in range(len(layout_list)):
        layout_list[i] = layout_list[i][:len(layout_list[i])//2] \
                         + layout_list[i][len(layout_list[i])//2]*(c + 1) \
                         + layout_list[i][len(layout_list[i])//2 + 1:]
    return ''.join(layout_list)







def save(level, movables, rev, alt, lives, /, flags=[]):

    '''Save progresses.'''

    with open(r'.\Data\savefile', 'wb') as file:
        dump(level, file)
        dump(movables, file)
        dump(rev, file)
        dump(alt, file)
        dump(lives, file)
        dump(flags, file)
        return True
    return False







def convey(level_layout, message=None, /, npc=None):

    '''Make the character speak.'''

    lvllst = [i+'\n' for i in str(level_layout).split('\n')]
    if not npc: coord = level_layout.coordinates
    else:
        if npc not in level_layout.npc: raise ValueError("NPC is not a character of current level.")
        coord = npc.coordinates
    if message is None: return str(level_layout)
    message_l = message.split('\n')[::-level_layout.gravity]
    for i in range(len(message_l)):
        lvllst[coord[1] - level_layout.gravity*(i+1)] = lvllst[coord[1] - level_layout.gravity*(i+1)][:coord[0]] \
                                                      + message_l[i] \
                                                      + lvllst[coord[1] - level_layout.gravity*(i+1)][coord[0] + len(message_l[i]):]
        if len(lvllst[coord[1] - level_layout.gravity*(i)]) > (level_layout.width + coord[0]): return str(level_layout)
    return ''.join(lvllst)







def ckb():

    '''Clear keyboard buffer.'''

    while kbhit(): getch()







def speak(level_layout, message=None, /, npc=None):

    '''Character speech.'''

    ckb()
    system('cls')
    printf(convey(level_layout, message, npc=npc))
    return getch() in b'\x08\x7f\n'









def intro():

    '''An introduction cutscene.'''

    scientist = npc('□', 6, 17)
    layout = level(r'.\Data\Cutscene 1.lvl', ' abcdefghijklmnopqrstuvwxyz,;.:\'"/1234567890-↑↓→←↔░⃝', (scientist,))
    PlaySound(None, ASYNC)
    ckb()
    system('cls')
    layout.layout = layout.layout.replace('←', ' ')
    printf(str(layout))
    sleep(1)
    if speak(layout, "Get away now,\nbefore they\nfind out...", scientist): return 
    if speak(layout, "You won't have\ntime when the\nhunt begins.", scientist): return

    PlaySound('.\Data\Sounds\Hard Rock (Looped).wav', ASYNC | LOOP | FILE | NODEFAULT)

    if speak(layout, "Now go! Run\nand don't ever\nshow your face\nhere again.", scientist): return
    if speak(layout, "But you will-..."): return
    if speak(layout, "Not this time.\nPlease...", scientist): return
    if speak(layout, "If your don't\ngo now, all\nour efforts will\nbe in vain.", scientist): return
    if speak(layout, "I will be waiting\nby the broken\nbridge. You better\nbe there..."): return
    while layout.move(b'\x04'):
        system('cls')
        layout.floating()
        printf(str(layout))
        sleep(0.1)
    if speak(layout, "Huh...?\nSomething\nfeels off."): return
    system('cls')
    printf(str(layout))
    for i in range(3):
        layout.move(b'\x01')
        system('cls')
        printf(str(layout))
        sleep(0.1)
    layout.layout = layout.layout.replace('░▒▒      ║', '░░░      ║').replace('▒▒▒▒      →', '░░        →')
    if speak(layout, "What just...?"): return
    if speak(layout, "RUN!\nI HEAR SOMEONE!", scientist): return
    if speak(layout, "But-..."): return
    if speak(layout, "JUST GO!!!", scientist): return
    for i in range(6):
        system('cls')
        layout.move(b'\x04')
        printf(str(layout))
        sleep(0.1)
    while layout.floating():
        system('cls')
        printf(convey(layout, "NOO!"))
        sleep(0.1)
    ckb()







def scene1(layout, easter, /):

    '''Where am I?'''

    system('cls')
    level.gravity = 1
    printf(convey(layout, "*huff*huff*"))
    sleep(0.75)
    if speak(layout, "I should\nhave lost them."): return
    if speak(layout, "Dammit, I\nshouldn't have\nlet Q make me\nrun away like\nthis."): return
    if speak(layout, "*sigh* ..."): return
    layout.move(b'D')
    system('cls')
    printf(str(layout))
    sleep(1)
    layout.move(b'A')
    system('cls')
    printf(str(layout))
    sleep(0.2)
    if speak(layout, "Where have\nI fallen\ninto now?"): return
    if not easter:
        if speak(layout, "The way I\ncame through\nclosed, so\nI can't go\nback that way..."): return
    else:
        if speak(layout, "I don't think\nit would be\nwise to go\nback the way\nI came through."): return
    speak(layout, "This place seems\nhabitable. The\nwalls and the\nlike... Maybe\nsomeone lives here.")







def scene2(layout, npc, /):

    '''Not alone?'''

    system('cls')
    printf(str(layout))
    sleep(1)
    speak(layout, "Hello?", npc=ckb())
    speak(layout, "Is anybody\nhere?")
    speak(layout, "...", npc=npc)
    speak(layout, "No... One...", npc=npc)
    speak(layout, "What was that?")
    coordchecker = layout.coordinates.copy()
    coordchecker[0] += 7
    while coordchecker != npc.coordinates:
        layout.move(b'd')
        layout.floating()
        system('cls')
        printf(str(layout))
        sleep(0.1)
        coordchecker = layout.coordinates.copy()
        coordchecker[0] += 7
    if speak(layout, "Who are you?"): return
    if speak(layout, "Are you...", npc=npc): return
    if speak(layout, "Are you... Alive?", npc=npc): return
    system('cls')
    printf(convey(layout, "???"))
    sleep(0.75)
    if speak(layout, "To the best of\nmy knowledge, yes,\nI am."): return
    if speak(layout, "Good.", npc=npc): return
    if speak(layout, "Good. Good, good.", npc=npc): return
    if speak(layout, "You must fear\nyourself.", npc=npc): return
    if speak(layout, "I do not\nunderstand you."): return
    if speak(layout, "The artefact that\nyou possess...", npc=npc): return
    if speak(layout, "It is more\nthan just a\ndevice.", npc=npc): return
    if speak(layout, "A day will\ncome where you\nmust fight against\nyourself...", npc=npc): return
    if speak(layout, "... Such is the\nfate of the one\nwho possesses that\nwretched artefact.", npc=npc): return
    if speak(layout, "Who are you?"): return
    if speak(layout, "... the wretched\natrefact...", npc=npc): return
    if speak(layout, "What? No,\nwho are you?"): return
    if speak(layout, "...", npc=npc): return
    speak(layout, "He won't talk.")
    






def scene3(layout, /):

    '''Dangers.'''

    level.gravity = 1
    system('cls')
    printf(str(layout))
    sleep(1)
    if speak(layout, "This is strange.\nThe path is too\nnarrow now."): return
    if speak(layout, "I must\nremain vigilant."): return
    if speak(layout, "I wonder what\nis up there,\nat the top..."): return
    if speak(layout, "..."): return
    for i in range(10):
        layout.coordinates[1] -= 1
        printf(convey(layout, '...'))
        sleep(0.175)
    for i in range(10):
        layout.coordinates[1] += 1
        printf(convey(layout, '!!!'))
        sleep(0.175)
    if speak(layout, "Holy hell is\nthat... Bloodstone!?"): return
    if speak(layout, "Had I just used\nthe artefact\nto go upwards\njust now..."): return
    if speak(layout, "It would\nhave hurt!"): return
    speak(layout, "I must be\nmore careful.")








Song = {0: None,
        1: '.\Data\Sounds\Abstract Vision #8 (Looped).wav',
        2: '.\Data\Sounds\Abstract Vision #8 (Looped).wav',
        3: '.\Data\Sounds\Abstract Vision #8 (Looped).wav',
        4: '.\Data\Sounds\Abstract Vision #8 (Looped).wav',
        5: '.\Data\Sounds\Abstract Vision #8 (Looped).wav',
        6: '.\Data\Sounds\Abstract Vision #8 (Looped).wav',
        7: '.\Data\Sounds\Abstract Vision #8 (Looped).wav',
        8: '.\Data\Sounds\Abstract Vision #8 (Looped).wav'}

printf = stdout.write
system('title FALL')
curr_lvl, movables, rev, alt, level.lives, *flags = menu()
if not curr_lvl: curr_lvl = 1
restart = False
curr_song = Song[curr_lvl]
PlaySound(Song[curr_lvl], FILE | ASYNC | LOOP | NODEFAULT)





while True:

    npcs = ()

    if restart:
        rev, alt, restart = (False,)*3
        curr_lvl, movables, npcs, *flags = 1, ' abcdefghijklmnopqrstuvwxyz,;.:\'"/1234567890-→←↔↑↓░⃝', ()

    match curr_lvl:                                     #For NPC Generation.
        case 4:
            WiseOne = npc('□', 80, 20)
            npcs = (WiseOne,)

    try: movables = layout.movables
    except NameError: pass
    lvlmap = r'.\Data\Level %d.lvl' % curr_lvl
    layout = level(lvlmap, movables, npcs, rev=rev, alt=alt)
    cls = True

    match curr_lvl:                                     #For level configuration.
        case 0:
            system('title Easter Egg!')
            PlaySound(None, ASYNC)
            flags.append(tuple(b'close'))
            flags.append(tuple(b'easter'))
        case 1:
            system('title FALL')
            if tuple(b'close') in flags and tuple(b'easter') not in flags:
                layout.layout = layout.layout.replace('←', ' ')
        case 2:
            if not tuple(b'scene1') in flags:
                scene1(layout, tuple(b'easter') in flags)
                flags.append(tuple(b'scene1'))
        case 3:
            if tuple(b'sp1') in flags:
                layout.layout = layout.layout.replace('⃝', ' ')
        case 4:
            if tuple(b'scene2') not in flags:
                scene2(layout, WiseOne)
                flags.append(tuple(b'scene2'))
        case 5:
            if tuple(b'scene3') not in flags:
                scene3(layout)
                flags.append(tuple(b'scene3'))
        case 7:
            if tuple(b'sp2') in flags:
                layout.layout = layout.layout.replace('⃝', ' ')

    if curr_song != Song[curr_lvl]:
        PlaySound(Song[curr_lvl], FILE | ASYNC | LOOP | NODEFAULT)
        curr_song = Song[curr_lvl]

    while True:

        if cls:
            system('cls')
            printf(str(layout))
            printf('\n  ' + ('♥'*layout.lives)*(tuple(b'scene3') in flags))

        if layout.nextlvl():
            system('cls')
            curr_lvl += 1
            rev = False
            if layout.altpass(): alt = True
            else: alt = False
            break
        

        elif layout.prevlvl():
            system('cls')
            curr_lvl -= 1
            rev = True
            if layout.altpass(): alt, rev = True, False
            else: alt = False
            break

        chklst = []
        for i in layout.npc:
            if i.can_die:
                if i.coordinates == [layout.coordinates[0], layout.coordinates[1]+layout.gravity]: i.kill()
            chklst.append(i.move())

        if kbhit(): cls = layout.move(getch())
        else: cls = any(chklst)

        if layout.floating():
            sleep(0.1)
            cls = True
            if not kbhit(): continue

        sleep(0.1)

        match cls:
            case 'paused': PlaySound(Song[curr_lvl], FILE | ASYNC | LOOP | NODEFAULT)
            case 'restart':
                cls, restart = True, True
                break

        if layout.isfloating(): cls = True
        else:
            if tuple(b'close') not in flags:
                layout.layout = layout.layout.replace('←', ' ')
                flags.append(tuple(b'close'))
                cls = True

        if layout.over():
            gameover(layout)
            break

        if layout.special():
            match curr_lvl:
                case 3:
                    level.lives += 1
                    layout.layout = layout.layout.replace('⃝', ' ')
                    flags.append(tuple(b'sp1'))
                case 7:
                    level.movables += '│'
                    layout.layout = layout.layout.replace('⃝', ' ')
                    flags.append(tuple(b'sp2'))
                    input(level.movables)

    save(curr_lvl, level.movables, rev, alt, level.lives, flags)









#   ─━┄┅┈┉╌╍═
#   │┃┆┇┊┋╎╏║
#   ┌┍┎┏┐┑┒┓
#   └┕┖┗┘┙┚┛
#   ├┝┞┟┠┡┢┣
#   ┤┥┦┧┨┩┪┫
#   ┬┭┮┯┰┱┲┳
#   ┴┵┶┷┸┹┺┻
#   ┼┽┾┿╀╁╂╃╄╅╆╇╈╉╊╋
#   ╒╓╔╕╖╗
#   ╘╙╚╛╜╝
#   ╞╟╠╡╢╣
#   ╤╥╦╧╨╩╪╫╬
#   ╭╮╯╰╱╲╳╴╵╶╷
#   ╸╹╺╻╼╽╾╿▀
#   ▁▂▃▄▅▆▇█▉▊▋▌▍▎▏▐
#   ░▒▓
#   ▔▕▖▗▘▙▚▛▜▝▞▟
#   ⃝⌂
