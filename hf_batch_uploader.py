# hf_batch_uploader_simplified.py

import os
import datetime
import zipfile
import json
from huggingface_hub import HfApi
from server import PromptServer

class HuggingFaceBatchUploader:
    """
    ## MODIFICADO ##
    Um node ComfyUI que monitora uma pasta de imagens, cria um arquivo .zip em lotes
    e faz o upload para um repositório Hugging Face.
    """
    
    OUTPUT_NODE = True

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        """Define os tipos de input que o node aceita no frontend do ComfyUI."""
        return {
            "required": {
                ## MODIFICADO: Renomeado de 'base_folder' para 'upload_folder' para maior clareza
                "upload_folder": ("STRING", {"multiline": False, "default": "D:/ComfyUI/output/MyCharacter"}),
                "hf_token": ("STRING", {"multiline": True, "default": ""}),
                "repo_id": ("STRING", {"multiline": False, "default": "username/repo-name"}),
                "upload_every_x_images": ("INT", {"default": 50, "min": 1, "max": 10000, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
            "optional": {
                ## MODIFICADO: Simplificado para um único input de imagem que age como trigger
                "image_trigger": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "execute"
    CATEGORY = "IO"

    def get_sorted_image_files(self, directory):
        """Retorna uma lista de arquivos de imagem (.png, .jpg, .jpeg, .webp) ordenados numericamente."""
        supported_extensions = {".png", ".jpg", ".jpeg", ".webp"}
        files = [f for f in os.listdir(directory) if os.path.splitext(f)[1].lower() in supported_extensions]
        # Filtra o próprio arquivo de log para não ser incluído na contagem de imagens
        files = [f for f in files if f != ".upload_log.json"]
        files.sort(key=lambda f: int("".join(filter(str.isdigit, f)) or 0))
        return files

    def load_upload_log(self, log_path):
        """Carrega a lista de arquivos já enviados de um arquivo de log JSON."""
        if not os.path.exists(log_path):
            return set()
        try:
            with open(log_path, 'r') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()

    def save_upload_log(self, log_path, uploaded_files_set):
        """Salva a lista atualizada de arquivos enviados para o log JSON."""
        with open(log_path, 'w') as f:
            json.dump(list(uploaded_files_set), f, indent=4)
            
    ## REMOVIDO: A função 'find_file_by_base_name' não é mais necessária ##

    ## MODIFICADO: A assinatura e a lógica da função foram simplificadas ##
    def execute(self, upload_folder, hf_token, repo_id, upload_every_x_images, seed, prompt=None, extra_pnginfo=None, image_trigger=None):
        """Lógica principal do node."""
        if not hf_token or not repo_id or repo_id == "username/repo-name":
            return ("Token ou Repo ID do Hugging Face não fornecido. Pulando upload.",)

        if not os.path.isdir(upload_folder):
            return (f"ERRO: A pasta de upload '{upload_folder}' não existe.",)

        ## REMOVIDO: Verificação de subpastas não é mais necessária ##

        log_file = os.path.join(upload_folder, ".upload_log.json")
        uploaded_files_log = self.load_upload_log(log_file)
        
        all_files_in_folder = self.get_sorted_image_files(upload_folder)
        new_files_to_process = [f for f in all_files_in_folder if f not in uploaded_files_log]

        print(f"[HF Uploader] Status: {len(uploaded_files_log)} arquivos já upados. {len(new_files_to_process)} novos arquivos encontrados em '{upload_folder}'.")

        if len(new_files_to_process) < upload_every_x_images:
            status_msg = f"Aguardando... {len(new_files_to_process)}/{upload_every_x_images} novas imagens para o próximo lote."
            print(f"[HF Uploader] {status_msg}")
            return (status_msg,)

        files_for_batch = new_files_to_process[:upload_every_x_images]
        
        folder_name = os.path.basename(os.path.normpath(upload_folder))
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y")
        zip_filename = f"{folder_name}_{timestamp}_{len(uploaded_files_log)}_to_{len(uploaded_files_log) + len(files_for_batch)}.zip"
        
        # Salva o zip na pasta pai da pasta de upload para não ser incluído em futuras varreduras
        parent_dir = os.path.dirname(os.path.normpath(upload_folder))
        zip_filepath = os.path.join(parent_dir, zip_filename)
        
        print(f"[HF Uploader] Criando lote: {zip_filename} com {len(files_for_batch)} imagens.")
        
        status_msg = ""
        try:
            # Lógica de zipping simplificada
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                for filename in files_for_batch:
                    file_path = os.path.join(upload_folder, filename)
                    # Adiciona o arquivo à raiz do zip
                    zf.write(file_path, arcname=filename)
            
            print(f"[HF Uploader] Fazendo upload de '{zip_filename}' para o repositório '{repo_id}'...")
            api = HfApi(token=hf_token)
            api.upload_file(
                path_or_fileobj=zip_filepath,
                path_in_repo=zip_filename,
                repo_id=repo_id,
                repo_type="model", # ou "dataset" se preferir
            )
            
            uploaded_files_log.update(files_for_batch)
            self.save_upload_log(log_file, uploaded_files_log)
            
            status_msg = f"Sucesso! Upload de '{zip_filename}' concluído."
            print(f"[HF Uploader] {status_msg}")

        except Exception as e:
            status_msg = f"ERRO durante o processo de upload: {e}"
            print(f"[HF Uploader] {status_msg}")
            return (status_msg,)
        finally:
            if os.path.exists(zip_filepath) and status_msg.startswith("Sucesso"):
                os.remove(zip_filepath)
                print(f"[HF Uploader] Arquivo ZIP local '{zip_filename}' removido.")

        return (status_msg,)

