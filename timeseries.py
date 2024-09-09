
import pandas as pd
import datetime
import numpy as np
import math
import precipitation
import re

class timeseries:
  @classmethod
  def from_file(cls, path_or_obj):
        """
        Create timeseries from a given DMNA file.

        :param path_or_obj: Path to the DMNA file or timeseries object.
        :return: timeseries object
        """ 
        if isinstance(path_or_obj, timeseries):
           return path_or_obj
        
        try:
            with open(path_or_obj, 'r') as file:
                z0s=None
                z=None        
                
                # Read the header lines to extract information
                ak_line_index = next((i for i, line in enumerate(file) if line.startswith('AK')), None)
                file.seek(0)

                header_lines = [next(file) for _ in range(int(ak_line_index))]
                print("Header Lines:", header_lines)

                name_line = header_lines[1].strip().split()
                print("Name Line:", name_line)

                date_line = header_lines[2].strip().split()
                print("Date Line:", date_line)
                
                name = ' '.join(name_line[2:])

                ha_line = header_lines[3].strip().split()
                ha = [item for item in ha_line if item.isdigit()]
                                    
                file.seek(0)

                df = pd.read_csv(file, delim_whitespace=True,header = 5 , names=[
                    'KENN', 'STA', 'JAHR', 'MONAT', 'TAG', 'STUN', 'NULL', 'QDD', 'QFF', 'DD', 'FF', 'QB1', 'KM', 'QB2',
                    'HM', 'QB3', 'PCP', 'QB4'
                ])
                print(df[:2])
        except Exception as e:
            raise ValueError(f"Error reading AKTERM file: {e}")
        return cls(df['STA'].iloc[0], name, df['JAHR'].iloc[0] , z, df['FF'], df['DD'], df['KM'], z0s, ha, precipitation=df['PCP'], month=1, day=1)

  def __init__(self, sta, name, year, z, u, dd, kmclass, z0s, ha, precipitation , month=1, day=1):
    """
    A pandas dataframe that describes the data of hourly wind measurments (and possibly precipitation) for a specific year. 
    :param u: Wind measurments:
    :return: z0s
    """
    if not len(u) == len(dd) == len(kmclass):
      raise ValueError('Length of data arrays should be equal but len(u)={}, len(dd)={} and len(kmclass)={}'.format(len(u), len(dd), len(kmclass)))
    if (precipitation.notna().any()) and (len(precipitation) != len(u)):
      raise ValueError('Length of data arrays should be equal but len(u)={}, len(dd)={}, len(kmclass)={}, len(precipitation)={}'.format(len(u), len(dd), len(kmclass), len(precipitation)))
    self.attrs = {
      'Format': {
        'KENN': '%s',
        'STA': '%s',
        'JAHR': '%.4d',
        'MONAT': '%0.2d',
        'TAG': '%0.2d',
        'STUN': '%0.2d',
        'NULL': '%s',
        'QDD': '%.1d',
        'QFF': '%.1d',
        'DD': '%3d',
        'FF': '%3d',
        'QB1': '%.1d',
        'KM': '%.1d',
        'QB2': '%.1d',
        'HM': '%+.3d',
        'QB3': '%.1d',
        'PCP': '%.3d',
        'QB4': '%.1d'
      }
    }
    self.name = name
    self.id = sta
    self.z = z
    self.year = year
    self.z0s = z0s
    self.ha = ha

    n = len(u)

    df = pd.DataFrame()
    df['KENN'] = ['AK']*n
    sta_str = str(sta).zfill(5)
    df['STA'] = [sta_str]*n
    df['JAHR'] = [year]*n

    x = datetime.datetime(year,month,day,0,0)
    dates = [x + datetime.timedelta(hours=i) for i in range(0, n)]

    month = []
    day = []
    hour = []
    for d in dates:
      month.append(d.month)
      day.append(d.day)
      hour.append(d.hour)

    df['MONAT'] = month
    df['TAG'] = day
    df['STUN'] = hour
    df['NULL'] = ['00']*n
    df['QDD'] = [1]*n
    df['QFF'] = [1]*n
    df['DD'] = dd
    df['FF'] = u
    df['QB1'] = [1]*n
    df['KM'] = kmclass
    df['QB2'] = [1]*n
    df['HM'] = [-999]*n
    df['QB3'] = [9]*n

    #@lennart - warum wurde hier FF mit 10 multipliziert? Sorgt im fall von updatePrecipitation für Fehler.
    #df['FF'] = df['FF']*10

    if (precipitation.notna().any()):
      self.precipitation = precipitation
      self.withprecipitation = True
      self.__formatprecipitation()
      df.loc[df['PCP']] = self.formattedPrecipitation
      df.loc[df['QB4']] = [1]*n 
      df.loc[df['PCP'] == 0, 'QB4'] = 9

    else:
      self.withprecipitation = False

    self.df = df

    # Set quality byte for missing values 
    df.loc[df['DD'].isna(), 'QDD'] = 9
    df.loc[df['DD'].isna(), 'DD'] = 0
    df.loc[df['FF'].isna(), 'QFF'] = 9
    df.loc[df['FF'].isna(), 'FF'] = 0

    self.valid = True

  def save(self, file):
    fmtstr = ''
    for i, f in enumerate(self.attrs['Format']):
      fmtstr += self.attrs['Format'][f]
      if i == len(self.df.columns)-1:
        break
      fmtstr += ' '

    header = '* AKTerm Zeitreihe, Ingenieurbuero Richters & Huels, Ahaus, {}'.format(datetime.date.today())
    if self.withprecipitation:
      header += ', mit Niederschlag\n'
    else:
      header += '\n'
    
    # Station Info
    header += '* Station {} ({}), Jahr {}\n'.format(self.name, self.id, self.year)
    header += '* href=100m, z0s={}, hs={}\n'.format(self.z0s,self.z)
    header += '+ Anemometerhoehen (0.1 m): ' + '  '.join(str(e) for e in self.ha)

    nparray = self.df.to_numpy()
    np.savetxt(file, nparray, fmt=fmtstr, header=header, comments='')

  
  def updatePrecipitation(self, precipitation):
    """
    Update akterm data with precipitation information.

    :param precipitation: Precipitation object containing data to be added.
    """

    """if not isinstance(precipitation, precipitation):
        raise ValueError("Invalid precipitation object provided.")
    """
    if not all(col in precipitation.df.columns for col in ['JAHR', 'MONAT', 'TAG', 'STUN', 'PCP', 'QB4']):
        raise ValueError("Precipitation object must have 'JAHR', 'MONAT', 'TAG', 'STUN', 'PCP', and 'QB4' columns.")

    if not all(col in self.df.columns for col in ['JAHR', 'MONAT', 'TAG', 'STUN']):
        raise ValueError("akterm object must have 'JAHR', 'MONAT', 'TAG', and 'STUN' columns.")   

    
    self.df['PCP']=[None] * len(self.df)
    self.df['QB4']=[None] * len(self.df)

    index_cols = ['JAHR', 'MONAT', 'TAG', 'STUN']
    merged_df = pd.merge(self.df[index_cols], precipitation.df[['JAHR', 'MONAT', 'TAG', 'STUN', 'PCP', 'QB4']], on=index_cols, how='left')

    self.df['PCP'] = merged_df['PCP']
    self.df['QB4'] = merged_df['QB4']

    # Optional: Set missing values to 0 or other default values
    self.df['PCP'].fillna(0, inplace=True)
    self.df['QB4'].fillna(9, inplace=True)
    
    self.withprecipitation = True
    self.__formatprecipitation()
    self.df['PCP'] = self.formattedPrecipitation
    self.df['QB4'] = 1

    
  
  def __formatprecipitation(self):
    def synop(i):
      if math.isnan(i):
        return 0
      if i >= 1:
        if i <=989:
          return int(round(i,0))
        return 989
      else:
        if i < 0.05:
          return 990
        else:
          return int(round(i*10,0)) + 990
    if self.withprecipitation:
      self.formattedPrecipitation = [synop(i) for i in self.df['PCP']]