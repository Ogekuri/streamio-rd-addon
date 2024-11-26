#!/bin/bash

# Nome del database SQLite
DB_PATH="caches_items.db"

# Verifica che il file del database esista
if [ ! -f "$DB_PATH" ]; then
  echo "Errore: Il file del database '$DB_PATH' non esiste."
  exit 1
fi

# Elenca le tabelle nel database
echo "Tabelle trovate nel database '$DB_PATH':"
TABLES=$(sqlite3 "$DB_PATH" ".tables")

if [ -z "$TABLES" ]; then
  echo "Nessuna tabella trovata."
  exit 0
fi

# Stampa i nomi delle tabelle
for TABLE in $TABLES; do
  echo "- $TABLE"
done

# Stampa il contenuto di ciascuna tabella
echo ""
echo "Contenuto delle tabelle:"
for TABLE in $TABLES; do
  echo ""
  echo "Tabella: $TABLE"
  echo "-------------------"

  # Ottieni le colonne della tabella
  COLUMNS=$(sqlite3 "$DB_PATH" "PRAGMA table_info($TABLE);" | awk -F'|' '{print $2}' | paste -sd "," -)

  echo "Colonne: $COLUMNS"

  # Stampa il contenuto della tabella
  DATA=$(sqlite3 "$DB_PATH" "SELECT * FROM $TABLE;")
  if [ -z "$DATA" ]; then
    echo "Nessun dato trovato."
  else
    sqlite3 "$DB_PATH" "SELECT * FROM $TABLE;" | cut -d "|" -f 1-4,7- # salto i traker
  fi
done
