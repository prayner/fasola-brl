# settings for testing
lyricsdir = '/home/unimelb.edu.au/prayner/nonwork/fasola/shenandoah-harmony/WholeBook/Lilypond files/'
fileName = '/home/unimelb.edu.au/prayner/nonwork/fasola/shenandoah-harmony/WholeBook/Lilypond files/AHR274_Pomfret.ly'
fileName = '/home/unimelb.edu.au/prayner/nonwork/fasola/shenandoah-harmony/WholeBook/Lilypond files/AV228_HeHathDoneAllThingsWell.ly'
fileName='/home/unimelb.edu.au/prayner/nonwork/fasola/shenandoah-harmony/WholeBook/Lilypond files/BSH049_Crucifixion.ly'
filterList =['words']

from os import path
import re
import ly.document
import ly.music
from fractions import Fraction
import glob

knownStructures = ['oneVerse','multiVerse'] # strings representing possible structures in SH
def lyFindAssignmentByName( musicList, name, depth=1):
    r""" find the assignment in the music list with name name and return it, will return multiple if they exist, level of search depth set by depth argument"""
    # note names are bracketed by "'" for some reason
    quotedName = "'"+name+"'"
    return [i for i in musicList.find_children( ly.music.items.Assignment) if str.__repr__( i.name()) == quotedName]

def lyFilterComponents( componentList, filterList):
    """ take a list of ly components and select the values of those that match   any regexp in filterList"""
    assert len( filterList) > 0
    # first make single regexp from filterList
    joined = '|'.join( filterList)
    regexp = r'('+joined+r')'
    result = []
    for i in componentList:
        if re.search( regexp, str(i.name())): result.append(i.value())
    return result

def lyLyricsFromLyricMode( node):
    """ extract lyrics from a LyricMode object and return as a string"""
    assert isinstance( node, ly.music.items.LyricMode)
    result = r''
    lyricList = [i for i in node.find_children((ly.music.items.LyricText, ly.music.items.LyricItem))]
    # remove skips from the start if present
    if (isinstance( lyricList[0], ly.music.items.LyricItem) and isinstance( lyricList[0].token, ly.lex.lilypond.LyricSkip)):
        while (isinstance( lyricList[0], ly.music.items.LyricItem) and isinstance( lyricList[0].token, ly.lex.lilypond.LyricSkip)): lyricList.pop(0)
    # now iterate over remaining items doing careful things to spacing
    lastWasText = False # flag to check on inserting spaces, should not happen after melismas
    for i in lyricList:
        if isinstance( i, ly.music.items.LyricText):
            if lastWasText: result+=' '
            result += str(i.token)
            lastWasText = True
        elif isinstance( i, ly.music.items.LyricItem):
            result += str( i.token)
            lastWasText = False
    result += '\n'
    return result

def lyAbsoluteTiming( l):
    """ creates a list where every object is associated with its absolute timing, should work for any iterator provided every ielded object has a length method
    returns list of tuples (object, absolutetiming)"""
    absoluteTiming = Fraction(0)
    result = []
    for i in l:
        result.append((i, absoluteTiming))
        absoluteTiming += i.length()
    return result

f=open( fileName, 'r')
text=f.read()
f.close()
lyDocument=ly.document.Document( text)
lyMusic=ly.music.document( lyDocument)
lyScore = [i for i in lyMusic.find_children(ly.music.items.Score, depth=1)][0] # messy wasy of extracting object from generator 
scoreComponents = [i for i in lyScore.find_children(ly.music.items.UserCommand)]
chosenComponents = lyFilterComponents( scoreComponents, filterList)
#lyLyricsFromLyricMode( chosenComponents[0])

def lyLyricStructure( fileName):
    """ analyzes the document to check which of several structures in SH is used, returns a string """
    with open( fileName, 'r') as f:
        text=f.read()
        try:
            lyDocument=ly.document.Document( text)
            lyMusic=ly.music.document( lyDocument)
            lyScore = [i for i in lyMusic.find_children(ly.music.items.Score, depth=1)][0] # messy wasy of extracting object from generator 
            scoreComponents = [i for i in lyScore.find_children(ly.music.items.UserCommand)]
        except:
            print(f'cannot get score from {fileName:s}')
            return None

        # now a series of heuristic tests on components
        if len( lyFilterComponents( scoreComponents, ['verse'])) > 0: structure = 'verses'
        elif len( lyFilterComponents( scoreComponents, ['words'])) > 0: structure = 'mixed'
        else: structure = 'nowords'
        return structure
    

def lyLyrics( fileName):
    """ extract lyrics from lilypond score used in the SH form at least ... very heuristic in parts.
    returns a string with the lyrics, maybe including some extra details if they're available"""
    structure = lyLyricStructure( fileName)
    if structure is None:
        return None
    else:
        return lyricFunctions[ structure]( fileName) # dictionary lookup of function

def lyLyricVerses( fileName):
    """ return a string containing the lyrics from a verse-structured song in SH"""
    with open( fileName, 'r') as f:
        result = ''
        text=f.read()
        lyDocument=ly.document.Document( text)
        lyMusic=ly.music.document( lyDocument)
        lyScore = [i for i in lyMusic.find_children(ly.music.items.Score, depth=1)][0] # messy wasy of extracting object from generator 
        scoreComponents = [i for i in lyScore.find_children(ly.music.items.UserCommand)]
        verses=  lyFilterComponents( scoreComponents, ['verse'])
        for v in verses:
            lyricList = [i for i in v.find_children((ly.music.items.LyricText, ly.music.items.LyricItem))]
            result +='\n ' # make verses separate paragraphs
            followingDash = False # is previous value a dash, impacts spacing
            for l in lyricList:
                if isinstance( l, ly.music.items.LyricText):
                    if not followingDash: result += ' '
                    result += str(l.token)
                    followingDash = False
                else:
                    if str(l.token) == '--':
                        result +='--'
                        followingDash = True
    return result

fileList = glob.glob(lyricsdir+'*.ly')
#for f in fileList: print(f'{path.basename( f)[:-3]:s} {repr(lyLyricStructure(f)):s}')
    
