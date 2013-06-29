import musicxml
from utils.rational import Rational 

# some rational numbers for comparing with note.getValue()
eighth = Rational(1,d=8)
quarter = Rational(1, d=4)
half = Rational(1,d=2)
whole = Rational(1,d=1)

# define dictionaries of braille output according to length
veryshort = {'fa':'f', 'so':'i', 'la':'b', 'mi':'c', 'rest':'g'}
short = {'fa':'p', 'so':'s', 'la':'l', 'mi':'m', 'rest':'q'}
long = {'fa':'$', 'so':'[', 'la':'<', 'mi':'%', 'rest':']'}
verylong ={'fa':'&', 'so':'!', 'la':'v', 'mi':'x', 'rest':'='}
# and known lengths
known_durations = [eighth, quarter, half, whole]
# dictionary mapping the needed tones onto shapes, do this as a dictionary since it guarantees it will break if it gets an accidental rather than producing rubbish
# starts with 0 as the tonic so expect lots of modulo
note2shape = {0:'fa', 2:'so', 4:'la', 5:'fa', 7:'so', 9:'la', 11:'mi', None:'rest'}

# some things to do with braille printers
dot = r"'"
linewidth = 32
unknown = '#'
upup = '"'
up = '^'
down = ';'
downdown = ','

def tonicMIDIpitch(key):
    """ returns the MIDIpitch of the tonic note in the key with the integer value "key" """
    return 60 + 7*key

def fasolagroup( note, key):
    """ returns the group (like stave I think) for the relevant note.
    There are 2 groups in each octave, the lower fasola and the upper fasolami
    .
    Groups are numbered from zero in the lower octave"""
    if note.pitch is None: return None
    tonic = tonicMIDIpitch( key) % 12 # key in range(0,12)
    note_number = note.pitch.getMIDIpitch()
    note_in_key = note_number - tonic
    if note_in_key % 12 < 5: group_in_octave = 0
    else: group_in_octave = 1
    # now there's 2 groups per octave so work out what octave it's in, multiply by 2 and add the group
    return 2*( note_in_key /12) + group_in_octave

def note2symbol(note, key):
    """ returns the braille symbol for the given note in the given key,
    the fasola group for the note"""
    if note.pitch is None:
        step = None
    else:
        note_number = note.pitch.getMIDIpitch()
        step = (note_number - tonicMIDIpitch( key)) % 12
    # we have four dictionaries of symbols depending on note length, now choose the right one
    duration = note.getValue()
    if (duration < eighth) | (duration >= whole): dict = verylong
    elif (duration >= eighth) & (duration < quarter): dict = veryshort
    elif (duration >= quarter) & (duration < half): dict = short
    else: dict = long
    try: return dict[ note2shape [ step]], fasolagroup( note, key)
    except KeyError: return unknown, None



def braille_shapenote_bar( bar, key):
    """ returns a string of symbols for the shapes in the bar
    The current plan is that each note is a symbol and optionally followed by a dot.
    If the note moves outside the fasola group it is preceded by symbols meaning up or down"""
    result = []
    notes = [n for n in bar if isinstance(n,  musicxml.Note)]
    oldsymbol = None
    oldgroup = None
    for note in notes:
        symbol, group = note2symbol( note, key)
        if oldgroup is not None:
            if group > oldgroup +1: result.append(upup)
            elif group == oldgroup + 1: result.append(up)
            elif group == oldgroup -1: result.append( down)
            elif group < oldgroup -1: result.append( downdown)
        result.append( symbol)
        if (note.getValue() not in known_durations) & (note.duration > 1): result.append( dot) # not very precise but gives warning it's nonstandard length
        if group is not None: oldgroup = group
    return r''.join(result) # simply concatenate 


        

def braille_shapenote_part( part):
    """ returns string which is transcription of part """
    result=r''
    line = ''
    measures = [m for m in part]
    key = measures[-1].key()
    for measure in part:
        bar = braille_shapenote_bar( measure, key)
        if len( line+bar) > linewidth:
            result +=line+"\n"
            line = bar
        else:
            line += bar+' '
    return result


def braille_extract_part( filename, partname, foldcase=False):
    """ extracts a part with name partname from a musicxml file filename,
    if foldcase is True the name match is case insensitive"""
    piece = musicxml.Score( filename)
    parts = [p for p in piece]
    if foldcase: copyname = partname.lower()
    else: copyname = partname
    if foldcase: names = [p.name.lower() for p in piece] # part names
    else: names = [p.name for p in piece]
    try: return parts[ names.index( copyname)]
    except ValueError:
        print 'braille_extract_part, cannot find part named ',partname
        return None

