__author__  =  'Jon K Peck'
__version__ =  '1.1'
version = __version__

# history
# 07-10-2021 add synonym and named entity search

import spss, spssaux
from extension import Template, Syntax, processcmd
import sys, re, os
from itertools import product

try:
    import nltk
except:
    print("""The nltk module is required in order to use this module.\n""")
    ver = int(spss.GetDefaultPlugInVersion()[4:])
    if ver < 280:
        print("""
*** Installation with SPSS Statistics Version 27 ***
This procedure requires several additional items. After installing it, do the following. 
Depending on your system setup, you might need to do these steps in Administrator mode.
*   Make sure that you have a registered Python 3 distribution matching the Statistics 
version you are using. For Statistics version 27, that would be Python 3.8. 
If you don't have this, go to Python Software Foundation and install from there. 
Don't install this over the distribution installed with Statistics. 
After installing it, go to Edit > Options > Files in Statistics and set 
this location for Python 3.
*   Open a command window, cd to the location of the Python installation, 
and install nltk and pyspellchecker from the PyPI site:
pip install nltk
pip install pyspellchecker
*   Start Python from that location and run this code.
import nltk
nltk.download()
This will display a table of items you can add to your installation. 
Select at least names, stopwords, wordnet, and vader_lexicon.
*   Optionally, go to spelling dictionary as mentioned above 
https://github.com/dwyl/english-words/blob/master/words.zip
and extract the words.txt file from words.zip.  
Specify that location when you run the procedure.
*   Install the SPSSINC TRANS extension command via the Statistics 
Exensions > Extension Hub menu.""")
    else:
        print("""
***Installation with SPSS Statistics Version 28 and Later ***
This procedure requires several additional items. After installing it, 
do the following. Depending on your system setup, you might need to 
do these steps in Administrator mode.  It is no longer necessary 
to install a separate Python distribution.
*   Start Statistics.  You might need to run it as Administrator 
depending on your security settings.
*   Open a syntax window and run the following commands
host command='"spssloc\statisticspython3.bat" -m pip install nltk'.
host command='"spssloc\statisticspython3.bat" -m pip install pyspellchecker'.
-   Replace spssloc with the full path of the location where SPSS Statistics 
is installed on your system.
-   Be sure to use the single quote character (') for the outer quotes 
in the command.  The double quotes (") are not necessary unless 
the SPSS location contains any blanks.
*   Run this code
begin program python3.
nltk.download()
end program.

This will bring up a window listing the packages available for nltk.  
*   Click on All Packages and choose at least 
names, stopwords, wordnet, and vader_lexicon.
*   Optionally, go to spelling dictionary 
https://github.com/dwyl/english-words/blob/master/words.zip
and extract the words.txt file 
from words.zip.  Specify that location when you run the procedure.
*   Install the SPSSINC TRANS extension command via the Statistics 
Extensions > Extension Hub menu.
""")
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
hasentitylistparams = {}

langabbrev = {'english':"en", "spanish":"es", "german":"de", "french":"fr", "portuguese": "pt"}

# main routine
def dotext(varnames=None, overwrite=False, stopwordslang="english", stemmerlang="english",
        dospelling=False, ignorenames=True, extradict=None, spsuffix="cor", language="english",
        dofreq=False, stem=False, freqcount=10, 
        doscores=False, scoresfile=None,
        dosent=False, stypes=None, ssuffixes=None,
        dosearch=False, searchwords=None, smode="anywords", swsuffix="ser", searchstem=False, 
            posp=None, displaysyn=False, searchlang="eng",
        doesearch=False, etype="alltypes", outsize=100, esuffix="eser",
        dolexicon=False, lexdsname=None,
        dostems=False, stemssuffix="stem"):
    
    global allnewnames, extraspelldict, laststopwordslang, sstopwords, stopwordslangg, stemmerlangg, stemmergg
    allnewnames = []
    
    if not any([dospelling, dofreq, dosent, dosearch, doesearch, dolexicon, doscores, dostems]):
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
        if (any([dospelling, dofreq, dosent, dosearch, dostems, doesearch])):
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
        searching(searchwords, smode, nameset, swsuffix, varnames, overwrite, searchstem, posp, displaysyn, searchlang)
        
    if doesearch:
        esearching(etype, esuffix, varnames, nameset, overwrite, outsize)
        
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

try:
    from nltk.corpus import wordnet as wn
except:
    print("installing wordnet")
    nltk.download("wordnet")
    
def searching(searchwords, smode, nameset, swsuffix, varnames, overwrite, searchstem, posp, displaysyn, searchlang):
    global haswordslistparams
    if searchwords is None:
        raise ValueError(_("A word search was specified, but no word list was given"))
    searchlang = searchlang.lower()
    if not searchlang in wn.langs():
        raise ValueError(f"Unsupported search language was specified: {searchlang}")
    outnames = " ".join(newnames(varnames, [swsuffix], nameset, overwrite))
    ###varnamesargs = ", ".join(varnames)
    customa = "criteria: " + " ".join(searchwords).replace(" - ", "-")
    searchitems = makesearch(searchwords, posp, searchlang)    # sideffects!
    if smode == "pattern":
        numwords = len(searchitems)
    else:
        numwords = 0
    varnames = " ".join(varnames)
    cmd = f"""spssinc trans result={outnames} type={numwords}
    /variables {varnames}
    /formula texta.haswordslist(<>)."""
    haswordslistparams["words"] = searchitems
    haswordslistparams["mode"] = smode
    haswordslistparams["searchstem"] = searchstem
    spss.Submit(cmd)
    spss.Submit("""VARIABLE ATTRIBUTE VARIABLES={0} ATTRIBUTE=search("{1}").
    MISSING VALUES {0} ("").""".format(outnames, customa))
    if displaysyn:
        rowlabels = []
        synonyms = []
        for synset in searchitems:
            items = []
            rowlabels.append(synset.rowlabel)
            for i, item in enumerate(synset.words):
                if isinstance(item, tuple):
                    items.append("(" + ", ".join(item) + ")")
                else:
                    items.append(item)
            synonyms.append(", ".join(items))
            
        spss.StartProcedure("Text Analysis Search")
        pt = spss.BasePivotTable("Search Synonyms", "SearchSynonyms")
        spss.AddProcedureFootnotes("Parenthesized synonyms are bigrams or trigrams")
        spss.AddProcedureFootnotes(f"Search language is {langsd[searchlang]}")
        pt.SimplePivotTable(rowlabels=rowlabels,
            collabels=["Word, Bigram, and Trigram Synonyms"],
            cells=synonyms)
        spss.EndProcedure()   

    # Any part of speech must come from this set  ('y' is converted to all parts).
    # There should be one character per segment of item, e.g., 2 for a bigram.
    
validposp  = set(['x', 'n','v','a', 'r', 's', None])
def validateposp(posp, length):
    
    posparts = list(posp.lower())   # e.g. nxv ==> ['n','x','v']
    if (len(posparts) < length):
        posparts += (length - len(posparts)) * 'x'
    if len(posparts) != length:
        raise ValueError(_(f"Invalid length for part of speech: {posp}, {length}"))
    
    for i in range(len(posparts)):
        if posparts[i] == "y":
            posparts[i] = ['n','v','a','r','s']
        elif posparts[i] == 'a':     # include that rarely used adjective variant form with 'a'
            posparts[i] = ['a', 's']
        if  set(posparts[i]) - validposp:
            raise ValueError(_(f"Invalid part of speech in : {posp}"))
    return posparts
        
class Word():
    length = 1
    
    def __init__(self, word, posp, lang):
        word = word.lower()
        self.text = word
        self.rowlabel = word + "(" + posp + ")"
        pos = validateposp(posp, 1)[0]
        if pos == "x":    # no synonyms
            self.words = set([word])
        else:
            if len(pos) == 1:                
                self.syns = wn.synsets(word, pos=pos[0], lang=lang)
            else:
                self.syns = wn.synsets(word, lang=lang)
            names = []
            if self.syns:  # there might not be any qualifying synonyms
                for syn in self.syns:
                    for item in syn.lemma_names(lang=lang):
                        names.append(item.replace("_", "-"))
            self.words = set(names + [word])
        
    # argument must be a sequence
    def isin(self, textlist):
        return any(item in self.words for item in textlist)
    
class Bigram():
    length = 2
    
    def __init__(self, bigram, posp, lang):
        bigram = bigram.lower()
        self.rowlabel = bigram + "(" + posp + ")"
        pos = validateposp(posp, 2)
        text = bigram.split('-')
        names = [[], []]
        # find the candidates for two two words and store all combinations
        # according to the part of speech specification
        for i in range(2):
            if pos[i] == "x":
                names[i].append(text[i])   # no synonyms
            else:
                if len(pos[i]) == 1:                
                    self.syns = wn.synsets(text[i], pos=pos[i][0], lang=lang)
                else:
                    self.syns = wn.synsets(text[i], lang=lang)                
                for syn in self.syns:
                    for item in syn.lemma_names(lang=lang):
                        names[i].append(item.replace("_", "-"))   #???
        self.words = list(product(set(names[0] + [text[0]]), set(names[1] + [text[1]])))
        
    def isin(self, textlist):
        return any(item in self.words for item in textlist)
    
class Trigram():
    length = 3
    
    def __init__(self, trigram, posp, lang):
        ###self.text = trigram.split("-")
        self.rowlabel = trigram + "(" + posp + ")"
        self.trigram = tuple(w.lower() for w in trigram)  #?
        pos = validateposp(posp, 3)
        text = trigram.split('-')
        names = [[], [], []]
        
        for i in range(3):
            if pos[i] == "x":
                names[i].append(text[i])
            else:
                if len(pos[i]) == 1:                
                    self.syns = wn.synsets(text[i], pos=pos[i][0], lang=lang)
                else:
                    self.syns = wn.synsets(text[i], lang=lang)                
                for syn in self.syns:
                    for item in syn.lemma_names(lang=lang):
                        names[i].append(item.replace("_", "-"))
            self.words = list(product(set(names[0] + [text[0]]), set(names[1] + [text[1]]), set(names[2] + [text[2]])))
        
    def isin(self, textlist):
        return any(item in self.words for item in textlist)

langs = [
    ('eng',	'english'),
    ('arb',	'arabic'),
    ('arb',	'arabic'),
    ('bul',	'bulgarian'),
    ('cat',	'catalan'),
    ('cmn',	'chinese (simplified)'),
    ('dan',	'danish'),
    ('ell',	'greek'),
    ('eus',	'basque'),
    ('fas',	'persian'),
    ('fin',	'finnish'),
    ('fra',	'french'),
    ('glg',	'galacian'),
    ('heb',	'hebrew'),
    ('hrv',	'croation'),
    ('ind',	'indonesian'),
    ('ita',	'italian'),
    ('jpn',	'japanese'),
    ('nld',	'dutch'),
    ('nno',	'norwegian'),
    ('nob',	'norwegian (bokmal)'),
    ('pol',	'polish'),
    ('por',	'portuguese'),
    ('slv',	'slovakian'),
    ('spa',	'spanish'),
    ('swe',	'swedish'),
    ('tha',	'thai')]
langsd = dict(langs)

def makesearch(items, posp, lang):
    """return list of lists of items as converted to lists of words, bigrams, or trigrams
    
    items is the list of terms, and posp is the part of speech:
    x none  no synonyms
    y any
    n noun
    v verb
    a adjective
    r adverb
    if part of speech is empty or None or x, do not search for synonyms
    for n-grams, the pos is listed for each item, e.g., nv or xn"""
    
    # hyphenation works for n-grams
    
    items, posp = restructure(items, posp)   # convert parethesized parts of speech to list and remove from items

    result = []        
    for i, item in enumerate(items):
        hyphencount = item.count("-")
        try:
            if hyphencount == 0:
                result.append(Word(item, posp[i], lang))
            elif hyphencount == 2:
                result.append(Trigram(item, posp[i], lang))
            elif hyphencount == 1:
                result.append(Bigram(item, posp[i], lang))
            else:
                raise ValueError("Invalid word list")
        except IndexError:
            raise ValueError(_("Too few part of speech items listed"))    

    # return list of input words or n-grams if no synonyms requested
    # The result is a list where each element is itself a list containing a single Word, Bigram, or Trigram object.
    # The objects contain the part-of-speech specification, but it will always be "-" and will, therefore, be ignored
    #if posp is None or posp.count("-") == len(posp):
        #return [[item] for item in result]
        
    return result

def restructure(items, posp):
    """convert paren parts of speech to separate list and remove
    return new items with ngrams resolved and posp lists"""
    
    # input has already been checked for both posp and parenthesized pos
    
    itemstr = "*".join(items)
    itemstr = re.sub(r"\*-\*", "-", itemstr)
    # 'direction*(*y*)*different-direction*(*nv*)*social-aspects*(*a*)*he-is-young*(*xxy*)*ideas*(*n*)'
    pos = re.findall(r"\*\(.*?\*\)", itemstr)  # find all parenthesized parts of speech  (nongreedy match)
    # ['y', 'nv', 'a', 'xxy', 'n']
    if len(pos) > 0:
        if posp is not None:
            raise ValueError(_("Parts of speech must be specified either in the words list or the POSP keyword but not both"))
        pos = [re.sub(r"\*\(\*|\*\)", "", po) for po in pos]
        itemstr = re.sub(r"\*\(.*?\*\)", "", itemstr)   # remove parenthesized parts of speech
        # 'direction*(*y*)*different-direction*(*nv*)*social-aspects*(*a*)*he-is-young*(*xxy*)*ideas*(*n*)'
    else:
        pos = posp   # no parenthesized pos found.  Use input list
    items = itemstr.split("*")
    # ['direction', 'different-direction', 'social-aspects', 'he-is-young', 'ideas']
    if pos is None or len(pos) == 0:
        pos = len(items) * ['x']
    if posp is not None and len(posp) == 1:
        pos = len(items) * posp        
    if len(items) != len(pos):
        raise ValueError(_("Missing part of speech or unclosed parenthesis in word list"))    
    return items, pos
    
                    
def esearching(etype, esuffix, varnames, nameset, overwrite, outsize):
    global hasentitylistparams
    #searchlang = searchlang.lower()
    #if not searchlang in wn.langs():
    #    raise ValueError(f"Unsupported search language was specified: {searchlang}")
    # types are not checked
    
    outnames = " ".join(newnames(varnames, [esuffix], nameset, overwrite))
    ###varnamesargs = ", ".join(varnames)
    varnames = " ".join(varnames)
    cmd = f"""spssinc trans result={outnames} type={outsize}
    /variables {varnames}
    /formula "texta.hasneslist(<>)"."""
    hasentitylistparams["etype"] = etype
    if etype.lower() != "alltypes":
        hasentitylistparams["regexp"] = re.compile("<" + etype.upper()[:3] + ">")
    else:
        hasentitylistparams["regexp"] = None
    spss.Submit(cmd)
    spss.Submit(f"""VARIABLE ATTRIBUTE VARIABLES={outnames} ATTRIBUTE=search("{etype}").
    MISSING VALUES {outnames} ("").""")


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
        Template("POSP", subc="SEARCH", ktype="str", var="posp", islist=True),
        Template("LANG", subc="SEARCH", ktype="str", var="searchlang"),
        Template("MODE", subc="SEARCH", ktype="str", var="smode",
            vallist=["anywords", "allwords", "pattern"]),
        Template("SUFFIX", subc="SEARCH", ktype="varname", var="swsuffix"),
        Template("STEM", subc="SEARCH", ktype="bool", var="searchstem"),
        Template("DISPLAYSYN", subc="SEARCH", ktype="bool", var="displaysyn"),
        
        Template("DOESEARCH", subc="ENTITYSEARCH", ktype="bool", var="doesearch"),
        Template("ETYPE", subc="ENTITYSEARCH", ktype="str", var="etype", islist=False),
        Template("SUFFIX", subc="ENTITYSEARCH", ktype="varname", var="esuffix", islist=False),
        Template("OUTSIZE", subc="ENTITYSEARCH", ktype="int", var="outsize", vallist=[1,]),
        
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
