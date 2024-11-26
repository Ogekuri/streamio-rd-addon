# Stremio-RD-Addon

Stremio plugins per la ricerca diretta dei torrent sui provider di rierca online.

# Esecuzione

## via Python

- Clonare il repository
    ```sh
    git clone https://github.com/Ogekuri/streamio-rd-addon
    ```
- Eseguire l'applicativo (la porta e l'ip sono facoltativi)
    ```sh
    cd streamio-rd-addon
    ./run-python.sh <PORT> <IP>
    ````
- Terminare l'applicazione
    ```sh
    Ctrl+C
    ````
  Ora è accessibile attraverso `<IP>:<PORT> o 127.0.0.1:44444`

## via Docker

- Eseguire l'immagine docker
    ```sh
    cd streamio-rd-addon
    ./run-docker.sh
    ```
# Opzionale
## Utilizzo dei certificati

Questa funzionalità è ancora da implementare.
