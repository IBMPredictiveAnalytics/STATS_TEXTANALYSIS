# STATS TEXTANALYSIS
## Extension command for working with text data
This procedure provides tools for working with text variables.  It provides frequencies, sentiment analysis,
searching, and spelling checks.

---
Requirements
----
- IBM SPSS Statistics 27 or later and the corresponding IBM SPSS Statistics-Integration Plug-in for Python.


---
Installation intructions
----
1. Open IBM SPSS Statistics
2. Navigate to Utilities -> Extension Bundles -> Download and Install Extension Bundles
3. Search for the name of the extension and click Ok.
4. It also requires several Python modules not installed with the procedure and the
SPSSINC TRANS extension command.  
See the dialog or syntax help after it is installed.

---
Tutorial
----

### Installation Location

Analyze →

&nbsp;&nbsp;Descriptive Statistics →

&nbsp;&nbsp;&nbsp;&nbsp;Text Analysis 

### UI
<img width="998" alt="image" src="https://user-images.githubusercontent.com/19230800/194338536-02738ae6-a2d6-41b4-b3fb-4b80005b3b61.png">
<img width="998" alt="image" src="https://user-images.githubusercontent.com/19230800/194338583-f0559ceb-4dcc-4b9d-8674-dd19187042d7.png">
<img width="998" alt="image" src="https://user-images.githubusercontent.com/19230800/194338612-564aa2e8-33b8-47a8-8d48-c2530cd4d985.png">
<img width="998" alt="image" src="https://user-images.githubusercontent.com/19230800/194338636-2282d6b2-5fdc-47b8-93d4-efaf89779b57.png">
<img width="998" alt="image" src="https://user-images.githubusercontent.com/19230800/194338660-9315e284-8bd1-48a7-af7c-1cc12d82922a.png">
<img width="998" alt="image" src="https://user-images.githubusercontent.com/19230800/194338685-bff2aa73-ccdc-4db5-9d59-34187adb789d.png">

### Synatax

Example:

```
STATS TEXTANALYSIS VARIABLES=x OVERWRITE=NO STOPWORDSLANG=english
  STEMMERLANG=english
 /SPELLING DOSPELLING=NO DICTLANGUAGE=ENGLISH
 /FREQUENCIES DOFREQ=YES STEM=NO COUNT=10
 /SENTIMENT DOSENT=YES TYPES=NEG COMP  SUFFIXES=neg comp
 /SEARCH DOSEARCH=NO MODE=ANYWORDS
 /ENTITYSEARCH DOESEARCH=NO
 /LEXICON DOLEXICON = NO
 /WORDSCORES DOSCORES=NO
 /SPECIALTERMS DOTERMS=YES
 /STEMS DOSTEMS=NO.
```

### Output

<img width="181" alt="image" src="https://user-images.githubusercontent.com/19230800/194566053-cd431ce5-504a-467a-87bf-1e577a79d69a.png">
<img width="201" alt="image" src="https://user-images.githubusercontent.com/19230800/194566100-ec3402e6-0ded-47e5-bb5c-217a1606f53a.png">
<img width="224" alt="image" src="https://user-images.githubusercontent.com/19230800/194566144-0393627e-d08a-4696-8caf-d65a1496090c.png">


License
----

- [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
                              
Contributors
----

  - Jon K Peck
