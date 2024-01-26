import pandas as pd
import numpy as np

class precipitation:
    @classmethod
    def from_file(cls,path):
        """
        Create precipitation from a given file.
        
        :param path: Path to the precipitation file
        :return: precipitation object

        STATIONS_ID - Station ID
        MESS_DATUM - Referendatum yyyymmdd24
        QN_8 - Qualitaetsniveau
        R1 - Niederschlagshöhe
        RS_IND - Indikator Niederschlag, \\0 nein, \\1 ja, \\-999Fehlwert
        WRTR - Niederschagsform \\0 kein Niederschlag
                                \\1 nur Regen (vor dem 01.01.1979)
                                \\4 Form nicht bekannt
                                \\6 nur Regen
                                \\7 nur Schnee
                                \\8 Regen und Schnee
                                \\9 Fehlkennung
                                \\-999 Fehlwert
        QN - Qualitaetsinformation
        QB - Qualitaetsbyte
        
                    
        """
        try:
            df= pd.read_csv(path, sep=';', skiprows =1,names=[
                'STATIONS_ID','MESS_DATUM','QN_8','R1','RS_IND','WRTR','eor'
            ])
            # Extracting year, month, day, and hour from 'MESS_DATUM'
           
            df['JAHR'] = df['MESS_DATUM'].astype(str).str[:4]
            df['MONAT'] = df['MESS_DATUM'].astype(str).str[4:6]
            df['TAG'] = df['MESS_DATUM'].astype(str).str[6:8]
            df['STUN'] = df['MESS_DATUM'].astype(str).str[8:]
            df.rename(columns={'R1': 'PCP', 'QN_8' :'QB4'},inplace = True)
        
        except Exception as e:
            raise ValueError(f"Error reading percipitation file: {e}")
        
        return cls(df)
    
    def __init__(self, df):
        """
        Initialize precipitation object from a DataFrame.
        
        :param df: DataFrame containing precipitation data.
        """
        self.attrs = {
         'Format': {
            'STATIONS_ID': '%s',
            'JAHR': '%.4d',
            'MONAT': '%0.2d',
            'TAG': '%0.2d',
            'STUN': '%0.2d',
            'NULL': '%s',
            'RS_IND': '%.1d',
            'WRTR': '%.1d',
            'PCP': '%0.2f',
            'QB4': '%.1d',
            'eor': '%s'
            }
        }

        df['JAHR'] = df['JAHR'].astype(np.int64)
        df['MONAT'] = df['MONAT'].astype(np.int64)
        df['TAG'] = df['TAG'].astype(np.int64)
        df['STUN'] = df['STUN'].astype(np.int64)

        self.df = df

    def save(self, path):
        """
        Save precipitation data to a text file.
        
        :param path: Path where the data will be saved.
        """
        try:
            # Speichern Sie die Daten unter Verwendung des angegebenen Formats und Pfads
            self.df.to_csv(
                path,
                sep=';',
                header=False,
                index=False,
                line_terminator='\n',
                float_format='%.3f',
                columns=[
                    'STATIONS_ID', 'MESS_DATUM', 'QB4', 'PCP', 'RS_IND', 'WRTR', 'eor'
                ]
            )
            return(f"Die Niederschlagsdaten wurden erfolgreich unter {path} gespeichert.")
        except Exception as e:
            return(f"Fehler beim Speichern der Niederschlagsdaten: {e}")