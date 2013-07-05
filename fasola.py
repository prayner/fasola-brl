import os
import musicxml
from utils.rational import Rational 
from HTMLParser import HTMLParser
import louis 
import textwrap 

lyricsdir='html'
musicdir='xml'

class Fasolaparser( HTMLParser):
    """ subclass for handling the html from fasola.org"""
    def __init__( self, filename):
        """ initialize the parser and get the file contents into a string"""
        HTMLParser.__init__(self)
        f = open(filename, 'r')
        self.content = f.read()
        f.close()
        self.title=''
        self.intitle = False
        self.lyrics=''
        self.inlyrics = False
        self.lyricsanchor = False
        self.feed(self.content)

    def handle_starttag(self, tag, attrs):
        """really just turning on tags for the handle_data"""
        if (tag == 'a') and (attrs[0][1] == 'LYRICS'): self.lyricsanchor = True
        if (tag == 'center') and self.lyricsanchor: self.inlyrics = True
        if tag == 'title': self.intitle = True
    def handle_endtag( self, tag):
        """ just unsets some booleans"""
        if tag == 'center': self.inlyrics = False
        if tag == 'title': self.intitle = False
    def handle_data( self, data):
        """ adds data to required fields, something tells me I should generalize this"""
        if self.inlyrics: self.lyrics+=data
        if self.intitle: self.title+=data
        
def braillewords( filename, louistable="en-GB-g2.ctb", width=33):
    """ returns brailled string of lyrics from fasola file filename using louistable"""
    result=''
    text = Fasolaparser(filename)
    verses = text.lyrics.replace('\r', '').split('\n\n')
    result += louis.translateString( [louistable],  text.title.lower().strip())+'\n'
    for verse in verses: # verse 0 is often empty but we'll deal with that later
        versestring = '  ' # two indented spaces to start
        lines = [l for l in verse.split('\n') if len(l.strip())]
        for line in lines:
            versestring += louis.translateString( [louistable],  line.lower().strip())
            versestring += ' > ' # braille line marker
        result += textwrap.fill( versestring, width=width)[0:-2]+'\n'
    return result


        

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
linewidth = 33
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



def braille_shapenote_bar( bar, key, oldgroup=None):
    """ returns a string of symbols for the shapes in the bar
    The current plan is that each note is a symbol and optionally followed by a dot.
    If the note moves outside the fasola group it is preceded by symbols meaning up or down"""
    result = []
    if bar.newSystem(): result += '> ' # add linebreak 
    notes = [n for n in bar if isinstance(n,  musicxml.Note)]
    oldsymbol = None
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
    return r''.join(result), oldgroup # simply concatenate 


        

def braille_shapenote_part( part):
    """ returns string which is transcription of part """
    result=r''
    line = ''
    measures = [m for m in part]
    key = measures[-1].key()
    lastgroup = None # records group of last note in bar, really state for printing up/down at start of next bar
    for measure in part:
        bar, lastgroup = braille_shapenote_bar( measure, key, oldgroup=lastgroup)
        result += bar + ' ' 
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

def braillesong( number, parts, louistable='en-GB-g2.ctb', width=33, sloppyname=True):
    """ produces string with lyrics and selected parts.
    If sloppyname is True it will sniff for t or a extensions to the filename"""
    result = r''
    # now some strange naming conventions mean we have to sniff about a bit here
    if not os.access( lyricsdir+'/'+number+'.htm', os.F_OK):
        if not sloppyname: raise IOError
        basenumber = number
        possible_extensions = ['t','a','ta'] # possible additions to name from most to least preferred order
        for extension in possible_extensions:
            number = basenumber+extension
            if os.access( lyricsdir+'/'+number+'.htm', os.F_OK): break # found one that works
    result+= braillewords( lyricsdir+'/'+number+'.htm', louistable=louistable, width=width)
    for p in parts:
        partstring = '  '+louis.translateString( [louistable], p)+': '
        partstring += braille_shapenote_part( braille_extract_part( musicdir+'/'+number+'.xml', p, foldcase=True))
        result += textwrap.fill( partstring, width=width)+'\n'
    result = '\r'.join([s for s in result.splitlines() if len(s.strip())]) # removing lines with only whitespace
    return result


def braillelist( numbers, parts, device='/dev/usb/lp0'):
    """ brailles shapenote numbers from list"""
    f=open(device, 'w')
    for number in numbers:
        try:
            song =  braillesong( number, parts)
            f.write( song + '\f')
        except IOError:
            print number,' not found'
            continue
    f.close()
    return

