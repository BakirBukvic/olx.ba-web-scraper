Problemi:
- Ciscenje podataka nije perfektno, moguce je da u dataset uleti npr: "Displej za telefon" a zapravo trazite telefon
- Open AI API prima vrlo mnogo podataka, cijene su relativno velike ako se radi veliki projekat prikupljanja podataka
- Moguce preopterecenje na Olx.ba API jer se mora svaki predmet zvati pojedinacno


Python skripta koja vas uloguje u Olx.ba, te koristi Olx.ba API da prikupi informacije o predmetima prodaje.
Predmete pokazuje u zavisnosti od kategorije koje izaberete i pretrage.


Kako radi?

PRIKUPLJANJE
1. Konstruise url u zavisnosti od vasih parametara (kategorije i search teksta)
2. Sa searcha uzme koliko je max stranica mogucih
3. Unesete kroz koliko stranica zelite da prodje
4. Uzima sve urlove predmeta za prodaju, url je tipa: artikal/<Artikal ID>
5. Sacuva sve ID-ove predmeta
6. Pokrece OLX.ba API GET request za iteme, API ocekuje da mu dadnes url sa artikal ID-om. API u responsu dadne json sa svim informacija predmeta, ukljucujuci cijenu i titl


CISCENJE
1. Uzme ekstreme pomocu kvartilnog ciscenja i z point ciscenja.
 Kvartilno ->https://medium.com/@datasciencejourney100_83560/how-to-handle-outliers-in-a-dataset-data-cleaning-exploratory-data-analysis-1fd0bf7f7d60
 Z point -> https://medium.com/@datasciencejourney100_83560/z-score-to-identify-and-remove-outliers-c17382a4a739

2. Korisit Open AI za ciscenje predmeta ciji titlovi ne pripadaju korisnikovim parametrima (kategroiji i tekst pretrazivanja).
Ovaj dio nije nuzan, ako korisnik nema Open AI API key samo preskoci.
Ako ima: Salje u batchovima python dict, koji u sebi sadrze ID i Title, ako dzipiti primjeti da neki titl ne pripada u kontestku onda posalje nazad ID, sa ' , ' delimiterom
3. Svi ID-ovi koje Dzipiti primjeti se prikupe, te dati ID-ovi se izbrisu iz Dataseta.

Porhani se u csv formatu: 
ID, price, title



















