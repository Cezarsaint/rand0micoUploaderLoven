# hf_batch_uploader.py (versão simplificada)

import os
import datetime
import zipfile
import json
from huggingface_hub import HfApi
from server import PromptServer

class HuggingFaceSimpleUploader: # <--- MODIFICADO: Nome da classe para clareza
    """
    Um node ComfyUI que monitora uma ÚNICA pasta de imagens, cria um arquivo .zip em lotes
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
                # <--- MODIFICADO: Nome do input para refletir a pasta única
                "input_folder": ("STRING", {"multiline": False, "default": "D:/ComfyUI/output/MyCharacter"}),
                "hf_token": ("STRING", {"multiline": True, "default": ""}),
                "repo_id": ("STRING", {"multiline": False, "default": "username/repo-name"}),
                "upload_every_x_images": ("INT", {"default": 50, "min": 1, "max": 10000, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
            # <--- REMOVIDO: Os inputs opcionais de imagem não são mais necessários
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "execute"
    CATEGORY = "IO" # Você pode querer mudar para "IO/Uploaders" ou algo assim

    def get_sorted_image_files(self, directory):
        """Retorna uma lista de arquivos de imagem (.png, .jpg, .jpeg, .webp) ordenados numericamente."""
        supported_extensions = {".png", ".jpg", ".jpeg", ".webp"}
        files = [f for f in os.listdir(directory) if os.path.splitext(f)[1].lower() in supported_extensions]
        # Ordena os arquivos com base nos números contidos em seus nomes
        files.sort(key=lambda f: int("".join(filter(str.isdigit, os.path.splitext(f)[0])) or 0))
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

    # <--- REMOVIDO: A função find_file_by_base_name não é mais necessária

    # <--- MODIFICADO: A assinatura da função agora usa 'input_folder'
    def execute(self, input_folder, hf_token, repo_id, upload_every_x_images, seed, prompt=None, extra_pnginfo=None):
        """Lógica principal do node."""
        if not hf_token or not repo_id or repo_id == "username/repo-name":
            return ("Token ou Repo ID do Hugging Face não fornecido. Pulando upload.",)

        # <--- MODIFICADO: Verifica se o diretório de entrada existe
        if not os.path.isdir(input_folder):
            return (f"ERRO: A pasta de entrada '{input_folder}' não existe.",)

        # <--- REMOVIDO: A verificação de subpastas foi completamente removida

        # <--- MODIFICADO: O arquivo de log agora fica diretamente na pasta de entrada
        log_file = os.path.join(input_folder, ".upload_log.json")
        uploaded_files_log = self.load_upload_log(log_file)
        
        # <--- MODIFICADO: Busca arquivos diretamente na pasta de entrada
        all_image_files = self.get_sorted_image_files(input_folder)
        new_files_to_process = [f for f in all_image_files if f not in uploaded_files_log]

        print(f"[HF Uploader] Status: {len(uploaded_files_log)} arquivos já upados. {len(new_files_to_process)} novos arquivos encontrados.")

        if len(new_files_to_process) < upload_every_x_images:
            status_msg = f"Aguardando... {len(new_files_to_process)}/{upload_every_x_images} novas imagens para o próximo lote."
            print(f"[HF Uploader] {status_msg}")
            return (status_msg,)

        # <--- MODIFICADO: O lote agora é formado pelos arquivos diretamente
        files_for_batch = new_files_to_process[:upload_every_x_images]
        
        folder_name = os.path.basename(os.path.normpath(input_folder))
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y")
        zip_filename = f"{folder_name}_{timestamp}_{len(uploaded_files_log)}_to_{len(uploaded_files_log) + len(files_for_batch)}.zip"
        zip_filepath = os.path.join(input_folder, zip_filename)

        print(f"[HF Uploader] Criando lote: {zip_filename} com {len(files_for_batch)} imagens.")
        
        status_msg = ""
        try:
            # <--- MODIFICADO: Lógica de criação do ZIP muito mais simples
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                for filename_to_add in files_for_batch:
                    full_file_path = os.path.join(input_folder, filename_to_add)
                    # Adiciona o arquivo ao zip usando apenas seu nome, sem caminho de pasta
                    zf.write(full_file_path, arcname=filename_to_add)
            
            print(f"[HF Uploader] Fazendo upload de '{zip_filename}' para o repositório '{repo_id}'...")
            api = HfApi(token=hf_token)
            api.upload_file(
                path_or_fileobj=zip_filepath,
                path_in_repo=zip_filename,
                repo_id=repo_id,
                repo_type="model", # ou "dataset" se preferir
            )
            
            # <--- MODIFICADO: Atualiza o log com os nomes de arquivo do lote atual
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
