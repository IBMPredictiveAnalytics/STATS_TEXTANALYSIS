__author__  =  'Jon K Peck'
__version__ =  '1.0.2'
version = __version__

# history

import spss, spssaux
from extension import Template, Syntax, processcmd
import sys, re

try:
    import nltk
except:
    print("""The nltk module is required in order to use this module.
    install using
    pip -m install nltk
    Then use nltk.download() to add specific packages including
    at least stopwords and names
    
    If numpy errors occur, update the numpy module using
    pip install  numpy==1.19.5""")
    raise

from nltk import SnowballStemmer
import texta

extraspelldicts = []
scoresfiles = []
allnewnames = []
laststopwordslang = ""
sstopwords = set()
stopwordslangg = ""
stemmerlangg = ""
stemmergg = None
searchstemg = False
haswordslistparams = {}
spellcorrectionparams = {}
sentimentparams = {}

langabbrev = {'english':"en", "spanish":"es", "german":"de", "french":"fr", "portuguese": "pt"}

# main routine
def dotext(varnames=None, overwrite=False, stopwordslang="english", stemmerlang="english",
        dospelling=False, ignorenames=True, extradict=None, spsuffix="cor", language="english",
        dofreq=False, stem=False, freqcount=10, 
        doscores=False, scoresfile=None,
        dosent=False, stypes=None, ssuffixes=None,
        dosearch=False, searchwords=None, smode="anywords", swsuffix="ser", searchstem=False,
        dolexicon=False, lexdsname=None,
        dostems=False, stemssuffix="stem"):
    
    global allnewnames, extraspelldict, laststopwordslang, sstopwords, stopwordslangg, stemmerlangg, stemmergg
    allnewnames = []
    
    if not any([dospelling, dofreq, dosent, dosearch, dolexicon, doscores, dostems]):
        raise ValueError(_("No actions were specified for the command"))
    
    language = langabbrev[language.lower()]
    # varnames must not be None if spellcheck, sentiment, or search is used
    if varnames is not None:
        # check whethr variable names are legal Python identifiers
        badnames = [name for name in varnames if not name.isidentifier()]
        if badnames:
            raise ValueError(_("These variable names are not valid in Python.  Please rename.\n{0}".format(" ".join(badnames))))
        vardict = spssaux.VariableDict()
        if any(vardict[v].VariableType == 0 for v in varnames):
            raise ValueError(_("A numeric variable was found in the variable list"))
        nameset = set(vardict.variables)
        # nameset will be updated as new variables are created
        if stopwordslang != laststopwordslang:
            if stopwordslang != "none":
                sstopwords = frozenset(nltk.corpus.stopwords.words(stopwordslang))
            else:
                sstopwords = frozenset(["none"])
            laststopwordslang = stopwordslang        
    else:
        if (any([dospelling, dofreq, dosent, dosearch, dostems])):
            raise ValueError(_("""A task requiring a variable list was specified, but no list was given"""))
        
    stemmergg = SnowballStemmer(stemmerlang).stem
    stemmerlangg = stemmerlang
    ###searchstemg = searchstem

    #spell checking
    if dospelling:
        spelling(spsuffix, varnames, nameset, ignorenames, overwrite, extradict, vardict, language)
        
    if doscores:
        if scoresfile is None:
            raise ValueError(_("A scores file load was required, but no file name was specified"))
        texta.addSentimentScores(scoresfile)
    
    if dofreq:
        texta.freqslist(varnames, stem=stem, stemcode=stemmergg, stemmerlang=stemmerlang, count=freqcount)
        
    if dosent:
        sentiment(stypes, ssuffixes, nameset, varnames, overwrite)
    
    if dosearch:
        searching(searchwords, smode, nameset, swsuffix, varnames, overwrite, searchstem)
        
    activeds = spss.ActiveDataset()
    if dolexicon:
        if activeds == "*" and dolexicon:
            raise ValueError(_("The active dataset must have a name to create a lexicon."))
        if lexdsname is None:
            raise ValueError(_("No dataset name was specified for the lexicon dataset"))
        texta.createLexiconDataset(lexdsname)
        spss.Submit("dataset activate {0}".format(activeds))
        
    if dostems:
        stemming(varnames, nameset, overwrite, stemssuffix, vardict)
    # report variable creation or modification
    report(allnewnames)

def sentiment(stypes, ssuffixes, nameset, varnames, overwrite):
    
    global sentimentparams
    
    ssdict = {"neg": "neg", "neu":"neu", "pos":"pos", "comp":"comp"}
    if stypes is None:
        stypes = ["neg", "neu", "pos", "comp"]
    if ssuffixes is None:
        ssuffixes = [ssdict[item] for item in stypes]
    if len(stypes) != len(ssuffixes):
        raise ValueError("Number of sentiment suffixes is different from Number of sentiment types.")
    sdict = dict(zip(stypes, ssuffixes))
    outnames = " ".join(newnames(varnames, ssuffixes, nameset, overwrite))
    varnamesargs = ", ".join(varnames)
    stypesargs = " ".join(stypes)
    sentimentparams['types'] = stypesargs
    cmd = """spssinc trans result={outnames} type=0
        /formula texta.sentscoreslist({varnamesargs}).""".format(**locals())
    spss.Submit(cmd)

def searching(searchwords, smode, nameset, swsuffix, varnames, overwrite, searchstem):
    global haswordslistparams
    if searchwords is None:
        raise ValueError(_("A word search was specified, but no word list was given"))
    outnames = " ".join(newnames(varnames, [swsuffix], nameset, overwrite))
    varnamesargs = ", ".join(varnames)
    ###searchwordsargs = "'" + " ".join(searchwords) + "'"
    customa = "criteria: " + " ".join(searchwords).replace(" - ", "-")
    searchitems = makesearch(searchwords)    # sideffects!
    if smode == "pattern":
        numwords = len(searchitems)
    else:
        numwords = 0

    cmd = """spssinc trans result={outnames} type={numwords}
    /formula texta.haswordslist({varnamesargs}).""".format(**locals())
    haswordslistparams["words"] = searchitems
    haswordslistparams["mode"] = smode
    haswordslistparams["searchstem"] = searchstem
    spss.Submit(cmd)
    spss.Submit("""VARIABLE ATTRIBUTE VARIABLES={0} ATTRIBUTE=search("{1}").
    MISSING VALUES {0} ("").""".format(outnames, customa))    

class Word():
    def __init__(self, word):
        self.word = word.lower()
        
    def isin(self, textlist):
        return self.word in textlist
    
class Bigram():
    def __init__(self, bigram):
        self.bigram = tuple(w.lower() for w in bigram)
        
    def isin(self, textlist):
        return self.bigram in textlist
    
class Trigram():
    def __init__(self, trigram):
        self.trigram = tuple(w.lower() for w in trigram)
        
    def isin(self, textlist):
        return self.trigram in textlist

def makesearch(items):
    """return list of items as converted to words, bigrams, or trigrams"""
    
    result = []
    i = 0
    items.extend([None, None, None])
    while items[i] is not None:
        if items[i+1] != "-":
            result.append(Word(items[i]))
            i += 1
        elif items[i+1] == "-" and items[i+3] == "-":
            result.append(Trigram(tuple([items[i], items[i+2], items[i+4]])))
            i += 5
        elif items[i+1] == "-":
            result.append(Bigram(tuple([items[i], items[i+2]])))
            i += 3
        else:
            raise ValueError("Invalid word list")
    return result

def spelling(spsuffix, varnames, nameset, ignorenames, overwrite, extradict, vardict, language):
    """Do spelling check"""
    global spellcorrectionparams
    
    outnames = " ".join(newnames(varnames, [spsuffix], nameset, overwrite))
    varnamescomma = ", ".join(varnames)
    ###outsizes = [item.VariableType +10 for item in vardict.Variables]
    outsizes = " ".join([str(v.VariableType + 10) for v in vardict if v in varnames])
    if extradict is None:
        xtra = ""
    else:
        ###xtra = """, extradict='{extradict}'""".format(**locals())
        xtra = extradict
    spellcorrectionparams['excludenames'] = ignorenames
    spellcorrectionparams['extradict'] = xtra
    spellcorrectionparams['language'] = language
    spellcorrectionparams['stopwords'] = sstopwords
    cmd = '''SPSSINC TRANS RESULT= {outnames} TYPE={outsizes}
    /FORMULA 
    texta.spellcorrection({varnamescomma}).'''.format(**locals())
    spss.Submit(cmd)
    
def stemming(varnames, nameset, overwrite, suffix, vardict):
    """Produce stemmed variables"""
    
    outnames = " ".join(newnames(varnames, [suffix], nameset, overwrite))
    outsizes = " ".join([str(v.VariableType) for v in vardict if v in varnames])
    varnamesargs = ",".join(varnames)

    cmd = """spssinc trans result={outnames}  TYPE={outsizes}
        /formula "texta.stems({varnamesargs})".""".format(**locals())
    spss.Submit(cmd)    
    
        
def newnames(varnames, suffixes, nameset, overwrite):
    """Return list of modified varnames with extension
        
    varnames is a list of variable names to modify.
    suffix is a list of suffixes to be appended to each name.
    if the suffix is not blank, it is preceded by "_".
    nameset is a set of the existing names.
    overwrite indicates whether existing names can be overwritten.
    
    If varname+suffix does not exist in vardict, that is returned
    If it does and overwrite = False, a numerical suffix is tried until the name avoids a collision
    newnames is updated with the generated names
    
    It is assumed that the new name will always fit within the 64-byte limit
    on names"""
    
    global allnewnames
    
    outnames = []
    for v in varnames:
        for s in suffixes:
            newname = v + (s != "" and "_" or "")  + s
            digits = 1
            while overwrite == False and newname in nameset:
                newname = v + (s != "" and "_" or "") + s + str(digits)
                digits += 1
            nameset.add(newname)
            outnames.append(newname)
    allnewnames.extend(outnames)
    return outnames

def report(newnames):
    """Display table of new or overwritten variables
    
    newnames is the list of variables"""
    
    if len(newnames) == 0:
        print(_("No variables were created or modified by STATS TEXTANALYSIS"))
        return
    
    spss.StartProcedure("Text Analysis")
    pt = spss.BasePivotTable(_("New or Modified Variables"), "Newvars")
    pt.SimplePivotTable(rowlabels=[str(i) for i in range(1, len(newnames) + 1)], collabels=[_("Variables")], cells=newnames)
    spss.EndProcedure()
    
    
def  Run(args):
    """Execute the STATS TEXTANALYSIS command"""

    args = args[list(args.keys())[0]]
    ###print args   #debug

    oobj = Syntax([
        Template("VARIABLES", subc="",  ktype="existingvarlist", var="varnames", islist=True),
        Template("OVERWRITE", subc="", ktype="bool", var="overwrite"),
        Template("STOPWORDSLANG", subc="", ktype="str", var="stopwordslang",
            vallist=['english', 'arabic', 'azerbaijani', 'danish', 'dutch', 'finnish', 'french', 
            'german', 'greek', 'hungarian', 'indonesian', 'italian', 'kazakh', 'nepali', 
            'none', 'norwegian', 'portuguese', 'romanian', 'russian', 'slovene', 
            'spanish', 'swedish', 'tajik', 'turkish']),
        Template("STEMMERLANG", subc="", ktype="str", var="stemmerlang",
            vallist=['arabic', 'danish', 'dutch', 'english', 'finnish', 'french', 
                'german', 'hungarian', 'italian', 'norwegian', 'porter', 'portuguese', 
                'romanian', 'russian', 'spanish', 'swedish']),
        
        Template("DOSPELLING", subc="SPELLING", ktype="bool", var="dospelling"),
        Template("EXCLUDENAMES", subc="SPELLING", ktype="bool", var="ignorenames"),
        Template("EXTRADICT", subc="SPELLING",  ktype="literal", var="extradict", islist=False),
        Template("SUFFIX", subc="SPELLING", ktype="varname", var="spsuffix", islist=False),
        Template("DICTLANGUAGE", subc="SPELLING", ktype="str", var="language",
            vallist=['english','spanish','german','french','portuguese']),
        
        Template("DOFREQ", subc="FREQUENCIES", ktype="bool", var="dofreq"),
        Template("STEM", subc="FREQUENCIES", ktype="bool", var="stem"),
        Template("COUNT", subc="FREQUENCIES", ktype="int", var="freqcount"), 

        Template("DOSENT", subc="SENTIMENT", ktype="bool", var="dosent"),
        Template("TYPES", subc="SENTIMENT", ktype="str", var="stypes", islist=True,
            vallist=['neg', 'neu', 'pos', 'comp']),
        Template("SUFFIXES", subc="SENTIMENT", ktype="varname", var="ssuffixes",
            islist=True),
        
        Template("DOSCORES", subc="WORDSCORES", ktype="bool", var="doscores"),
        Template("FILE", subc="WORDSCORES", ktype="literal", var="scoresfile"),        
                  
        Template("DOSEARCH", subc="SEARCH", ktype="bool", var="dosearch"),
        Template("WORDS", subc="SEARCH", ktype="str", var="searchwords", islist=True),
        Template("MODE", subc="SEARCH", ktype="str", var="smode",
            vallist=["anywords", "allwords", "pattern"]),
        Template("SUFFIX", subc="SEARCH", ktype="varname", var="swsuffix"),
        Template("STEM", subc="SEARCH", ktype="bool", var="searchstem"),
        
        Template("DOLEXICON", subc="LEXICON", ktype="bool", var="dolexicon"),
        Template("DSNAME", subc="LEXICON", ktype="varname", var="lexdsname"),
    
        Template("DOSTEMS", subc="STEMS", ktype="bool", var="dostems"),
        Template("SUFFIX", subc="STEMS", ktype="varname", var="stemssuffix")])
        
    #debugging
    try:
        import wingdbstub
        if wingdbstub.debugger != None:
            import time
            wingdbstub.debugger.StopDebug()
            time.sleep(2)
            wingdbstub.debugger.StartDebug()
    except:
        pass

    #enable localization
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg

    # A HELP subcommand overrides all else
    if "HELP" in args:
        #print helptext
        helper()
    else:
        processcmd(oobj, args, dotext)

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print(("Help file not found:" + helpspec))
try:    #override
    from extension import helper
except:
    pass        
