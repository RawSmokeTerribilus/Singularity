# Contribuir a Uploadrr (Edición EMUWAREZ)

¡Gracias por querer contribuir! A continuación tienes unas pautas rápidas para colaborar de forma clara y eficiente.

## Antes de empezar
- Revisa el `CODE_OF_CONDUCT.md` y la `LICENSE` del proyecto.
- Busca issues abiertos para evitar duplicados; si tienes una idea, abre un _issue_ describiendo el problema o la mejora.

## Flujo de trabajo recomendado
1. Haz fork del repositorio y crea una rama descriptiva desde `main`:
   ```bash
   git checkout -b feat/mi-mejora
   ```
2. Asegúrate de que tus cambios son pequeños, con un único propósito cada PR.
3. Incluye pruebas cuando sea posible o un ejemplo de uso que reproduzca el problema que solucionas.
4. Formatea y lint: sigue **PEP8** para Python (puedes usar `flake8`).
5. Envía un Pull Request (PR) hacia `main` con una descripción clara del cambio, por qué es necesario y cómo probarlo.

## Estilo de commits
- Usa mensajes descriptivos en inglés o español. Ejemplos:
  - `fix: corregir validación de tmdb id`
  - `feat: añadir comprobación --deep-debug`
  - `docs: actualizar README.md con sección Primeros Pasos`

## Pruebas y CI
- El proyecto integra GitHub Actions que ejecutan `flake8` y `pytest`.
- Añade tests en `tests/` si introduces lógica que pueda romperse.

## Revisión de PRs
- Sé paciente: los mantenedores revisarán y comentarán los cambios. Responde a los comentarios y actualiza tu PR.
- Si la revisión requiere cambios, hazlos en la misma rama y empuja `git push` para que se actualice el PR.

## Contribuciones en español
- Las contribuciones en español están bienvenidas; intenta mantener la terminología técnica en inglés cuando sea la práctica común (nombres de opciones, flags, API keys, etc.).

## Contacto
- Si tu contribución incluye contenido sensible o requiere comunicación privada, abre un issue etiquetado como privado o contacta a los mantenedores según lo indicado en `CODE_OF_CONDUCT.md`.

¡Gracias por ayudar a mejorar Uploadrr!