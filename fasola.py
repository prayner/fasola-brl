lyricsroot = "2025-edition/"
lyricsdir=lyricsroot+"lyrics/"
lyricsmeta = lyricsroot+"metadata/"
titlefile = lyricsmeta+"song_titles.tsv"
musicdir='/home/peter/nonwork/fasola/2025-music/MusicXML - Sacred Harp 2025/'
tmpdir = '/tmp/'
transform_file='transform.xslt'

# some things to do with braille printers
linewidth = 32
# hardcoded path to liblouis directory, only used if needed
LOUISDIR = "/usr/lib/python3/dist-packages"
import os
import glob
import music21
import unicodedata
import codecs
import subprocess

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
        try:
            part = input_part.expandRepeats()
        except:
            part = input_part
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


def extract_part( piece, partname, foldcase=False):
    """ extracts a part with name partname from a music21.stream.Score objectpiece,
    if foldcase is True the name match is case insensitive"""
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
    piece = music21.converter.parse( music_file, forceSource=True)
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
    tmpfile = tmpdir+'fasola_tmp.musicxml'
    preprocess_shapenote_file(music_file, tmpfile, transform_file)
    piece = music21.converter.parse( tmpfile, forceSource=True)
    canonicalize_shapenote_piece( piece)
    for p in parts:
        partstring = '  '+louis.translateString( [louistable], p)+':\n'
        partstring += braille_shapenote_part(
            extract_part(piece,p),
            key=key, expand_repeats=True)
        result += partstring
        result+='\n\n'
    result += lyrics
    #result = '\n'.join([s for s in result.splitlines() if len(s.strip())]) # removing lines with only whitespace
    return result

def brailleList(song_list, lyrics_dir, title_file, music_dir, parts, outdir,
               louistable="en-GB-g2.ctb", bad_numbers=None,
               transform_file='transform.xslt', debug=False):
    if not outdir.endswith('/'):
        outdir +='/'
    file2number,_ = get_lyricsfile2number( title_file)
    if bad_numbers is not None:
        for b in bad_numbers:
            file2number.pop(b)
    number2music_file = get_musicfile2number( musicdir)
    problems=[]
    for lyrics_file in song_list:
        try:
            lyrics_path = lyrics_dir+lyrics_file+'.txt'
            title, lyrics = braillewords( lyrics_path)
            music_path = number2music_file[lyrics_file]
            outfile = outdir + file2number[lyrics_file]
            tmpfile = temp_file_name('/tmp/')
            preprocess_shapenote_file( music_path, tmpfile, transform_file)
            with open(outfile,'w') as outf:
                outf.write(louis.translateString( [louistable],  file2number[lyrics_file]))
                outf.write(' ')
                outf.write( braillesong(lyrics_path, tmpfile, parts))
        except:
            if debug:
                raise
            else:
                problems.append(lyrics_file)
    return problems

def brailleAll(lyrics_dir, title_file, music_dir, parts, outdir,
               louistable="en-GB-g2.ctb", bad_numbers=None,
               transform_file='transform.xslt', debug=False):
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
            tmpfile = temp_file_name('/tmp/')
            preprocess_shapenote_file( music_path, tmpfile, transform_file)
            with open(outfile,'w') as outf:
                outf.write(louis.translateString( [louistable],  file2number[lyrics_file]))
                outf.write(' ')
                outf.write( braillesong(lyrics_path, tmpfile, parts))
        except:
            if debug:
                raise
            else:
                problems.append(lyrics_file)
    return problems

def temp_file_name(tmpdir): return tmpdir+'fasola_tmp.musicxml'

def preprocess_shapenote_file(infile, outfile, transform_file):
    command_list = ['xsltproc', '--novalid']
    command_list.append('-o')
    command_list.append(outfile)
    command_list.append(transform_file)
    command_list.append(infile)
    subprocess.run(command_list)
def canonicalize_shapenote_piece( piece):
    """ at the moment only fixing weird measure number in pickup bars """
    for p in piece.parts:
        canonicalize_shapenote_part( p)

def canonicalize_shapenote_part(part):
    """fixing weird measure numbers for partial bars and weird final repeat.
       note it modifies in place"""
    measures =part.recurse().getElementsByClass(music21.stream.Measure)
    measure_suffixes = set([m.numberSuffix for m in measures])
    if measure_suffixes != set([None]): # need to alter numbers and suffixes
        for i,m in enumerate(measures):
            if m.numberSuffix is not None:
                m.number = measures[1].number -1 if i == 0 else \
                measures[i-1].number +1
                m.numberSuffix = None
    # now delete repeat from final bar if it's there
    if isinstance(part.measure(-1).elements[0], music21.bar.Repeat):
        part.measure(-1).remove(part.measure(-1).elements[0])
