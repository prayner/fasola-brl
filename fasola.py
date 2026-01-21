lyricsroot = "2025-edition/"
lyricsdir=lyricsroot+"lyrics/"
lyricsmeta = lyricsroot+"metadata/"
titlefile = lyricsmeta+"song_titles.tsv"
musicdir='/home/peter/nonwork/fasola/2025-music/MusicXML - Sacred Harp 2025/'
tmpdir = '/tmp/'
# some things to do with braille printers
linewidth = 32
# hardcoded path to liblouis directory, only used if needed
LOUISDIR = "/usr/lib/python3/dist-packages"
import os
import glob
import subprocess
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

def get_musicfile2number( musicdir):
    """ returns dictionary mapping canonical song numbers (using decimal
        point notation) to music file paths"""
    number2file = {}
    if musicdir.endswith("/"):
        musicpath = musicdir
    else:
        musicpath = musicdir+"/"
    allfiles = glob.glob(musicpath + "*musicxml")
    for f in allfiles:
        filename = os.path.basename(f)
        song_number = filename.split("-")[0]
        song_number = song_number.lstrip("0") 
        number2file[song_number] = f
    return number2file


def get_lyricsfile2number( infile):
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
tie = brlP(36)
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
    # first check if it's a new system whereupon we need a new line
    layouts = bar.recurse().getElementsByClass('layout.SystemLayout')
    if len(layouts) > 0:
        if layouts[0].isNew:
            result += '\n'
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
            if e.tie is not None and e.tie != music21.tie.Tie('stop'):
                result +=tie
        if isinstance(e, (music21.note.Note, music21.note.Rest)):
            symbol, octave = note2symbol( e, key)
            if (oldOctave is not None) and (isinstance(e, music21.note.Note)):
                if octave == oldOctave +1: result += up
                elif octave == oldOctave -1: result += down
            result += symbol
            if (e.duration.quarterLength not in known_durations) & (e.duration.quarterLength > 0.5): result +=  dot # not very precise but gives warning it's nonstandard length
            if octave is not None: oldOctave = octave
            if e.tie is not None and e.tie != music21.tie.Tie('stop'):
                result += tie
    return result, oldOctave # simply concatenate 


        

def braille_shapenote_part( input_part, key=None, expand_repeats=False):
    """ returns string which is transcription of part. first braille it then wordwrap each line separately """
    if expand_repeats:
        part = input_part.expandRepeats()
        # remove duplicate time signatures if they don't change
        sigs=list(part.recurse().getElementsByClass(
            music21.meter.TimeSignature))
        if len(sigs) > 1:
            current_sig = sigs[0]
            for sig in sigs[1:]:
                if sig == current_sig:
                    part.remove(sig,recurse=True)
                current_sig = sig
    else:
        part = input_part
                
    unfilled =u''
    line = u''
    measures = part.recurse().getElementsByClass('Measure')
    if key is None: key = part.analyze('key')
    unfilled += str(key)+'\n'
    lastOctave = None # records group of last note in bar, really state for printing up/down at start of next bar
    for measure in measures:
        bar, lastOctave = braille_shapenote_bar( measure, key, oldOctave=lastOctave)
        if (measure.number == 0 or measure.number ==1):
            unfilled += bar
        else:
            if bar.startswith('\n'):
                unfilled += bar
            else:
                unfilled += ' '+bar
    return unfilled


def braille_extract_part( filename, partname, foldcase=False):
    """ extracts a part with name partname from a musicxml file filename,
    if foldcase is True the name match is case insensitive"""
    try: piece = music21.converter.parse( filename)
    except: raise IndexError
    if foldcase: copyname = partname.lower()
    else: copyname = partname
    try: return piece.parts[ copyname]
    except KeyError:
        # create fallback dictionary depending on number of parts and try it by number
        if len(piece.parts) == 4:
            fallback_dict = {'treble':0, 'alto':1, 'tenor':2, 'bass':3}
        else:
            fallback_dict = {'treble':0, 'tenor':1, 'bass':2}
        part_number = fallback_dict[partname.lower()]
        return piece.parts[part_number]

def key_from_file( music_file):
    """ there are two ways of getting this and they don't always agree.
       The musicxml lists every mode as major though it's sharp count is correct.
       the music21.analyze method occasionally gets it wrong.
       our heuristic is if they agree we return that.
       if they don't we take the number of sharps from the read key and mode from the analyzed"""
    piece = music21.converter.parse( music_file)
    analyzed_key = piece.analyze('key')
    read_key = list(piece.recurse().getElementsByClass(music21.key.Key))[0]
    if read_key == analyzed_key:
        result = read_key
    else:
        if analyzed_key.mode == read_key.mode:
            print(f"key problem in music file {music_file:s}")
            result = read_key
        else:
            result = read_key.relative
    return result
        
def braillesong( lyrics_file, music_file, parts, louistable='en-GB-g2.ctb', width=32,):
    """ produces string with lyrics and selected parts."""
    title, lyrics = braillewords( lyrics_file, louistable=louistable, width=width)
    result = title
    key = key_from_file( music_file)
    for p in parts:
        partstring = '  '+louis.translateString( [louistable], p)+':\n'
        partstring += braille_shapenote_part(
            braille_extract_part( music_file,p,foldcase=True),
            key=key, expand_repeats=True)
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

def brailleAll(lyrics_dir, title_file, music_dir, parts, outdir, louistable="en-GB-g2.ctb", bad_numbers=None):
    if not outdir.endswith('/'):
        outdir +='/'
    file2number,_ = get_lyricsfile2number( title_file)
    if bad_numbers is not None:
        for b in bad_numbers:
            file2number.pop(b)
    number2music_file = get_musicfile2number( musicdir)
    problems=[]
    for lyrics_file in file2number.keys():
        try:
            lyrics_path = lyrics_dir+lyrics_file+'.txt'
            title, lyrics = braillewords( lyrics_path)
            music_path = number2music_file[lyrics_file]
            outfile = outdir + file2number[lyrics_file]
            
            with open(outfile,'w') as outf:
                outf.write(louis.translateString( [louistable],  file2number[lyrics_file]))
                outf.write(' ')
                outf.write( braillesong(lyrics_path, music_path, parts))
        except:
            problems.append(lyrics_file)
    return problems

def braille_shapenote_line_by_line( filename, part, expand_repeats=False):
    key = key_from_ile(filename)
    input_piece = music21.converter.parse(filename)
    if expand_repeats:
        piece = input_piece.expandRepeats()
        # remove duplicate time signatures if they don't change
        sigs=list(piece.recurse().getElementsByClass(
            music21.meter.TimeSignature))
        if len(sigs) > 1:
            current_sig = sigs[0]
            for sig in sigs[1:]:
                if sig == current_sig:
                    piece.remove(sig,recurse=True)
                current_sig = sig
    else:
        piece = input_piece

    result = u''
    systems = systems_from_stream( piece)
    for verse in range(1, count_verses(piece)+1):
        for system in systems:
            result += braille_shapenote_system( system, part, verse, key=key, )
    return result

def count_verses( stream):
    """ count the number of verses in a stream """
    notes=stream.flatten().getElementsByClass(music21.note.Note)

    nested_lyrics=[n.lyrics for n in notes]
    flattened_lyrics = [l for lyrics in nested_lyrics for l in lyrics]
    numbers = [f.number for f in flattened_lyrics]
    return max(numbers)

def lyrics_by_verse(stream, verse):
    notes=stream.flatten().getElementsByClass(music21.note.Note)
    nested_lyrics=[n.lyrics for n in notes]
    flattened_lyrics = [l for lyrics in nested_lyrics for l in lyrics]
    if verse is None:
        result = flattened_lyrics # select everything
    else:
        result = [f for f in flattened_lyrics if f.number == verse]
    return result

def systems_from_piece( piece):
    result = []
    layout_stream = piece.recurse().getElementsByClass('layout.SystemLayout')
    newsystem_measures = [l.measureNumber for l in layout_stream if l.isNew]
    newsystem_measures = list(set(newsystem_measures)) # unique elements 
    newsystem_measures.insert(0,0) # assume always new system at beginning
    for i in range( len(newsystem_measures)-1): # skipped if newsystem only at beginning
        result.append (piece.measures( newsystem_measures[i], newsystem_measures[i-1]-1))
    result.append(piece.measures(newsystem_measures[-1], None))
    return result

def temp_file_name(tmpdir): return tmpdir+'fasola_tmp.musicxml'

def preprocess_shapenote_file(infile, outfile, transform_file):
    command_list = ['xsltproc', '--novalid']
    command_list.append('-o')
    command_list.append(outfile)
    command_list.append(transform_file)
    command_list.append(infile)
    subprocess.run(command_list)

def systems_from_file( filename, expand_repeats=True):
    piece = music21.converter.parse( filename, forceSource=True)
    if not expand_repeats:
        piece_copy = piece
    else:
        try:
            parts=[p.expandRepeats() for p in piece.parts]
            piece_copy = music21.stream.Score()
            for p in parts:
                piece_copy.append(p)
        except:
            piece_copy = piece # fall back to just copying
    return systems_from_piece(piece_copy)

def find_measure_in_part( measure_index, n_measures_in_part):
    """ measure_index is the string from repeat.Expander.measureMap,
       may have form like "5" or "5a" for repeats"""
    try:
        result = int(measure_index)
    except ValueError:
        result = int(measure_index[0:-1])
    # now deal with bug in repeat.Expander.measureMap for DC etc
    if result > n_measures_in_part:
        result -= n_measures_in_part
    return result


def find_lyrics( piece,
                 part_number,
                 verse_number,
                 measure_number,
                 measure_list=None,
                 n_measures_in_part=None,
                ):
    """ note that measure_number is after repeats have been expanded"""
    part = piece.parts[part_number]
    if measure_list is None:
        measure_list = music21.repeat.Expander(part).measureMap()
    if n_measures_in_part is None:
        n_measures_in_part = len(part.measures(1,None))
    measure_in_part = find_measure_in_part( measure_list[ measure_number],
                                            n_measures_in_part)
    # now the fun starts, first see if there are lyrics in the part itself

def canonicalize_shapenote_piece( piece):
    """ at the moment only fixing weird measure number in pickup bars """
    for p in piece.parts:
        canonicalize_shapenote_part( p)

def canonicalize_shapenote_part(part):
    """ at the moment only fixing weird measure numbers for partial bars.
       note it modifies in place"""
    measures =part.recurse().getElementsByClass(music21.stream.Measure)
    measure_suffixes = set([m.numberSuffix for m in measures])
    if measure_suffixes != set([None]): # need to alter numbers and suffixes
        for i,m in enumerate(measures):
            if m.numberSuffix is not None:
                m.number = measures[1].number -1 if i == 0 else \
                measures[i-1].number +1
                m.numberSuffix = None
