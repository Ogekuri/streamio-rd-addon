# Stremio-RD-Addon

Stremio plugins per la ricerca diretta dei torrent sui provider di rierca online.

# Download

- Clonare il repository
    ```sh
    git clone https://github.com/Ogekuri/streamio-rd-addon
    ```
# Esecuzione

## via Python

- Eseguire l'applicativo (la porta e l'ip sono facoltativi)
    ```sh
    cd streamio-rd-addon
    ./run-python.sh <PORT> <IP>
    ````
  Ora è accessibile attraverso `<IP>:<PORT> o 127.0.0.1:44444`

- Terminare l'applicazione
    ```sh
    Ctrl+C
    ````

## via Docker

- Eseguire l'immagine docker
    ```sh
    cd streamio-rd-addon
    ./run-docker.sh
    ```
  Istanza PRODUCTION: L'istanza di produzione è ora accessibile attraverso `<IP>:<PORT> o 127.0.0.1:44444`.
  
  Istanza TEST: L'istanza di test è ora accessibile attraverso `<IP>:<PORT> o 127.0.0.1:33333`.

- Terminare l'applicazione
    ```sh
    Ctrl+C
    ````
# Opzionale
## Utilizzo dei certificati

Questa funzionalità è ancora da implementare.
