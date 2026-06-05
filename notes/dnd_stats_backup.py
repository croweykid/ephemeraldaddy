
DND_STAT_PREDICTORS = { #mostly currently theoretical, just based on lore - unless otherwise indicated
    "STR" : { #based on 33 charts:
        "signs":{
            "Capricorn":31,"Cancer":5,"Libra":11,"Gemini":5, #cumulatively, Cap is 5% positive & Can is 2% positive
            "Taurus":-14,"Leo":-12,"Pisces":-7 #cumulatively, Taurus is 3% neg & Leo is 2% neg
            }, 
        "antisigns":{}, 
        "houses":{
            5:9,7:4,1:3,6:3,
            3:-6,9:-6
        }, #cumulatively, only 6 is strong (3%) but 6 doesn't show up in the 'dominant houses top 3'
        "antihouses":{}, #cumulatively, only 3rd house is super neg, 9th is 2% neg
        "bodies":{
            "Moon":5,"Pluto":3,"Saturn":3, #cumulatively, no relevance shown
            "Venus":-6,"Jupiter":-7,"Neptune":-3 #cumulatively, only Venus is negative
        },
        "antibodies":{}, 
        "nakshatras":{
            "Punarvasu":11,"Uttara Ashadha":10,"Purva Ashadha":6,"Mula":8,"Ardra":8,"Mrigashira":6,"Chitra":12,"Revati":7,"Swati":7, #wondering if P Ash is only implicated by proximity to Ut Ash in charts... Cumulatively, only Punarvasu is 4% positive. P. Ash & Ut Ash are 2%. Everything else is 1% or less. #Similar Charts view & Database Analytics disagree about this for some reason.
            "Bharani":6,"Rohini":4,"Pushya":8,"Ashlesha":8,"Purva Phalguni":4,"Uttara Phalguni":8,"Vishakha":11,"Uttara Bhadrapada":6 #cumulatively, Ashwini & Jyestha are 2% neg. #Similar Charts view & Database Analytics disagree about this for some reason.
        }, 
        "antinakshatras":{}, 
        "positions":{
            "Sun in Capricorn":10,"Sun in Sagittarius":5,"Sun in Leo":4,"Sun in H4":18,
            "Moon in Aries":4,"Moon in Cancer":4,"Moon in Libra":5,
            "Mercury in Capricorn":10,"Mercury in Sagittarius":5,"Mercury in Aries":4,"Mercury in H5":19,
            "Venus in Capricorn":11,"Venus in Cancer":7,"Venus in Aquarius":9,"Venus in Virgo":4,
            "Mars in Cancer":8,"Mars in Taurus":4,
            "Jupiter in Gemini":8,"Jupiter in Scorpio":8,"Jupiter in Cancer":6,"Jupiter in Aries":4,"Jupiter in H5":17,
            "Saturn in Gemini":8,"Saturn in Libra":4,
            "Pluto in H6":19,
            "Ceres in H1":17,
            "Sun in Aries":-6,"Sun in Gemini":-4,"Sun in Virgo":-8,"Sun in Scorpio":-4,
            "Moon in Taurus":-5,"Moon in Sagittarius":-5,
            "Mercury in Taurus":-7,"Mercury in Leo":-4,"Mercury in Pisces":-9,
            "Venus in Libra":-7,"Venus in Leo":-7,"Venus in Pisces":-8,"Venus in Taurus":-4,
            "Mars in Leo":-6,"Mars in Virgo":-7,"Mars in Pisces":-4,
            "Jupiter in Leo":-7,"Jupiter in Virgo":-9,"Jupiter in Sagittarius":-7,"Jupiter in Pisces":-8,"Jupiter in Aquarius":-4,
            "Saturn in Taurus":-4,"Saturn in Virgo":-6,"Saturn in Sagittarius":-7,
        },
        "antipositions":{},
        "aspects":{
            "Chiron opposition Uranus":16,"Moon square Fortune":16,"Chiron trine Vesta":16,"Mars sextile Mercury":16,"Ceres sextile Rahu":16,"Ceres trine Ketu":14,"Ceres trine Moon":13,"Mercury sextile Venus":10,"Neptune square Pallas":14,"Chiron opposition Saturn":10,"Chiron square Mars":10
        },
        "antiaspects":{},
        "gates":{58,34,44,20,46,10,32,61,62,8,12,19,38},
        "antigates":{59,29,47,27,5,26,4,22,25,36,33},
        "channels": {
            (20, 34): 2,
            (10, 20): 4,
            (10, 34): 3,
            (34, 57): 2,
            (20, 57): 2,
        },
        "antichannels": {
            (6, 59): 2,
            (47, 64): 3,
        },
        "hdtypes":{"MF Generator":6},
        "antihdtypes":{"Projector":7},
        "centers":{"Spleen":3},
        "anticenters":{"Solar Plexus":3},
        "profiles":{"4/6":11,"5/1":9,"6/2":7},
        "antiprofiles":{"1/3":11,"3/5":11},
        "authorities":{"Sacral":12,"Ego Manifested":3},
        "antiauthorities":{"Emotional":14},
        "bazisigns":{},
        "antibazisigns":{},
        "color":"#cc99ff",
        "motivation":"",
        "description":"",
        "quotes":{""},
    },
    "DEX" : { #sampled 28 charts, sooo tiny selection...
        "signs":{"Taurus":8,"Gemini":6,"Virgo":12,"Sagittarius":10},
        "antisigns":{"Pisces":11,"Leo":6,"Aries":6},
        "houses":{1:7,11:4,12:5},
        "antihouses":{4:6,6:8,8:4},
        "bodies":{"Pluto":12,"Moon":6,"Saturn":8},
        "antibodies":{"Venus":20,"Jupiter":10},
        "nakshatras":{"Bharani":8,"Punarvasu":14,"Mrigashira":9,"Ardra":7,"Purva Ashadha":12,"Shravana":11,"Revati":8}, 
        "antinakshatras":{"Hasta":8,"Anuradha":5,"Mula":5,"Shatabhisha":10,"Purva Bhadrapada":5,"Uttara Phalguni":4}, 
        "positions":{
            "Sun in Taurus":5,"Sun in Gemini":4,"Sun in Sagittarius":4,
            "Moon in Gemini":10,
            "Mercury in Pisces":5,"Mercury in Cancer":7,
            "Venus in Aries":18,"Venus in Taurus":4,"Venus in Virgo":9,
            "Mars in Virgo":8,"Mars in Aquarius":7,
            "Jupiter in Virgo":5,
            "Saturn in Gemini":10,
            "Pluto in Scorpio":9,
            "Ceres in Libra":7,
            "Juno in Sagittarius":14,"Juno in Scorpio":6,
            "Pallas in Virgo":14,"Pallas in Scorpio":11,
            "Lilith in Taurus":13,"Vesta in Cancer":10,"Fortune in Scorpio":11,
            "Rahu in Capricorn":17,
        },
        "antipositions":{
            "Sun in Cancer":7,"Sun in Leo":5,"Sun in Scorpio":7,"Sun in Capricorn":5,
            "Moon in Virgo":7,"Moon in Sagittarius":4,
            "Mercury in Gemini":5,
            "Venus in Cancer":5,"Venus in Libra":6,"Venus in Sagittarius":7,"Venus in Capricorn":8,"Venus in Aquarius":6,
            "Mars in Libra":5,
            "Jupiter in Pisces":8,"Jupiter in Libra":6,
            "Saturn in Cancer":6,"Saturn in Sagittarius":6
        },
        "aspects":{},
        "antiaspects":{},
        "gates":{54:21,25:16,38:16,11:15,23:18,48:11,6:11,12:13,32:9,41:14,61:13,62:9,9:8},
        "antigates":{16:8,33:15,40:12,51:10,15:16,15:16,55:15,10:20},
        "channels": {
            (26, 44): 11,
            (6, 59): 7,
            (19, 49): 7,
            (2, 14): 8,
        },
        "antichannels": {
            (10, 34): 1,
        },
        "hdtypes":{"Generator":10},
        "antihdtypes":{"MF Generator":6},
        "centers":{"Emotional":6},
        "anticenters":{},
        "profiles":{"1/3":7,"4/6":7},
        "antiprofiles":{"3/5":4},
        "authorities":{},
        "antiauthorities":{},
        "bazisigns":{},
        "antibazisigns":{},
        "color":"#cc99ff",
        "motivation":"",
        "description":"",
        "quotes":{""},
    },
    "CON" : {
        "signs":{"Aquarius":7,"Capricorn":6,"Pisces":5},
        "antisigns":{"Libra":5,},
        "houses":{
            1:15, #high con list
            9:-6,
            11:-6,
            12:10,

            3:13, #'highest CON' list
            },
        "antihouses":{
            },
        "bodies":{
            "Sun":2,
            "Moon":1,
            "Uranus":1,
            },
        "antibodies":{
            "Mars":2,
            "Neptune":1,
            "Jupiter":1,
            },
        "nakshatras":{
            "Purva Ashadha":3,
            "Uttara Ashadha":4, #high con list
            "Shravana":4,
            "Magha":-6, #high con list
        }, 
        "antinakshatras":{"Magha":7}, 
        "positions":{
            #highest con list:
            "Moon in H3": 33,
            "Mercury in H7": 15,
            "Venus in Libra": 10,
            "Mars in Cancer": 16,
            "Jupiter in Sagittarius": 13,
            "Jupiter in H3": 19,
            "Pluto in Taurus": 7,
            "Pluto in H2": 14,
            "Chiron in Gemini": 11,
            "Ceres in H9": 21,
            "Vesta in Leo": 16,
            "MC in Pisces": 15,
            "Virgo in H4": 15,
            "Pisces in H10": 15,
            "True Lilith in Aquarius": 23,
            
            #high con list:
            "Sun in Capricorn":8, 
            "Mercury in H9":-6,
            "Mercury in H3":7,
            "Mercury in Capricorn":4,
            "Venus in Capricorn":5,
            "Jupiter in H3":6,"Saturn in Libra": -5,
            "Uranus in Virgo": 5,
            "Neptune in Sagittarius": -6,
            "Pluto in Libra": -6,
            "Ceres in Pisces": 5,
            "Pallas in Aquarius": 6,
            "Pallas in H3": 7,
            "Juno in Aries": 4,
            "Part of Fortune in Aquarius": 4,
            "Part of Fortune in H6": 6,
            "Lilith in Aquarius": 6,
            "Mars in H8":4,
        },
        "antipositions":{"Neptune in Sagittarius":8},
        "aspects":{
            #high con
            "Moon square Fortune":7,
            "Pluto sextile Vesta":5,
            "Pallas sextile Sun": 5,
            "Mercury sextile Rahu": 4,
            "Sun trine Uranus": 5,
            "Pallas conjunction Uranus": 4,
            "Ceres conjunction Chiron": 3,
            "Juno opposition Saturn": 3,
            "Juno quintile Vesta": 3,
            "Jupiter quincunx Vesta": 3,
            "Neptune biquintile Venus": 3,
            "AS opposition Sun": 4,
            "AS semisquare Juno": 5,
            "Chiron square Mars": -5,
            "Mars trine Pallas": -5,
            "AS quincunx Chiron": 4,
            "Chiron biquintile MC": 3,
            "Mars square Part of Fortune": -4,
            "AS biquintile Pluto": 3,
            "MC quintile Part of Fortune": 3,
            "MC quintile Pluto": 4,
            "Part of Fortune sextile Vesta": -4,
            "MC trine Mars": -7,
            "Rahu opposition Uranus": -3,
            "Pluto opposition Rahu": -4,

            #highest con
            "Mars trine Uranus": 21,
            "Jupiter trine Moon": 18,
            "Mars sextile True Lilith": 21,
            "Pluto sextile Vesta": 15,
            "Ceres semisextile Pallas": 14,
            "Ceres trine Pluto": 12,
            "Chiron sextile Mars": 12,
            "Juno opposition Pluto": 17,
            "Mars sextile Sun": 11,
            "Mercury conjunction Vesta": 14,
            "Mercury sextile Part of Fortune": 14,
            "Mercury sextile Rahu": 12,
            "Pallas trine Vesta": 13,
            "Sun trine Uranus": 13,
            "Chiron square Venus": 10,
            "Jupiter sextile Saturn": 11,
            "Part of Fortune conjunction Pluto": 12,
            "Rahu opposition Saturn": 12,
            "Sun opposition True Lilith": 12,
            "Venus trine Vesta": 10,
            "AS square Neptune": 21,
            "AS square Uranus": 18,
            "Ceres conjunction Saturn": 9,
            "Ceres quincunx Uranus": 11,
            "Chiron conjunction True Lilith": 9,
            "Juno semisextile True Lilith": 11,
            "Jupiter quintile Rahu": 12,
            "Mars biquintile Part of Fortune": 11,
            "MC square Sun": 21,
            "Mercury biquintile Uranus": 11,
            "Moon quintile Sun": 11,
            "Neptune quincunx Pallas": 11,
            "Pallas sesquiquadrate Saturn": 12,
            "Pallas sextile Rahu": 9,
            "Part of Fortune conjunction Saturn": 9,
            "Saturn sesquiquadrate Vesta": 9,
            "Sun opposition Uranus": 10,
            "True Lilith opposition Vesta": 10,
            "AS conjunction Vesta": 15,
            "AS sextile Vesta": 14,
            "Chiron quincunx Neptune": 7,
            "Chiron quintile Mercury": 8,
            "Juno biquintile Rahu": 8,
            "Juno semisquare Pluto": 8,
            "Juno semisquare Saturn": 9,
            "Jupiter quincunx Vesta": 7,
            "Jupiter semisextile Neptune": 8,
            "Jupiter semisextile Pluto": 9,
            "Jupiter semisextile Vesta": 7,
            "Mars biquintile Saturn": 8,
            "Mars semisextile Venus": 7,
            "Mars semisquare Rahu": 8,
            "MC quincunx Pluto": 18,
            "MC quintile Part of Fortune": 19,
            "MC square Neptune": 14,
            "MC square Pallas": 15,
            "Mercury quincunx Pluto": 8,
            "Mercury quintile Saturn": 8,
            "Mercury semisextile True Lilith": 8,
            "Moon semisquare Neptune": 8,
            "Neptune semisquare Part of Fortune": 9,
            "Pallas opposition Uranus": 7,
            "Pallas quintile Venus": 8,
            "Part of Fortune quincunx Venus": 7,
            "Part of Fortune quincunx Vesta": 7,
            "Pluto semisextile Vesta": 8,
            "Pluto sesquiquadrate Rahu": 7,
            "Rahu quintile Venus": 8,
            "AS opposition Neptune": 11,
            "AS semisextile Moon": 12,
            "AS semisextile Pluto": 12,
            "AS semisquare True Lilith": 11,
            "Ceres biquintile Jupiter": 5,
            "Ceres semisquare Part of Fortune": 5,
            "Chiron biquintile MC": 11,
            "Chiron biquintile Venus": 5,
            "Chiron quintile Juno": 5,
            "Chiron semisextile Pallas": 5,
            "Chiron semisquare Moon": 5,
            "Chiron sesquiquadrate Rahu": 5,
            "Juno biquintile Mercury": 5,
            "Mars quintile Uranus": 5,
            "Mars sesquiquadrate Moon": 5,
            "MC biquintile Mars": 12,
            "MC opposition Uranus": 11,
            "MC semisextile True Lilith": 12,
            "MC semisextile Vesta": 12,
            "Mercury sesquiquadrate Uranus": 5,
            "Neptune quintile Rahu": 5,
            "Part of Fortune semisextile Uranus": 5,
            "Pluto quintile Saturn": 5,
            "Sun sesquiquadrate Vesta": 5,
            "Uranus semisquare Venus": 6,
            "Venus biquintile Vesta": 5,

        },
        "antiaspects":{"Sun semisquare Venus":6},
        "gates":{
            38: 7, #high con
            27: 19, #highest con list
            22: -18, #highest con list

            },
        "antigates":{48:5,26:5,28:8,18:6,49:5,5:6,55:4,2:5},
        "channels": {
            (27, 50): 18, #highest CON list
            (28, 38): 11, #highest CON list
        },
        "antichannels": {
            (20, 57): 5,
        },
        "hdtypes":{},
        "antihdtypes":{},
        "centers":{"Sacral":7},
        "anticenters":{"Emotional":6},
        "profiles":{"4/1":2},
        "antiprofiles":{"5/1":3},
        "authorities":{
            "Sacral": 8,
            },
        "antiauthorities":{},
        "bazisigns":{},
        "antibazisigns":{},
        "color":"#cc99ff",
        "motivation":"",
        "description":"",
        "quotes":{""},
    },
    "INT" : {
        "signs":{
            "Gemini":6,
            "Cancer":3,
            "Scorpio":3,
            },
        "antisigns":{},
        "houses":{
            7:-2,
            12:-2
            }, #even 1% cumulative.
        "antihouses":{}, #none
        "bodies":{
            "Neptune":4
            }, #what, you were expecting Mercury?? <_<
        "antibodies":{"Mercury":6}, #lol yeah it got -6% in 'Similarities Analysis'
        "nakshatras":{"Mrigashira":3,"Punarvasu":4,"Vishakha":3,"Uttara Ashadha":3,}, 
        "antinakshatras":{}, 
        "positions":{
            "Sun in Gemini":3,
            "Sun in Aries":2,
            "Sun in Leo":-4,

            "Mercury in Gemini":3,
            "Mercury in Scorpio":4,
            "Mercury in Virgo":-3,

            "Venus in Aquarius":-3,
            "Venus in Virgo":-3,

            "Mars in Capricorn":4,
            "Mars in Taurus":-4,

            "Saturn in Capricorn":-4,
            "Uranus in Cancer":3,
            "Neptune in Sagittarius":-5,
            "Neptune in Scorpio":-4,

            "Pluto in Virgo":-5,
            "Pluto in Libra":-4,
            "Pluto in Taurus":4,

            "Virgo in H1":6,
            "Aquarius in H1":-3,
            "Aries in H1":-3,
            "Capricorn in H10":-5,
            "Gemini in H10":5,
        },
        "antipositions":{
        },
        "aspects":{
            "Chiron opposition Uranus":8,"Mars trine Fortune":5,"Fortune trine Lilith":5,"Rahu trine Sun":4,"Moon trine Uranus":5,"Juno sextile Jupiter":5,"Neptune opposition Fortune":6,"AS square Mercury":5,"Mars conjunction Moon":5,"Pallas opposition Vesta":4,"AS square Juno":5,"Fortune opposition Vesta":4,"MC sextile Fortune":5
        },
        "antiaspects":{},
        "gates":{
            39: 6,
            5: -6,
            40: -6,
            #45,62,51,12,61,36,
            },
        "antigates":{
            #59,44,29,5,63,37,13
            },
        "channels": {
            (35, 36): 5,
        },
        "antichannels": {},
        "hdtypes":{},
        "antihdtypes":{},
        "centers":{},
        "anticenters":{},
        "profiles":{},
        "antiprofiles":{},
        "authorities":{},
        "antiauthorities":{},
        "bazisigns":{"Goat":-2},
        "antibazisigns":{},
        "color":"#cc99ff",
        "motivation":"",
        "description":"",
        "quotes":{""},
    },
    "WIS" : {
        "signs":{"Gemini":8,"Virgo":6,"Pisces":11,"Sagittarius":4},
        "antisigns":{"Libra":8,"Scorpio":4,"Aquarius":4},
        "houses":{1:6},
        "antihouses":{9:6},
        "bodies":{},
        "antibodies":{"Saturn":3},
        "nakshatras":{"Shatabhisha":7,"Mrigashira":4,"Rohini":6,"Purva Phalguni":6,"Jyestha":4,"Mula":3}, 
        "antinakshatras":{"Ashwini":4,"Pushya":4,"Hasta":4,"Swati":6,"Uttara Bhadrapada":4}, 
        "positions":{
            "Sun in Virgo":5,"Sun in Taurus":4,"Sun in Cancer":3,"Sun in Pisces":3,
            "Moon in Pisces":7,
            "Mercury in Gemini":8,"Venus in Libra":3,"Venus in Aquarius":3,
            "Mars in Pisces":4,"Mars in Libra":3,
            "Jupiter in Virgo":5,"Jupiter in Aries":4,
            "Saturn in Pisces":4,"Saturn in Sagittarius":6,"Saturn in Cancer":4,
            "Aries in H1":8,"Scorpio in H1":4
        },
        "antipositions":{
            "Sun in Aries":7,"Sun in Leo":6,"Sun in Libra":4,
            "Moon in Sagittarius":5,"Moon in Cancer":3,
            "Mercury in Cancer":6,"Mercury in Scorpio":3,"Mercury in Taurus":3,
            "Venus in Sagittarius":3,
            "Mars in Scorpio":4,
            "Jupiter in Leo":3,"Jupiter in Scorpio":3,
            "Saturn in Libra":5,"Saturn in Aquarius":3,"Saturn in Scorpio":3,
            "Cancer in H1":8,"Libra in H1":6,"Sagittarius in H1":4
        },
        "aspects":{},
        "antiaspects":{},
        "gates":{47:11,50:5,6:6,10:7,15:8,37:10,12:7,9:6,35:7,22:6,36:6,16:5},
        "antigates":{58:5,14:5,48:5,28:6,33:6,39:6,46:8,19:8,21:6,54:7,8:7,60:11},
        "channels": {
            (37, 40): 6,
            (6, 59): 4,
            (12, 22): 6,
        },
        "antichannels": {
            (18, 58): 7,
            (28, 38): 6,
        },
        "hdtypes":{"MF Generator":6},
        "antihdtypes":{"Projector":6},
        "centers":{},
        "anticenters":{},
        "profiles":{"3/5":5,"5/1":5},
        "antiprofiles":{"1/3":4,"2/4":4,"6/2":3},
        "authorities":{"Emotional":7},
        "antiauthorities":{"Sacral":5,"Splenic":3},
        "bazisigns":{"snake":3},
        "antibazisigns":{},
        "color":"#cc99ff",
        "motivation":"",
        "description":"",
        "quotes":{""},
    },
    "CHA" : { #looked at 147-400 charts. This was tricky to nail down - because what I find charismatic differs from public opinion quite a bit. So I started with a list of who I found charismatic, found norms. Then added who I thought other people find charismatic. Found norms. Mixed the two - found nothing. Tried to pick out just the MOST charismatic from both - found nothing. Picked out who I think are most universally agreed upon as charismatic, found patterns. The criteria below represent a mix of these findings.
        "signs": {
            "Cancer": 6,
            "Leo":5, #dominated in "high CHA"  but not 'highest CHA'
        },
        "antisigns": {
            "Sagittarius":12,
            "Aquarius":14, #Sun in Aqu d2 was most represented in low CHA. Moon in Aqu d1. Mercury in Aq d2. But it's pretty distributed. 
        },
        "houses": {
            "10": 9, #dominant in 'high cha' too.
            "4": 6,
            "9": 5,
            "2": 6,
            "11": 4, #dominant in 'high cha' too.
        },
        "antihouses": {
            12:7, #overrep in low CHA
        },
        "bodies": {
            "Sun":2,
            "Mercury": 9,
            "Venus":2,
            "Saturn":1,
        },
        "antibodies": {
            "Pluto":1,
            "Rahu":1,
            "Moon":1,
            "Mercury":-4, #both overrepresented in high CHA & underrep in low CHA
        },
        "nakshatras": {
            "Ashlesha": 5,
            "Mrigashira": 4,
            "Chitra":2,
            "Swati":2,
            "Dhanishta":4,
            "Uttara Bhadrapada":3,
            "Pushya":3,
            "Revati":-3
        },
        "antinakshatras": {
            "Ashwini":11,
            "Magha":10,
            "Punarvasu":11,
            "Mula":8,
        },
        "positions": {
            "Sun in Gemini": 5,
            "Sun in Leo": 4,
            "Sun in Sagittarius": 2,
            #"Sun in Aquarius": 2, #both overrepresented in most CHA and least CHA
            "Sun in Capricorn": -2,
            #Libra Decan 1 is NOT very CHA, Libra Decan 2 (Aqu) is high-moderate; Libra Decan 3 (Gem) is the most CHA. Chitra, Swati & Vishakha were most dom in high CHA Libras.
            "Sun in H2": 6,
            "Moon in H3": 5,
            "Mercury in Taurus": 3,
            "Uranus in Pisces": 4,
            "Neptune in Leo": 6,
            "Pluto in Cancer": 6,
            "Ceres in Leo": 5,
            "Ceres in Scorpio": -4,
            "Pallas in Cancer": 4,
            "Juno in Aries": 3,
            "Vesta in Cancer": 5,
            "Vesta in Aquarius": -3,
            "Aries in H2": 4,
            "Libra in H8": 4,
        },
        "antipositions": {
            "Cancer in H1":17,
            "Sun in Aries":-2, #1% overrepresented in most CHA, -3 in least CHA. 
            "Sun in Virgo":-3,
            #"Sun in Aquarius":3, #both overrepresented in most CHA and least CHA
            "Sun in Scorpio":3, #their cha is built almost entirely around abrasivness, volition & shock value
            "Moon in Aries":6,
            "Moon in Taurus":-4,
            "Mercury in Virgo":-5,
            "Mercury in Aquarius":5,
            "Venus in Aries":-3,
            "Venus in Aquarius":4,
            "Mars in Cancer":7,
            "Mars in Sagittarius":-4,
            "Mars in Pisces":-4,
            "Jupiter in Gemini":5,
            "Saturn in Sagittarius":6,
            },
        "aspects": {
            "Chiron trine Neptune": 6,
            "Neptune square Saturn": 5,
            "Jupiter trine Sun": 4,
            "Neptune trine Venus": 4,
            "True Lilith sextile Uranus": 3,
            "Pluto sextile Venus": 3,
            "Jupiter opposition Rahu": 3,
            "Chiron quincunx Part of Fortune": 4,
            "Pluto trine Uranus": 3,
            "MC quincunx Part of Fortune": 4,
            "Chiron trine Part of Fortune": -3,
            "Ceres sextile Mercury": -4,
            "Juno sextile Moon": -3,
            "MC trine Part of Fortune": -4,
            "MC conjunction Sun": -4,
        },
        "antiaspects": {},
        "gates": {
            37: 8,
            3: 7,
            59: -6,
            9: -6,
            15: -7,
        },
        "antigates": {},
        "channels": {
            (37, 40): 5,
            (30, 41): 6,
            (5, 15): -4,
        },
        "antichannels": {},
        "centers": {},
        "anticenters": {},
        "profiles": {},
        "antiprofiles": {},
        "authorities": {},
        "antiauthorities": {},
        "bazisigns": {},
        "antibazisigns": {
            "Rabbit":-3,
        },
        "color": "#cc99ff",
        "motivation": "",
        "description": "",
        "quotes": {},
    },
}

DND_STATS_HYPOTHETICAL = { #lore- x research-based. (GPT edited my findings to try and parse out white noise. But I'm not sure how good of a job it did)
    "STR": {
        "label": "Strength",
        "sample_note": "Mostly measures durable applied force, work capacity, bodily persistence, and resistance under load.",
        "confidence": "medium",

        "signs": {
            "Capricorn": 31,
            "Cancer": 5,
            "Libra": 11,
            "Gemini": 5,

            # underrepresented in STR sample, not necessarily overrepresented in weak/opposite sample
            "Taurus": -14,
            "Leo": -12,
            "Pisces": -7,
        },

        "antisigns": {
            # only use this for traits found in an explicit low-STR / weak / opposite-STR cohort
        },

        "houses": {
            5: 9,
            7: 4,
            1: 3,
            6: 3,
            3: -6,
            9: -6,
        },

        "antihouses": {},

        "bodies": {
            "Moon": 5,
            "Pluto": 3,
            "Saturn": 3,
            "Venus": -6,
            "Jupiter": -7,
            "Neptune": -3,
        },

        "antibodies": {},

        "nakshatras": {
            "Punarvasu": 11,
            "Uttara Ashadha": 10,
            "Purva Ashadha": 6,
            "Mula": 8,
            "Ardra": 8,
            "Mrigashira": 6,
            "Chitra": 12,
            "Revati": 7,
            "Swati": 7,

            "Bharani": -6,
            "Rohini": -4,
            "Pushya": -8,
            "Ashlesha": -8,
            "Purva Phalguni": -4,
            "Uttara Phalguni": -8,
            "Vishakha": -11,
            "Uttara Bhadrapada": -6,
        },

        "antinakshatras": {},

        "positions": {
            "Sun in Capricorn": 10,
            "Sun in Sagittarius": 5,
            "Sun in Leo": 4,
            "Sun in H4": 18,
            "Moon in Aries": 4,
            "Moon in Cancer": 4,
            "Moon in Libra": 5,
            "Mercury in Capricorn": 10,
            "Mercury in Sagittarius": 5,
            "Mercury in Aries": 4,
            "Mercury in H5": 19,
            "Venus in Capricorn": 11,
            "Venus in Cancer": 7,
            "Venus in Aquarius": 9,
            "Venus in Virgo": 4,
            "Mars in Cancer": 8,
            "Mars in Taurus": 4,
            "Jupiter in Gemini": 8,
            "Jupiter in Scorpio": 8,
            "Jupiter in Cancer": 6,
            "Jupiter in Aries": 4,
            "Jupiter in H5": 17,
            "Saturn in Gemini": 8,
            "Saturn in Libra": 4,
            "Pluto in H6": 19,
            "Ceres in H1": 17,

            "Sun in Aries": -6,
            "Sun in Gemini": -4,
            "Sun in Virgo": -8,
            "Sun in Scorpio": -4,
            "Moon in Taurus": -5,
            "Moon in Sagittarius": -5,
            "Mercury in Taurus": -7,
            "Mercury in Leo": -4,
            "Mercury in Pisces": -9,
            "Venus in Libra": -7,
            "Venus in Leo": -7,
            "Venus in Pisces": -8,
            "Venus in Taurus": -4,
            "Mars in Leo": -6,
            "Mars in Virgo": -7,
            "Mars in Pisces": -4,
            "Jupiter in Leo": -7,
            "Jupiter in Virgo": -9,
            "Jupiter in Sagittarius": -7,
            "Jupiter in Pisces": -8,
            "Jupiter in Aquarius": -4,
            "Saturn in Taurus": -4,
            "Saturn in Virgo": -6,
            "Saturn in Sagittarius": -7,
        },

        "antipositions": {},

        "aspects": {
            #"Neptune sextile Pluto": 20,
            "Chiron opposition Uranus": 16,
            "Moon square Fortune": 16,
            "Chiron trine Vesta": 16,
            "Mars sextile Mercury": 16,
            "Ceres sextile Rahu": 16,
            "Ceres trine Ketu": 14,
            "Ceres trine Moon": 13,
            "Mercury sextile Venus": 10,
            "Neptune square Pallas": 14,
            "Chiron opposition Saturn": 10,
            "Chiron square Mars": 10,
        },

        "antiaspects": {},

        "gates": {
            58, 34, 44, 20, 46, 10, 32, 61, 62, 8, 12, 19, 38,
            -59, -29, -47, -27, -5, -26, -4, -22, -25, -36, -33,
        },

        "antigates": set(),

        "hdtypes": {
            "MF Generator": 6,
            "Projector": -7,
        },

        "antihdtypes": {},

        "centers": {
            "Spleen": 3,
            "Solar Plexus": -3,
        },

        "anticenters": {},

        "profiles": {
            "4/6": 11,
            "5/1": 9,
            "6/2": 7,
            "1/3": -11,
            "3/5": -11,
        },

        "antiprofiles": {},

        "authorities": {
            "Sacral": 12,
            "Ego Manifested": 3,
            "Emotional": -14,
        },

        "antiauthorities": {},

        "notes": {
            "Taurus": "Do not overread as anti-strength. It is underrepresented in the STR sample, not necessarily a true weak-stat marker.",
            "Leo": "Likely underrepresented for durable/labor STR, not necessarily raw force or physical presence.",
            "Neptune sextile Pluto": "Low-confidence until birth-year normalized; likely generational contamination.",
        },
    },

    "DEX": {
        "label": "Dexterity",
        "sample_note": "Mostly measures precision, reflex, timing, technical movement, and bodily adjustment.",
        "confidence": "medium-high",

        "signs": {
            "Taurus": 8,
            "Gemini": 6,
            "Virgo": 12,
            "Sagittarius": 10,
            "Pisces": -11,
            "Leo": -6,
            "Aries": -6,
        },

        "antisigns": {},

        "houses": {
            1: 7,
            11: 4,
            12: 5,
            4: -6,
            6: -8,
            8: -4,
        },

        "antihouses": {},

        "bodies": {
            "Pluto": 12,
            "Moon": 6,
            "Saturn": 8,
            "Venus": -20,
            "Jupiter": -10,
        },

        "antibodies": {},

        "nakshatras": {
            "Bharani": 8,
            "Punarvasu": 14,
            "Mrigashira": 9,
            "Ardra": 7,
            "Purva Ashadha": 12,
            "Shravana": 11,
            "Revati": 8,

            "Hasta": -8,
            "Anuradha": -5,
            "Mula": -5,
            "Shatabhisha": -10,
            "Purva Bhadrapada": -5,
            "Uttara Phalguni": -4,
        },

        "antinakshatras": {},

        "positions": {
            "Sun in Taurus": 5,
            "Sun in Gemini": 4,
            "Sun in Sagittarius": 4,
            "Moon in Gemini": 10,
            "Mercury in Pisces": 5,
            "Mercury in Cancer": 7,
            "Venus in Aries": 18,
            "Venus in Taurus": 4,
            "Venus in Virgo": 9,
            "Mars in Virgo": 8,
            "Mars in Aquarius": 7,
            "Jupiter in Virgo": 5,
            "Saturn in Gemini": 10,
            "Pluto in Scorpio": 9,
            "Ceres in Libra": 7,
            "Juno in Sagittarius": 14,
            "Juno in Scorpio": 6,
            "Pallas in Virgo": 14,
            "Pallas in Scorpio": 11,
            "Lilith in Taurus": 13,
            "Vesta in Cancer": 10,
            "Fortune in Scorpio": 11,
            "Rahu in Capricorn": 17,

            "Sun in Cancer": -7,
            "Sun in Leo": -5,
            "Sun in Scorpio": -7,
            "Sun in Capricorn": -5,
            "Moon in Virgo": -7,
            "Moon in Sagittarius": -4,
            "Mercury in Gemini": -5,
            "Venus in Cancer": -5,
            "Venus in Libra": -6,
            "Venus in Sagittarius": -7,
            "Venus in Capricorn": -8,
            "Venus in Aquarius": -6,
            "Mars in Libra": -5,
            "Jupiter in Pisces": -8,
            "Jupiter in Libra": -6,
            "Saturn in Cancer": -6,
            "Saturn in Sagittarius": -6,
        },

        "antipositions": {},

        "gates": {
            54: 21,
            25: 16,
            38: 16,
            11: 15,
            23: 18,
            48: 11,
            6: 11,
            12: 13,
            32: 9,
            41: 14,
            61: 13,
            62: 9,
            9: 8,

            16: -8,
            33: -15,
            40: -12,
            51: -10,
            15: -16,
            55: -15,
            10: -20,
        },

        "antigates": {},

        "hdtypes": {
            "Generator": 10,
            "MF Generator": -6,
        },

        "centers": {
            "Emotional": 6,
        },

        "profiles": {
            "1/3": 7,
            "4/6": 7,
            "3/5": -4,
        },

        "notes": {
            "Venus": "Likely underrepresented for reflex/precision DEX, not necessarily anti-grace.",
            "Pluto in Scorpio": "Low-confidence until birth-year normalized.",
            "Rahu in Capricorn": "Check for cohort clustering.",
        },
    },

    "CON": {
        "label": "Constitution",
        "sample_note": "Mostly measures survivability, reserve, stress tolerance, recovery capacity, and abnormal-condition endurance.",
        "confidence": "medium",

        "signs": {
            "Aquarius": 6,
            "Capricorn": 6,
            "Pisces": 5,
            "Libra": -8,
            "Sagittarius": -4,
            "Gemini": -4,
        },

        "antisigns": {},

        "houses": {
            1: 6,
            12: 6,
            11: -5,
            9: -5,
        },

        "antihouses": {},

        "bodies": {
            "Sun": 7,
            "Moon": 4,
            "Mars": -5,
            "Uranus": -4,
        },

        "antibodies": {},

        "nakshatras": {
            "Purva Ashadha": 5,
            "Uttara Ashadha": 5,
            "Magha": -7,
        },

        "antinakshatras": {},

        "positions": {
            "Sun in Capricorn": 9,
            "Mercury in H5": 5,
            "Venus in Capricorn": 6,
            "Mars in H8": 4,
            "Ceres in Pisces": 6,
            "Ceres in H4": 5,
            "Lilith in H6": 6,
            "Rahu in H2": 6,
            "Ketu in H1": 5,
            "Neptune in Sagittarius": -8,
        },

        "antipositions": {},

        "aspects": {
            "Moon square Fortune": 7,
            "Lilith trine Uranus": 6,
            "Ceres trine Vesta": 5,
            "Pluto sextile Vesta": 5,
            "Uranus trine Vesta": 4,
            "DS trine Pallas": 7,
            "MC trine Neptune": 5,
            "Pallas conjunction Uranus": 5,
            "IC square Vesta": 5,
            "MC trine Lilith": 5,
            "Sun semisquare Venus": -6,
        },

        "antiaspects": {},

        "gates": {
            44: 5,
            47: 8,
            46: 5,
            12: 7,
            29: 5,
            56: 5,
            28: 7,
            25: 5,
            63: 5,

            48: -5,
            26: -5,
            18: -6,
            49: -5,
            5: -6,
            55: -4,
            2: -5,
        },

        "polarizing": {
            "gates": {
                28: {
                    "positive": 7,
                    "negative": -8,
                    "note": "Crisis-facing signal; can indicate resilience or depletion.",
                },
            },
        },

        "centers": {
            "Sacral": 7,
            "Emotional": -6,
        },

        "profiles": {
            "4/1": 2,
            "5/1": -3,
        },

        "notes": {
            "Mars": "Probably underrepresented for reserve-based CON, not vitality generally. Mars spends energy; CON stores it.",
            "Aquarius": "May indicate detachment under strain.",
            "Pisces": "May indicate absorptive endurance, not simple physical robustness.",
        },
    },

    "INT": {
        "label": "Intelligence",
        "subtype": "scientific / research intelligence",
        "sample_note": (
            "Because this cohort is literal scientists, this measures scientific eminence more than generic D&D INT: "
            "model-building, hypothesis pursuit, technical reasoning, problem attack, conceptual persistence, and public legibility."
        ),
        "confidence": "medium-low",

        "signs": {
            "Gemini": 8,
            "Cancer": 5,
            "Libra": 5,
            "Aries": 3,
            "Sagittarius": -5,
        },

        "antisigns": {},

        "houses": {
            3: 2,
        },

        "antihouses": {},

        "bodies": {
            "Mars": 8,
            "Mercury": -6,
        },

        "antibodies": {},

        "nakshatras": {
            "Mrigashira": 6,
            "Punarvasu": 3,
            "Purva Phalguni": 2,
            "Revati": 2,
            "Purva Ashadha": -2,
        },

        "antinakshatras": {},

        "positions": {
            "Moon in Aries": 3,
            "Mercury in Scorpio": 4,
            "Venus in Scorpio": 5,
            "Mars in Capricorn": 4,
            "Saturn in Gemini": 4,
            "Pluto in Leo": 5,
            "Neptune in Libra": 4,
            "Scorpio in H1": 5,
            "Virgo in H1": 4,
            "Leo in H10": 5,
            "Juno in Scorpio": 4,

            "Sun in Leo": -4,
            "Saturn in Capricorn": -4,
            "Neptune in Scorpio": -4,
            "Pluto in Virgo": -4,
            "Aquarius in H1": -4,
        },

        "antipositions": {},

        "aspects": {
            "Chiron opposition Uranus": 8,
            "Mars trine Fortune": 5,
            "Fortune trine Lilith": 5,
            "Rahu trine Sun": 4,
            "Moon trine Uranus": 5,
            "Juno sextile Jupiter": 5,
            "Neptune opposition Fortune": 6,
            "AS square Mercury": 5,
            "Mars conjunction Moon": 5,
            "Pallas opposition Vesta": 4,
            "AS square Juno": 5,
            "Fortune opposition Vesta": 4,
            "MC sextile Fortune": 5,
        },

        "antiaspects": {},

        "gates": {
            45, 62, 51, 12, 61, 36,
            -59, -44, -29, -5, -63, -37, -13,
        },

        "antigates": set(),

        "profiles": {
            "1/4": 3,
            "3/5": 4,
            "1/3": -4,
            "6/2": -4,
        },

        "authorities": {
            "Emotional": 2,
        },

        "notes": {
            "Mars": "Legit if interpreted as hypothesis pursuit, competitive reasoning, and problem attack.",
            "Mercury": "Do not treat as anti-intelligence. It is underrepresented in this scientist cohort, likely because the sample favors consequential research drive over quick verbal cleverness.",
            "Sagittarius": "Probably underrepresented for narrow technical scientific eminence, not broad intelligence.",
        },
    },

    "WIS": {
        "label": "Wisdom",
        "sample_note": "The capacity to notice what is happening internally and interpersonally, stay regulated under emotional pressure, read context accurately, and choose responses that are proportionate, humane, and non-self-sabotaging.",
        "confidence": "medium-high",
        "signs": {
            "Gemini": 8,
            "Virgo": 6,
            "Pisces": 11,
            "Sagittarius": 4,
            "Libra": -8,
            "Scorpio": -4,
            "Aquarius": -4,
        },

        "antisigns": {},

        "houses": {
            1: 6,
            9: -6,
        },

        "antihouses": {},

        "bodies": {
            "Saturn": -3,
        },

        "antibodies": {},

        "nakshatras": {
            "Shatabhisha": 7,
            "Mrigashira": 4,
            "Rohini": 6,
            "Purva Phalguni": 6,
            "Jyestha": 4,
            "Mula": 3,

            "Ashwini": -4,
            "Pushya": -4,
            "Hasta": -4,
            "Swati": -6,
            "Uttara Bhadrapada": -4,
        },

        "antinakshatras": {},

        "positions": {
            "Sun in Virgo": 5,
            "Sun in Taurus": 4,
            "Sun in Cancer": 3,
            "Sun in Pisces": 3,
            "Moon in Pisces": 7,
            "Mercury in Gemini": 8,
            "Venus in Libra": 3,
            "Venus in Aquarius": 3,
            "Mars in Pisces": 4,
            "Mars in Libra": 3,
            "Jupiter in Virgo": 5,
            "Jupiter in Aries": 4,
            "Saturn in Pisces": 4,
            "Saturn in Sagittarius": 6,
            "Saturn in Cancer": 4,
            "Aries in H1": 8,
            "Scorpio in H1": 4,

            "Sun in Aries": -7,
            "Sun in Leo": -6,
            "Sun in Libra": -4,
            "Moon in Sagittarius": -5,
            "Moon in Cancer": -3,
            "Mercury in Cancer": -6,
            "Mercury in Scorpio": -3,
            "Mercury in Taurus": -3,
            "Venus in Sagittarius": -3,
            "Mars in Scorpio": -4,
            "Jupiter in Leo": -3,
            "Jupiter in Scorpio": -3,
            "Saturn in Libra": -5,
            "Saturn in Aquarius": -3,
            "Saturn in Scorpio": -3,
            "Cancer in H1": -8,
            "Libra in H1": -6,
            "Sagittarius in H1": -4,
        },

        "antipositions": {},

        "gates": {
            47: 11,
            50: 5,
            6: 6,
            10: 7,
            15: 8,
            37: 10,
            12: 7,
            9: 6,
            35: 7,
            22: 6,
            36: 6,
            16: 5,

            58: -5,
            14: -5,
            48: -5,
            28: -6,
            33: -6,
            39: -6,
            46: -8,
            19: -8,
            21: -6,
            54: -7,
            8: -7,
            60: -11,
        },

        "antigates": {},

        "hdtypes": {
            "MF Generator": 6,
            "Projector": -6,
        },

        "profiles": {
            "3/5": 5,
            "5/1": 5,
            "1/3": -4,
            "2/4": -4,
            "6/2": -3,
        },

        "authorities": {
            "Emotional": 7,
            "Sacral": -5,
            "Splenic": -3,
        },

        "bazisigns": {
            "snake": 3,
        },

        "notes": {
            "9th house": "Suspicious as negative. Could mean theory-over-situation, not lack of wisdom.",
            "Gemini": "Legit if WIS includes noticing, updating, reading signals, and adaptive perception.",
            "Saturn": "Body-level negative should not override positive Saturn placements.",
        },
    },

    "CHA": {
        "label": "Charisma",
        "sample_note": "Measures magnetism, recognizability, attention capture, social/vocal impact, and status signal. Not the same as niceness.",
        "confidence": "high but noisy",

        "signs": {
            "Gemini": 3,
            "Capricorn": 3,
            "Leo": 3,
            "Taurus": 2,
            "Libra": -4,
            "Sagittarius": -8,
            "Aquarius": -13,
        },

        "antisigns": {},

        "houses": {
            10: 5,
            4: 10,
            3: 5,
            2: 6,
            11: 4,
        },

        "antihouses": {},

        "bodies": {
            "Mercury": 7,
            "Sun": 2,
            "Jupiter": 2,
            "Saturn": -5,
            "Pluto": -5,
            "Uranus": -7,
        },

        "antibodies": {},

        "nakshatras": {
            "Rohini": 4,
            "Bharani": 4,
            "Ashlesha": 5,
            "Purva Ashadha": 3,
            "Mrigashira": 1,
            "Revati": 3,
            "Purva Phalguni": 6,
            "Mula": 5,

            "Hasta": -2,
            "Anuradha": -6,
            "Chitra": -4,
            "Jyestha": -4,
            "Shravana": -4,
        },

        "antinakshatras": {},

        "positions": {
            "Sun in Gemini": 4,
            "Sun in Taurus": 4,
            "Sun in Leo": 4,
            "Sun in Capricorn": 4,
            "Sun in H2": 9,
            "Moon in Capricorn": 4,
            "Mercury in Taurus": 3,
            "Mercury in Leo": 3,
            "Mercury in H3": 4,
            "Mercury in H2": 4,
            "Venus in Taurus": 2,
            "Venus in Gemini": 5,
            "Venus in Aries": 3,
            "Mars in Aries": 3,
            "Mars in H4": 3,
            "Jupiter in Aquarius": 3,
            "Jupiter in Sagittarius": 2,
            "Jupiter in H6": 4,
            "Saturn in H11": 4,
            "Saturn in H10": 4,
            "Neptune in H6": 5,
            "Neptune in Leo": 4,
            "Uranus in Pisces": 4,
            "Uranus in H1": 4,
            "Pluto in Cancer": 7,
            "Pluto in H4": 5,
            "Lilith in H10": 4,
            "Juno in H4": 5,
            "Pallas in H3": 4,
            "Fortune in H8": 5,
            "Chiron in Aries": 4,
            "Vesta in Taurus": 5,
            "Ceres in Leo": 5,
            "Rahu in Aquarius": 4,
            "Lilith in Sagittarius": 4,
            "Cancer in H1": 2,
            "Taurus in H10": 4,
            "Gemini in H12": 4,
            "Pallas in Cancer": 5,
            "Scorpio in H4": 4,
            "Chiron in Pisces": 8,
            "Pisces in H7": 6,
            "Neptune in Libra": 6,
            "Pallas in Pisces": 6,
            "Ceres in Taurus": 7,
            "Mars in Pisces": 5,

            "Sun in Aquarius": -5,
            "Sun in Libra": -3,
            "Moon in Taurus": -6,
            "Moon in H10": -5,
            "Mercury in Aquarius": -4,
            "Mercury in Libra": -4,
            "Mercury in H11": -8,
            "Venus in Leo": -2,
            "Venus in Sagittarius": -3,
            "Venus in Scorpio": -3,
            "Mars in Cancer": -8,
            "Mars in H10": -13,
            "Jupiter in Aries": -3,
            "Jupiter in Gemini": -6,
            "Saturn in Libra": -2,
            "Saturn in H10": -4,
            "Saturn in H12": -6,
            "Neptune in Capricorn": -4,
            "Neptune in H5": -6,
            "Neptune in H7": -5,
            "Uranus in Sagittarius": -5,
            "Pluto in H4": -9,
            "Fortune in Leo": -4,
            "Fortune in H7": -4,
            "Chiron in Aquarius": -6,
            "Chiron in H12": -6,
            "Chiron in H5": -8,
            "Juno in Leo": -5,
            "Juno in Cancer": -5,
            "Pallas in H10": -7,
            "Pallas in Aquarius": -5,
            "Pallas in H8": -7,
            "Ceres in Pisces": -6,
            "Ketu in Aries": -8,
            "Ketu in H7": -8,
            "Rahu in Libra": -8,
            "Rahu in H1": -8,
            "Fortune in Aquarius": -5,
            "Vesta in Leo": -6,
            "Vesta in H12": -7,
            "Pisces in H10": -9,
            "Cancer in H1": -18,
        },

        "antipositions": {},

        "aspects": {
            "Saturn trine Vesta": 5,
            "Pallas square Uranus": 3,
            "Chiron trine Neptune": 4,
            "Mercury trine Moon": 6,
            "Neptune trine Fortune": 4,
            "Lilith trine Vesta": 4,
            "Mars conjunction Mercury": 4,
            "Fortune trine Venus": 4,
            "Rahu trine Venus": 4,
            "Chiron sextile Venus": 4,
            "Pluto sextile Vesta": 4,
            "Ketu square Neptune": 4,
            "Lilith sextile Uranus": 5,
            "Jupiter square Pluto": 4,
            "Jupiter trine Neptune": 4,
            "Mercury square Neptune": 4,
            "Neptune square Saturn": 4,
            "DS square Sun": 4,
            "IC trine Moon": 4,

            "Chiron opposition Uranus": -5,
            "Sun semisquare Venus": -6,
            "Pallas square Saturn": -10,
            "Juno square Venus": -8,
            "Ceres square Uranus": -6,
            "Ketu square Fortune": -6,
            "Mars square Neptune": -5,
            "Lilith sextile Uranus": -7,
            "Jupiter square Vesta": -6,
            "Saturn sextile Uranus": -7,
            "Sun square Vesta": -6,
            "Ketu square Vesta": -5,
        },

        "antiaspects": {},

        "gates": {
            7: 7,
            62: 7,
            1: 6,
            37: 6,
            53: 5,
            40: 4,
            61: 4,
            13: 4,
            50: 7,
            52: 6,
            56: 6,
            55: 6,
            42: 6,
            49: 8,
            54: 7,
            27: 9,
            36: 6,
            39: 10,
            60: 10,
            24: 5,
            4: 21,
            16: 12,

            59: -5,
            28: -5,
            18: -5,
            10: -7,
            11: -6,
            9: -7,
            15: -7,
            44: -6,
            26: -9,
            7: -9,
            61: -10,
            9: -9,
            29: -5,
            5: -5,
            17: -9,
            62: -5,
            21: -6,
            35: -5,
            34: -11,
            32: -10,
        },

        "antigates": {},

        "hdtypes": {
            "MF Generator": -4,
        },

        "profiles": {
            "6/2": 5,
            "5/1": 5,
            "3/5": -4,
            "1/3": -3,
        },

        "authorities": {
            "Emotional": 2,
            "Sacral": -2,
        },

        "polarizing": {
            "positions": {
                "Cancer in H1": {
                    "positive": 2,
                    "negative": -18,
                    "net": -16,
                    "note": "Strongly divided; likely anti-broad-appeal, but may still produce niche magnetism.",
                },
                "Pluto in H4": {
                    "positive": 5,
                    "negative": -9,
                    "net": -4,
                    "note": "Private intensity; polarizing rather than cleanly anti-charisma.",
                },
                "Saturn in H10": {
                    "positive": 4,
                    "negative": -4,
                    "net": 0,
                    "note": "Status visibility without easy likability.",
                },
            },
            "aspects": {
                "Lilith sextile Uranus": {
                    "positive": 5,
                    "negative": -7,
                    "net": -2,
                    "note": "Niche magnetism / volatility; not cleanly positive or negative.",
                },
            },
            "gates": {
                7: {"positive": 7, "negative": -9, "net": -2},
                9: {"positive": 7, "negative": -9, "net": -2},
                61: {"positive": 4, "negative": -10, "net": -6},
                62: {"positive": 7, "negative": -5, "net": 2},
            },
        },

        "notes": {
            "Libra": "Underrepresented in CHA sample may mean social polish without attention capture.",
            "Aquarius": "Probably anti-broad appeal, not anti-niche charisma.",
            "Sagittarius": "May be too diffuse or blunt for broad charisma in this sample.",
            "CHA overall": "Keep polarizing factors separate; charisma is not one variable wearing six hats.",
        },
    },
}