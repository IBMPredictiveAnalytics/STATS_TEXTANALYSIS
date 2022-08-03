# text analysis functions
# These are meant to be used with the SPSSINC TRANS extension command

# Author: Jon K Peck
# History
# 24-jan-2021 Initial version
# 01-feb-2021 Add spell checker and createLexiconDataset
# 02-feb-2021 Add split file support
# 17-mar-2021 Output improvements
# 18-apr-2021 Weight support, n-gram improvements, more language support
# 03-jun-2021 surface exception if vader_lexicon is not installed
# Citations:
# nltk
# Steven Bird, Ewan Klein, and Edward Loper (2009). Natural Language Processing with Python. O'Reilly Media Inc.
# VADER sentiment analysis
# C.J. Hutto and Eric Gilbert, VADER: A Parsimonious Rule-based Model for
# Sentiment Analysis of Social Media Text
# Association for the Advancement of Artificial Intelligence (www.aaai.org)
# Spell checker from
# https://pypi.org/project/pyspellchecker/
# debugging
# makes debug apply only to the current thread
#try:
    #import wingdbstub
    #import threading
    #wingdbstub.Ensure()
    #wingdbstub.debugger.SetDebugThreads({threading.get_ident(): 1})
#except:
    #pass

import spss, spssdata, spssaux, re, nltk, sys

m = sys.modules["STATS_TEXTANALYSIS"]  # for referring to the global variables there

#from nltk.stem.lancaster import LancasterStemmer
#st = LancasterStemmer()
###pst = nltk.PorterStemmer()
###from nltk import SnowballStemmer


# Nltk notes:
# Use nltk.download('packagename') to add a package
# nltk.download('punkt') gets the sentence tokenizer
# tokens = nltk.sent_tokenize(text) into a list of sentences
# punkt as parameters as described here
# https://linuxhint.com/extract_sentences_nltk_python_module

extraspelldict = None

#*****************************************************************
#This function takes as input a string variable and produces frequency counts
#of words, bigrams (pairs of words) and trigrams (triples of words) ignoring case
#The variable name is case sensitive.
#Usage examples:
#begin program python3.
#import textanalysis
    
#textanalysis.freqs("comment")
#end program.    

#* stem words and display the 20 most frequent words, bigrams, and trigrams
#begin program python3.
#import textanalysis
    
#textanalysis.freqs("comment", stem=True, count=20)
#end program.
#*****************************************************************    

# freqslist handles a list of variables producing word counts for each

def freqslist(varlist, stem=False, stemcode=None, stemmerlang=None, count=10):
    vardict = spssaux.VariableDict(varlist)
    weightvar = spss.GetWeightVar()
    for v in varlist:
        freqs(v, vardict[v].VariableLabel, weightvar, stem, stemcode, stemmerlang, count)
        

def freqs(varname, label="", weightvar=None, stem=False, stemcode=None, stemmerlang=None, count=10):
    """Display word, bigram, and trigram counts
    
    varname is the text variable to analyze
    label is the variable label
    weightvar is the name of the weightvar or None
    stem indicates whether or not to stem words
    stemcode is the function for stemming
    stemmerlang is the stemming language
    counts is the number of instances to display
    """

    if weightvar:
        tofetch = [varname, weightvar]
    else:
        tofetch = varname

    allwords = []
    bigr = []
    trigr = []
    weights = []
    hastextcount = 0
    caseweight = 1    # unweighted
    
    # loop over cases and accumulate words, bigrams, and trigrams for frequency tables
    curs = spssdata.Spssdata(tofetch, names=False)
    for case in curs:
        t = case[0].rstrip()
        if len(t) == 0:
            continue
        hastextcount += 1
        if weightvar:
            caseweight = round(case[1])   # round returns an integer
        sentences = nltk.tokenize.sent_tokenize(t)
        # treat each sentence separately
        for s in sentences:
            wordlist = [w.lower() for w in nltk.word_tokenize(s)]
            if stem:
                words = [stemcode(w) for w in wordlist if w.isalpha()]
            else:
                words = [w for w in wordlist if w.isalpha()]
            if m.laststopwordslang != "none":
                words = [w for w in words if not w in m.sstopwords]
            allwords.append(caseweight * words)   # flatten later
            # replicate the n-grams according to the case weight
            for w in nltk.bigrams(words):
                if len(set(w)) == len(w):  # don't add it unless elements are unique
                    bigr.extend(w for i in range(caseweight))
            for w in nltk.trigrams(words):
                if len(set(w)) == len(w):
                    trigr.extend(w for i in range(caseweight))

    curs.CClose()
    
    
    #flatten the list
    allwords = [item for sublist in allwords for item in sublist]        
    if len(allwords) == 0:
        print("Variable {0} has no text".format(varname))
        return    
    fd = nltk.FreqDist(allwords)
    if weightvar and len(fd) == 0:
        print(_("The weighted counts are zero"))
        return
    
    bfd = nltk.FreqDist(bigr)
    tfd = nltk.FreqDist(trigr)
    
    pt = spss.StartProcedure("Text Analysis")
    spss.AddProcedureFootnotes("Case and stopwords are ignored")
    if stem:
        spss.AddProcedureFootnotes("Words have been stemmed using stemmer {0}".format(stemmerlang))
    else:
        spss.AddProcedureFootnotes("Words have not been stemmed")
    spss.AddProcedureFootnotes("{0} most common items".format(count))
    spss.AddProcedureFootnotes("{0} cases have text".format(hastextcount))
    if weightvar:
        spss.AddProcedureFootnotes("Frequencies are based on rounded weights")
    pt = spss.BasePivotTable("Word Frequencies for {0}\n {1} ".format(varname, label), "WordFrequencies")
    pt.SetDefaultFormatSpec(spss.FormatSpec.Count)
    labels, counts = zip(*fd.most_common(count))
    pt.SimplePivotTable(rowlabels=labels,
        collabels=["{}".format("Word Frequency")],
        cells=counts)
    
    if len(bfd) > 0:       
        labels, counts = zip(*bfd.most_common(count))
        if len(labels) > 0:
            labels = ["{0} {1}".format(item[0], item[1]) for item in labels]
            pt = spss.BasePivotTable("Bigram Frequencies for {0} \n {1}".format(varname, label), "BigramFrequencies")
            pt.SetDefaultFormatSpec(spss.FormatSpec.Count)
            pt.SimplePivotTable(rowlabels=labels,
                collabels=["Bigram Frequency"],
                cells=counts)
    else:
        print(_("No bigrams were found for variable {0}".format(varname)))
    
    if len(tfd) > 0:
        labels, counts = zip(*tfd.most_common(count))
        if len(labels) > 0:
            labels = ["{0} {1} {2}".format(item[0], item[1], item[2]) for item in labels]
            pt = spss.BasePivotTable("Trigram Frequencies for {0} \n {1}".format(varname, label), "TrigramFrequencies")
            pt.SetDefaultFormatSpec(spss.FormatSpec.Count)
            pt.SimplePivotTable(rowlabels=labels,
                collabels=["Trigram Frequency"],
                cells=counts)
    else:
        print(_("No trigrams were found for variable {0}".format(varname)))
    spss.EndProcedure()    

try:
    from nltk.sentiment import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
except:
    # Can't raise exception here as exception details will be suppressed higher up
    print("*** The vader_lexicon file was not found.  Please use nltk.download() to install it")


#*****************************************************************
#This function takes a string variable as input and produces
#up to four sentiment scores for each case.  It is meant to be used with
#SPSSINC TRANS.  See the VADER document cited above for details.

#spssinc trans result = negative neutral positive compound
#/formula "textanalysis.sentscores(comment)".
#*****************************************************************

def sentscoreslist(*vartexts):
    
    results = []
    for t in vartexts:
        results.extend(sentscores(t, m.sentimentparams['types']))
    return results

def sentscores(text, types=None):
    """return list of sentiment scores for string text
    
    types is a list of types to return.  It defaults to
    [negative, neutral, positive, compound] in that order"""
    
    text = text.rstrip()
    stdtypes = ['neg', 'neu', 'pos', 'compound']
    if types is None:
        ttypes= stdtypes
    else:
        ttypes = types.split()
    if len(text) == 0:
        return len(ttypes) * [None]    
    # map 'comp' extension to s dictionary key 'compound'
    try:
        ttypes[ttypes.index('comp')] = 'compound'
    except:
        pass
    
    ###wordlist = nltk.word_tokenize(text)
    ###words = [w for w in wordlist if w.isalpha()]
    ###allwords2Cased = [w for w in words if not w.lower() in sstopwords]    
    s = sia.polarity_scores(text)
    return list(s[item] for item in stdtypes if item in ttypes)

#*****************************************************************
#This function takes a string variable as input and returns values indicating whether particular
#words are found in each.  It is meant to be used with SPSSINC TRANS.
#Usage examples:
#Create variable hascontacts that is 1 or 0 as the input has the word "contacts" in it
#spssinc trans result = hascontacts
#/formula "textanalysis.haswords(comment, 'contacts')".
#Note that the word(s) to search for must be quoted differently from the formula quotes.

#Create variable indicating whether each case has both 'contacts' and 'personal' in the
#text in any order.  Note that the list is enclosed in square brackets
#spssinc trans result = hascontactsandpersonal
#/formula "textanalysis.haswords(Q6, ['contacts','personal'], mode='all')".

#Create a variable for each listed word.  There are as many output words as
#words in the list.
#spssinc trans result = hascontacts haspersonal
#/formula "textanalysis.haswords(Q6, ['contacts','personal'], mode='each')".
#*****************************************************************
    

# Find tokens in text
# stemming not supported here

from functools import lru_cache

@lru_cache
def bigram(textlist):
    return tuple(nltk.bigrams(textlist))

@lru_cache
def trigram(textlist):
    return tuple(nltk.trigrams(textlist))



###def haswordslist(*varnames, words, mode='anywords', searchstem="False"):
def haswordslist(*varnames):
    result = []

    for v in varnames:
        result.append(haswords(v, 
            m.haswordslistparams['words'], 
            m.haswordslistparams['mode'], 
            m.haswordslistparams['searchstem']))

    return result

        
def haswords(text, words, mode="anywords", searchstem=False):
    """Return True or False for words in text
    
    text is the string to search
    words is a list of words and n-grams to look for (ignoring case).  It can also be a simple string
    mode is 
        "pattern" - return a string of 1's and 0's
        "allwords" - return True if has all words in words
        "anywords" - return True if any of the words appear
    searchstem specifies whether words in the text should be stemmed before searching"""
    ###from STATS_TEXTANALYSIS import Word, Bigram, Trigram
    
    # The stemmer object is passed behind the scenes.
    stemcode = m.stemmergg
    
    if len(text.rstrip()) == 0:
        return ""
    textlist = tuple(nltk.word_tokenize(text.lower()))
    if searchstem:
        textlist = tuple(stemcode(w) for w in textlist if w.isalpha())
    if not spssaux._isseq(words):   #???
        words = [words]
    # each item in words is a list with nonsynonyms being singletons
    # and synonym lists being possibly multiple
    # any synonym occurence in the list makes "all" true
    scan = []
    for w in words:
        if isinstance(w, m.Word):
            scan.append(w.isin(textlist))
        elif isinstance(w, m.Bigram):
            scan.append(w.isin(bigram(textlist)))
        else:
            scan.append(w.isin(trigram(textlist)))
    if mode == "anywords":
        return any(scan)
    elif mode == "allwords":
        return all(scan)
    elif mode == "pattern":
        return "".join(item and "1" or "0" for item in scan)
    #else:
        #return scanlist

def stems(*texts):
    """return list of stemmed text for texts"""
    
    stemcode = m.stemmergg
    result = []
    for v in texts:
        if len(v.rstrip()) == 0:
            result.append("")
        else:
            textlist = nltk.word_tokenize(v.lower())
            textlist = [stemcode(w) for w in textlist]
            result.append(" ".join(textlist))
    return result

# get chunks for Named Entities
#def get_continuous_chunks(text, netype, binary=True):
    #"""Return list of Named Entities found in text
    
    #text is the text to search
    #netype is the entity type, which can be "all" or a specific type
    #binary is True or False for chunking"""
    
    
    #chunked = nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(text)), binary)
    #continuous_chunk = []
    #current_chunk = []

    #for i in chunked:
        #if type(i) == nltk.Tree:
            ####if netype == "all":
            #current_chunk.append("<" + i.label()[:3] + ">")
            #current_chunk.append(" ".join([token for token, pos in i.leaves()]))
        #elif current_chunk:
            ## remove redundant entity type ids
            #if len(current_chunk) > 1:
                #cc = [current_chunk[0]]
                #cc.extend(item for item in current_chunk[1:] if item != cc[0])
                #current_chunk = cc
            #named_entity = " ".join(current_chunk)
            #if named_entity not in continuous_chunk:
                #continuous_chunk.append(named_entity)
                #current_chunk = []
        #else:
            #continue

    #if continuous_chunk:
        #named_entity = " ".join(current_chunk)
        #if named_entity not in continuous_chunk:
            #continuous_chunk.append(named_entity)

    #return continuous_chunk

def get_continuous_chunks(text, netype, binary=True):
    """Return list of Named Entities found in text
    
    text is the text to search
    netype is the entity type, which can be "all" or a specific type
    binary is True or False for chunking"""
    
    
    chunked = nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(text)), binary)
    chunked.append("<DONE>")    # make sure to get the last tree
    continuous_chunk = []
    current_chunk = []
    ctype = None

    for i in chunked:
        if type(i) == nltk.Tree:
            if ctype is None:
                ctype = i.label()[:3]
            current_chunk.append(" ".join([token for token, pos in i.leaves()]))
        elif current_chunk:
            named_entity = "<" + ctype + ">" +" ".join(current_chunk)
            if named_entity not in continuous_chunk:
                continuous_chunk.append(named_entity)
            current_chunk = []
            ctype = None
    return continuous_chunk
    
def hasneslist(*text):
    """Evaluate text for named entities
    
            ctype = None
        else:
            continue

    #if continuous_chunk:
        #named_entity = "<" + ctype + ">" + " ".join(current_chunk)
        #if named_entity not in continuous_chunk:
            #continuous_chunk.append(named_entity)
    args is a list of variables"""
    
    result = []

    for t in text:
        result.append(hasnes(t, 
            m.hasentitylistparams["etype"], m.hasentitylistparams["regexp"]))
    return result    
    
    
def hasnes(text, etype, ecompiled):
    """return list of entities found
    
    etype is the entity type to look for"""
    
    # binary choice not yet implemented
    
    if len(text.rstrip()) == 0:
        return ""    
    
    allent = get_continuous_chunks(text, etype, binary=False)
    if etype == "alltypes":
        return "/".join(item for item in allent if len(item) > 0)
    else:
        return "/".join(item for item in allent if len(item) > 0 and re.match(ecompiled, item) is not None)

    
# ********************************************************************    
# This function creates an SPSS dataset containing the words and Vader
# scores for the sentiment lexicon.  It includes any added words
# Usage example:
# begin program python3.
# import textanalysis
# textanalysis.createLexiconDataset()
# end program.
# ********************************************************************

def createLexiconDataset(name="lexicon"):
    
    activeds = spss.ActiveDataset()
    if activeds == "*":
        raise ValueError("""Stopping.  The active dataset is unnamed.""")
    curs = spssdata.Spssdata(accessType='n')
    curs.append(spssdata.vdef("word", 30))
    curs.append(spssdata.vdef("score", 0))
    curs.commitdict()
    
    for item in sia.lexicon.items():
        curs.appendvalue('word', item[0])
        curs.appendvalue('score', item[1])
        curs.CommitCase()
    curs.CClose()
    # can't reactivate an empty active dataset
    try:
        spss.Submit(f"""DATASET NAME {name}.
DATASET ACTIVATE {activeds}.""")
    except:
        pass
    
# ********************************************************************
# This function adds words with scores or changes existing scores
# Usage example
# begin program python3.
# import textanalysis
# addSentimentScores("c:/data/sentiments.txt")
# end program.

# file format is csv (no header)
# word score
# Note that words are lowercased
# ********************************************************************

def terms(negationfile, negationdsname, emphasisfile, emphasisdsname):
    """Execute doterms actions"""
    
    addNegationTerms(negationfile)
    addEmphasisTerms(emphasisfile)
    createSpecialDatasets([negationdsname, emphasisdsname])
    
    
def addSentimentScores(filespec):
    """ add a file of word, score pairs to the sentiment lexicon
    
    filespec specifies the file containing the pairs.
    SPSS file handles are supported"""

    if filespec is None:
        return
    
    filespec = spssaux.FileHandles().resolve(filespec)
    wordcount = 0
    badcount = 0
    with open(filespec) as f:
        for line in f:
            try:
                word, score = line.split()
                score = float(score)
            except:
                badcount += 1
                if badcount <= 10:
                    newline = "\n"
                    print(f"""invalid sentiment score input: {line.replace(newline, "")}""")
            else:
                sia.lexicon[word.lower()] = score
                wordcount += 1
    print ("*** words added to lexicon from {0}: {1}".format(filespec, wordcount))
    if badcount > 0:
        print(f"*** Badlines: {badcount}")
    
def addNegationTerms(filespec):
    """Add terms in filespec to negate terms set"""
    
    if filespec is None:
        return
    
    wordcount = 0
    with open(filespec) as f:
        for line in f:
            sia.constants.NEGATE.add(line.replace("\n", "").lower())   # stripping \n if present
            wordcount += 1    
    print(f"Negative terms processed: {wordcount}")
    
def addEmphasisTerms(filespec):
    """Add terms with scores to emphasis term dict"""
    
    if filespec is None:
        return
    
    wordcount = 0
    badcount = 0
    with open(filespec) as f:
        for line in f:
            try:
                word, score = line.split()
                score = float(score)
            except:
                badcount += 1
                if badcount <= 10:
                    print(f"invalid emphasis score input: {line}")
            else:
                sia.constants.BOOSTER_DICT[word.lower()] = score
                wordcount += 1    
    print(f"Emphasis terms processed: {wordcount}")
    if badcount > 0:
        print(f"Bad emphasis terms: {badcount}")
    
def createSpecialDatasets(names):
    """create negate and emphasis datasets named as per entries in names"""
    
    activeds = spss.ActiveDataset()
    if activeds == "*" and any(names):
        raise ValueError("""The active dataset must have a name to create negative or emphasis dataset.""")
    
    if names[0]:         # negate terms dataset
        curs = spssdata.Spssdata(accessType='n')
        curs.append(spssdata.vdef("negativeWord", 30))
        curs.commitdict()
        
        for item in sorted(sia.constants.NEGATE):
            curs.appendvalue('negativeWord', item)
            curs.CommitCase()
        curs.CClose()
        # if the active dataset is empty as on startup, it can't be re-activated
        try:
            spss.Submit(f"""DATASET NAME {names[0]}.
DATASET ACTIVATE {activeds}.""")
        except:
            pass
    
    if names[1]:  # emphasis terms dataset
        curs = spssdata.Spssdata(accessType='n')
        curs.append(spssdata.vdef("emphasisWord", 30))
        curs.append(spssdata.vdef("score", 0))
        curs.commitdict()        
        for item in sorted(sia.constants.BOOSTER_DICT.items()):
            curs.appendvalue('emphasisWord', item[0])
            curs.appendvalue('score', item[1])
            curs.CommitCase()        
        curs.CClose()
        spss.Submit(f"""DATASET NAME {names[1]}.
DATASET ACTIVATE {activeds}.""")
        
    
extraspelldict = []
spell = None
dictlang = None
names = set(nltk.corpus.names.words())
try:
    import spellchecker
    ###spell = spellchecker.SpellChecker(language=None, case_sensitive=False)
except:
    print("""The spellcorrection function requires the spellchecker module.  Install as pip install spellchecker.""")
    raise

# ********************************************************************
# This function accepts a list of variable names and corrects spelling
# according to Levenshtein distance against a built-in word list
# Usage example:
# spssinc trans result = ccomment c secondcomment type=100
# /formula "textanalys.spellcorrection(comment, secondcomment)".
# argument excludenames causes recognized names to be ignored (mostly first names).
#
# An extra spelling dictionary can be specified with the extradict argument.
# It is just a text file listing words to be added, however those words will
# not have frequency weights in the correction algorithms - or, rather, they
# will all have a weight of 1, assuming no repetition
# One source of a large collection of words is
# https://github.com/dwyl/english-words/blob/master/words.zip
# extract the words.txt file from words.zip.
# You can also get just words with alpha characters there.
# That location also contains words for some other languages
# A corpus of text where the words are spelled correctly can also be used,
# and frequency weights will be based on that.

###def spellcorrection(*args, excludenames=True, excludestopwords=False, extradict=None, language="en"):

@lru_cache(maxsize=2048)
def cachedcorrection(spell, w):
    wr = w.rstrip()
    if len(wr) <= 1:         # or wr[0] in ['.', ',', ';', ':', '!', '?']:
        outword = w
    else:
        wlower = w.lower()

        # Preserve case of first letter if letter is the same after correction
        # Corrections always come back in lower case

        outword = spell.correction(w)
        if outword[0] == wlower[0]:
            outword = w[0] + outword[1:]    
    return outword
    
def spellcorrection(*args):
    """Check spelling of each arg value and return corrected text
    
    excludenames specifies whether names are checked"""
    

    global extraspelldict, spell, dictlang
    
    excludenames = m.spellcorrectionparams['excludenames']
    extradict = m.spellcorrectionparams['extradict']
    language = m.spellcorrectionparams['language']
    stopwords = m.spellcorrectionparams['stopwords']
    
    if spell is None or language != dictlang:
        spell = spellchecker.SpellChecker(language=language, case_sensitive=False)
        dictlang = language
    
    if extradict != "":
        extradictx = spssaux.FileHandles().resolve(extradict)
        if not extradictx in extraspelldict:
            print("""Loading supplemental spell dictionary: {0}.
            It will be used for the duration of this session.""".format(extradictx))
            try:
                spell.word_frequency.load_text_file(extradictx)
                extraspelldict.append(extradictx)
            except:
                raise ValueError(_("Extra spelling dictionary not found: {0}").format(extradictx))
    
    vout = []  # for corrected list for each variable checked
    for v in args:
        v = v.rstrip() + ' '   # always need a terminator
        if len(v) <= 1:        # spell check "corrects" empty string to "i"
            vout.append('')
            continue

        outwords = []
        vs = re.split("([ ,\.]+)", v)   # includes split character in list, hence the append below
        for i, w in enumerate(vs):
            if i % 2 == 0:    # the word
                if len(w) == 0:
                    continue
                wl = w.lower()
                if wl in stopwords or (excludenames and wl in names):
                    outwords.append(w + vs[i+1])
                    continue                
                outword = cachedcorrection(spell, w)
                outwords.append(outword + vs[i+1])
        vout.append("".join(outwords))
    return vout
                
        
        
    
    
