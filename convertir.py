#!/bin/python

import csv

csv_file = "./datos_salida/casino_procesado.csv"
sql_file = "./datos_salida/casino_procesado.sql"

with open(csv_file, mode="r", encoding="utf-8") as file:
    csv_reader = csv.reader(file)
    headers = next(csv_reader)  # Lee la primera fila como encabezados
    values_list = []

    for row in csv_reader:
        values = ", ".join(f"'{v}'" for v in row)  # Escapa los valores
        values_list.append(f"({values})")  # Añade cada fila como una tupla

    # Crea la sentencia SQL
    insert_statement = (
        f"INSERT INTO MY_TABLE ({', '.join(headers)}) VALUES {',\n'.join(values_list)};"
    )

    with open(sql_file, mode="w", encoding="utf-8") as sql:
        sql.write(insert_statement + "\n")

print(f"Conversión completada. Consulta el archivo {sql_file}.")
