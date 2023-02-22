
import re
import ly.document
import ly.music
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


fileName = '/home/unimelb.edu.au/prayner/nonwork/fasola/shenandoah-harmony/WholeBook/Lilypond files/AHR274_Pomfret.ly'
filterList =['basswords']
f=open( fileName, 'r')
text=f.read()
f.close()
lyDocument=ly.document.Document( text)
lyMusic=ly.music.document( lyDocument)
lyScore = [i for i in lyMusic.find_children(ly.music.items.Score, depth=1)][0] # messy wasy of extracting object from generator 
scoreComponents = [i for i in lyScore.find_children(ly.music.items.UserCommand)]
chosenComponents = lyFilterComponents( scoreComponents, filterList)
#lyLyricsFromLyricMode( chosenComponents[0])
