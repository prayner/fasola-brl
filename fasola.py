import musicxml

# define dictionaries of braille output according to length
veryshort = {'fa':'f', 'so':'i', 'la':'b', 'mi':'c', 'rest':'g'}
short = {'fa':'p', 'so':'s', 'la':'l', 'mi':'m', 'rest':'q'}
long = {'fa':'$', 'so':'[', 'la':'<', 'mi':'%', 'rest':']'}
verylong ={'fa':'&', 'so':'!', 'la':'v', 'mi':'x', 'rest':'='}
# and known lengths
known_durations = [2, 4, 8, 16]
# dictionary mapping the needed tones onto shapes, do this as a dictionary since it guarantees it will break if it gets an accidental rather than producing rubbish
# starts with 0 as the tonic so expect lots of modulo
note2shape = {0:'fa', 2:'so', 4:'la', 5:'fa', 7:'so', 9:'la', 11:'mi', None:'rest'}

# some things to do with braille printers
dot = "'"
linewidth = 32
unknown = '#' 
up = '^'
down = ';'

def tonicMIDIpitch(key):
    """ returns the MIDIpitch of the tonic note in the key with the integer value "key" """
    return 60 + 7*key

def note2symbol(note, key):
    """ returns the braille symbol for the given note in the given key,
    the canonical symbol for that pitch (i.e always from the "short" dictionary 
 and as the midipitch """
    if note.pitch is None:
        note_number = None
        step = None
    else:
        note_number = note.pitch.getMIDIpitch()
        step = (note_number - tonicMIDIpitch( key)) % 12
    # we have four dictionaries of symbols depending on note length, now choose the right one 
    if (note.duration < 2) | (note.duration >= 16): dict = verylong
    elif (note.duration >= 2) & (note.duration < 4): dict = veryshort
    elif (note.duration >= 4) & (note.duration < 8): dict = short
    else: dict = long
    try: return dict[ note2shape [ step]], short[ note2shape [ step]], note_number
    except KeyError: return unknown, unknown,  note_number



def braille_shapenote_bar( bar, key):
    """ returns a string of symbols for the shapes in the bar
    The current plan is that each note is a symbol and optionally followed by a dot.
    If the symbol will b the same but the pitch different from the last note the symbol will be preceeded by an up or down indication """
    result = []
    notes = [n for n in bar if isinstance(n,  musicxml.Note)]
    oldsymbol = None
    old_canonicalsymbol = None
    oldpitch = None
    for note in notes:
        symbol, canonicalsymbol, pitch = note2symbol( note, key)
        if (canonicalsymbol == old_canonicalsymbol) & (pitch != oldpitch):
            # then we've moved note but not symbol, indicate up or down, note with the initializations of old_canonicalsymbol this will never happen at the start of a bar
            if pitch > oldpitch: result.append( up)
            else: result.append( down)
        result.append( symbol)
        if (note.duration not in known_durations) & (note.duration > 1): result.append( dot) # not very precise but gives warning it's nonstandard length
        oldsymbol, old_canonicalsymbol, oldpitch = symbol, canonicalsymbol, pitch
    return ''.join(result) # simply concatenate 


        

def braille_shapenote_part( part):
    """ returns string which is transcription of part """
    result=""
    line = ''
    for measure in part:
        bar = braille_shapenote_bar( measure, part.key())
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

