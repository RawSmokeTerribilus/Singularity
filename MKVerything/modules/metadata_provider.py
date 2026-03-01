import requests
import os
import logging

class MetadataProvider:
    def __init__(self):
        # Usamos la clave que ya tenemos en el entorno o la de emergencia
        self.api_key = os.getenv("TMDB_API_KEY", "")
        self.base_url = "https://api.themoviedb.org/3"

    def get_best_match(self, name, year=None):
        """
        Busca en TMDB usando el nombre y opcionalmente el año para 
        evitar errores como el de 'Vibes' en lugar de 'El secreto de la pirámide'.
        """
        search_url = f"{self.base_url}/search/multi"
        params = {
            "api_key": self.api_key,
            "query": name,
            "language": "es-ES"
        }
        
        # Si el sabueso encontró un año, lo inyectamos en la búsqueda
        if year:
            params["year"] = year
            params["first_air_date_year"] = year # Para series

        try:
            response = requests.get(search_url, params=params, timeout=10)
            data = response.json()
            results = data.get("results", [])

            if not results:
                logging.warning(f"No se encontraron resultados para: {name}")
                return None

            # Cogemos el primer resultado (el más relevante)
            first = results[0]
            
            # Normalizamos los datos (TMDB usa nombres distintos para cine y TV)
            return {
                "id": first.get("id"),
                "clean_name": first.get("title") or first.get("name"),
                "year": (first.get("release_date") or first.get("first_air_date") or "0000")[:4],
                "type": "tv" if first.get("media_type") == "tv" else "movie"
            }
        except Exception as e:
            logging.error(f"Error en la consulta a TMDB: {e}")
            return None
