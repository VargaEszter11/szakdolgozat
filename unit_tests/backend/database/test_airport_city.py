from database.airport_city import airport_name_as_city


def test_airport_name_as_city_removes_common_facility_suffixes():
    assert airport_name_as_city("Tirana International Airport Nene Tereza", "TIA") == "Tirana"
    assert airport_name_as_city("Andorra la Vella Heliport", "ALV") == "Andorra la Vella"
    assert airport_name_as_city("Flugplatz Wiener Neustadt/Ost", "QEW") == "Wiener Neustadt"


def test_airport_name_as_city_cleans_ground_station_labels():
    assert airport_name_as_city("Aachen Bf West Bus Station", "AAW") == "Aachen Bf West"
    assert airport_name_as_city("Cologne central station", "QKL") == "Cologne"
    assert airport_name_as_city("Rostock Hauptbahnhof", "RTK") == "Rostock"


def test_airport_name_as_city_uses_overrides_for_named_airports():
    assert airport_name_as_city("Estacion de Autobuses Benidorm", "BBF") == "Benidorm"
    assert airport_name_as_city("George Best Belfast City Airport", "BHD") == "Belfast"
    assert airport_name_as_city("Bologna Guglielmo Marconi Airport", "BLQ") == "Bologna"
    assert airport_name_as_city("Budapest Ferenc Liszt International Airport", "BUD") == "Budapest"
    assert airport_name_as_city("Helsinki-Malmi Airport", "HEM") == "Helsinki"
    assert airport_name_as_city("Helsinki-Vantaa Airport", "HEL") == "Helsinki"
    assert airport_name_as_city("Haskovo Malevo Airport", "HKV") == "Haskovo"
    assert airport_name_as_city("Gdansk Lech Walesa Airport", "GDN") == "Gdansk"
    assert airport_name_as_city("Prague Vaclav Havel Airport", "PRG") == "Prague"
    assert airport_name_as_city("John Paul II International Airport Krakow-Balice", "KRK") == "Krakow"
    assert airport_name_as_city("Lyon-Saint Exupery Airport", "LYS") == "Lyon"
    assert airport_name_as_city("Mannheim City Airport", "MHG") == "Mannheim"
    assert airport_name_as_city("Federico Garcia Lorca Airport", "GRX") == "Granada"
    assert airport_name_as_city("Henri Coanda International Airport", "OTP") == "Bucharest"
    assert airport_name_as_city("Falcone-Borsellino Airport", "PMO") == "Palermo"
    assert airport_name_as_city("Targovishte Bukhovtsi Airport", "TGV") == "Targovishte"


def test_airport_name_as_city_keeps_iata_when_no_real_name_exists():
    assert airport_name_as_city("DXB", "DXB") == "DXB"
