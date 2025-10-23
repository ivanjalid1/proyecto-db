#!/bin/python

"""
================================================================================
ETL CASINO - ANÁLISIS REGIONAL DE DEPÓSITOS
================================================================================
Metodología: Hefesto (Extracción → Transformación → Carga)
Propósito: Procesar transacciones de casino y enriquecer con datos geográficos
Fila Aprox: 122,100 registros
Fecha: 2025-10-14
================================================================================
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path

# ================================================================================
# CONFIGURACIÓN DE LOGGING
# ================================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_casino.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ETLCasino:
    """
    Clase que implementa el ETL para análisis regional de depósitos en casino.
    Sigue la metodología Hefesto: Extract → Transform → Load
    """
    
    def __init__(self, csv_path, json_path, json_pobreza_path=None):
        """Inicializa rutas de archivos"""
        self.csv_path = csv_path
        self.json_path = json_path
        self.json_pobreza_path = json_pobreza_path
        self.df_transacciones = None
        self.df_regiones = None
        self.df_pobreza = None
        self.df_procesado = None
        self.area_code_set = None
        self.area_code_to_prov = None
        logger.info("ETL inicializado")
    
    # ============================================================================
    # ETAPA 1: EXTRACCIÓN (EXTRACT)
    # ============================================================================
    
    def extract_csv(self):
        """
        Extrae datos del CSV de transacciones del casino.
        Maneja posibles errores de lectura.
        """
        try:
            logger.info(f"Extrayendo datos de {self.csv_path}")
            self.df_transacciones = pd.read_csv(self.csv_path)
            logger.info(f"✓ CSV extraído: {len(self.df_transacciones)} filas")
            logger.info(f"  Columnas: {list(self.df_transacciones.columns)}")
            return self.df_transacciones
        except FileNotFoundError:
            logger.error(f"✗ Archivo no encontrado: {self.csv_path}")
            raise
        except Exception as e:
            logger.error(f"✗ Error al extraer CSV: {e}")
            raise
    
    def extract_json_regiones(self):
        """
        Extrae datos de regiones desde JSON.
        Estructura esperada: lista de objetos con areaCode, city, province.
        """
        try:
            logger.info(f"Extrayendo datos de {self.json_path}")
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convertir a DataFrame
            self.df_regiones = pd.DataFrame(data)
            logger.info(f"✓ JSON extraído: {len(self.df_regiones)} registros")
            logger.info(f"  Columnas: {list(self.df_regiones.columns)}")
            return self.df_regiones
        except FileNotFoundError:
            logger.error(f"✗ Archivo no encontrado: {self.json_path}")
            raise
        except Exception as e:
            logger.error(f"✗ Error al extraer JSON: {e}")
            raise

    def extract_json_pobreza(self):
        """
        Extrae datos de índices de pobreza desde JSON.
        Estructura esperada: lista de objetos con provincia, ciudad e índices socioeconómicos.
        """
        if not self.json_pobreza_path:
            logger.warning("⚠ No se especificó archivo de datos de pobreza, omitiendo...")
            return None

        try:
            logger.info(f"Extrayendo datos de pobreza de {self.json_pobreza_path}")
            with open(self.json_pobreza_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convertir a DataFrame
            self.df_pobreza = pd.DataFrame(data)
            logger.info(f"✓ JSON pobreza extraído: {len(self.df_pobreza)} registros")
            logger.info(f"  Columnas: {list(self.df_pobreza.columns)}")
            return self.df_pobreza
        except FileNotFoundError:
            logger.error(f"✗ Archivo no encontrado: {self.json_pobreza_path}")
            raise
        except Exception as e:
            logger.error(f"✗ Error al extraer JSON pobreza: {e}")
            raise
    
    # ============================================================================
    # ETAPA 2: TRANSFORMACIÓN (TRANSFORM)
    # ============================================================================

    def normalizar_provincia(self, provincia):
        """
        Normaliza nombres de provincias para hacer match entre diferentes fuentes.
        Elimina acentos y estandariza nombres.
        """
        if pd.isna(provincia):
            return None

        # Diccionario de normalización
        normalizacion = {
            'CÓRDOBA': 'CORDOBA',
            'CORDOBA': 'CORDOBA',
            'NEUQUÉN': 'NEUQUEN',
            'NEUQUEN': 'NEUQUEN',
            'RÍO NEGRO': 'RIO NEGRO',
            'RIO NEGRO': 'RIO NEGRO',
            'TUCUMÁN': 'TUCUMAN',
            'TUCUMAN': 'TUCUMAN',
            'CIUDAD DE BUENOS AIRES': 'BUENOS AIRES',  # CABA se mapea a Buenos Aires
        }

        provincia_upper = str(provincia).upper().strip()
        return normalizacion.get(provincia_upper, provincia_upper)

    def transform_pobreza(self):
        """
        Transforma datos de pobreza:
        - Normaliza nombres de provincias
        - Elimina duplicados por provincia (agregando promedios si hay múltiples ciudades)
        """
        if self.df_pobreza is None:
            logger.warning("⚠ No hay datos de pobreza para transformar")
            return None

        logger.info("🔄 Iniciando transformación de datos de pobreza...")

        df = self.df_pobreza.copy()

        # 1. Normalizar nombres de provincias
        df['provincia_normalizada'] = df['provincia'].apply(self.normalizar_provincia)

        # Detectar cuáles provincias fueron normalizadas
        df['provincia_upper'] = df['provincia'].str.upper().str.strip()
        cambios = df[df['provincia_upper'] != df['provincia_normalizada']]
        sin_cambios = df[df['provincia_upper'] == df['provincia_normalizada']]

        logger.info("  ✓ Provincias normalizadas")
        if len(cambios) > 0:
            logger.info(f"    - Modificadas: {len(cambios['provincia'].unique())} provincias")
            for _, row in cambios[['provincia', 'provincia_normalizada']].drop_duplicates().iterrows():
                logger.info(f"      • {row['provincia']:25} → {row['provincia_normalizada']}")
        logger.info(f"    - Sin cambios: {len(sin_cambios['provincia'].unique())} provincias")

        # Limpiar columnas temporales
        df = df.drop(columns=['provincia_upper'])

        # 2. Para provincias con múltiples aglomerados, calculamos promedio ponderado por población
        # (esto es importante para Buenos Aires que tiene CABA + GBA)
        columnas_indices = [
            'indice_pobreza_personas', 'indice_pobreza_hogares',
            'indice_indigencia_personas', 'indice_indigencia_hogares',
            'ingreso_promedio_familia', 'canasta_basica_total',
            'brecha_pobreza_pct'
        ]

        # Agrupar por provincia y calcular promedio ponderado por población
        df_agrupado = df.groupby('provincia_normalizada').apply(
            lambda x: pd.Series({
                'indice_pobreza_personas': (x['indice_pobreza_personas'] * x['poblacion_estimada']).sum() / x['poblacion_estimada'].sum(),
                'indice_pobreza_hogares': (x['indice_pobreza_hogares'] * x['poblacion_estimada']).sum() / x['poblacion_estimada'].sum(),
                'indice_indigencia_personas': (x['indice_indigencia_personas'] * x['poblacion_estimada']).sum() / x['poblacion_estimada'].sum(),
                'indice_indigencia_hogares': (x['indice_indigencia_hogares'] * x['poblacion_estimada']).sum() / x['poblacion_estimada'].sum(),
                'ingreso_promedio_familia': (x['ingreso_promedio_familia'] * x['poblacion_estimada']).sum() / x['poblacion_estimada'].sum(),
                'canasta_basica_total': (x['canasta_basica_total'] * x['poblacion_estimada']).sum() / x['poblacion_estimada'].sum(),
                'brecha_pobreza_pct': (x['brecha_pobreza_pct'] * x['poblacion_estimada']).sum() / x['poblacion_estimada'].sum(),
                'poblacion_estimada': x['poblacion_estimada'].sum()
            })
        ).reset_index()

        logger.info(f"  ✓ Datos agregados por provincia: {len(df_agrupado)} provincias únicas")

        self.df_pobreza = df_agrupado
        return df_agrupado

    def extract_area_code(self, phone):
        """
        Extrae el código de área usando el conjunto de códigos reales (self.area_code_set).
        Intenta coincidencias de 4, 3 y 2 dígitos (longest-first).
        Devuelve el código como string (o None si no hay match).
        """
        try:
            phone_str = str(phone).strip()
            if phone_str.startswith('+54'):
                phone_str = phone_str[3:]
            # Si es celular con '9' después del +54, quitar ese 9
            if phone_str.startswith('9'):
                phone_str = phone_str[1:]
            # Quitar ceros leading (por si vienen mal formateados)
            phone_str = phone_str.lstrip('0')

            # Si no tenemos el set preparado, hacer un fallback simple (2-4 dígitos)
            if not hasattr(self, 'area_code_set') or not self.area_code_set:
                logger.fatal("no existe el set que mapea codigos de area con las provincias, es necesario para el programa")
                exit(2)

            # Intentar match con los códigos conocidos (longest-first)
            for length in (4, 3, 2):
                if len(phone_str) >= length:
                    candidate = phone_str[:length]
                    if candidate in self.area_code_set:
                        return candidate

            # Si no hay match explícito, devolvemos None (así queda NaN y lo podés auditar)
            return 'DESCONOCIDO'

        except Exception as e:
            logger.warning(f"Error extrayendo área de {phone}: {e}")
            return None

    def transform_transacciones(self):
        """
        Transforma y limpia datos de transacciones:
        - Normaliza nombres de columnas
        - Extrae código de área
        - Convierte tipos de dato
        - Valida estados
        """
        logger.info("🔄 Iniciando transformación de transacciones...")
        
        df = self.df_transacciones.copy()
        
        # 1. Normalizar nombres de columnas
        df.columns = df.columns.str.lower().str.strip()
        logger.info("  ✓ Columnas normalizadas a minúsculas")
        
        # 2. Filtrar y eliminar teléfonos que no empiezan por '+54'
        mask_valid_phone = df['phone'].notna() & df['phone'].astype(str).str.strip().str.startswith('+54')
        invalid_count = len(df) - mask_valid_phone.sum()
        if invalid_count > 0:
            logger.warning(f"  ⚠ Eliminando {invalid_count} filas cuyo teléfono no empieza con '+54'")
        df = df[mask_valid_phone].copy()

        # 3. Extraer código de área (solo sobre teléfonos válidos)
        df['area_code'] = df['phone'].apply(self.extract_area_code)
        logger.info("  ✓ Códigos de área extraídos (solo teléfonos +54)")


        # 3. Convertir fecha a datetime
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')

        # Eliminar filas con fechas nulas
        filas_antes_fecha = len(df)
        df = df[df['fecha'].notna()].copy()
        filas_eliminadas_fecha = filas_antes_fecha - len(df)
        if filas_eliminadas_fecha > 0:
            logger.warning(f"  ⚠ Eliminadas {filas_eliminadas_fecha} filas con fecha nula")

        logger.info("  ✓ Fechas convertidas a datetime")
        
        # 4. Convertir monto a numérico
        df['monto'] = pd.to_numeric(df['monto'], errors='coerce')

        # Validar y eliminar montos inválidos (nulos, negativos o cero)
        filas_antes_monto = len(df)
        df = df[(df['monto'].notna()) & (df['monto'] > 0)].copy()
        filas_eliminadas_monto = filas_antes_monto - len(df)
        if filas_eliminadas_monto > 0:
            logger.warning(f"  ⚠ Eliminadas {filas_eliminadas_monto} filas con monto inválido (nulo, negativo o cero)")

        logger.info("  ✓ Montos convertidos a numérico y validados")
        
        # 5. Normalizar estado
        df['estado'] = df['estado'].str.upper()
        logger.info("  ✓ Estados normalizados")
        
        # 6. Normalizar tipo
        df['tipo'] = df['tipo'].str.upper()
        logger.info("  ✓ Tipos normalizados")
        
        # 7. Detectar filas problemáticas
        filas_incompletas = df[df['area_code'].isna()].shape[0]
        if filas_incompletas > 0:
            logger.warning(f"  ⚠ {filas_incompletas} filas con área_code inválido")
        
        self.df_transacciones = df
        return df
    
    def transform_regiones(self):
        """
        Transforma datos de regiones:
        - Normaliza areaCode
        - Normaliza nombres de provincia y ciudad
        - Elimina duplicados (manteniendo el primero)
        """
        logger.info("🔄 Iniciando transformación de regiones...")
        
        df = self.df_regiones.copy()
        
        # 1. Convertir areaCode a string y remover leading zeros
        df['areaCode'] = df['areaCode'].astype(str).str.strip()
        logger.info("  ✓ Códigos de área estandarizados")
        
        # 2. Normalizar nombres
        df['province'] = df['province'].str.upper().str.strip()
        df['city'] = df['city'].str.upper().str.strip()
        logger.info("  ✓ Provincias y ciudades normalizadas")
        
        # 3. Eliminar duplicados (mantener primer registro)
        filas_antes = len(df)
        df = df.drop_duplicates(subset=['areaCode'], keep='first')
        filas_despues = len(df)
        logger.info(f"  ✓ Duplicados eliminados: {filas_antes - filas_despues} registros")
        
        # 4. Crear clave de búsqueda
        df['region_key'] = df['areaCode']

        # Normalizar areaCode sin ceros iniciales (por si vinieron como "034" o "011")
        df['areaCode'] = df['areaCode'].str.lstrip('0')

        # Crear set y diccionario para matching rápido
        self.area_code_set = set(df['areaCode'].astype(str).unique())
        # mapping area_code -> provincia (normalizada)
        self.area_code_to_prov = df.set_index('areaCode')['province'].to_dict()

        logger.info(f"  ✓ Diccionario de códigos de área creado ({len(self.area_code_set)} códigos)")

        
        self.df_regiones = df
        return df
    
    def merge_datos(self):
        """
        Combina datos de transacciones con regiones mediante JOIN.
        Matching por código de área telefónico.
        """
        logger.info("🔗 Realizando JOIN entre transacciones y regiones...")

        # Asegurar que las transacciones tengan area_code usando el diccionario creado
        if 'area_code' not in self.df_transacciones.columns or self.df_transacciones['area_code'].isnull().all():
            logger.info("  ✓ Extrayendo area_code de transacciones usando diccionario de regiones")

            self.df_transacciones['area_code'] = self.df_transacciones['phone'].apply(self.extract_area_code)
            missing = self.df_transacciones['area_code'].isna().sum()

            if missing > 0:
                logger.warning(f"  ⚠ {missing} filas sin match de area_code tras intentar con el diccionario")

        
        # Preparar DataFrames
        trans = self.df_transacciones.copy()
        regiones = self.df_regiones[['areaCode', 'province', 'city']].copy()
        regiones.columns = ['area_code', 'provincia', 'ciudad']
        
        # JOIN
        df_merge = trans.merge(
            regiones,
            on='area_code',
            how='left'
        )
        
        # Estadísticas del JOIN
        matches = df_merge['provincia'].notna().sum()
        no_matches = df_merge['provincia'].isna().sum()

        logger.info(f"  ✓ JOIN completado")
        logger.info(f"    - Registros con región: {matches} ({100*matches/len(df_merge):.1f}%)")
        logger.info(f"    - Registros sin región: {no_matches} ({100*no_matches/len(df_merge):.1f}%)")

        # Eliminar filas donde la provincia es nula (no se encontró match)
        filas_antes_provincia = len(df_merge)
        df_merge = df_merge[df_merge['provincia'].notna()].copy()
        filas_eliminadas_provincia = filas_antes_provincia - len(df_merge)
        if filas_eliminadas_provincia > 0:
            logger.warning(f"  ⚠ Eliminadas {filas_eliminadas_provincia} filas sin match de provincia")

        # JOIN con datos de pobreza (si están disponibles)
        if self.df_pobreza is not None:
            logger.info("🔗 Realizando JOIN con datos de pobreza...")

            # Normalizar provincia en transacciones para hacer match
            df_merge['provincia_normalizada'] = df_merge['provincia'].apply(self.normalizar_provincia)

            # JOIN con datos de pobreza
            df_merge = df_merge.merge(
                self.df_pobreza,
                on='provincia_normalizada',
                how='left'
            )

            # Estadísticas del JOIN
            matches_pobreza = df_merge['indice_pobreza_personas'].notna().sum()
            no_matches_pobreza = df_merge['indice_pobreza_personas'].isna().sum()

            logger.info(f"  ✓ JOIN con pobreza completado")
            logger.info(f"    - Registros con datos de pobreza: {matches_pobreza} ({100*matches_pobreza/len(df_merge):.1f}%)")
            if no_matches_pobreza > 0:
                logger.warning(f"    - Registros sin datos de pobreza: {no_matches_pobreza} ({100*no_matches_pobreza/len(df_merge):.1f}%)")
                # Mostrar qué provincias no tienen match
                provincias_sin_match = df_merge[df_merge['indice_pobreza_personas'].isna()]['provincia_normalizada'].unique()
                logger.warning(f"    - Provincias sin datos: {list(provincias_sin_match)}")

        self.df_transacciones = df_merge
        return df_merge
    
    def agregar_campos_derivados(self):
        """
        Crea campos calculados para análisis:
        - Año, mes, día de transacción
        - Clasificación de monto (bajo/medio/alto)
        - Flag de depósito exitoso
        """
        logger.info("➕ Agregando campos derivados...")
        
        df = self.df_transacciones.copy()
        
        # 1. Componentes de fecha
        df['anio'] = df['fecha'].dt.year
        df['mes'] = df['fecha'].dt.month
        df['dia'] = df['fecha'].dt.day
        df['dia_semana'] = df['fecha'].dt.day_name()
        df['hora'] = df['fecha'].dt.hour
        logger.info("  ✓ Componentes de fecha extraídos")    
        
        self.df_transacciones = df
        return df
    
    def validar_calidad(self):
        """
        Realiza validaciones de calidad de datos.
        Registra anomalías detectadas.
        """
        logger.info("✅ Realizando validaciones de calidad...")

        df = self.df_transacciones

        # 1. Validación crítica: Campos obligatorios no pueden ser nulos
        campos_criticos = ['provincia', 'ciudad', 'fecha', 'monto', 'area_code']
        filas_antes_validacion = len(df)

        for campo in campos_criticos:
            if campo in df.columns:
                nulos_campo = df[campo].isna().sum()
                if nulos_campo > 0:
                    logger.error(f"  ❌ CRÍTICO: {nulos_campo} valores nulos en campo '{campo}'")
                    df = df[df[campo].notna()].copy()

        filas_eliminadas_validacion = filas_antes_validacion - len(df)
        if filas_eliminadas_validacion > 0:
            logger.warning(f"  ⚠ Eliminadas {filas_eliminadas_validacion} filas adicionales por validación de campos críticos")
            self.df_transacciones = df

        # 2. Nulos en campos no críticos
        nulos = df.isnull().sum()
        if nulos.sum() > 0:
            logger.warning("  ⚠ Campos con valores nulos detectados:")
            for col, count in nulos[nulos > 0].items():
                logger.warning(f"    - {col}: {count} ({100*count/len(df):.2f}%)")
        else:
            logger.info("  ✓ No hay campos con valores nulos")

        # 3. Validar montos
        montos_neg = (df['monto'] < 0).sum()
        montos_cero = (df['monto'] == 0).sum()
        if montos_neg > 0:
            logger.error(f"  ❌ CRÍTICO: {montos_neg} montos negativos detectados")
        if montos_cero > 0:
            logger.error(f"  ❌ CRÍTICO: {montos_cero} montos en cero detectados")
        if montos_neg == 0 and montos_cero == 0:
            logger.info(f"  ✓ Todos los montos son válidos (> 0)")

        # 4. Estados desconocidos
        estados_unicos = df['estado'].unique()
        logger.info(f"  ℹ Estados únicos: {estados_unicos}")

        # 5. Cobertura geográfica
        cobertura = (df['provincia'].notna().sum() / len(df)) * 100
        logger.info(f"  ℹ Cobertura geográfica: {cobertura:.1f}%")

        # 6. Rango de fechas
        if df['fecha'].notna().any():
            fecha_min = df['fecha'].min()
            fecha_max = df['fecha'].max()
            logger.info(f"  ℹ Rango de fechas: {fecha_min} a {fecha_max}")

        # 7. Estadísticas de montos
        logger.info(f"  ℹ Monto mínimo: ${df['monto'].min():,.2f}")
        logger.info(f"  ℹ Monto máximo: ${df['monto'].max():,.2f}")
        logger.info(f"  ℹ Monto promedio: ${df['monto'].mean():,.2f}")

        logger.info("✓ Validaciones completadas")
    
    # ============================================================================
    # ETAPA 3: CARGA (LOAD)
    # ============================================================================
    
    def load_csv(self, output_path='casino_procesado.csv'):
        """Exporta datos procesados a CSV"""
        try:
            logger.info(f"💾 Exportando datos a {output_path}")

            # Seleccionar columnas relevantes (incluir datos de pobreza si existen)
            cols_export = [
                'username', 'phone', 'area_code', 'provincia', 'ciudad',
                'monto', 'fecha', 'anio', 'mes', 'dia', 'hora',
                'estado', 'tipo', 'dia_semana'
            ]

            # Agregar columnas de pobreza si están disponibles
            if 'indice_pobreza_personas' in self.df_transacciones.columns:
                cols_pobreza = [
                    'indice_pobreza_personas', 'indice_pobreza_hogares',
                    'indice_indigencia_personas', 'indice_indigencia_hogares',
                    'ingreso_promedio_familia', 'canasta_basica_total',
                    'brecha_pobreza_pct', 'poblacion_estimada'
                ]
                cols_export.extend(cols_pobreza)
                logger.info(f"  ✓ Incluyendo {len(cols_pobreza)} columnas de índices socioeconómicos")

            # Filtrar solo columnas que existan
            cols_export = [col for col in cols_export if col in self.df_transacciones.columns]

            df_export = self.df_transacciones[cols_export].copy()
            df_export.to_csv(output_path, index=False, encoding='utf-8')

            logger.info(f"✓ Archivo guardado: {output_path}")
            logger.info(f"  - Filas: {len(df_export)}")
            logger.info(f"  - Columnas: {len(df_export.columns)}")
            return output_path
        except Exception as e:
            logger.error(f"✗ Error al exportar CSV: {e}")
            raise
    
    def load_parquet(self, output_path='casino_procesado.parquet'):
        """Exporta datos procesados a Parquet (formato optimizado)"""
        try:
            logger.info(f"💾 Exportando datos a {output_path}")
            self.df_transacciones.to_parquet(output_path, index=False)
            logger.info(f"✓ Archivo Parquet guardado: {output_path}")
            return output_path
        except ImportError:
            logger.warning("⚠ pyarrow no instalado. Instala con: pip install pyarrow")
        except Exception as e:
            logger.error(f"✗ Error al exportar Parquet: {e}")
            raise
    
    # ============================================================================
    # EJECUCIÓN DEL ETL COMPLETO
    # ============================================================================
    
    def ejecutar(self):
        """Ejecuta todas las etapas del ETL"""
        inicio = datetime.now()
        logger.info("=" * 80)
        logger.info("INICIANDO ETL CASINO")
        logger.info("=" * 80)
        
        try:
            # EXTRACT
            logger.info("\n📥 ETAPA 1: EXTRACCIÓN")
            self.extract_csv()
            self.extract_json_regiones()
            self.extract_json_pobreza()

            # TRANSFORM
            logger.info("\n🔄 ETAPA 2: TRANSFORMACIÓN")
            self.transform_regiones()
            if self.df_pobreza is not None:
                self.transform_pobreza()
            self.transform_transacciones()
            self.merge_datos()
            self.agregar_campos_derivados()
            self.validar_calidad()
            
            # LOAD
            logger.info("\n📤 ETAPA 3: CARGA")
            self.load_csv('./datos_salida/casino_procesado.csv')
            self.load_parquet('./datos_salida/casino_procesado.parquet')
            
            # RESUMEN
            tiempo_total = (datetime.now() - inicio).total_seconds()
            logger.info("\n" + "=" * 80)
            logger.info(f"✅ ETL COMPLETADO EXITOSAMENTE en {tiempo_total:.2f} segundos")
            logger.info("=" * 80)
            
            return self.df_transacciones
            
        except Exception as e:
            logger.error(f"\n❌ ETL FALLÓ: {e}")
            raise

# ================================================================================
# EJECUCIÓN
# ================================================================================

if __name__ == "__main__":
    # Configurar rutas
    csv_file = "./datos_entrada/casino_transacciones.csv"           # Tu archivo CSV
    json_file = "./datos_entrada/regiones_argentina.json"           # Tu archivo JSON regiones
    json_pobreza_file = "./datos_entrada/datos_pobreza.json"        # Tu archivo JSON pobreza

    # Crear instancia y ejecutar ETL
    etl = ETLCasino(csv_file, json_file, json_pobreza_file)
    df_final = etl.ejecutar()
    
    # Mostrar muestra de datos finales
    logger.info("\n📊 MUESTRA DE DATOS PROCESADOS:")
    logger.info(df_final.head(10).to_string())
    
    # Estadísticas finales
    logger.info("\n📈 ESTADÍSTICAS FINALES:")
    logger.info(f"Total depósitos: {len(df_final):,}")
    logger.info(f"Monto total: ${df_final['monto'].sum():,.2f}")
    logger.info(f"Monto promedio: ${df_final['monto'].mean():,.2f}")
    logger.info(f"Provincias: {df_final['provincia'].nunique()}")
    logger.info(f"Ciudades: {df_final['ciudad'].nunique()}")
    logger.info(f"\nDepositos por provincia:\n{df_final.groupby('provincia')['monto'].agg(['count', 'sum', 'mean']).round(2)}")
