#!/bin/python

"""
================================================================================
ANALÍTICAS CASINO - ANÁLISIS REGIONAL
================================================================================
Script para análisis y visualización de datos procesados por ETL
Genera reportes ejecutivos y gráficos para presentación
================================================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsCasino:
    """Clase para análisis de datos del casino por región"""
    
    def __init__(self, csv_path='casino_procesado.csv'):
        """Carga datos procesados"""
        logger.info(f"Cargando datos desde {csv_path}")
        self.df = pd.read_csv(csv_path)
        self.df['fecha'] = pd.to_datetime(self.df['fecha'])
        logger.info(f"✓ {len(self.df):,} registros cargados")
    
    # ========================================================================
    # ANÁLISIS POR PROVINCIA
    # ========================================================================
    
    def analisis_por_provincia(self):
        """Top provincias por depósitos y monto"""
        logger.info("\n📊 ANÁLISIS POR PROVINCIA")
        
        resultado = self.df[self.df['tipo'] == 'DEPOSIT'].groupby('provincia').agg({
            'monto': ['count', 'sum', 'mean', 'min', 'max', 'std'],
            'es_exitoso': 'sum'
        }).round(2)
        
        resultado.columns = ['Transacciones', 'Total_ARS', 'Promedio', 'Mín', 'Máx', 'Desv_Est', 'Exitosas']
        resultado['% Exitoso'] = (resultado['Exitosas'] / resultado['Transacciones'] * 100).round(1)
        resultado = resultado.sort_values('Total_ARS', ascending=False)
        
        print("\n" + "="*100)
        print("TOP PROVINCIAS - DEPÓSITOS")
        print("="*100)
        print(resultado)
        
        return resultado
    
    def top_usuarios_por_provincia(self, top_n=5):
        """Top N usuarios depositantes por provincia"""
        logger.info(f"\n👥 TOP {top_n} USUARIOS POR PROVINCIA")
        
        print("\n" + "="*100)
        print(f"TOP {top_n} USUARIOS DEPOSITANTES POR PROVINCIA")
        print("="*100)
        
        for provincia in self.df['provincia'].dropna().unique()[:10]:
            usuarios = self.df[
                (self.df['provincia'] == provincia) & 
                (self.df['tipo'] == 'DEPOSIT')
            ].groupby('username').agg({
                'monto': ['count', 'sum'],
                'username': 'count'
            }).round(2)
            
            usuarios.columns = ['Transacciones', 'Total_ARS']
            usuarios = usuarios.sort_values('Total_ARS', ascending=False).head(top_n)
            
            print(f"\n🔹 {provincia}")
            print(usuarios)
    
    def usuarios_por_ciudad(self):
        """Distribución de usuarios por ciudad"""
        logger.info("\n🏙️ DISTRIBUCIÓN POR CIUDAD")
        
        resultado = self.df[self.df['tipo'] == 'DEPOSIT'].groupby('ciudad').agg({
            'username': 'nunique',
            'monto': ['count', 'sum', 'mean']
        }).round(2)
        
        resultado.columns = ['Usuarios_Unicos', 'Transacciones', 'Total_ARS', 'Promedio']
        resultado = resultado.sort_values('Total_ARS', ascending=False).head(20)
        
        print("\n" + "="*100)
        print("TOP 20 CIUDADES - DEPÓSITOS")
        print("="*100)
        print(resultado)
        
        return resultado
    
    # ========================================================================
    # ANÁLISIS POR OPERADOR
    # ========================================================================
    
    def analisis_por_operador(self):
        """Análisis de depósitos por operador telefónico"""
        logger.info("\n📱 ANÁLISIS POR OPERADOR")
        
        resultado = self.df[self.df['tipo'] == 'DEPOSIT'].groupby('operador').agg({
            'monto': ['count', 'sum', 'mean'],
            'username': 'nunique',
            'es_exitoso': 'sum'
        }).round(2)
        
        resultado.columns = ['Transacciones', 'Total_ARS', 'Promedio', 'Usuarios_Unicos', 'Exitosas']
        resultado['% Exitoso'] = (resultado['Exitosas'] / resultado['Transacciones'] * 100).round(1)
        resultado = resultado.sort_values('Total_ARS', ascending=False)
        
        print("\n" + "="*100)
        print("ANÁLISIS POR OPERADOR TELEFÓNICO")
        print("="*100)
        print(resultado)
        
        return resultado
    
    # ========================================================================
    # ANÁLISIS TEMPORAL
    # ========================================================================
    
    def analisis_por_mes(self):
        """Evolución mensual de depósitos"""
        logger.info("\n📅 ANÁLISIS TEMPORAL MENSUAL")
        
        df_dep = self.df[self.df['tipo'] == 'DEPOSIT'].copy()
        df_dep['anio_mes'] = df_dep['fecha'].dt.to_period('M')
        
        resultado = df_dep.groupby('anio_mes').agg({
            'monto': ['count', 'sum', 'mean'],
            'es_exitoso': 'sum'
        }).round(2)
        
        resultado.columns = ['Transacciones', 'Total_ARS', 'Promedio', 'Exitosas']
        resultado['% Exitoso'] = (resultado['Exitosas'] / resultado['Transacciones'] * 100).round(1)
        
        print("\n" + "="*100)
        print("EVOLUCIÓN MENSUAL DE DEPÓSITOS")
        print("="*100)
        print(resultado)
        
        return resultado
    
    def analisis_por_hora(self):
        """Distribución de depósitos por hora del día"""
        logger.info("\n⏰ ANÁLISIS POR HORA DEL DÍA")
        
        resultado = self.df[self.df['tipo'] == 'DEPOSIT'].groupby('hora').agg({
            'monto': ['count', 'sum', 'mean']
        }).round(2)
        
        resultado.columns = ['Transacciones', 'Total_ARS', 'Promedio']
        resultado['Hora'] = [f"{h:02d}:00" for h in resultado.index]
        resultado = resultado.sort_values('Transacciones', ascending=False)
        
        print("\n" + "="*100)
        print("DEPÓSITOS POR HORA DEL DÍA")
        print("="*100)
        print(resultado)
        
        return resultado
    
    def analisis_por_dia_semana(self):
        """Depósitos por día de la semana"""
        logger.info("\n📆 ANÁLISIS POR DÍA DE LA SEMANA")
        
        resultado = self.df[self.df['tipo'] == 'DEPOSIT'].groupby('dia_semana').agg({
            'monto': ['count', 'sum', 'mean']
        }).round(2)
        
        resultado.columns = ['Transacciones', 'Total_ARS', 'Promedio']
        
        orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        traducciones = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        resultado.index = [traducciones.get(dia, dia) for dia in resultado.index]
        resultado = resultado.reindex([traducciones[dia] for dia in orden_dias if traducciones[dia] in resultado.index])
        
        print("\n" + "="*100)
        print("DEPÓSITOS POR DÍA DE LA SEMANA")
        print("="*100)
        print(resultado)
        
        return resultado
    
    # ========================================================================
    # ANÁLISIS DE MONTOS
    # ========================================================================
    
    def analisis_rangos_monto(self):
        """Distribución por rango de monto"""
        logger.info("\n💰 ANÁLISIS DE RANGOS DE MONTO")
        
        resultado = self.df[self.df['tipo'] == 'DEPOSIT'].groupby('rango_monto').agg({
            'monto': ['count', 'sum', 'mean', 'min', 'max']
        }).round(2)
        
        resultado.columns = ['Transacciones', 'Total_ARS', 'Promedio', 'Mínimo', 'Máximo']
        resultado['% del Total'] = (resultado['Total_ARS'] / resultado['Total_ARS'].sum() * 100).round(1)
        
        print("\n" + "="*100)
        print("DISTRIBUCIÓN POR RANGO DE MONTO")
        print("="*100)
        print(resultado)
        
        return resultado
    
    def estadisticas_montos(self):
        """Estadísticas descriptivas de montos"""
        logger.info("\n📊 ESTADÍSTICAS DESCRIPTIVAS DE MONTOS")
        
        montos = self.df[self.df['tipo'] == 'DEPOSIT']['monto']
        
        stats = {
            'Cantidad Transacciones': len(montos),
            'Monto Total (ARS)': f"${montos.sum():,.2f}",
            'Promedio': f"${montos.mean():,.2f}",
            'Mediana': f"${montos.median():,.2f}",
            'Desviación Estándar': f"${montos.std():,.2f}",
            'Mínimo': f"${montos.min():,.2f}",
            'Máximo': f"${montos.max():,.2f}",
            'P25': f"${montos.quantile(0.25):,.2f}",
            'P50': f"${montos.quantile(0.50):,.2f}",
            'P75': f"${montos.quantile(0.75):,.2f}",
            'P95': f"${montos.quantile(0.95):,.2f}",
        }
        
        print("\n" + "="*100)
        print("ESTADÍSTICAS DESCRIPTIVAS - MONTOS DE DEPÓSITO")
        print("="*100)
        for key, value in stats.items():
            print(f"{key:.<40} {value:>50}")
        
        return stats
    
    # ========================================================================
    # ANÁLISIS DE CALIDAD
    # ========================================================================
    
    def analisis_calidad(self):
        """Análisis de calidad de datos y tasas de éxito"""
        logger.info("\n✅ ANÁLISIS DE CALIDAD Y TASAS DE ÉXITO")
        
        total_registros = len(self.df)
        depositos = len(self.df[self.df['tipo'] == 'DEPOSIT'])
        exitosos = self.df['es_exitoso'].sum()
        con_region = self.df['provincia'].notna().sum()
        sin_region = self.df['provincia'].isna().sum()
        
        print("\n" + "="*100)
        print("ANÁLISIS DE CALIDAD Y COBERTURA")
        print("="*100)
        print(f"Total de registros........................ {total_registros:,}")
        print(f"Depósitos................................. {depositos:,} ({100*depositos/total_registros:.1f}%)")
        print(f"Transacciones exitosas................... {exitosos:,} ({100*exitosos/total_registros:.1f}%)")
        print(f"")
        print(f"Registros con región identificada........ {con_region:,} ({100*con_region/total_registros:.1f}%)")
        print(f"Registros sin región (sin match)......... {sin_region:,} ({100*sin_region/total_registros:.1f}%)")
        print(f"")
        print(f"Provincias únicas........................ {self.df['provincia'].nunique()}")
        print(f"Ciudades únicas.......................... {self.df['ciudad'].nunique()}")
        print(f"Usuarios únicos.......................... {self.df['username'].nunique()}")
        print(f"Operadores identificados................ {self.df['operador'].nunique()}")
    
    def usuarios_por_volume(self):
        """Segmentación de usuarios por volumen de depósito"""
        logger.info("\n📈 SEGMENTACIÓN DE USUARIOS POR VOLUMEN")
        
        usuarios_depositos = self.df[self.df['tipo'] == 'DEPOSIT'].groupby('username').agg({
            'monto': 'sum'
        }).reset_index()
        usuarios_depositos.columns = ['username', 'total_depositado']
        
        # Cuartiles
        q1 = usuarios_depositos['total_depositado'].quantile(0.25)
        q2 = usuarios_depositos['total_depositado'].quantile(0.50)
        q3 = usuarios_depositos['total_depositado'].quantile(0.75)
        
        def clasificar_usuario(monto):
            if monto <= q1:
                return 'BAJO'
            elif monto <= q2:
                return 'MEDIO-BAJO'
            elif monto <= q3:
                return 'MEDIO-ALTO'
            else:
                return 'ALTO'
        
        usuarios_depositos['segmento'] = usuarios_depositos['total_depositado'].apply(clasificar_usuario)
        
        resultado = usuarios_depositos.groupby('segmento').agg({
            'username': 'count',
            'total_depositado': ['sum', 'mean']
        }).round(2)
        
        resultado.columns = ['Cantidad_Usuarios', 'Total_ARS', 'Promedio_Usuario']
        resultado['% Usuarios'] = (resultado['Cantidad_Usuarios'] / resultado['Cantidad_Usuarios'].sum() * 100).round(1)
        resultado['% Monto'] = (resultado['Total_ARS'] / resultado['Total_ARS'].sum() * 100).round(1)
        
        print("\n" + "="*100)
        print("SEGMENTACIÓN DE USUARIOS POR VOLUMEN DE DEPÓSITO")
        print("="*100)
        print(resultado)
        
        return resultado
    
    # ========================================================================
    # REPORTE EJECUTIVO
    # ========================================================================
    
    def generar_reporte_ejecutivo(self):
        """Genera reporte ejecutivo completo"""
        logger.info("\n" + "="*100)
        logger.info("GENERANDO REPORTE EJECUTIVO")
        logger.info("="*100)
        
        print("\n\n")
        print("╔" + "="*98 + "╗")
        print("║" + " "*30 + "REPORTE EJECUTIVO - CASINO POR REGIÓN" + " "*30 + "║")
        print("║" + " "*98 + "║")
        print("║" + f" Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(99) + "║")
        print("╚" + "="*98 + "╝")
        
        # 1. Estadísticas generales
        self.estadisticas_montos()
        
        # 2. Análisis de calidad
        self.analisis_calidad()
        
        # 3. Provincias
        self.analisis_por_provincia()
        
        # 4. Operadores
        self.analisis_por_operador()
        
        # 5. Temporal
        self.analisis_por_dia_semana()
        
        # 6. Montos
        self.analisis_rangos_monto()
        
        # 7. Segmentación
        self.usuarios_por_volume()
        
        print("\n" + "="*100)
        print("FIN DEL REPORTE")
        print("="*100 + "\n")

# ================================================================================
# EXPORTAR REPORTES A EXCEL
# ================================================================================

def exportar_reportes_excel(csv_path='./datos_salida/casino_procesado.csv', output_path='./datos_salida/casino_reportes.xlsx'):
    """Exporta múltiples análisis a un archivo Excel con múltiples sheets"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        logger.warning("openpyxl no instalado. Instala con: pip install openpyxl")
        return
    
    analytics = AnalyticsCasino(csv_path)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        logger.info(f"Exportando reportes a {output_path}")
        
        analytics.analisis_por_provincia().to_excel(writer, sheet_name='Por Provincia')
        analytics.analisis_por_operador().to_excel(writer, sheet_name='Por Operador')
        analytics.analisis_por_mes().to_excel(writer, sheet_name='Temporal Mensual')
        analytics.analisis_por_hora().to_excel(writer, sheet_name='Por Hora')
        analytics.analisis_rangos_monto().to_excel(writer, sheet_name='Rangos Monto')
        analytics.usuarios_por_volume().to_excel(writer, sheet_name='Segmentación Usuarios')
        analytics.analisis_por_ciudad().to_excel(writer, sheet_name='Top Ciudades')
        
    logger.info(f"✓ Reportes exportados a {output_path}")

# ================================================================================
# EJECUCIÓN
# ================================================================================

if __name__ == "__main__":
    # Crear instancia de analytics
    analytics = AnalyticsCasino('./datos_salida/casino_procesado.csv')
    
    # Generar reporte ejecutivo completo
    analytics.generar_reporte_ejecutivo()
    
    # Exportar a Excel (opcional)
    try:
        exportar_reportes_excel()
    except Exception as e:
        logger.warning(f"No se pudo exportar a Excel: {e}")
    
    logger.info("\n✅ ANÁLISIS COMPLETADO")