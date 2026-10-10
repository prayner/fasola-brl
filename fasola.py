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

def brailleTimeSignature( sig): return brlP(3456)+sig.ratioString
        


def braille_shapenote_bar( bar, key, oldOctave=None, showSplits=None, show_time_signature=True, return_pieces=False):
    """ returns a string of symbols for the shapes in the bar
    The current plan is that each note is a symbol and optionally followed by a dot.
    If the note moves outside the octave it is preceded by symbols meaning up or down
    showSplits determines whether chords are listed in full or just the top note
    if return_pieces is True the string is returned as a list of (offset in bar, symbols)
    with one entry per note or rest, so that a bar can be split between lines"""
    result = u''
    note_starts = [] # (offset, position in result) for each note, chord or rest
    # first check if it's a new system whereupon we need a new line
    layouts = bar.recurse().getElementsByClass('layout.SystemLayout')
    if len(layouts) > 0:
        if layouts[0].isNew:
            result += '\n'
    for e in bar.flatten():
        if isinstance(e, music21.bar.Repeat):
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
                outf.write( braillesong_line_by_line(lyrics_path, tmpfile, parts))
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
            result += line_by_line
        except:
            pass
    result += lyrics
    result = '\n'.join([s for s in result.splitlines() if len(s.strip())]) # removing lines with only whitespace
    return result

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


def clean_markup_text( text):
    """ tidies the spacing used to place markup lyrics under notes, e.g. 'ach - ing  void' -> 'ach-ing void' """
    text = text.replace('__', ' ')
    text = re.sub(r'\s*-\s*-?\s*', '-', text) if ' - ' in text or '- ' in text else text
    return ' '.join(text.split())


def markup_phrases( piece):
    """ returns {verse: {part_number: phrases}} for verses written as text under the
    notes, where phrases is a sorted list of [start, end, text] in quarter lengths.
    The verse of a text comes from a leading "2." (which carries on to later texts
    in the same part and line of a text column), else from the same text (ignoring
    spacing and line breaks) with a known verse, else each such part's texts are
    taken as a further verse.
    A right-aligned text ends at the note it is attached to, others start there and
    run to the next text of the verse """
    tracks = {} # (part number, column line) -> list of [anchor, end of anchor note, right aligned, text, verse]
    for p, part in enumerate(piece.parts):
        note_ends = {n.offset: n.offset + n.quarterLength for n in part.flatten().notesAndRests}
        for t in part.recurse().getElementsByClass(music21.expressions.TextExpression):
            anchor = t.getOffsetInHierarchy(part)
            # lines of a text column are verses if labelled, or if that column line
            # had a verse before; otherwise they continue the line above
            lines = []
            for line_number, line in enumerate(t.content.split('\n')):
                text = clean_markup_text(line)
                if len(lines) > 0 and not re.match(r'\d+\.', text) and (p, len(lines)) not in tracks:
                    lines[-1] = (lines[-1] + ' ' + text).strip()
                else:
                    lines.append(text)
            for line_number, text in enumerate(lines):
                if not re.search('[A-Za-z]{2}', text) or text.lower() in navigation_words:
                    continue
                label = re.match(r'(\d+)\.\s*', text)
                track = tracks.setdefault((p, line_number), [])
                verse = int(label.group(1)) if label else (track[-1][4] if track else None)
                if label:
                    text = text[label.end():]
                track.append([anchor, note_ends.get(anchor, anchor), t.style.justify == 'right', text, verse])
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
            phrases = [[e[0] if not e[2] else None, e[1] if e[2] else None, e[3]] for e in entries]
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
    Lines are wrapped to width, breaking words and music at the same note """
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
    """ produces string with the title then, for each part, its music without words
    followed by each verse as alternating lines of words and music """
    piece = music21.converter.parse(music_file, forceSource=True)
    result = textwrap.fill(louis.translateString([louistable], shenandoah_title(music_file).lower()),
                           width=width, break_on_hyphens=False) + '\n'
    key = key_from_file_or_piece(piece)
    part_names = [str(p.partName).lower() for p in piece.parts]
    for p in parts:
        if p.lower() not in part_names:
            continue # e.g. no alto in a three part song
        part_number = part_names.index(p.lower())
        result += '  ' + louis.translateString([louistable], p) + ':\n'
        result += braille_shenandoah_part(piece.parts[part_number], key, louistable=louistable, width=width)
        result += braille_shenandoah_part_line_by_line(piece, part_number, key, louistable=louistable, width=width)
    result = '\n'.join([s for s in result.splitlines() if len(s.strip())]) # removing lines with only whitespace
    return result


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
