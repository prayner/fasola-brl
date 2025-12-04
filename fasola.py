lyricsroot = "2025-edition/"
lyricsdir=lyricsroot+"lyrics/"
lyricsmeta = lyricsroot+"metadata/"
titlefile = lyricsmeta+"song_titles.tsv"
musicdir='xml'
# some things to do with braille printers
linewidth = 32
# hardcoded path to liblouis directory, only used if needed
LOUISDIR = "/usr/lib/python3/dist-packages"
import os
from glob import glob
import music21
import unicodedata
import codecs
# cannot install louis from conda, hack to get it from system package
try:
    import louis
except ImportError:
    import sys
    sys.path.append(LOUISDIR)
    import louis
    sys.path.remove( LOUISDIR)
import textwrap 


def get_file2number( infile):
    """ creates dictionaries mapping file names to titles and vice versa """
    with open(infile,'r') as f:
        file2number={}
        number2file = {}
        f.readline()
        for line in f.readlines():
            keys = line.split("\t")
            number2file[keys[0]] = keys[1]
            file2number[keys[1]] = keys[0]
    return file2number,number2file

def braillewords( filename, louistable="en-GB-g2.ctb", width=32):
    """ returns brailled string of lyrics from fasola file filename using louistable, separates title and lyrics"""
    with open(filename) as f:
        in_title = f.readline()
        in_title = in_title[2:] # strip off comment
        title = louis.translateString( [louistable],  in_title.lower().strip())
        _ =f.readline() # empty line
        lyrics = ''
        for line in f.readlines():
            linestring = louis.translateString( [louistable],  line.lower().strip())
            lyrics += textwrap.fill( linestring, width=width)+'\n'
    return title, lyrics


        

def brlP(n):
    """returns the braille character for pattern n e.g. grlP(1234) returns the unicode character Braille Pattern dots-1234 or p"""
    return unicodedata.lookup('BRAILLE PATTERN DOTS-'+'{}'.format(n))

# define dictionaries of braille output
# start by defining patterns for major, patterns are different for different note lengths
majorVeryShort = {0:brlP(1234), 2:brlP(234), 4:brlP(123), 5:brlP(1246), 7:brlP(246), 9:brlP(126), 11:brlP(146), None:brlP(1245)} 
majorShort = {0:brlP(12347), 2:brlP(2347), 4:brlP(1237), 5:brlP(12467), 7:brlP(2467), 9:brlP(1267), 11:brlP(1467), None:brlP(12457)} 
majorLong = {0:brlP(12348), 2:brlP(2348), 4:brlP(1238), 5:brlP(12468), 7:brlP(2468), 9:brlP(1268), 11:brlP(1468), None:brlP(12458)} 
majorVeryLong = {0:brlP(123478), 2:brlP(23478), 4:brlP(12378), 5:brlP(124678), 7:brlP(24678), 9:brlP(12678), 11:brlP(14678), None:brlP(124578)}
# now set up the minor patterns from the major ones, noting that note numbers are different
minorVeryShort = {}
minorShort = {}
minorLong = {}
minorVeryLong = {}
# tuples have first minor number then corresponding major number
for t in [(0, 4), (2, 11), (3, 0), (5, 2), (7, 9), (8, 5), (10, 7), (None, None)]:
    minorVeryShort[t[0]] = majorVeryShort[t[1]]
    minorShort[t[0]] = majorShort[t[1]]
    minorLong[t[0]] = majorLong[t[1]] 
    minorVeryLong[t[0]] = majorVeryLong[t[1]]


# now create dictionaries for each mode keyed by length
majorDict = {'veryShort':majorVeryShort, 'short':majorShort, 'long':majorLong, 'veryLong':majorVeryLong}
minorDict = {'veryShort':minorVeryShort, 'short':minorShort, 'long':minorLong, 'veryLong':minorVeryLong}

symbolDict={'major':majorDict, 'minor':minorDict}
dot = brlP(3)
unknown = brlP(3456)
up = brlP(45)
down = brlP(68)
known_durations = [0.5, 1.0, 2.0, 4.0]


def tonicMIDIpitch(key):
    """ returns the MIDIpitch of the tonic note in the key with the integer value "key" """
    return key.tonic.midi

def octaveInKey( note, key):
    """ returns the octave for the key, i.e only changes at tonic not c"""
    if isinstance(note, music21.note.Rest): return None
    tonic = tonicMIDIpitch( key) % 12 # key in range(0,12)
    note_number = note.pitch.midi
    note_in_key = note_number - tonic
    return  note_in_key // 12
def dictByLength( note):
    """ select correct dictionary for this notelength
     we have four dictionaries of symbols depending on note length, now choose the right one"""
    duration = note.duration.quarterLength
    if (duration < known_durations[0]) | (duration >= known_durations[-1]): return "veryLong"
    elif (duration >= known_durations[0]) & (duration < known_durations[1]): return  "veryShort"
    elif (duration >= known_durations[1]) & (duration < known_durations[2]): return "short"
    else: return "long"


def note2symbol(note, key):
    """ returns the braille symbol for the given note in the given key,
    the octave relative to tonic  group for the note"""
    if isinstance(note, music21.note.Rest):
        step = None
    else:
        note_number = note.pitch.midi
        step = (note_number - tonicMIDIpitch( key)) % 12
    try: return symbolDict[key.mode][dictByLength( note)][ step], octaveInKey( note, key)
    except KeyError: return unknown, octaveInKey( note, key)

def brailleTimeSignature( sig): return brlP(3456)+sig.ratioString+' '
        


def braille_shapenote_bar( bar, key, oldOctave=None, showSplits=None):
    """ returns a string of symbols for the shapes in the bar
    The current plan is that each note is a symbol and optionally followed by a dot.
    If the note moves outside the octave it is preceded by symbols meaning up or down
    showSplits determines whether chords are listed in full or just the top note"""
    result = u''
    if len(bar.getElementsByClass('SystemLayout')) > 0: result +='\n' # new line in print so newline in braille
    for e in bar:
        if isinstance(e, music21.bar.Repeat):
            if e.direction == 'start': result+=brlP(238)+brlP(3678)
            elif e.direction == 'end': result += brlP(3678)+brlP(567)
        if isinstance(e, music21.meter.TimeSignature): result += brailleTimeSignature(e)
        if isinstance(e, music21.chord.Chord):
            if showSplits is not None:
                result+=brlP(12378)
                # make list of notes then braille using existing machinery
                chordNotes = [music21.note.Note(p, duration=e.duration) for p in e.pitches]
                for note in chordNotes:
                    symbol, octave = note2symbol( note, key)
                    if (oldOctave is not None) and (note.pitch is not None):
                        if octave == oldOctave +1: result += up
                        elif octave == oldOctave -1: result +=  down
                    result += symbol
                    if (note.duration.quarterLength not in known_durations) & (note.duration.quarterLength > 0.5): result += dot # not very precise but gives warning it's nonstandard length
                    if octave is not None: oldOctave = octave
                result += brlP(45678)
            else:
                topNote = sorted( e.pitches)[-1] # highest note in chord
                note = music21.note.Note(topNote, duration=e.duration)
                symbol, octave = note2symbol( note, key)
                if (oldOctave is not None) and (note.pitch is not None):
                    if octave == oldOctave +1: result += up
                    elif octave == oldOctave -1: result +=  down
                result += symbol
                if (note.duration.quarterLength not in known_durations) & (note.duration.quarterLength > 0.5): result += dot # not very precise but gives warning it's nonstandard length
                if octave is not None: oldOctave = octave
        if isinstance(e, (music21.note.Note, music21.note.Rest)):
            symbol, octave = note2symbol( e, key)
            if (oldOctave is not None) and (isinstance(e, music21.note.Note)):
                if octave == oldOctave +1: result += up
                elif octave == oldOctave -1: result += down
            result += symbol
            if (e.duration.quarterLength not in known_durations) & (e.duration.quarterLength > 0.5): result +=  dot # not very precise but gives warning it's nonstandard length
            if octave is not None: oldOctave = octave
    return result, oldOctave # simply concatenate 


        

def braille_shapenote_part( part, key=None):
    """ returns string which is transcription of part. first braille it then wordwrap each line separately """
    unfilled =u''
    line = u''
    measures = part.recurse().getElementsByClass('Measure')
    if key is None: key = list(part.recurse(classFilter=('Key')))[0]
    lastOctave = None # records group of last note in bar, really state for printing up/down at start of next bar
    for measure in measures:
        bar, lastOctave = braille_shapenote_bar( measure, key, oldOctave=lastOctave)
        unfilled += bar + ' '
    linelist = []
    for line in unfilled.split('\n'): linelist.append(textwrap.fill( line, width=32)+'\n')
    return ''.join(linelist)


def braille_extract_part( filename, partname, foldcase=False):
    """ extracts a part with name partname from a musicxml file filename,
    if foldcase is True the name match is case insensitive"""
    try: piece = music21.converter.parse( filename)
    except: raise IndexError
    if foldcase: copyname = partname.lower()
    else: copyname = partname
    try: return piece.parts[ copyname]
    except KeyError:
        print ('braille_extract_part, cannot find part named ',partname)
        return None

def braillesong( number, parts, louistable='en-GB-g2.ctb', width=32, sloppyname=True):
    """ produces string with lyrics and selected parts.
    If sloppyname is True it will sniff for extensions to the filename"""
    # now some strange naming conventions mean we have to sniff about a bit here
    copynumber = number
    if not os.access( lyricsdir+number, os.F_OK):
        if not sloppyname: raise IOError
        possible_extensions = ['t','a','ta'] # possible additions to name from most to least preferred order
        for extension in possible_extensions:
            copynumber = number+extension
            if os.access( lyricsdir+copynumber, os.F_OK): break # found one that works
    title, lyrics = braillewords( lyricsdir+copynumber, louistable=louistable, width=width)
    result = title[:-1]
    # now we need to play the same game with the music
    copynumber = number
    if not os.access(musicdir+'/'+copynumber+'.xml', os.F_OK):
        if not sloppyname: raise IOError
        possible_extensions = ['t','a','ta'] # possible additions to name from most to least preferred order
        for extension in possible_extensions:
            copynumber = number+extension
            if os.access( musicdir+'/'+copynumber+'.xml', os.F_OK): break # found one that works
    
    musicFile = musicdir+'/'+copynumber+'.xml'
    try:
        key=music21.converter.parse( musicFile).analyze('key')
        result +=' '+str(key)+'\n'
    except music21.converter.ConverterException:
        print ('braillesong, problem with music for ',number)
        return result+lyrics
    for p in parts:
        partstring = '  '+louis.translateString( [louistable], p)+':\n'
        try: partstring += braille_shapenote_part( braille_extract_part( musicFile, p, foldcase=True), key=key)
        except IndexError:
            print ('braillesong, problem with',number)
            continue
        result += partstring
    result += lyrics
    result = '\n'.join([s for s in result.splitlines() if len(s.strip())]) # removing lines with only whitespace
    return result


def braillelist( numbers, parts, device='/dev/usb/lp0'):
    """ brailles shapenote numbers from list"""
    f=codecs.open(device, 'w',encoding='utf-8')
    for number in numbers:
        print (number)
        try:
            song =  braillesong( number, parts)
            f.write( song)
        except IOError:
            print (number,' not found')
            continue
    f.close()
    return

def extract_numbers( filename):
    """ returns a set of strings which are words containing a digit from the filename """
    import re
    f = open( filename, 'r')
    # now return the words with punctuation removed and lower case
    words = re.sub('[.,;]', ' ', f.read()).lower().split()
    f.close()
    return [w for w in words if re.search('\d', w)]

def brailleAll(indir, outdir, louistable="en-GB-g2.ctb",):
    file2number,_ = get_file2number( titlefile)
    for infile in file2number.keys():
        inpath = lyricsdir+infile+'.txt'
        title, lyrics = braillewords( inpath)
#        outname = os.path.basename(infile).replace('.txt','')
        outfile = outdir + file2number[infile]
        
        with open(outfile,'w') as outf:
            outf.write(louis.translateString( [louistable],  file2number[infile]))
            outf.write(' ')
            outf.write( title)
            outf.write('\n')
            outf.write(lyrics)
            outf.write('\n')
            outf.close()
    return

