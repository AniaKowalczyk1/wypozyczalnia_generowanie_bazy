import random
from faker import Faker
import psycopg2
from psycopg2.extras import execute_batch
from datetime import timedelta, date

fake = Faker("pl_PL")

DB_CONFIG = {
    "host": "localhost",
    "dbname": "wypozyczalnia",
    "user": "postgres",
    "password": "1234",
    "port": 5432
}

MAX_LEN = {
    "imie": 50,
    "nazwisko": 50,
    "rola": 50,
    "login": 50,
    "email": 100,
    "nazwa_filia": 100,
    "adres": 255,
    "tytul": 255,
    "gatunek": 50,
    "rezyser": 100,
    "metoda": 50
}

def truncate(s, max_len):
    return s[:max_len]

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# ---------------------------
# FILIA
# ---------------------------
filie = [(truncate(fake.company(), MAX_LEN["nazwa_filia"]),
          truncate(fake.address(), MAX_LEN["adres"]),
          truncate(fake.phone_number(), MAX_LEN["adres"]),
          truncate(fake.company_email(), MAX_LEN["email"]))
         for _ in range(10)]
execute_batch(cur,
    "INSERT INTO Filia (nazwa, adres, telefon, email) VALUES (%s,%s,%s,%s)",
    filie
)

# ---------------------------
# KLIENCI
# ---------------------------
klienci = [(truncate(fake.first_name(), MAX_LEN["imie"]),
            truncate(fake.last_name(), MAX_LEN["nazwisko"]),
            truncate(fake.address(), MAX_LEN["adres"]))
           for _ in range(10000)]
execute_batch(cur,
    "INSERT INTO Klient (imie, nazwisko, adres) VALUES (%s,%s,%s)",
    klienci
)

# ---------------------------
# PRACOWNICY
# ---------------------------
pracownicy = []
for filia_id in range(1, 11):
    for _ in range(random.randint(3, 10)):
        pracownicy.append((
            truncate(fake.first_name(), MAX_LEN["imie"]),
            truncate(fake.last_name(), MAX_LEN["nazwisko"]),
            truncate(random.choice(["pracownik", "kierownik", "kasjer", "admin"]), MAX_LEN["rola"]),
            filia_id
        ))
execute_batch(cur,
    "INSERT INTO Pracownik (imie, nazwisko, rola, id_filii) VALUES (%s,%s,%s,%s)",
    pracownicy
)

# Mapowanie filii -> pracownicy
filia_do_pracownikow = {i+1: [] for i in range(10)}
for idx, prac in enumerate(pracownicy, start=1):
    filia_do_pracownikow[prac[3]].append(idx)

# ---------------------------
# KONTO
# ---------------------------
kont_pracownicy = [(truncate(f"{p[0].lower()}.{p[1].lower()}{i}", MAX_LEN["login"]),
                    truncate(f"{p[0].lower()}.{p[1].lower()}{i}@example.com", MAX_LEN["email"]),
                    fake.password(length=10),
                    p[2],
                    i,
                    None)
                   for i, p in enumerate(pracownicy, start=1)]
kont_klienci = [(truncate(f"{k[0].lower()}.{k[1].lower()}{i}", MAX_LEN["login"]),
                 truncate(f"{k[0].lower()}.{k[1].lower()}{i}@example.com", MAX_LEN["email"]),
                 fake.password(length=10),
                 'klient',
                 None,
                 i)
                for i, k in enumerate(klienci, start=1)]
execute_batch(cur,
    "INSERT INTO Konto (login, email, haslo, rola, id_pracownika, id_klienta) VALUES (%s,%s,%s,%s,%s,%s)",
    kont_pracownicy + kont_klienci
)

# ---------------------------
# FILMY
# ---------------------------
gatunki = ["Akcja", "Dramat", "Komedia", "Sci-Fi", "Horror"]
filmy = [(truncate(fake.sentence(nb_words=3), MAX_LEN["tytul"]),
          truncate(random.choice(gatunki), MAX_LEN["gatunek"]),
          random.randint(1985, 2024),
          truncate(fake.first_name() + " " + fake.last_name(), MAX_LEN["rezyser"]),
          truncate(fake.text(max_nb_chars=200), 200))
         for _ in range(2000)]
execute_batch(cur,
    "INSERT INTO Film (tytul, gatunek, rok_wydania, rezyser, opis) VALUES (%s,%s,%s,%s,%s)",
    filmy
)

# ---------------------------
# EGZEMPLARZE
# ---------------------------
egzemplarze = []
for _ in range(10000):
    r = random.random()
    if r < 0.02:
        status = 'uszkodzony'
    elif r < 0.10:
        status = 'zarezerwowany'
    elif r < 0.50:
        status = 'dostępny'
    else:
        status = 'wypożyczony'
    egzemplarze.append((status, random.randint(1, 2000), random.randint(1, 10)))
execute_batch(cur,
    "INSERT INTO Egzemplarz (status, id_filmu, id_filii) VALUES (%s,%s,%s)",
    egzemplarze
)

# Mapowanie filii -> egzemplarze
filia_do_egzemplarzy = {i+1: [] for i in range(10)}
for idx, egz in enumerate(egzemplarze):
    filia_do_egzemplarzy[egz[2]].append((idx+1, egz[0]))

# ---------------------------
# WYPOŻYCZENIA
# ---------------------------
wypozyczenia = []
for _ in range(10000):
    start = fake.date_between(start_date="-60d", end_date="-1d")
    termin = start + timedelta(days=random.randint(3, 10))
    zwrot = None
    if random.random() > 0.3:
        zwrot = termin + timedelta(days=random.randint(0, 5))
    filia_wyp = random.randint(1, 10)
    id_pracownika = None if random.random() < 0.2 else random.choice(filia_do_pracownikow[filia_wyp])
    wypozyczenia.append((start, termin, zwrot, id_pracownika, None, filia_wyp))

# ---------------------------
# PRZYDZIELANIE KLIENTÓW
# ---------------------------
klienci_aktywni = list(range(1, 1001))
klienci_srednio_aktywni = list(range(1001, 5001))
klienci_raz_na_rzadko = list(range(5001, 10001))

wypozyczenia_real = []
for wyp in wypozyczenia:
    start, termin, zwrot, id_pracownika, _, filia_wyp = wyp
    r = random.random()
    if r < 0.5:
        id_klienta = random.choice(klienci_aktywni)
    elif r < 0.85:
        id_klienta = random.choice(klienci_srednio_aktywni)
    else:
        id_klienta = random.choice(klienci_raz_na_rzadko)
    wypozyczenia_real.append((start, termin, zwrot, id_pracownika, id_klienta, filia_wyp))

wypozyczenia = wypozyczenia_real

execute_batch(cur,
    "INSERT INTO Wypozyczenie (data_wypozyczenia, termin_zwrotu, data_zwrotu, id_pracownika, id_klienta, id_filii) VALUES (%s,%s,%s,%s,%s,%s)",
    wypozyczenia
)

# ---------------------------
# WYPOŻYCZENIE ↔ EGZEMPLARZ
# ---------------------------
we = []
zajete_egzemplarze = set()

for i, wyp in enumerate(wypozyczenia, start=1):
    start, termin, zwrot, id_pracownika, id_klienta, filia_wyp = wyp

    # Lista egzemplarzy w filii, które można przypisać
    egz_list = [egz_id for egz_id, status in filia_do_egzemplarzy[filia_wyp]
                if egz_id not in zajete_egzemplarze]

    if not egz_list:
        # Jeśli wszystkie już zajęte, weź wszystkie egzemplarze filii
        egz_list = [egz_id for egz_id, _ in filia_do_egzemplarzy[filia_wyp]]

    # Losowa liczba egzemplarzy do przypisania (1–3)
    liczba_egz = random.randint(1, min(3, len(egz_list)))
    wybrane_egz = random.sample(egz_list, liczba_egz)

    for egz_id in wybrane_egz:
        we.append((i, egz_id))
        zajete_egzemplarze.add(egz_id)

        # Pobranie obecnego statusu
        cur.execute("SELECT status FROM Egzemplarz WHERE id_egzemplarza=%s", (egz_id,))
        obecny_status = cur.fetchone()[0]

        # Ustaw status zgodnie z datą zwrotu, z losową szansą na zarezerwowany/uszkodzony
        if zwrot is None:
            # egzemplarz nadal w wypożyczeniu
            nowy_status = 'wypożyczony'
        else:
            # egzemplarz już oddany
            r = random.random()
            if r < 0.1:
                nowy_status = 'uszkodzony'
            elif r < 0.2:
                nowy_status = 'zarezerwowany'
            else:
                nowy_status = 'dostępny'
        # Aktualizacja w bazie
        cur.execute("UPDATE Egzemplarz SET status=%s WHERE id_egzemplarza=%s", (nowy_status, egz_id))

# Wstawienie powiązań do tabeli
execute_batch(cur,
              "INSERT INTO Wypozyczenie_Egzemplarz (id_wypozyczenia, id_egzemplarza) VALUES (%s,%s)",
              we)

# ---------------------------
# PŁATNOŚCI
# ---------------------------
platnosci = []
wyp_to_egz_count = {}
for wyp_id, egz_id in we:
    wyp_to_egz_count[wyp_id] = wyp_to_egz_count.get(wyp_id, 0) + 1

for i, wyp in enumerate(wypozyczenia, start=1):
    liczba_egz = wyp_to_egz_count.get(i, 1)
    start = wyp[0]
    termin = wyp[1]
    id_pracownika = wyp[3]
    dni = (termin - start).days
    kwota = round(dni * 5 * liczba_egz, 2)
    data_platnosci = start - timedelta(days=random.randint(1,7)) if id_pracownika is None else start + timedelta(days=random.randint(0,1))
    metoda = truncate(random.choice(["karta","gotówka","blik"]), MAX_LEN["metoda"])
    platnosci.append((kwota, data_platnosci, metoda, i))

execute_batch(cur,
              "INSERT INTO Platnosc (kwota, data_platnosci, metoda, id_wypozyczenia) VALUES (%s,%s,%s,%s)",
              platnosci
)

# ---------------------------
# KARY
# ---------------------------
kary = []
for i, wyp in enumerate(wypozyczenia, start=1):
    data_zwrotu = wyp[2]
    termin_zwrotu = wyp[1]
    if data_zwrotu and data_zwrotu > termin_zwrotu:
        dni_spoznienia = (data_zwrotu - termin_zwrotu).days
        kwota_za_dzien = round(random.uniform(2,5),2)
        kwota_calkowita = round(dni_spoznienia*kwota_za_dzien,2)
        oplacone = random.choice([True,False])
        kary.append((dni_spoznienia, kwota_za_dzien, kwota_calkowita, oplacone, i))

execute_batch(cur,
              "INSERT INTO Kara (dni_spoznienia, kwota_za_dzien, kwota_calkowita, oplacone, id_wypozyczenia) VALUES (%s,%s,%s,%s,%s)",
              kary
)

# ---------------------------
# REZERWACJE
# ---------------------------
rezerwacje = []
rezerwacja_egz = []


klienci_do_rezerwacji = list(range(1, 2001))

# Mapa filia -> egzemplarze dostępne
dostepne_egzemplarze = {i + 1: [] for i in range(10)}
for idx, egz in enumerate(egzemplarze):
    if egz[0] == 'dostępny':
        filia_id = egz[2]
        dostepne_egzemplarze[filia_id].append(idx + 1)

rezerwacja_id_counter = 1

for _ in range(1000):  # generujemy 1000 rezerwacji
    id_klienta = random.choice(klienci_do_rezerwacji)
    filia_id = random.randint(1, 10)

    egz_list = dostepne_egzemplarze[filia_id]
    if not egz_list:
        continue  # jeśli brak dostępnych egzemplarzy w tej filii, pomiń

    liczba_egz = random.randint(1, min(3, len(egz_list)))
    wybrane_egz = random.sample(egz_list, liczba_egz)

    # Data rezerwacji i termin odbioru
    data_rezerwacji = fake.date_between(start_date="-30d", end_date="today")
    termin_odbioru = data_rezerwacji + timedelta(days=random.randint(3, 7))

    # Dodanie do listy rezerwacji
    rezerwacje.append((data_rezerwacji, termin_odbioru, 'AKTYWNA', id_klienta))

    # Dodanie do tabeli pośredniej
    for egz_id in wybrane_egz:
        rezerwacja_egz.append((rezerwacja_id_counter, egz_id))
        # aktualizacja statusu egzemplarza na 'zarezerwowany'
        cur.execute("UPDATE Egzemplarz SET status='zarezerwowany' WHERE id_egzemplarza=%s", (egz_id,))
        dostepne_egzemplarze[filia_id].remove(egz_id)

    rezerwacja_id_counter += 1

# Wstawienie danych do bazy
execute_batch(cur,
              "INSERT INTO Rezerwacja (data_rezerwacji, termin_odbioru, status, id_klienta) VALUES (%s,%s,%s,%s)",
              rezerwacje)

execute_batch(cur,
              "INSERT INTO Rezerwacja_Egzemplarz (id_rezerwacji, id_egzemplarza) VALUES (%s,%s)",
              rezerwacja_egz)



# ---------------------------
# ZAMKNIĘCIE POŁĄCZENIA
# ---------------------------
conn.commit()
cur.close()
conn.close()

print("✅ Dane testowe wygenerowane realistycznie")
