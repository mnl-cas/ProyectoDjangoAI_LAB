"""Comprueba que el modelo CLIP se puede cargar. Uso: python verificar_clip.py"""
if __name__ == "__main__":
    print("Iniciando script...", flush=True)
    from sentence_transformers import SentenceTransformer
    print("Librería importada correctamente.", flush=True)
    print("Cargando 'clip-ViT-B-32' (la primera vez descarga el modelo)...", flush=True)
    SentenceTransformer("clip-ViT-B-32")
    print("¡CLIP cargado correctamente!", flush=True)
