# 📊 ETL Casino - Análisis Regional de Depósitos
## Documentación Técnica - Metodología Hefesto

---

## 1. Introducción

Este proyecto implementa un **proceso ETL (Extract-Transform-Load)** para procesar y enriquecer datos de transacciones de un casino online, permitiendo análisis regional basado en códigos telefónicos argentinos.

**Objetivo:** Identificar patrones de depósito por región geográfica para análisis empresarial.

**Volumen de datos:** ~122,100 registros de transacciones

---

## 2. Arquitectura del Proceso

```
┌─────────────────────────────────────────────────────────────────┐
│                     ETL HEFESTO                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  EXTRACT              TRANSFORM              LOAD               │
│  ────────             ────────              ────                │
│  • CSV (122K)    ┌──→ Limpieza         ┌──→ CSV limpio        │
│  • JSON (Regiones)   │  Validación     │    (optimizado)      │
│                  │  Enriquecimiento    │                       │
│                  └──→ JOIN por área    └──→ Parquet           │
│                                            (comprimido)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Datos de Entrada

### 3.1 CSV - Transacciones del Casino

**Archivo:** `casino_transacciones.csv`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `username` | string | Identificador del usuario |
| `phone` | string | Número telefónico argentino (+549...) |
| `monto` | float | Cantidad depositada en ARS |
| `fecha` | datetime | Timestamp de transacción |
| `estado` | string | SUCCESS / FAILED / PENDING |
| `tipo` | string | DEPOSIT / WITHDRAWAL / etc |

**Ejemplo:**
```
username,phone,monto,fecha,estado,tipo
marco068690,+5493518612669,500,2025-10-14 19:30:58.954,SUCCESS,DEPOSIT
rica07134,+5491167935855,2500,2025-10-14 19:30:52.235,SUCCESS,DEPOSIT
```

### 3.2 JSON - Mapeo Geográfico

**Archivo:** `regiones_argentina.json`

**Estructura:**
```json
{
  "areaCode": "2345",           // Código de área telefónico
  "city": "25 DE MAYO",         // Ciudad
  "province": "Buenos Aires",   // Provincia
  "carrier": "TELECOM PERSONAL S.A.",  // Operador
  "numberType": "M"             // Tipo (M=móvil)
}
```

**Propósito:** Mapear códigos de área telefónico a región geográfica.

---

## 4. Transformaciones Realizadas

### 4.1 Extracción de Código de Área

**Problema:** El número completo no es suficiente para regional.

**Solución:** Extraer el código de área del formato argentino:

```
Entrada: +5493518612669
  ↓
Eliminar +54: 93518612669
  ↓
Eliminar 9 de celular: 3518612669
  ↓
Extraer primeros 3-4 dígitos: 351
  ↓
Salida: area_code = "351"
```

**Casos especiales:**
- `+5491167935855` → area_code = `11` (CABA)
- `+5493518612669` → area_code = `351` (Córdoba)
- `+5492345123456` → area_code = `2345` (interior)

### 4.2 Unificación de Fechas

**Problema:** Datos con múltiples formatos de fecha.

**Solución:** Convertir todas a ISO format `YYYY-MM-DD HH:MM:SS.mmm`

```python
fecha_original: "2025-10-14 19:30:58.954"
fecha_procesada: 2025-10-14 19:30:58.954  # datetime64
```

Luego extraer componentes:
- `anio`: 2025
- `mes`: 10
- `dia`: 14
- `hora`: 19
- `dia_semana`: "Tuesday"

### 4.3 JOIN con Datos Geográficos

**Método:** LEFT JOIN por código de área

```
Transacciones (L) ←LEFT JOIN→ Regiones (R)
     ON transacciones.area_code = regiones.areaCode
```

**Resultado:**
- ✅ Registros con provincia y ciudad identificada
- ⚠️ Registros sin match (códigos no encontrados en JSON)

**Estadísticas esperadas:**
- Cobertura geográfica: ~85-95%
- Registros sin región: 5-15%

### 4.4 Campos Derivados

#### Clasificación de Monto

Basado en percentiles (terciles):

| Rango | Descripción |
|-------|-------------|
| BAJO | Monto ≤ P33 |
| MEDIO | P33 < Monto ≤ P66 |
| ALTO | Monto > P66 |

#### Flag de Éxito

```python
es_exitoso = 1 if estado == "SUCCESS" else 0
```

---

## 5. Validaciones de Calidad

### 5.1 Verificaciones Realizadas

| Validación | Acción |
|-----------|--------|
| Valores nulos | Registrar % de ausencia |
| Montos negativos | Detectar anomalías |
| Códigos área inválidos | Identificar desajustes |
| Estados desconocidos | Listar valores únicos |
| Duplicados | Eliminar en regiones |
| Cobertura geográfica | Calcular % de match |

### 5.2 Logging Detallado

Cada transformación genera logs en `etl_casino.log`:

```
2025-10-14 19:45:23,123 - INFO - ✓ CSV extraído: 122100 filas
2025-10-14 19:45:24,456 - INFO - ✓ JSON extraído: 18450 registros
2025-10-14 19:45:25,789 - INFO - 🔄 Iniciando transformación...
2025-10-14 19:45:30,234 - WARNING - ⚠ 145 filas con área_code inválido
2025-10-14 19:45:35,567 - INFO - 🔗 JOIN completado
2025-10-14 19:45:35,890 - INFO - Registros con región: 120789 (98.9%)
```

---

## 6. Datos de Salida

### 6.1 CSV Limpio

**Archivo:** `casino_procesado.csv`

**Columnas exportadas:**

```
username, phone, area_code, provincia, ciudad, operador,
monto, fecha, anio, mes, dia, hora, rango_monto,
estado, tipo, es_exitoso, dia_semana
```

**Tamaño estimado:** ~45 MB (sin compresión)

### 6.2 Parquet Optimizado

**Archivo:** `casino_procesado.parquet`

**Ventajas:**
- Compresión nativa (~5x más pequeño)
- Lectura 10x más rápida
- Ideal para herramientas BI

---

## 7. Analíticas Posibles

Con los datos procesados, se pueden responder preguntas como:

### 7.1 Por Provincia
```sql
SELECT provincia, 
       COUNT(*) as transacciones,
       SUM(monto) as total_depositado,
       AVG(monto) as monto_promedio
FROM casino_procesado
WHERE estado = 'SUCCESS' AND tipo = 'DEPOSIT'
GROUP BY provincia
ORDER BY total_depositado DESC
```

### 7.2 Top Usuarios por Región
```sql
SELECT provincia, username, 
       COUNT(*) as num_depositos,
       SUM(monto) as total
FROM casino_procesado
WHERE tipo = 'DEPOSIT'
GROUP BY provincia, username
ORDER BY provincia, total DESC
LIMIT 100
```

### 7.3 Patrones Temporales
```sql
SELECT anio, mes, rango_monto,
       COUNT(*) as cantidad,
       AVG(monto) as promedio
FROM casino_procesado
GROUP BY anio, mes, rango_monto
```

### 7.4 Análisis de Operadores
```sql
SELECT operador, provincia,
       COUNT(*) as clientes,
       SUM(monto) as total
FROM casino_procesado
GROUP BY operador, provincia
```

---

## 8. Instrucciones de Uso

### 8.1 Requisitos

```bash
pip install pandas pyarrow
```

### 8.2 Ejecución Básica

```python
from etl_casino import ETLCasino

etl = ETLCasino(
    csv_path="casino_transacciones.csv",
    json_path="regiones_argentina.json"
)

df_procesado = etl.ejecutar()
```

### 8.3 Consultar Resultados

```python
# Leer datos procesados
df = pd.read_csv("casino_procesado.csv")

# Depósitos por provincia
print(df.groupby('provincia')['monto'].sum().sort_values(ascending=False))

# Top 10 usuarios
print(df.groupby('username')['monto'].sum().nlargest(10))
```

---

## 9. Consideraciones de Desempeño

### 9.1 Optimizaciones Implementadas

- ✅ Uso de `merge()` optimizado (O(n))
- ✅ Eliminación de duplicados en regiones antes del JOIN
- ✅ Conversión a tipos eficientes (int32, float32 donde aplica)
- ✅ Exportación a Parquet para almacenamiento

### 9.2 Tiempo Estimado de Ejecución

Con ~122,100 registros:

| Etapa | Tiempo |
|-------|--------|
| Extract | ~2-3 seg |
| Transform | ~5-8 seg |
| Load | ~2-3 seg |
| **Total** | **~10-15 seg** |

---

## 10. Posibles Problemas y Soluciones

| Problema | Solución |
|----------|----------|
| Códigos de área no encontrados | Verificar formato en JSON vs CSV |
| Fechas con formato inconsistente | Usar `pd.to_datetime(errors='coerce')` |
| Memoria insuficiente | Procesar en chunks con `chunksize` |
| Duplicados en JSON | Implementado `drop_duplicates()` |
| Caracteres especiales en textos | Usar `encoding='utf-8'` |

---

## 11. Conclusiones

Este ETL implementa un pipeline robusto para:

✅ Procesar ~122K transacciones en ~15 segundos
✅ Enriquecer datos con información geográfica
✅ Generar salidas limpias y validadas
✅ Facilitar análisis regional de depósitos

La metodología Hefesto garantiza trazabilidad, validación y reproducibilidad del proceso.

---

**Autor:** [Tu nombre]  
**Fecha:** 2025-10-14  
**Versión:** 1.0