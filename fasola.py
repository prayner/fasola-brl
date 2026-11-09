lyricsroot = "2025-edition/"
lyricsdir=lyricsroot+"lyrics/"
lyricsmeta = lyricsroot+"metadata/"
titlefile = lyricsmeta+"song_titles.tsv"
musicdir='/home/peter/nonwork/fasola/2025-music/MusicXML - Sacred Harp 2025/'
tmpdir = '/tmp/'
transform_file='transform.xslt'
copyright_file = 'copyright.txt'

# some things to do with braille printers
linewidth = 32
# hardcoded path to liblouis directory, only used if needed
LOUISDIR = "/usr/lib/python3/dist-packages"
import os
import glob
import shutil
import re
import music21
import unicodedata
import codecs
import subprocess
import xml.etree.ElementTree as ElementTree
from collections import defaultdict

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
    # songs whose music is named without the .1 or .2 of the lyrics, e.g. 347 for 347.1
    for f in glob.glob(lyricsdir + "*.txt"):
        song_number = os.path.basename(f)[:-len(".txt")]
        if song_number not in number2file and song_number.split(".")[0] in number2file:
            number2file[song_number] = number2file[song_number.split(".")[0]]
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

def brailleTimeSignature( sig): return brlP(3456)+sig.ratioString
        


def braille_shapenote_bar( bar, key, oldOctave=None, showSplits=None, show_time_signature=True, return_pieces=False,
                           show_repeats=True, window=None):
    """ returns a string of symbols for the shapes in the bar
    The current plan is that each note is a symbol and optionally followed by a dot.
    If the note moves outside the octave it is preceded by symbols meaning up or down
    showSplits determines whether chords are listed in full or just the top note
    if return_pieces is True the string is returned as a list of (offset in bar, symbols)
    with one entry per note or rest, so that a bar can be split between lines
    show_repeats False leaves out repeat barlines (e.g. where they are written from elsewhere)
    window (start, end) only includes what is between those offsets in the bar, for a bar
    of which only part is repeated"""
    result = u''
    note_starts = [] # (offset, position in result) for each note, chord or rest
    # first check if it's a new system whereupon we need a new line
    layouts = bar.recurse().getElementsByClass('layout.SystemLayout')
    if len(layouts) > 0:
        if layouts[0].isNew:
            result += '\n'
    for e in bar.flatten():
        if window is not None and not window[0] <= e.offset < window[1]:
            continue
        if isinstance(e, music21.bar.Repeat) and show_repeats:
            if e.direction == 'start': result+=brlP(238)+brlP(3678)
            elif e.direction == 'end': result += brlP(3678)+brlP(567)
        if isinstance(e, music21.meter.TimeSignature) and show_time_signature: result += brailleTimeSignature(e)
        if isinstance(e, (music21.chord.Chord, music21.note.Note, music21.note.Rest)):
            note_starts.append((e.offset, len(result)))
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
    if return_pieces:
        # split at the start of each note; anything before the first note (a repeat sign,
        # time signature) goes with it, anything after the last with that
        if len(note_starts) == 0:
            return [(0.0, result.strip())], oldOctave
        cuts = [0] + [position for _, position in note_starts[1:]] + [len(result)]
        return [(offset, result[cuts[i]:cuts[i+1]].strip()) for i, (offset, _) in enumerate(note_starts)], oldOctave
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
    measures = part.measures(1,None, collect=[], gatherSpanners=False)
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
    if isinstance(partname, int): # got part directly
        return piece.parts[partname]
    else:
        if foldcase:
            copyname = partname.lower()
        else:
            copyname = partname
        part_number = find_part_number(piece, copyname)
        return piece.parts[part_number]

def find_part_number(piece, part_name):
    part_names = [str(p.partName).lower() for p in piece.parts]
    if isinstance(part_name, int):
        part_number = part_name
    elif part_name.lower() in part_names: # parts named in the file, e.g. shenandoah harmony
        part_number = part_names.index(part_name.lower())
    else:
        # create fallback dictionary depending on number of parts and try it by number
        if len(piece.parts) == 4:
            fallback_dict = {'treble':0, 'alto':1, 'tenor':2, 'bass':3}
        else:
            fallback_dict = {'treble':0, 'tenor':1, 'bass':2}
        part_number = fallback_dict[part_name.lower()]
    return part_number

def key_from_file_or_piece( input):
    """ input can either be a file name or a music21.stream.Stream
 there are two ways of getting this and they don't always agree.
       The musicxml lists every mode as major though it's sharp count is correct.
       the music21.analyze method occasionally gets it wrong.
       our heuristic is if they agree we return that.
       if they don't we take the number of sharps from the read key and mode from the analyzed"""
    if not isinstance(input, music21.stream.Stream):
        piece = music21.converter.parse( input, forceSource=True)
    else:
        piece = input
        
    analyzed_key = piece.analyze('key')
    # read key from file, might be Key or KeySignature object
    key_list = list(piece.recurse().getElementsByClass(music21.key.Key))
    if len(key_list) >0:
        read_key = key_list[0]
    else:
        keysig_list = list(piece.recurse().getElementsByClass(music21.key.KeySignature))
        if len(keysig_list) > 0:
            read_key = keysig_list[0].asKey()
        else:
            read_key = None
        
    if read_key is None:
        result = analyzed_key # fall back 
    elif read_key == analyzed_key:
        result = read_key
    elif  analyzed_key.sharps != read_key.sharps: 
        print(f"key problem: read {read_key}, analyzed {analyzed_key}")
        result = read_key
    else:
        result = read_key.relative
    return result
        
def braillesong( lyrics_file, music_file, parts, louistable='en-GB-g2.ctb', width=32,):
    """ produces string with lyrics and selected parts."""
    title, lyrics = braillewords( lyrics_file, louistable=louistable, width=width)
    result = title
    tmpfile = tmpdir+'fasola_tmp.musicxml'
    preprocess_shapenote_file(music_file, tmpfile, transform_file)
    piece = music21.converter.parse( tmpfile, forceSource=True)
    canonicalize_shapenote_piece( piece)
    key = key_from_file_or_piece( piece)
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
    shutil.copy( copyright_file, outdir)
    file2number,_ = get_lyricsfile2number( title_file)
    if bad_numbers is not None:
        for b in bad_numbers:
            file2number.pop(b)
    number2music_file = get_musicfile2number( music_dir)
    problems=[]
    for lyrics_file in song_list:
        try:
            lyrics_path = lyrics_dir+lyrics_file+'.txt'
            title, lyrics = braillewords( lyrics_path)
            music_path = number2music_file[lyrics_file]
            outfile = outdir + file2number[lyrics_file]
            with open(outfile,'w') as outf:
                outf.write(louis.translateString( [louistable],  file2number[lyrics_file]))
                outf.write(' ')
                outf.write( braillesong_general(lyrics_path, music_path, parts, louistable=louistable,
                                                tmp_file=temp_file_name(tmpdir), transform_file=transform_file))
        except:
            if debug:
                raise
            else:
                problems.append(lyrics_file)
    return problems

def brailleAll(lyrics_dir, title_file, music_dir, parts, outdir,
               louistable="en-GB-g2.ctb", bad_numbers=None,
               transform_file='transform.xslt', debug=False):
    file2number,_ = get_lyricsfile2number( title_file)
    if bad_numbers is not None:
        for b in bad_numbers:
            file2number.pop(b)
    problems = brailleList(file2number.keys(), lyrics_dir, title_file, music_dir, parts, outdir,
               louistable=louistable, bad_numbers=bad_numbers,
                           transform_file=transform_file, debug=debug)
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


def count_verses( stream):
    """ count the number of verses in a stream. uses heuristic that a lyric starting with number followed by dot is a verse number """
    lyric_string = music21.text.assembleAllLyrics( stream)
    digit_list = re.findall(r'\d', lyric_string)
    if len(digit_list) == 0:
        return 1
    else:
        return max([int(d) for d in digit_list])


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
                 number_of_verses=None,
                 simple_multi_verse = None,
                ):
    """ note that measure_number is after repeats have been expanded"""
    if simple_multi_verse is None:
        simple_multi_verse = is_simple_multi_verse(piece)
    part = piece.parts[part_number]
    if measure_list is None:
        measure_list = music21.repeat.Expander(part).measureMap()
    if n_measures_in_part is None:
        n_measures_in_part = len(part.measures(1,None, collect=[], gatherSpanners=False))
    if number_of_verses is None:
        number_of_verses = count_verses(piece)
    measure_in_part = find_measure_in_part( measure_list[ measure_number],
                                            n_measures_in_part)
    found_measure = part.measure(measure_in_part)
    if contains_only_rests(found_measure):
        return [] # no lyrics
    if simple_multi_verse:
        part_has_text =[len(extract_lyrics(p)) > 0 for p in piece.parts]
        part_lyric_dict={}
        verse = 1
        for i in range(len(piece.parts)):
            measure_lyrics = extract_lyrics(piece.parts[i].measure(measure_in_part))
            if part_has_text[i]:
                part_lyric_dict[verse] = measure_lyrics
                verse += 1
        return part_lyric_dict[verse_number]
    else:
        measure_lyrics = extract_lyrics(found_measure)
        if len(measure_lyrics) > 0: # we have lyrics explicitly for this part
            return measure_lyrics
        else: # we need to look at different parts
            part_lyric_dict={}
            key_lyric_dict = 1
            for i in range(len(piece.parts)):
                measure_lyrics = extract_lyrics(piece.parts[i].measure(measure_in_part))
                if len(measure_lyrics) > 0:
                    part_lyric_dict[key_lyric_dict] = measure_lyrics
                    key_lyric_dict += 1
            if len(part_lyric_dict) == 0:
                return [] # no lyrics
            if number_of_verses == 1 or len(part_lyric_dict) == 1: # words attached to only one other part
                return part_lyric_dict[1]


def flatten_lyric_text( lyric_list):
    return [l.text for l in lyric_list if l is not None]


def contains_only_rests( stream):
    result = True
    for n in stream.flatten().notesAndRests:
        if not isinstance(n, music21.note.Rest):
            result = False
    return result

def is_simple_multi_verse( stream):
    result = True
    part_lyrics = [music21.text.assembleAllLyrics( p) for p in stream.parts]
    for part_lyric in part_lyrics:
        if len(part_lyric) > 0 and re.match('^\d\.', part_lyric) is None:
            result = False
    return result

def extract_lyrics( stream, line_number=1):
    ''' based on music21.text.assembleLyrics but with some of its perverse intelligence removed'''
    note_stream = stream.flatten().notesAndRests
    result = []
    for n in note_stream:
        try:
            lyric = n.lyrics[line_number -1]
        except IndexError:
            continue
        if lyric.text is not None:
            result.append(lyric.text)
    return result

def join_sections(sections):
    """ removes lines with only whitespace within each section and separates
    the non-empty sections by a blank line """
    sections = ['\n'.join([s for s in section.splitlines() if len(s.strip())]) for section in sections]
    return '\n\n'.join([s for s in sections if len(s)])

def word_key( word):
    """ the letters of a word, for comparing words regardless of case and punctuation """
    return re.sub('[^a-z]', '', word.lower())


def braillesong_line_by_line( lyrics_file, music_file, parts,
                              louistable='en-GB-g2.ctb',
                              width=32,
                              tmp_file='./fasola_tmp.musicxml',
                              transform_file='transform.xslt',
                              expand_repeats=False,
                             ):
    """ produces string with lyrics and selected parts."""
    title, lyrics = braillewords( lyrics_file, louistable=louistable, width=width)
    result = title
    preprocess_shapenote_file(music_file, tmp_file, transform_file)
    piece = music21.converter.parse(tmp_file,forceSource=True)
    canonicalize_shapenote_piece(piece, )
    key = key_from_file_or_piece( piece)
    line_by_lines = u''
    for p in parts:
        part_number = find_part_number(piece, p)
        partstring = '  '+louis.translateString( [louistable], p)+':\n'
        partstring += braille_shapenote_part(
            piece.parts[part_number],
            key=key, expand_repeats=expand_repeats)
        result += partstring
        result+='\n'
        try:
            line_by_line =braille_shapenote_part_line_by_line(
                piece,part_number,key,bars_per_line=4)
            if len(line_by_line) > 0:
                print(f'success with {title}')
            line_by_lines += line_by_line
        except:
            pass
    # music, lyrics then each verse line by line, separated by blank lines
    return join_sections([result, lyrics] + line_by_lines.split('\n\n'))

def braille_shapenote_part_line_by_line( piece, part_name, key, bars_per_line):
    """ rough approach is to only do this for simple_multi_verse,
       loop over all verses, then for each measure in expanded measuremap
       find the measure, braille it and attach the relevant lyrics.
       generate a separate string for each verse and append them."""
    result = u''
    if not is_simple_multi_verse(piece):
        return result
    part = extract_part(piece, part_name)
    measure_list = music21.repeat.Expander(part).measureMap(returnType='measureNumber')
    n_measures_in_part = len(part.measures(1,None, collect=[], gatherSpanners=False))
    number_of_verses = count_verses(piece)
    for verse in range(number_of_verses):
        lyric_string = u''
        music_string = u''
        lastOctave=None
        for m in range(len(measure_list)):
            if m % bars_per_line == 0:
                result += lyric_string.rstrip()
                result += music_string.rstrip()
                lyric_string = u'\n'
                music_string = u'\n'
            measure_lyric_list = find_lyrics( piece, 3, verse+1, m,
                                              measure_list=measure_list,
                                              n_measures_in_part=n_measures_in_part,
                 number_of_verses=number_of_verses,
                 simple_multi_verse = True)
            measure_lyric_string = ' '.join(measure_lyric_list)
            lyric_string += measure_lyric_string + ' '
            measure_in_part = find_measure_in_part( measure_list[m],
                                                    n_measures_in_part)
            found_measure = part.measure(measure_in_part)
            bar, lastOctave = braille_shapenote_bar( found_measure, key,
                                                     oldOctave=lastOctave)
            music_string +=bar + ' '
        result += lyric_string.rstrip()
        result += music_string.rstrip()
        result+='\n\n'
    return result


# ---------------------------------------------------------------------------
# Shenandoah Harmony: music converted from the LilyPond sources by
# shenandoah-harmony/WholeBook/converter (python check_book.py --out ../MusicXML).
# The lyrics exist only in those files. Repeats are written as repeat barlines
# and endings, lyric numbers are verse numbers, and parts are named
# treble/alto/tenor/bass. Songs either have lyric syllables attached to notes,
# or have their verses only as text (markup) under the first or last note of
# each phrase. In both cases the words for a verse are often printed under a
# different part from the one being transcribed.
shenandoah_musicdir = '/home/peter/nonwork/fasola/shenandoah-harmony/WholeBook/MusicXML/'
navigation_words = {'d.c.', 'd.s.', 'fine', 'd.c. al fine', 'd.s. al fine'}


def expanded_measures( part):
    """ returns list of (expanded measure, original measure) pairs, following
    repeats, endings and D.C./D.S. as music21 expands them """
    originals = list(part.getElementsByClass(music21.stream.Measure))
    for i, m in enumerate(originals):
        m.editorial.fasola_index = i
    try:
        expanded = part.expandRepeats()
    except Exception:
        expanded = part
    measures = list(expanded.getElementsByClass(music21.stream.Measure))
    # remove duplicate time signatures if they don't change
    current_sig = None
    for m in measures:
        for sig in list(m.getElementsByClass(music21.meter.TimeSignature)):
            if current_sig is not None and sig.ratioString == current_sig.ratioString:
                m.remove(sig)
            current_sig = sig
    return [(m, originals[m.editorial.get('fasola_index', i)]) for i, m in enumerate(measures)]


def measure_span( measure, part):
    """ start and end of a measure in quarter lengths from the start of the part, repeats as written """
    start = measure.getOffsetBySite(part)
    return start, start + measure.highestTime


def sounding_spans( part):
    """ (onset, end) of every note or chord in the part, repeats as written """
    return [(n.offset, n.offset + n.quarterLength) for n in part.flatten().notes]


def part_syllables( part):
    """ list of (onset, verse, text, syllabic) for the lyrics attached to the part,
    keeping the first lyric of each verse on a note """
    result = []
    for n in part.flatten().notes:
        verses = set()
        for l in n.lyrics:
            if l.text and l.number not in verses:
                verses.add(l.number)
                result.append((n.offset, l.number, l.text, l.syllabic))
    return result


def syllables_to_text( syllables):
    """ joins syllables into words, e.g. Ho-ly Spir-it """
    text = ''
    for _, _, syllable, syllabic in syllables:
        text += syllable + ('-' if syllabic in ('begin', 'middle') else ' ')
    return text.strip()


def verse_with_words( all_syllables, verse, start, end):
    """ verse if any part has words for it between start and end, else the first verse
    that does: words printed once (e.g. a chorus) are sung in every verse """
    verses = sorted(set(s[1] for syllables in all_syllables for s in syllables if start <= s[0] < end))
    if verse in verses or len(verses) == 0:
        return verse
    return verses[0]


def measure_syllables( all_syllables, all_spans, part_number, verse, start, end):
    """ the syllables of verse sung by part part_number between start and end.
    if the part has no words of its own here, they are borrowed from the part
    whose syllables best match its rhythm, keeping those sung while it sounds """
    verse = verse_with_words(all_syllables, verse, start, end)
    def in_window(s):
        return s[1] == verse and start <= s[0] < end
    own = [s for s in all_syllables[part_number] if in_window(s)]
    if len(own) > 0:
        return own
    spans = [(a, b) for a, b in all_spans[part_number] if a < end and b > start]
    if len(spans) == 0:
        return [] # resting
    onsets = set(a for a, _ in spans)
    best_key, best = None, []
    for q, syllables in enumerate(all_syllables):
        if q == part_number:
            continue
        sung = [s for s in syllables if in_window(s) and any(a <= s[0] < b for a, b in spans)]
        if len(sung) == 0:
            continue
        key = (sum(1 for s in sung if s[0] in onsets), len(sung))
        if best_key is None or key > best_key:
            best_key, best = key, sung
    return best


def clean_markup_text( text, join_syllables=False):
    """ tidies the spacing used to place markup lyrics under notes, e.g. 'ach - ing  void' -> 'ach-ing void',
    or with join_syllables 'aching void' """
    text = text.replace('__', ' ')
    text = re.sub(r'\s*-\s*-?\s*', '' if join_syllables else '-', text) if ' - ' in text or '- ' in text else text
    return ' '.join(text.split())


def markup_phrases( piece):
    """ returns {verse: {part_number: phrases}} for verses written as text under the
    notes, where phrases is a sorted list of [start, end, text] in quarter lengths.
    The verse of a text comes from a leading "2." (which carries on to later texts
    in the same part and line of a text column), else from the same text (ignoring
    spacing and line breaks) with a known verse, else each such part's texts are
    taken as a further verse.
    A right-aligned text ends at the note it is attached to, others start there and
    run to the next text of the verse. Each phrase also has a fourth entry, the text
    with its syllables joined into words (for the lyrics) """
    tracks = {} # (part number, column line) -> list of [anchor, end of anchor note, right aligned, text, verse]
    for p, part in enumerate(piece.parts):
        note_ends = {n.offset: n.offset + n.quarterLength for n in part.flatten().notesAndRests}
        for t in part.recurse().getElementsByClass(music21.expressions.TextExpression):
            anchor = t.getOffsetInHierarchy(part)
            # lines of a text column are verses if labelled, or if that column line
            # had a verse before; otherwise they continue the line above
            lines = [] # (text, text with syllables joined into words)
            for line_number, line in enumerate(t.content.split('\n')):
                text, joined = clean_markup_text(line), clean_markup_text(line, join_syllables=True)
                if len(lines) > 0 and not re.match(r'\d+\.', text) and (p, len(lines)) not in tracks:
                    lines[-1] = ((lines[-1][0] + ' ' + text).strip(), (lines[-1][1] + ' ' + joined).strip())
                else:
                    lines.append((text, joined))
            for line_number, (text, joined) in enumerate(lines):
                if not re.search('[A-Za-z]{2}', text) or text.lower() in navigation_words:
                    continue
                label = re.match(r'(\d+)\.\s*', text)
                track = tracks.setdefault((p, line_number), [])
                verse = int(label.group(1)) if label else (track[-1][4] if track else None)
                if label:
                    text = text[label.end():]
                    joined = re.sub(r'^\d+\.\s*', '', joined)
                track.append([anchor, note_ends.get(anchor, anchor), t.style.justify == 'right', text, verse, joined])
    def letters(text):
        return re.sub('[^a-z]', '', text.lower())
    known = {letters(entry[3]): entry[4] for track in tracks.values() for entry in track if entry[4] is not None}
    def known_verse(text):
        """ verse of a known text that is the same as text, or contains it or is part of it """
        text = letters(text)
        if text in known:
            return known[text]
        return next((v for k, v in known.items() if min(len(k), len(text)) >= 10 and (k in text or text in k)), None)
    next_verse = max(list(known.values()) + [0]) + 1
    for key in sorted(tracks):
        unlabelled = [e for e in tracks[key] if e[4] is None]
        if len(unlabelled) == 0:
            continue
        matches = [known_verse(e[3]) for e in unlabelled if known_verse(e[3]) is not None]
        if len(matches) > 0:
            verse = max(set(matches), key=matches.count)
        else:
            verse, next_verse = next_verse, next_verse + 1
        for e in unlabelled:
            e[4] = verse
            known.setdefault(letters(e[3]), verse)
    piece_end = piece.highestTime
    # a verse's last phrase, when left aligned, ends where the next text anywhere begins
    all_starts = sorted(set(e[0] for track in tracks.values() for e in track if not e[2]))
    result = {}
    for (p, _), track in sorted(tracks.items()):
        for entry in sorted(track, key=lambda e: e[0]):
            result.setdefault(entry[4], {}).setdefault(p, []).append(entry)
    for verse in result:
        for p, entries in result[verse].items():
            entries.sort(key=lambda e: e[0])
            phrases = [[e[0] if not e[2] else None, e[1] if e[2] else None, e[3], e[5]] for e in entries]
            for i, phrase in enumerate(phrases):
                if phrase[0] is None: # right aligned: starts where the last phrase ended
                    if i == 0:
                        phrase[0] = 0
                    elif phrases[i-1][1] is not None:
                        phrase[0] = phrases[i-1][1]
                    else: # boundary not marked, split the difference
                        phrase[0] = (phrases[i-1][0] + phrase[1]) / 2
                if i > 0 and phrases[i-1][1] is None:
                    phrases[i-1][1] = phrase[0]
            if phrases[-1][1] is None:
                phrases[-1][1] = next((t for t in all_starts if t > phrases[-1][0]), piece_end)
            result[verse][p] = phrases
    return result


def phrase_at( phrases_by_verse, verse, part_number, time):
    """ (verse, part number, index) of the phrase sung at time: the part's own phrase of
    verse, else that of another part. If no part has words for verse there, the first
    verse that does: words printed once (e.g. a chorus) are sung in every verse """
    for v in [verse] + sorted(phrases_by_verse):
        by_part = phrases_by_verse.get(v, {})
        for q in [part_number] + sorted(by_part):
            index = next((i for i, ph in enumerate(by_part.get(q, [])) if ph[0] <= time < ph[1]), None)
            if index is not None:
                return v, q, index
    return None


system_end = brlP(4568) # ends a lyric and a music line where a line of music (system) ends


def system_ends( part):
    """ for each measure of the part as written, whether a line of music (system) ends with it """
    measures = list(part.getElementsByClass(music21.stream.Measure))
    def starts_system(m):
        return any(l.isNew for l in m.recurse().getElementsByClass(music21.layout.SystemLayout))
    return [i == len(measures) - 1 or starts_system(measures[i+1]) for i in range(len(measures))]


def bar_atoms( measure, start, pieces):
    """ the notes of a bar as dicts with the time of the note (from the start of the part,
    repeats as written), its symbols, whether it is a rest or starts the bar, and the
    syllables sung to it (filled in later) """
    rests = set(n.offset for n in measure.flatten().notesAndRests if n.isRest)
    return [{'time': start + offset, 'music': symbols, 'rest': offset in rests,
             'bar_start': i == 0, 'syllables': []} for i, (offset, symbols) in enumerate(pieces)]


def attach_syllables( atoms, syllables):
    """ each syllable goes with the note sounding when it is sung """
    for syllable in syllables:
        sounding = [a for a in atoms if a['time'] <= syllable[0]]
        (sounding[-1] if sounding else atoms[0])['syllables'].append(syllable)


def estimated_syllables( word):
    return max(1, len(re.findall('[aeiouy]+', re.sub('e$', '', word.lower()))))


def attach_phrase( atoms, text):
    """ spreads the words of a phrase written under the notes over the notes it is sung
    to, in proportion to their (estimated) syllables; rests take none """
    notes = [a for a in atoms if not a['rest']] or atoms
    words = text.split()
    total = sum(estimated_syllables(w) for w in words)
    done = 0
    for w in words:
        notes[min(len(notes) - 1, done * len(notes) // total)]['syllables'].append((None, None, w, 'single'))
        done += estimated_syllables(w)


def wrap_atoms( atoms, ends_system, louistable, width, prefix=''):
    """ splits a passage into pairs of lyric and music lines that each fit in width,
    breaking the two at the same note, at a barline where possible. The lyric line is
    empty where there are no words. prefix (e.g. a verse number) starts the first
    lyric. Where the passage ends a line of music both lines end with system_end.
    returns the lines and the prefix if it is still unused """
    def texts(chunk, prefix):
        music = ''
        for a in chunk:
            music += (' ' if a['bar_start'] and music else '') + a['music']
        words = syllables_to_text([s for a in chunk for s in a['syllables']])
        lyric = louis.translateString([louistable], (prefix + ' ' + words).lower().strip()) if words else ''
        return lyric, music
    lines = []
    i = 0
    while i < len(atoms):
        at_bar, at_note = None, None
        for j in range(i + 1, len(atoms) + 1):
            lyric, music = texts(atoms[i:j], prefix)
            limit = width - (1 if ends_system and j == len(atoms) else 0)
            if len(lyric) > limit or len(music) > limit:
                break
            at_note = j
            if j == len(atoms) or atoms[j]['bar_start']:
                at_bar = j
        j = at_bar or at_note or i + 1
        lyric, music = texts(atoms[i:j], prefix)
        if len(lyric) > 0:
            prefix = ''
        mark = system_end if ends_system and j == len(atoms) else ''
        if len(lyric) > 0: # a single note can carry more words than fit
            lyric_lines = textwrap.wrap(lyric, width=width - len(mark), break_on_hyphens=False)
            lines += lyric_lines[:-1] + [lyric_lines[-1] + mark]
        lines.append(music + mark)
        i = j
    return lines, prefix


def braille_shenandoah_part( part, key, louistable='en-GB-g2.ctb', width=linewidth):
    """ the part without words, repeats as written, a line of music per system,
    wrapped to width """
    result = str(key) + '\n'
    ends = system_ends(part)
    atoms, lastOctave = [], None
    for i, measure in enumerate(part.getElementsByClass(music21.stream.Measure)):
        pieces, lastOctave = braille_shapenote_bar(measure, key, oldOctave=lastOctave, return_pieces=True)
        atoms += bar_atoms(measure, 0, pieces)
        if ends[i]:
            result += '\n'.join(wrap_atoms(atoms, True, louistable, width)[0]) + '\n'
            atoms = []
    return result


def measure_words( all_syllables, all_spans, phrases_by_verse, part_number, verse, start, end):
    """ the words of verse for the part in the measure from start to end, as
    (('syllables',), syllables) or (('phrase', phrase), text). The part's own words come
    first, attached to notes or written as text; then those of other parts """
    if not any(a < end and b > start for a, b in all_spans[part_number]):
        return ('phrase', None), '' # resting
    syllables = measure_syllables(all_syllables, all_spans, part_number, verse, start, end)
    own_syllables = len(syllables) > 0 and any(s in all_syllables[part_number] for s in syllables)
    phrase = phrase_at(phrases_by_verse, verse, part_number, start)
    own_phrase = phrase is not None and phrase[1] == part_number
    if own_syllables or (len(syllables) > 0 and not own_phrase):
        return ('syllables',), syllables
    if phrase is not None:
        phrase_verse, q, index = phrase
        return ('phrase', phrase), phrases_by_verse[phrase_verse][q][index][2]
    return ('phrase', None), ''


def braille_shenandoah_part_line_by_line( piece, part_number, key, louistable='en-GB-g2.ctb',
                                         width=linewidth):
    """ for each verse, alternating lines of words and the music they are sung to,
    with repeats expanded and without time signatures. Lines end where a line of
    music (system) ends, marked by system_end, and where the music goes back; where the
    verse is written as text under the notes, a line also ends with each phrase.
    Lines are wrapped to width, breaking words and music at the same note.
    Verses are separated by a blank line """
    part = piece.parts[part_number]
    measures = expanded_measures(part)
    ends = system_ends(part)
    all_syllables = [part_syllables(p) for p in piece.parts]
    all_spans = [sounding_spans(p) for p in piece.parts]
    phrases_by_verse = markup_phrases(piece)
    verses = sorted(set(s[1] for syllables in all_syllables for s in syllables) | set(phrases_by_verse))
    result = ''
    for verse in verses:
        lastOctave, previous, prefix = None, None, f'{verse}.'
        atoms, line_kind, phrase_text = [], None, ''
        def finish( ends_system):
            nonlocal result, prefix, atoms, line_kind, phrase_text
            if len(atoms) > 0:
                if len(phrase_text) > 0:
                    attach_phrase(atoms, phrase_text)
                lines, prefix = wrap_atoms(atoms, ends_system, louistable, width, prefix)
                result += '\n'.join(lines) + '\n'
            atoms, line_kind, phrase_text = [], None, ''
        for expanded, original in measures:
            index = original.editorial.fasola_index
            if previous is not None and index <= previous:
                finish(False) # back to the start of a repeat, D.C. or D.S.
            start, end = measure_span(original, part)
            kind, words = measure_words(all_syllables, all_spans, phrases_by_verse, part_number, verse, start, end)
            has_words = kind != ('phrase', None)
            if has_words and line_kind is not None and kind != line_kind:
                finish(False) # syllables to text under the notes, or the next phrase
            if has_words and line_kind is None:
                line_kind = kind
                if kind[0] == 'phrase':
                    phrase_text = words
            pieces, lastOctave = braille_shapenote_bar(expanded, key, oldOctave=lastOctave,
                                                       show_time_signature=False, return_pieces=True)
            bar = bar_atoms(expanded, start, pieces)
            if kind[0] == 'syllables':
                attach_syllables(bar, words)
            atoms += bar
            if ends[index]:
                finish(True)
            previous = index
        finish(True)
        result += '\n'
    return result


def syllables_to_words( syllables):
    """ joins syllables (as from part_syllables) into a list of words, without hyphens,
    e.g. Ho- ly Spir- it -> Holy Spirit. A syllable starting with a hyphen also carries
    on the word before, unless that word is finished and already ends with it, as where
    a second ending repeats the end of the first (a-bove. -bove.) """
    words, open_word = [], False
    for _, _, syllable, syllabic in syllables:
        text = ' '.join(syllable.split())
        carries_on = len(words) > 0 and (open_word or text.startswith('-'))
        repeated = len(words) > 0 and not open_word and text.startswith('-') and words[-1].endswith(text.strip('-'))
        open_word = syllabic in ('begin', 'middle') or text.endswith('-')
        text = text.strip('-')
        if repeated:
            continue
        if carries_on:
            words[-1] += text
        else:
            words.append(text)
    return ' '.join(words).split()


def part_verse_words( syllables, phrases, verse):
    """ the words of verse written under one part, in the order they are written: its
    syllables (from part_syllables) joined into words and its phrases written as text
    (from markup_phrases, the part's list for verse). Where there are two notes at once
    (e.g. a divided last note) only the first syllable is kept, and D.C. and D.S. are
    left out """
    onsets = {}
    for s in syllables:
        if s[1] == verse:
            onsets.setdefault(s[0], s)
    events = sorted([(s[0], 0, s) for s in onsets.values()] +
                    [(ph[0], 1, ph) for ph in phrases], key=lambda e: e[:2])
    words, run = [], []
    for _, kind, item in events:
        if kind == 0:
            run.append(item)
            continue
        words += syllables_to_words(run) + item[3].split()
        run = []
    words += syllables_to_words(run)
    return [w for w in words if w.lower() not in ('d.c.', 'd.s.')]


def drop_repeated_phrases( words, shortest=3):
    """ removes a run of at least shortest words sung again straight after itself, e.g.
    'Whence all our blessings flow? Whence all our blessings flow?' """
    keys = [word_key(w) for w in words]
    i = 0
    while i < len(words):
        for length in range((len(words) - i) // 2, shortest - 1, -1):
            if keys[i:i+length] == keys[i+length:i+2*length]:
                # keep the punctuation at the end of the second time
                words[i+length-1] = words[i+2*length-1]
                del words[i+length:i+2*length], keys[i+length:i+2*length]
                i = 0 # a longer repeat may now be next to itself
                break
        else:
            i += 1
    return words


def verse_words( all_syllables, phrases_by_verse, verse):
    """ the words of a verse for the lyrics. Each part may have only some of them, or sing
    some more than once, so those of the part with most of the different words of the verse
    are used, of those the one with fewest words, without phrases sung twice in a row """
    candidates = []
    for q, syllables in enumerate(all_syllables):
        words = part_verse_words(syllables, phrases_by_verse.get(verse, {}).get(q, []), verse)
        if len(words) > 0:
            words = drop_repeated_phrases(words)
            if len(words) > 1 and word_key(words[-1]) == word_key(words[-2]):
                words.pop() # the last word written again in a second ending
            candidates.append(words)
    if len(candidates) == 0:
        return []
    every = set(word_key(w) for c in candidates for w in c)
    return max(candidates, key=lambda c: (len(every & set(word_key(w) for w in c)), -len(c)))


line_end_punctuation = re.compile(r'[,;:.!?][\'"’”)]*$')
strong_punctuation = re.compile(r'[;:.!?][\'"’”)]*$')
# words that often start a line of a hymn but are seldom capitalised in the middle of one
line_starts = set("""
    a and as at but by do for from had has have here how if in is it let lo may my no nor not
    now of oh on or our see shall should so such that the their then there these they this
    those though through thus till to up we were what when where which while who whose why
    will with would ye yet you your""".split())


def poem_lines( words, shortest=3):
    """ splits the words of a verse into the lines of the poem. A new line starts with a
    capital letter, after a line of at least shortest words that ends with punctuation or
    where the new line starts with a word that often starts one (line_starts). After a
    comma a line does not start with I or O (e.g. 'Jesus, I my cross') """
    lines = [[]]
    for i, w in enumerate(words):
        lines[-1].append(w)
        following = words[i+1] if i + 1 < len(words) else None
        if following is None or not following[0].isupper() or len(lines[-1]) < shortest:
            continue
        if (strong_punctuation.search(w) or word_key(following) in line_starts or
                (line_end_punctuation.search(w) and not re.match(r'(I|O)\W', following + ' '))):
            lines.append([])
    return [' '.join(line) for line in lines if len(line) > 0]


def braille_shenandoah_lyrics( piece, louistable='en-GB-g2.ctb', width=linewidth):
    """ the words of each verse on their own, a line of the poem at a time (wrapped to
    width), the first line starting with the verse number. Verses are separated by a
    blank line """
    all_syllables = [part_syllables(p) for p in piece.parts]
    phrases_by_verse = markup_phrases(piece)
    verses = sorted(set(s[1] for syllables in all_syllables for s in syllables) | set(phrases_by_verse))
    result = ''
    for verse in verses:
        lines = poem_lines(verse_words(all_syllables, phrases_by_verse, verse))
        for n, line in enumerate(lines):
            text = (f'{verse}. ' if n == 0 else '') + line
            result += textwrap.fill(louis.translateString([louistable], text.lower()),
                                    width=width, break_on_hyphens=False) + '\n'
        result += '\n'
    return result


def shenandoah_title( music_file):
    """ title from the file name, e.g. CH144_WalkWithGod -> Walk With God (CH144).
    The titles inside the files are unreliable (often left as the template's) """
    name = os.path.basename(music_file).split('.')[0]
    source, _, tune = name.partition('_')
    if len(tune) == 0:
        return name
    return ' '.join(re.findall(r'[A-Z][a-z’\']*|[a-z]+|\d+', tune)) + f' ({source})'


def braillesong_shenandoah( music_file, parts, louistable='en-GB-g2.ctb', width=linewidth):
    """ produces string with the title and, for each part, its music without words; then
    the words of each verse on their own; then for each part each verse as alternating
    lines of words and music. Sections are separated by blank lines """
    piece = music21.converter.parse(music_file, forceSource=True)
    result = textwrap.fill(louis.translateString([louistable], shenandoah_title(music_file).lower()),
                           width=width, break_on_hyphens=False) + '\n'
    key = key_from_file_or_piece(piece)
    part_names = [str(p.partName).lower() for p in piece.parts]
    line_by_lines = []
    for p in parts:
        if p.lower() not in part_names:
            continue # e.g. no alto in a three part song
        part_number = part_names.index(p.lower())
        header = '  ' + louis.translateString([louistable], p) + ':\n'
        result += header
        result += braille_shenandoah_part(piece.parts[part_number], key, louistable=louistable, width=width)
        verses = braille_shenandoah_part_line_by_line(piece, part_number, key, louistable=louistable,
                                                      width=width).split('\n\n')
        line_by_lines += [header + verses[0]] + verses[1:]
    lyrics = braille_shenandoah_lyrics(piece, louistable=louistable, width=width)
    # music, lyrics then each verse line by line
    return join_sections([result] + lyrics.split('\n\n') + line_by_lines)


def brailleShenandoah( parts, outdir, music_dir=shenandoah_musicdir, louistable='en-GB-g2.ctb',
                       song_list=None, debug=False):
    """ brailles every song in music_dir (or those in song_list, given as file names
    without extension) into outdir, one file per song named after the music file.
    returns the songs that failed """
    if not outdir.endswith('/'):
        outdir += '/'
    os.makedirs(outdir, exist_ok=True)
    if song_list is None:
        song_list = sorted(os.path.basename(f)[:-len('.musicxml')] for f in glob.glob(music_dir + '*.musicxml'))
    problems = []
    for song in song_list:
        try:
            with open(outdir + song, 'w') as outf:
                outf.write(braillesong_shenandoah(music_dir + song + '.musicxml', parts, louistable=louistable))
        except Exception:
            if debug:
                raise
            problems.append(song)
    return problems


# ---------------------------------------------------------------------------
# 2025 edition: general song structures.
# The words of every verse come from the plain text lyrics (2025-edition/lyrics), which
# are complete. The lyrics in the MusicXML are only used to find where those words go:
# each word written under the notes is matched to its place in the plain text, so it
# does not matter which part, lyric line or repeat it is written under. Verses with no
# words under the notes (or only some) are laid out like the verse that has the most.
# Repeats are read from the MusicXML itself, where the engravers mostly wrote them as
# text directions ("SH repeat dots", "SH repeat left", ...) rather than barlines, and the
# song is expanded into the spans of written time in the order they are sung.

repeat_start_directions = ('sh repeat dots', 'repeat dots', 'sh repeat right', 'sh repeat start')
repeat_end_directions = ('sh repeat left', 'sh repeat end')
repeat_both_directions = ('sh coincident repeat', 'sh repeat double')
ending_signs = {1: brlP(2), 2: brlP(23), 3: brlP(25), 4: brlP(256)} # lower digits after a number sign
lyric_label = re.compile(r'^(\d+\.|d\.\s?c\.|d\.\s?s\.|chorus\.?|fine\.?)\s*', re.IGNORECASE)
time_tolerance = 1e-3


def direction_kind( text):
    """ 'start', 'end', 'both' (an end and a start) or None for the text of an other-direction """
    text = ' '.join(text.lower().replace('musicxml importer:', '').split())
    text = re.sub(r' (ftm|svg)$', '', text)
    if text in repeat_both_directions: return 'both'
    if text in repeat_end_directions: return 'end'
    if text in repeat_start_directions: return 'start'
    return None


def read_structure( music_file):
    """ the repeats, endings and D.C./D.S. of a MusicXML file, as times in quarter notes from
    the start of the song (repeats as written). Returns a dict with
      length: of the song
      starts, ends: sets of times where a repeated section starts and ends
      endings: list of (numbers, start, end), e.g. ({1}, 40.0, 44.0) for a first ending
      dc, ds, segno, fine: times of D.C., D.S., the segno and Fine, or None
      double_bars: set of times of double barlines
    The repeat directions sit where the dots are, e.g. "SH repeat left" after the last note
    of a measure is a repeat ending with that measure. Endings may be brackets or, in the
    top part, just the numbers written as words """
    root = ElementTree.parse(music_file).getroot()
    result = {'starts': set(), 'ends': set(), 'endings': [], 'dc': None, 'ds': None,
              'segno': None, 'fine': None, 'double_bars': set()}
    offsets, lengths = [], []
    bracket_endings = {} # numbers -> [start, end]
    word_endings = {} # measure index -> number
    for p, part in enumerate(root.findall('part')):
        divisions, start = 1.0, 0.0
        for i, measure in enumerate(part.findall('measure')):
            if p > 0 and i < len(offsets):
                start = offsets[i]
            t, longest, barlines = 0.0, 0.0, []
            for e in measure:
                if e.tag == 'attributes' and e.findtext('divisions'):
                    divisions = float(e.findtext('divisions'))
                elif e.tag == 'note':
                    if e.find('chord') is None and e.find('grace') is None and e.findtext('duration'):
                        t += float(e.findtext('duration')) / divisions
                elif e.tag in ('backup', 'forward') and e.findtext('duration'):
                    t += (1 if e.tag == 'forward' else -1) * float(e.findtext('duration')) / divisions
                elif e.tag == 'barline':
                    barlines.append(e)
                if e.tag in ('direction', 'sound'):
                    time = start + t
                    for d in e.iter('other-direction'):
                        kind = direction_kind(d.text or '')
                        if kind in ('start', 'both'): result['starts'].add(time)
                        if kind in ('end', 'both'): result['ends'].add(time)
                    for w in e.iter('words'):
                        text = (w.text or '').strip().lower()
                        if p == 0 and re.fullmatch(r'\(?\d\)?\.?', text):
                            word_endings[i] = int(re.sub(r'\D', '', text))
                        elif text.startswith('d.c'): result['dc'] = time
                        elif text.startswith('d.s'): result['ds'] = time
                        elif text.startswith('fine'): result['fine'] = time
                    if any(True for _ in e.iter('segno')): result['segno'] = time
                    for s in ([e] if e.tag == 'sound' else []) + list(e.iter('sound')):
                        if s.get('dacapo') == 'yes': result['dc'] = time
                        if s.get('dalsegno'): result['ds'] = time
                        if s.get('fine'): result['fine'] = time
                longest = max(longest, t)
            if p == 0:
                offsets.append(start)
                lengths.append(longest)
                start += longest
            end = offsets[i] + lengths[i] if i < len(offsets) else start + longest
            for b in barlines:
                time = offsets[i] if b.get('location') == 'left' else end
                repeat = b.find('repeat')
                if repeat is not None:
                    result['starts' if repeat.get('direction') == 'forward' else 'ends'].add(time)
                ending = b.find('ending')
                if ending is not None:
                    numbers = frozenset(int(n) for n in re.findall(r'\d+', ending.get('number', '')))
                    span = bracket_endings.setdefault(numbers, [offsets[i], end])
                    if ending.get('type') == 'start': span[0] = min(span[0], offsets[i])
                    else: span[1] = end
                if b.findtext('bar-style') in ('light-light', 'light-heavy'):
                    result['double_bars'].add(time)
    result['length'] = offsets[-1] + lengths[-1] if offsets else 0.0
    result['endings'] = [(set(n), a, b) for n, (a, b) in bracket_endings.items() if len(n) > 0]
    if len(result['endings']) == 0 and len(word_endings) > 1:
        indices = sorted(word_endings)
        for j, i in enumerate(indices):
            end = offsets[indices[j+1]] if j + 1 < len(indices) else offsets[i] + lengths[i]
            result['endings'].append(({word_endings[i]}, offsets[i], end))
    result['double_bars'].discard(result['length'])
    return result


def expand_structure( structure, max_spans=100):
    """ the order a song is sung in, as a list of (start, end, pass, after D.C./D.S.) spans
    of written time.
    A repeated section is sung twice, or once for each of its endings, leaving out an
    ending the other times. As usual in the Sacred Harp a repeat with no end repeats to
    the end of the first ending, or of the song, and one with no start from the last
    end of a repeat or the start. A D.C. (D.S.) goes back to the start (the segno) and,
    without the repeats, ends at the Fine, else the first double bar or end of a repeat """
    length = structure['length']
    endings = sorted(structure['endings'], key=lambda e: e[1])
    ends = set(t for t in structure['ends'] if t > time_tolerance)
    # a forward repeat at the start of a later ending is left over from the engraving,
    # unless a repeat ends after it
    starts = sorted(t for t in structure['starts'] if t < length - time_tolerance and
                    (not any(abs(a - t) < time_tolerance and min(n) > 1 for n, a, _ in endings) or any(e > t + time_tolerance for e in ends)))
    for numbers, a, b in endings:
        if 1 in numbers and not any(a < e <= b + time_tolerance for e in ends):
            ends.add(b)
    for i, s in enumerate(starts):
        following = starts[i+1] if i + 1 < len(starts) else length
        if not any(s < e <= following + time_tolerance for e in ends):
            ends.add(following)
    ends = sorted(ends)
    def times_through(section, end):
        return max([max(n) for n, a, _ in endings if section <= a <= end + time_tolerance] + [2])
    spans = []
    t, section, current_pass, done = 0.0, 0.0, 1, set()
    stop_at, navigation = length, structure['dc'] is not None or structure['ds'] is not None
    navigated = False
    while len(spans) < max_spans:
        if t >= stop_at - time_tolerance:
            if not navigation:
                break
            navigation, navigated = False, True
            t = structure['segno'] if structure['ds'] is not None and structure['segno'] is not None else 0.0
            if structure['fine'] is not None and structure['fine'] > t:
                stop_at = structure['fine']
            else:
                stop_at = min([x for x in set(structure['double_bars']) | set(ends) if x > t + time_tolerance] + [length])
            done, current_pass = set(ends), max([max(n) for n, _, _ in endings] + [1])
            continue
        end = min([e for e in ends if t + time_tolerance < e <= stop_at + time_tolerance and e not in done], default=None)
        start = min([s for s in starts if t + time_tolerance < s < stop_at - time_tolerance], default=None)
        stop = min(x for x in (end, start, stop_at) if x is not None)
        skip = [(a, b) for n, a, b in endings if t - time_tolerance <= a < stop - time_tolerance
                and a > section + time_tolerance and current_pass not in n]
        if skip:
            a, b = skip[0]
            if a > t + time_tolerance:
                spans.append((t, a, current_pass, navigated))
            t = b
            if any(abs(s - b) < time_tolerance for s in starts):
                section, current_pass = b, 1
            continue
        spans.append((t, stop, current_pass, navigated))
        t = stop
        if end is not None and abs(stop - end) < time_tolerance:
            if current_pass < times_through(section, end):
                current_pass += 1
                t = section
                continue
            done.add(end)
            section = end
            if not any(abs(a - end) < time_tolerance for _, a, _ in endings):
                current_pass = 1
        if start is not None and abs(stop - start) < time_tolerance:
            section, current_pass = start, 1
    return spans


def sung_atoms( part, key, spans, show_time_signature=False):
    """ the notes and rests of the part in the order they are sung, as dicts with the time
    (written, from the start of the song), length, music (its symbols), whether it is a rest,
    tied from the note before or starts a bar, the span it is in and the words sung to it
    (filled in later) """
    measures = [(m.getOffsetBySite(part), m) for m in part.getElementsByClass(music21.stream.Measure)]
    atoms, lastOctave = [], None
    for s, (a, b, *_) in enumerate(spans):
        first_in_span = True
        for start, m in measures:
            end = start + m.highestTime
            if end <= a + time_tolerance or start >= b - time_tolerance:
                continue
            window = (a - start - time_tolerance, b - start - time_tolerance)
            notes = {}
            for n in m.flatten().notesAndRests:
                notes.setdefault(n.offset, n)
            pieces, lastOctave = braille_shapenote_bar(m, key, oldOctave=lastOctave, show_time_signature=show_time_signature,
                                                       show_repeats=False, return_pieces=True, window=window)
            for j, (offset, symbols) in enumerate(pieces):
                n = notes.get(offset)
                if n is None or len(symbols) == 0:
                    continue
                atoms.append({'time': start + offset, 'length': n.quarterLength, 'music': symbols,
                              'rest': n.isRest, 'tied': n.tie is not None and n.tie.type in ('stop', 'continue'),
                              'bar_start': j == 0 or first_in_span, 'span': s, 'pass': spans[s][2],
                              'navigated': len(spans[s]) > 3 and spans[s][3], 'syllables': []})
                first_in_span = False
    return atoms


def braille_written_part( part, key, structure, louistable='en-GB-g2.ctb', width=linewidth):
    """ the part without words as written, with the repeats, endings and D.C./D.S. read by
    read_structure, wrapped to width """
    atoms = sung_atoms(part, key, [(0.0, structure['length'], 1, False)], show_time_signature=True)
    if len(atoms) == 0:
        return str(key) + '\n'
    def at(time):
        """ the atom starting at time, or the first after it """
        return next((a for a in atoms if a['time'] > time - time_tolerance), atoms[-1])
    def before(time):
        """ the last atom starting before time """
        return ([a for a in atoms if a['time'] < time - time_tolerance] or atoms[:1])[-1]
    for numbers, a, _ in structure['endings']:
        at(a)['music'] = brlP(3456) + ''.join(ending_signs.get(n, '') for n in sorted(numbers)) + at(a)['music']
    for t in structure['starts']:
        if t < structure['length'] - time_tolerance:
            at(t)['music'] = brlP(238) + brlP(3678) + at(t)['music']
    for t in structure['ends']:
        before(t)['music'] += brlP(3678) + brlP(567)
    for word in ('dc', 'ds'):
        if structure[word] is not None:
            before(structure[word] + time_tolerance)['music'] += louis.translateString([louistable], word[0] + '.' + word[1] + '.')
    return str(key) + '\n' + '\n'.join(wrap_atoms(atoms, False, louistable, width)[0]) + '\n'


def read_lyrics_text( lyrics_file):
    """ the title and verses of a plain text lyrics file (2025-edition/lyrics). Stanzas are
    separated by blank lines and may be labelled, e.g. [chorus], [verse 2 chorus],
    [alto, bass] or [solos]. An unlabelled stanza starts a verse unless it follows one
    for particular parts (or solos), when it carries that verse on; a chorus is sung after
    every verse, a [verse n chorus] after verse n. Each verse is a list of words, as dicts
    with word, key, id (stanza, word in the stanza), line (stanza, line in the stanza) and
    parts (those that sing it, None for all), in the order they are sung """
    with open(lyrics_file) as f:
        lines = f.read().splitlines()
    title = lines[0].lstrip('#').strip()
    stanzas, current = [], None
    for line in lines[1:]:
        line = line.strip()
        if len(line) == 0:
            current = None
            continue
        label = re.fullmatch(r'\[(.*)\]', line)
        if label or current is None:
            text = label.group(1).lower() if label else ''
            verse = re.search(r'verse (\d+)', text)
            current = {'label': text, 'lines': [], 'chorus': 'chorus' in text,
                       'verse': int(verse.group(1)) if verse else None,
                       'parts': [p for p in ('treble', 'alto', 'tenor', 'bass') if p in text] or None}
            stanzas.append(current)
            if label:
                continue
        current['lines'].append(line.split())
    def words(s):
        result = []
        for l, line in enumerate(stanzas[s]['lines']):
            for w in line:
                result.append({'word': w, 'key': word_key(w), 'id': (s, len(result)), 'line': (s, l),
                               'parts': stanzas[s]['parts']})
        return result
    verses = [] # lists of stanza numbers
    for s, stanza in enumerate(stanzas):
        if stanza['chorus'] or len(stanza['lines']) == 0:
            continue
        follows_special = s > 0 and stanzas[s-1]['label'] != '' and not stanzas[s-1]['chorus']
        if len(verses) > 0 and (stanza['label'] != '' or follows_special):
            verses[-1].append(s)
        else:
            verses.append([s])
    result = []
    for v, verse in enumerate(verses):
        choruses = [s for s, stanza in enumerate(stanzas) if stanza['chorus'] and stanza['verse'] in (None, v + 1)]
        result.append([w for s in verse + choruses for w in words(s)])
    return title, result


def xml_words( piece):
    """ the words written under the notes of each part: for each part a list of lines (one
    per lyric number) of words as dicts with key, times (of each syllable, from the start of
    the song) and elided, True for the second and later words written under one note
    (e.g. a whole line of a later verse), which say what is sung but not where """
    result = []
    for part in piece.parts:
        lines = defaultdict(list)
        for n in part.flatten().notes:
            for l in n.lyrics:
                components = l.components if l.isComposite and l.components else [l]
                texts = [(lyric_label.sub('', c.text or ''), c.syllabic) for c in components]
                texts = [(text, syllabic) for text, syllabic in texts if len(word_key(text)) > 0]
                line = lines[l.number or 1]
                for c, (text, syllabic) in enumerate(texts):
                    if len(line) > 0 and line[-1]['open']:
                        word = line[-1]
                        word['text'] += text
                        if c == 0:
                            word['times'].append(n.offset)
                    else:
                        word = {'text': text, 'times': [n.offset], 'elided': c > 0}
                        line.append(word)
                    word['open'] = syllabic in ('begin', 'middle')
        for line in lines.values():
            for word in line:
                word['key'] = word_key(word['text'])
        result.append([lines[number] for number in sorted(lines)])
    return result


def align_to_text( words, tokens):
    """ the index into tokens (the words of the lyrics) of each of the words written under
    the notes in one lyric line, None where it is not found. The words of a lyric line are
    mostly consecutive in the lyrics, so the alignment with fewest jumps is chosen """
    where = defaultdict(list)
    for j, t in enumerate(tokens):
        where[t['key']].append(j)
    jump, back, miss = 1.0, 1.2, 1.5 # going back is less likely than on
    previous = {None: (0.0, None)} # matched token -> (cost, token matched by the word before)
    history = []
    for i, w in enumerate(words):
        best_state = min(previous, key=lambda s: previous[s][0])
        best = previous[best_state][0]
        current = {None: (best + miss, best_state)}
        for j in where.get(w['key'], []):
            cost = 0.0 if i == 0 else (jump if best_state is None or j > best_state else back)
            options = [(best + cost, best_state)]
            if j - 1 in previous:
                options.append((previous[j-1][0], j - 1))
            current[j] = min(options, key=lambda o: o[0])
        history.append(current)
        previous = current
    state = min(previous, key=lambda s: previous[s][0])
    result = [None] * len(words)
    for i in range(len(words) - 1, -1, -1):
        result[i] = state
        state = history[i][state][1]
    return result


def anchor_words( piece, verses):
    """ the words written under the notes, as a list per part of dicts with times (of the
    syllables), token (id of the word in the lyrics, None if not found), key, elided, line
    (part and lyric line it is written in) and index (in that line) """
    tokens = {}
    for verse in verses:
        for w in verse:
            tokens.setdefault(w['id'], w)
    tokens = list(tokens.values())
    result = []
    for q, lines in enumerate(xml_words(piece)):
        anchors = []
        for number, line in enumerate(lines):
            for index, (word, j) in enumerate(zip(line, align_to_text(line, tokens))):
                anchors.append({'times': word['times'], 'token': tokens[j]['id'] if j is not None else None,
                                'key': word['key'], 'elided': word['elided'], 'line': (q, number), 'index': index})
        result.append(anchors)
    return result


def candidates_at( anchors, part_number, atom):
    """ the anchored words that can be sung to atom, as (part, word): those of the part
    starting with it, and those of other parts starting while it sounds """
    if atom['rest'] or atom['tied']:
        return []
    result = []
    for q, words in enumerate(anchors):
        for w in words:
            if w['elided']:
                continue
            onset = w['times'][0]
            if q == part_number and abs(onset - atom['time']) < time_tolerance:
                result.append((q, w))
            elif q != part_number and atom['time'] - time_tolerance <= onset < atom['time'] + atom['length'] - time_tolerance:
                result.append((q, w))
    return result


def follow_text( atoms, anchors, part_number, verses, first_verse):
    """ walks through the sung notes of a part matching words written under them (or under
    other parts) to the words of verse first_verse, in order. Words can be passed over
    (where they are not written under the notes) but no more than there are notes for.
    Words are sung again (going back in the lyrics) where the part's own words say so, or
    those of the part it takes its words from when it has none; also on going back for
    a repeat where the same words are written once. Where the verse runs on into the next
    in the music (an anthem written as stanzas) the verses are joined.
    returns the words sung (a list of tokens), the number of verses used and the anchors,
    a list of (atom index, index into the words) """
    words, verse_ends = [], []
    for verse in verses[first_verse:]:
        words += verse
        verse_ends.append(len(words))
    positions, key_positions = defaultdict(list), defaultdict(list)
    for i, w in enumerate(words):
        positions[w['id']].append(i)
        key_positions[w['key']].append(i)
    candidates = [candidates_at(anchors, part_number, a) for a in atoms]
    has_own = len(anchors[part_number]) > 0
    allowed_end, used_verses = verse_ends[0], 1
    k, k_at, k_last, result, notes_since, donor = 0, {}, {}, [], 0, None
    def trusted(q):
        """ whether the words of part q can say a phrase is sung again """
        return q == part_number or (not has_own and q == donor)
    def forward(i, low, high, by_key=False, words=None):
        high = min(high, low + notes_since + 3)
        return sorted(((p, q != part_number, q, w) for q, w in (candidates[i] if words is None else words)
                       if not by_key or trusted(q)
                       for p in (key_positions[w['key']] if by_key else positions[w['token']]) if low <= p < high),
                      key=lambda f: f[:3])
    last = None # the last word found under the notes
    for i, atom in enumerate(atoms):
        if i > 0 and atom['span'] != atoms[i-1]['span'] and atom['time'] < atoms[i-1]['time'] and atom['time'] in k_at:
            # going back for a repeat: the same words again if no others are written,
            # after a D.C. those of the last time through
            again = k_last[atom['time']] if atom['navigated'] else k_at[atom['time']]
            ahead = [j for j in range(i, len(atoms)) if atoms[j]['span'] == atom['span']][:8]
            if not any(forward(j, k, allowed_end) for j in ahead) and any(forward(j, again, k) for j in ahead):
                k = again
        k_at.setdefault(atom['time'], k)
        k_last[atom['time']] = k
        # first the next word of the lyric line being followed, which may be sung again
        following = [(q, w) for q, w in candidates[i] if last is not None and
                     w['line'] == last['line'] and w['index'] == last['index'] + 1]
        found = forward(i, k, allowed_end, words=following) or forward(i, k, allowed_end, by_key=True, words=following)
        if len(found) == 0 and len(following) > 0:
            back = sorted(((-p, q, w) for q, w in following for p in positions[w['token']] + key_positions[w['key']] if p < k),
                          key=lambda f: f[:2])
            found = [(-p, q != part_number, q, w) for p, q, w in back][:1]
        if len(found) == 0:
            found = forward(i, k, allowed_end)
        if len(found) == 0 and k >= allowed_end:
            # the words have run out but the music goes on: words of the verse sung again
            back = sorted(((q != part_number, -p, q, w) for q, w in candidates[i] for p in positions[w['token']] if p < k),
                          key=lambda f: f[:3])
            found = [(-p, other, q, w) for other, p, q, w in back][:1]
        if len(found) == 0 and k >= allowed_end and used_verses < len(verse_ends):
            found = forward(i, k, min(k + 3, verse_ends[used_verses]))
            if len(found) > 0:
                allowed_end = verse_ends[used_verses]
                used_verses += 1
        if len(found) == 0:
            # the same word close by, where a phrase sung twice was matched to the wrong one
            found = forward(i, k, allowed_end, by_key=True)
        if len(found) > 0:
            p, _, q, last = found[0]
            result.append((i, p))
            k, notes_since = p + 1, 0
            if q != part_number:
                donor = q
        elif not atom['rest'] and not atom['tied']:
            notes_since += 1
    return words[:allowed_end], used_verses, result


def place_words( atoms, words, gap, region, slots):
    """ puts the words of gap (indices into words) on the atoms of region, which has none
    of its own, in proportion to their estimated syllables. slots maps atom index to the
    line of words that a reference verse sings there; where the gap and the slots in region
    have the same number of lines they are matched line by line """
    if len(gap) == 0:
        return
    def lines_of(items, line):
        groups = []
        for item in items:
            if len(groups) == 0 or line(item) != line(groups[-1][-1]):
                groups.append([])
            groups[-1].append(item)
        return groups
    def notes_in(items):
        return [i for i in items if not atoms[i]['rest'] and not atoms[i]['tied']]
    gap_lines = lines_of(gap, lambda g: words[g]['line'])
    region_slots = [i for i in region if i in slots]
    slot_lines = lines_of(region_slots, lambda i: slots[i])
    if len(slot_lines) != len(gap_lines):
        slot_lines, gap_lines = [region_slots], [gap]
    # where too few syllables are written under the notes, use every note of the line
    starts = [region[0]] + [line[0] for line in slot_lines[1:]] + [region[-1] + 1]
    for n, line_words in enumerate(gap_lines):
        total = sum(estimated_syllables(words[g]['word']) for g in line_words)
        if len(slot_lines[n]) < total:
            notes = notes_in([i for i in region if starts[n] <= i < starts[n+1]])
            if len(notes) > len(slot_lines[n]):
                slot_lines[n] = notes
    for line_slots, line_words in zip(slot_lines, gap_lines):
        if len(line_slots) == 0:
            line_slots = notes_in(region) or [region[0]]
        total = sum(estimated_syllables(words[g]['word']) for g in line_words)
        done = 0
        for g in line_words:
            atom = atoms[line_slots[min(len(line_slots) - 1, done * len(line_slots) // total)]]
            atom['syllables'].append((None, words[g]['line'], words[g]['word'], 'single'))
            done += estimated_syllables(words[g]['word'])


def syllable_onsets( atoms, anchors, part_number):
    """ the atoms on which a syllable is written, under the part itself or, if it has no
    words of its own, under another part while the atom sounds """
    own = len(anchors[part_number]) > 0
    times = sorted(t for q, words in enumerate(anchors) if (q == part_number) == own
                   for w in words if not w['elided'] for t in w['times'])
    result = set()
    for i, a in enumerate(atoms):
        if a['rest'] or a['tied']:
            continue
        end = a['time'] + (time_tolerance if own else a['length'] - time_tolerance)
        if any(a['time'] - time_tolerance <= t < end for t in times):
            result.add(i)
    return result


def lay_out_verse( atoms, words, found, slots):
    """ copies of atoms with the words on them: those found under the notes where they were
    found, the rest spread over the notes between them (see place_words). Where the words
    go back for a repeat, the line being sung is finished first.
    returns the atoms and counts of words found and placed between """
    atoms = [dict(a, syllables=[]) for a in atoms]
    occupied = set()
    for i, p in found:
        atoms[i]['syllables'].append((None, words[p]['line'], words[p]['word'], 'single'))
        occupied.add(i)
    filled, reached = 0, -1
    bounds = [(-1, -1)] + found + [(len(atoms), len(words))]
    for (ia, pa), (ib, pb) in zip(bounds[:-1], bounds[1:]):
        reached = max(reached, pa)
        if ib == len(atoms) and pa < reached:
            # the end of words sung again: finish the line, then any words never sung
            line = words[pa]['line']
            gap = [p for p in range(pa + 1, len(words)) if words[p]['line'] == line and p <= reached]
            gap += list(range(reached + 1, len(words)))
            region = [i for i in range(ia + 1, ib) if i not in occupied] or [ia]
            place_words(atoms, words, gap, region, slots)
            filled += len(gap)
            continue
        if pb <= pa:
            if not any(atoms[i]['time'] < atoms[i-1]['time'] for i in range(max(ia + 1, 1), min(ib + 1, len(atoms)))):
                continue # words sung again
            # going back for a repeat: the rest of the line goes before
            line = words[pa]['line']
            pb = next((p for p in range(pa + 1, len(words)) if words[p]['line'] != line), len(words))
            ib = next((i for i in range(ia + 1, ib + 1) if atoms[i]['span'] != atoms[ia]['span']), ib)
        if pb <= pa + 1:
            continue
        gap = list(range(pa + 1, pb))
        region = [i for i in range(ia + 1, ib) if i not in occupied] or ([ia] if ia >= 0 else [max(ib - 1, 0)])
        place_words(atoms, words, gap, region, slots)
        filled += len(gap)
    return atoms, len(found), filled


def verse_slots( atoms, onsets):
    """ the line of words sung on each atom of onsets, in a laid out verse """
    result, line = {}, None
    for i, a in enumerate(atoms):
        if len(a['syllables']) > 0:
            line = a['syllables'][0][1]
        if i in onsets and line is not None:
            result[i] = line
    return result


def verse_lines( atoms, louistable, width, prefix):
    """ the braille lines of a verse: a line of words then the music it is sung to, starting
    afresh with each line of the lyrics and where the music goes back for a repeat """
    result, chunk, line = [], [], None
    for i, a in enumerate(atoms):
        new_line = len(a['syllables']) > 0 and a['syllables'][0][1] != line and line is not None
        going_back = i > 0 and a['span'] != atoms[i-1]['span'] and a['time'] < atoms[i-1]['time']
        if (new_line or going_back) and len(chunk) > 0:
            lines, prefix = wrap_atoms(chunk, False, louistable, width, prefix)
            result += lines
            chunk = []
        if len(a['syllables']) > 0:
            line = a['syllables'][-1][1]
        chunk.append(a)
    if len(chunk) > 0:
        result += wrap_atoms(chunk, False, louistable, width, prefix)[0]
    return result


def part_verses( piece, part_number, key, spans, verses, anchors, part_name=None):
    """ the verses of a part laid out on its sung notes: a list of (verse numbers, atoms,
    words found, words placed between). part_name (e.g. bass) picks out the words of
    stanzas for particular parts; by default the name in the file """
    atoms = sung_atoms(piece.parts[part_number], key, spans)
    if part_name is None:
        part_name = str(piece.parts[part_number].partName)
    part_name = part_name.strip('[] ').lower()
    def for_part(verse):
        return [w for w in verse if w['parts'] is None or part_name not in ('treble', 'alto', 'tenor', 'bass')
                or part_name in w['parts']]
    verses = [for_part(v) for v in verses]
    followed, v = [], 0
    while v < len(verses):
        words, used, found = follow_text(atoms, anchors, part_number, verses, v)
        followed.append((list(range(v + 1, v + used + 1)), words, found))
        v += used
    # lay out the verse with most words found first, so the others can follow it
    order = sorted(range(len(followed)), key=lambda f: -len(followed[f][2]))
    onsets = syllable_onsets(atoms, anchors, part_number)
    slots, result = {}, [None] * len(followed)
    for f in order:
        numbers, words, found = followed[f]
        laid_out, n_found, n_filled = lay_out_verse(atoms, words, found, slots)
        if len(slots) == 0:
            slots = verse_slots(laid_out, onsets)
        result[f] = (numbers, laid_out, n_found, n_filled)
    return result


def braillesong_general( lyrics_file, music_file, parts, louistable='en-GB-g2.ctb', width=linewidth,
                         tmp_file=tmpdir + 'fasola_tmp.musicxml', transform_file=transform_file, report=None):
    """ the title then, for each part, its music as written followed by each verse as
    alternating lines of words and the music they are sung to, repeats expanded; then the
    words. Works from the structure of the music (read_structure) and the plain text lyrics
    (read_lyrics_text), so any arrangement of words under the notes will do.
    report, if a list, gets a dict per part and verse with the words found under the notes
    and placed between them """
    title, lyrics = braillewords(lyrics_file, louistable=louistable, width=width)
    _, verses = read_lyrics_text(lyrics_file)
    structure = read_structure(music_file)
    spans = expand_structure(structure)
    preprocess_shapenote_file(music_file, tmp_file, transform_file)
    piece = music21.converter.parse(tmp_file, forceSource=True)
    key = key_from_file_or_piece(piece)
    anchors = anchor_words(piece, verses)
    result = title + '\n'
    verse_music = []
    for p in parts:
        try:
            part_number = find_part_number(piece, p)
        except KeyError:
            continue # e.g. no alto in a three part song
        if part_number >= len(piece.parts):
            continue
        result += '  ' + louis.translateString([louistable], p) + ':\n'
        result += braille_written_part(piece.parts[part_number], key, structure, louistable=louistable, width=width)
        for numbers, atoms, n_found, n_filled in part_verses(piece, part_number, key, spans, verses, anchors, part_name=p):
            prefix = '-'.join(str(n) for n in [numbers[0], numbers[-1]][:len(set([numbers[0], numbers[-1]]))]) + '.'
            verse_music.append('\n'.join(verse_lines(atoms, louistable, width, prefix)))
            if report is not None:
                report.append({'part': p, 'verses': numbers, 'found': n_found, 'filled': n_filled,
                               'notes': sum(1 for a in atoms if not a['rest'])})
    # music, lyrics then each verse with its music, separated by blank lines
    return join_sections([result, lyrics] + verse_music)


# ---------------------------------------------------------------------------
# Choosing the book. The settings of each book; the globals above stay for
# code that uses them directly.
books = {
    'sacred-harp': {'lyrics_dir': lyricsdir, 'title_file': titlefile, 'music_dir': musicdir,
                    'transform_file': transform_file},
    'shenandoah': {'music_dir': shenandoah_musicdir},
}
default_book = 'sacred-harp'
book_variable = 'FASOLA_BOOK' # environment variable naming the book


def choose_book( book=None):
    """ the name of the book: book if given, else the FASOLA_BOOK environment variable,
    else the Sacred Harp """
    if book is None:
        book = os.environ.get(book_variable) or default_book
    book = book.lower()
    if book not in books:
        raise ValueError(f'unknown book {book!r}, choose one of {", ".join(books)}')
    return book


def brailleBook( parts, outdir, book=None, song_list=None, louistable='en-GB-g2.ctb', debug=False):
    """ brailles the songs of a book (see choose_book) into outdir, every song or those
    in song_list: song numbers (e.g. 347.1) for the Sacred Harp, music file names without
    extension (e.g. CH144_WalkWithGod) for the Shenandoah Harmony.
    returns the songs that failed """
    book = choose_book(book)
    settings = books[book]
    os.makedirs(outdir, exist_ok=True)
    if book == 'shenandoah':
        return brailleShenandoah(parts, outdir, music_dir=settings['music_dir'], louistable=louistable,
                                 song_list=song_list, debug=debug)
    if song_list is None:
        return brailleAll(settings['lyrics_dir'], settings['title_file'], settings['music_dir'], parts, outdir,
                          louistable=louistable, transform_file=settings['transform_file'], debug=debug)
    return brailleList(song_list, settings['lyrics_dir'], settings['title_file'], settings['music_dir'], parts,
                       outdir, louistable=louistable, transform_file=settings['transform_file'], debug=debug)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='braille shape note songbooks')
    parser.add_argument('--book', choices=sorted(books),
                        help=f'the book to braille (default: ${book_variable}, else {default_book})')
    parser.add_argument('--parts', nargs='+', default=['bass'], help='parts to braille (default: bass)')
    parser.add_argument('--outdir', required=True, help='directory for the brailled songs')
    parser.add_argument('--songs', nargs='+', help='only these songs (see brailleBook)')
    parser.add_argument('--louistable', default='en-GB-g2.ctb', help='liblouis table for the words')
    parser.add_argument('--debug', action='store_true', help='stop at the first song that fails')
    args = parser.parse_args()
    book = choose_book(args.book)
    problems = brailleBook(args.parts, args.outdir, book=book, song_list=args.songs,
                           louistable=args.louistable, debug=args.debug)
    print(f'{book}: {len(problems)} songs failed' + (': ' + ' '.join(problems) if problems else ''))
