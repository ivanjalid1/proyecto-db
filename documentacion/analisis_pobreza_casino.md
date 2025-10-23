# Análisis: Índice de Pobreza vs Depósitos de Casino

**Fuente:** INDEC - EPH Primer Semestre 2025

---

## 1. DATOS EXTRAÍDOS DEL PDF

### Ciudades con MAYOR pobreza (% de personas):
```
1. Concordia (Entre Ríos):      49.2%  ⚠️ MÁS POBRE
2. Gran Resistencia (Chaco):    48.1%
3. Gran San Juan (San Juan):    36.0%
4. Corrientes (Corrientes):     37.4%
5. Gran La Plata (Buenos Aires):35.2%

Total país promedio:             31.6%
```

### Ciudades con MENOR pobreza (% de personas):
```
1. Ushuaia (Tierra del Fuego):  22.3%  ✅ MÁS RICA
2. Bahía Blanca (Buenos Aires): 23.5%
3. Río Cuarto (Córdoba):        24.4%
4. Santa Rosa (La Pampa):       25.6%
5. Viedma (Río Negro):          26.7%
```

---

## 2. DATOS CLAVE POR REGIÓN

| Región | Pobreza % | Indigencia % | Ingreso Promedio | Ciudad Más Pobre |
|--------|-----------|--------------|------------------|-----------------|
| **Noreste (NEA)** | 39.0% | 8.5% | $368,409 | Gran Resistencia (48.1%) |
| **Cuyo** | 33.8% | 4.5% | $397,614 | Gran San Juan (36.0%) |
| **Noroeste (NOA)** | 31.2% | 4.4% | $391,908 | La Rioja (32.4%) |
| **Gran Buenos Aires** | 31.5% | 7.8% | $693,474 | Partidos GBA (35.3%) |
| **Pampeana** | 30.5% | 6.4% | $554,637 | Gran Santa Fe (35.8%) |
| **Patagonia** | 27.0% | 3.8% | $678,203 | Río Gallegos (32.3%) |

---

## 3. INTEGRACIÓN CON ETL CASINO

### Paso 1: Agregar JOIN en `etl_casino.py`

Después del JOIN por **area_code + provincia**, hacer un segundo JOIN por **ciudad**:

```python
# ETAPA 2: TRANSFORM - Agregar después del JOIN de regiones

# 1. Cargar JSON de pobreza
df_pobreza = pd.read_json("regiones_pobreza.json")

# 2. Normalizar nombres de ciudades (muy importante!)
df['ciudad_limpia'] = df['ciudad'].str.upper().str.strip()
df_pobreza['ciudad'] = df_pobreza['ciudad'].str.upper().str.strip()

# 3. JOIN por ciudad
df_merged = df.merge(
    df_pobreza[['ciudad', 'indice_pobreza_personas', 'indice_indigencia_personas', 
                'ingreso_promedio_familia', 'poblacion_estimada']],
    left_on='ciudad_limpia',
    right_on='ciudad',
    how='left'
)

# 4. Crear indicador de correlación
df_merged['ratio_pobreza_depositos'] = df_merged['monto'] / df_merged['indice_pobreza_personas']
```

---

## 4. ANÁLISIS EXPLORATORIO ESPERADO

### Pregunta: ¿Hay correlación entre pobreza y depósitos en casino?

**Hipótesis:**
- ❌ Ciudades pobres = **menos** depósitos (menos dinero disponible)
- ✅ Ciudades pobres = **más** depósitos (mayor riesgo de juego compulsivo)
- ❓ Sin correlación (el juego no discrimina por nivel de pobreza)

---

## 5. MÉTRICAS A CALCULAR

### 5.1 Correlación de Pearson
```python
correlacion = df.corr()[['monto', 'indice_pobreza_personas']]
```

**Interpretación:**
- r > 0.5 = Correlación positiva fuerte (mayor pobreza → más depósitos)
- 0.3 < r < 0.5 = Correlación positiva moderada
- r ≈ 0 = Sin correlación
- r < -0.3 = Correlación negativa (mayor pobreza → menos depósitos)

### 5.2 Usuarios por Nivel de Pobreza
```python
segmentos_pobreza = pd.cut(df['indice_pobreza_personas'], 
                           bins=[0, 25, 30, 35, 50],
                           labels=['Baja', 'Media', 'Media-Alta', 'Alta'])

df.groupby(segmentos_pobreza).agg({
    'monto': ['sum', 'mean', 'count'],
    'username': 'nunique'
})
```

### 5.3 Relación Ingresos vs Depósitos
```python
df['ratio_ingreso_deposito'] = (df['monto'] / df['ingreso_promedio_familia'] * 100)

# ¿Qué porcentaje del ingreso promedio se deposita en casino?
# Si ratio > 1%, es significativo
```

---

## 6. DATOS BRUTOS DEL PDF (Ciudades principales)

### Buenos Aires (CABA):
- Pobreza: 15.1% (personas)
- Ingreso promedio: $872,945
- Población: 3,006,087

### Partidos GBA:
- Pobreza: 35.3% (personas)
- Ingreso promedio: $514,942
- Población: 13,109,295

### Córdoba:
- Pobreza: 29.5% (personas)
- Ingreso promedio: $550,436
- Población: 1,608,807

### Rosario:
- Pobreza: 28.1% (personas)
- Ingreso promedio: $571,511
- Población: 1,359,830

### Mendoza:
- Pobreza: 33.5% (personas)
- Ingreso promedio: $465,612
- Población: 1,063,050

### Neuquén:
- Pobreza: 26.0% (personas) ✅ Baja pobreza
- Ingreso promedio: $742,854 ✅ Alto ingreso
- Población: 326,002

### Resistencia (Chaco):
- Pobreza: 48.1% (personas) ⚠️ CRÍTICA
- Ingreso promedio: $318,841
- Población: 426,988

### Concordia (Entre Ríos):
- Pobreza: 49.2% (personas) ⚠️ LA MÁS POBRE
- Ingreso promedio: $369,064
- Población: 166,552

---

## 7. INTERPRETACIONES POTENCIALES

### Si hay correlación positiva (más pobreza = más depósitos):
```
⚠️ HALLAZGO CRÍTICO: Poblaciones vulnerables juegan más
→ Riesgo: Juego compulsivo en personas de bajo ingreso
→ Acción: Considerar medidas de responsabilidad social
```

### Si hay correlación negativa (más pobreza = menos depósitos):
```
✓ HALLAZGO ESPERADO: Gente con menos recursos juega menos
→ Interpretación: Dinero disponible limita participación
→ Acción: Enfoque en segmentos de mayor ingreso
```

### Si sin correlación:
```
? HALLAZGO NEUTRAL: Pobreza no predice comportamiento de juego
→ Interpretación: Otros factores más relevantes
→ Acción: Investigar qué SÍ predice depósitos
```

---

## 8. GRÁFICOS A GENERAR

1. **Scatter plot:** Pobreza vs Monto de depósitos
2. **Box plot:** Distribución de depósitos por nivel de pobreza
3. **Mapa:** Pobreza vs Usuarios activos por región
4. **Heatmap:** Matriz pobreza × rango_monto × región
5. **Línea:** Evolución ingreso vs depósitos

---

## 9. RECOMENDACIONES PARA PRESENTACIÓN

### Título de sección en presentación:
> **"¿Quién Juega? Análisis de Depósitos Casino vs Vulnerabilidad Social"**

### Diapositiva clave:
```
HALLAZGOS:
• Ciudades con mayor pobreza: Concordia (49.2%), Resistencia (48.1%)
• Ciudades con menor pobreza: Ushuaia (22.3%), Bahía Blanca (23.5%)
• Correlación encontrada: [Resultado del análisis]
• Implicaciones: [Según correlación]
```

### Ética de investigación:
⚠️ Mencionar que este análisis es **descriptivo**, no causal.
No implica que la pobreza "cause" depósitos en casino.

---

## 10. NOTAS IMPORTANTES DEL PDF

- **Metodología:** Encuesta Permanente de Hogares (EPH) - INDEC
- **Cobertura:** 31 aglomerados urbanos principales
- **Período:** Primer semestre 2025 (actualizado al 25/09/2025)
- **Confiabilidad:** Algunos datos con CV > 16% (marcados como "u" en PDF)
- **Canasta Básica Total (CBT):** Varía por región ($285-$425k por adulto equivalente)
- **Brecha de Pobreza:** 37% promedio (población pobre está 37% por debajo de LP)

---

## Resumen Ejecutivo

El análisis integrará 31 ciudades argentinas con sus índices de pobreza, permitiendo responder:

✅ ¿Qué ciudades generan más depósitos en casino?  
✅ ¿Tienen relación con niveles de pobreza?  
✅ ¿Hay segmentos poblacionales de mayor riesgo?  
✅ ¿Qué provincias son más vulnerables al juego?  

**Impacto:** Insights para política de responsabilidad social del casino.