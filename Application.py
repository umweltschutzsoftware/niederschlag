import streamlit as st
import numpy as np
import pandas as pd
import io
from io import StringIO
import os
import re
from urllib import request
import zipfile
import datetime
import pydeck as pdk
from geopy.geocoders import Nominatim
from functools import partial
from bs4 import BeautifulSoup
from akterm import akterm
from precipitation import precipitation
import tempfile
import shutil
from tempfile import NamedTemporaryFile

st.set_page_config(
            page_title="R&H Niederschlag"
)
temp_dir = os.path.join('.', 'temp')
os.makedirs(temp_dir,exist_ok=True)
precipitation_data_path= os.path.join(temp_dir, "precipitation_data.txt")
akterm_instance_path = os.path.join(temp_dir, "akterm_instance.akterm")

def searchforzip (file_number):
  # open https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/precipitation/historical/
  # look for .zip belonging to Stations_id; Download Zip; Load produkt{}.txt in pd  
  url="https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/precipitation/historical/"
  file_prefix='stundenwerte_RR_' + file_number
  html_content= request.urlopen(url).read()
  soup= BeautifulSoup(html_content, 'html.parser')
  links= soup.find_all('a', href=True)
 
  zip_file_urls=[link['href'] for link in links if link['href'].endswith('.zip') and link['href'].startswith(file_prefix)]
  if zip_file_urls:
    zip_file_url = url + zip_file_urls[0]
    with request.urlopen(zip_file_url) as response, zipfile.ZipFile(io.BytesIO(response.read())) as z:
      txt_file=[file for file in z.namelist() if file.endswith('.txt') and file.startswith('produkt')]

      if txt_file:
        temp_file_path = os.path.join(temp_dir, txt_file[0])
        precipitation_data_path = os.path.join(temp_dir, "precipitation_data.txt")
        with z.open(txt_file[0]) as zip_file, open(temp_file_path, 'wb') as target_file:
         target_file.write(zip_file.read())
    
        # Schreiben Sie den Inhalt der Textdatei in precipitation_data_path
        with open(precipitation_data_path, 'w') as file:
         file.write(open(temp_file_path).read())

      

        return temp_file_path        
      else: 
        st.warning(f"Keine passende .txt-Datei gefunden!")
        return None
  else:
    st.warning(f'Keine passene Zip-Datei gefunden!')
    return None 

def stationsfromtxt(url, urlfmt=None):
  # open file from url
  # replace the whitespaces by ; - take attention to column "Stationsname" as these names may be separated by whitespace but should not match to different columns
  filestring = ''
  for line in request.urlopen(url):
    s = line.decode('latin1')
    if s[0] == 'S':
      # this is the first line
      s = re.sub("\\s+", ";", s.strip())
    elif s[0] == "-":
      continue
    else:
      s = re.sub("([0-9])(\\s+)([0-9])", r'\1;\3', s.strip())
      s = re.sub("\\s{2,}", r';', s)
      s = re.sub("([0-9])(\\s+)", r'\1;', s)
    filestring += s + '\n'
  output = StringIO(filestring)
  
  allstationdf = pd.read_csv(
    output, 
    delimiter=";",
    dtype={
      'Stations_id': 'string',
      'Stationsname': 'string',
      'Bundesland': 'string',
      'von_datum': 'string',
      'bis_datum': 'string'
    })
  allstationdf['Startdatum'] = allstationdf.apply(lambda x: datetime.datetime.strptime(str(x['von_datum']), '%Y%m%d'), axis=1)
  allstationdf['Enddatum'] = allstationdf.apply(lambda x: datetime.datetime.strptime(str(x['bis_datum']), '%Y%m%d'), axis=1)
 
  return allstationdf

st.write(
    '''.akterm Niederschlag hinzufügen
    ''')

#Create Map and pin geolocations
station_df = stationsfromtxt("https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/precipitation/historical/RR_Stundenwerte_Beschreibung_Stationen.txt")
deck=pdk.Deck(
  map_style=None,
  initial_view_state=pdk.ViewState(
    latitude=51.545893,
    longitude=9.932010,
    zoom=4.5,
    pitch=0,
  ),
  layers=[
    pdk.Layer(
      'ScatterplotLayer',
      data= station_df,
      get_position='[geoLaenge, geoBreite]',
      get_radius='2000',  
      get_color='[200, 30, 0, 160]',
      pickable=True,
    ),
    ],
  tooltip={
    "html": "<b> </b>"
    "<br/> <b>Name:</b> {Stationsname}"
    "<br/> <b>ID:</b> {Stations_id}"
    "<br/> <b>lat:</b> {geoBreite}"
    "<br/> <b>lon:</b> {geoLaenge}"
    "<br/> <b>Bundesland:</b>{Bundesland}"
    "<br/> <b>Startdatum:</b>{von_datum}"
    "<br/> <b>Enddatum:</b> {bis_datum}",
  },
)
#chart_container.pydeck_chart(deck)
# Input for address using Nominatim
address_input = st.text_input("Adresseingabe:")
if st.button("Suche nach Adresse"):
    if address_input:
        geolocator = Nominatim(user_agent="your_app_name")
        location = geolocator.geocode(address_input)

        if location:
            # Create a new deck with the updated view state
            updated_deck = pdk.Deck(
                map_style=None,
                initial_view_state=pdk.ViewState(
                    latitude=location.latitude,
                    longitude=location.longitude,
                    zoom=10,
                    pitch=0,
                ),
                layers=[
                    pdk.Layer(
                        'ScatterplotLayer',
                        data=station_df,
                        get_position='[geoLaenge, geoBreite]',
                        get_radius='200',
                        get_color='[200, 30, 0, 160]',
                        pickable=True,
                    ),
                ],
                tooltip={
                    "html": "<b> </b>"
                            "<br/> <b>Name:</b> {Stationsname}"
                            "<br/> <b>ID:</b> {Stations_id}"
                            "<br/> <b>lat:</b> {geoBreite}"
                            "<br/> <b>lon:</b> {geoLaenge}"
                            "<br/> <b>Bundesland:</b>{Bundesland}"
                            "<br/> <b>Startdatum:</b>{von_datum}"
                            "<br/> <b>Enddatum:</b> {bis_datum}",
                },
            )
            # Display the updated deck
            #chart_container.pydeck_chart(updated_deck)
            st.pydeck_chart(updated_deck)
        else:
            st.warning("Location not found. Please enter a valid address.")
    else:
        st.warning("Please enter an address.")

# Input for Station ID
station_id_input = st.text_input("Enter Station ID (e.g., 00978):")

# Button to trigger method
if st.button("Wetterstation auswählen"):
    if station_id_input:
        file_path = searchforzip(station_id_input)
        if os.path.exists(precipitation_data_path):
          if os.access(precipitation_data_path, os.R_OK):
            if precipitation_data_path is not None:
             st.write("Niederschlagsdaten gefunden!")
            else:
             st.write("No data found for the specified Station ID.")
        else:
          st.write("File not found")
    else:
        st.write("Please enter a valid Station ID.")

# Eingabefeld für die Akterm-Datei
uploadedfile = st.file_uploader(label="Akterm Wetterzeitreihe auswählen.", type="akterm", accept_multiple_files=False)
if uploadedfile:
        path = os.path.join(temp_dir, uploadedfile.name)
        with open(path, "wb") as f:
                f.write(uploadedfile.getvalue())

# Button, um die akterm_instance zu erstellena
if st.button("Upload .AKTERM Datei"):
    if uploadedfile is not None:
        # Überprüfen Sie, ob die Dateiendung 'akterm' ist
        if uploadedfile.name.endswith('.akterm'):
            # Erstellen Sie die akterm_instance mit der ausgewählten Datei
            #akterm_instance = akterm.from_file(path)
            shutil.copyfile(path, akterm_instance_path)
            #akterm_instance.save(akterm_instance_path)
            st.write("AKTERM-Datei gefunden.")
        else:
            st.warning("Bitte laden Sie eine gültige Akterm-Datei hoch.")
    else:
        st.warning("Bitte wählen Sie eine Akterm-Datei aus.")

# Button, um die akterm_instance zu aktualisieren und herunterzuladen
if st.button("Aktualisierte AKTERM-Datei herunterladen"):
    precipitation_data = precipitation.from_file(precipitation_data_path)
    akterm_instance = akterm.from_file(akterm_instance_path)
    st.write("Aktermdatei zum Download bereit.")
    if akterm_instance is not None and precipitation_data is not None:
        # Führen Sie die updatePrecipitation-Methode aus
        akterm_instance.updatePrecipitation(precipitation_data)        
        # Speichern Sie die aktualisierte AKTERM-Datei temporär
        updated_akterm_path = os.path.join(temp_dir, "updated_akterm.akterm")
        akterm_instance.save(updated_akterm_path)

        # Lade die Datei herunter
        st.download_button(
            label="Download aktualisierte AKTERM-Datei",
            key="download_updated_akterm",
            data = open(updated_akterm_path, 'rb').read(),
            mime="application/octet-stream",
            on_click=None,  # Benötigt für das Herunterladen der Datei
            file_name="updated_akterm.akterm"
        )
        shutil.rmtree(temp_dir)
    else:
        st.warning("Bitte laden Sie zuerst eine gültige AKTERM-Datei und Niederschlagsdaten hoch.")