"""Translation catalog.

Every string the user reads lives here, in Brazilian Portuguese and English.
Code, comments and identifiers stay in English; only these values are
localized. Lookup falls back to the key itself so a missing entry is obvious
during development instead of crashing at runtime.
"""

from __future__ import annotations

from typing import Final

PT_BR: Final = "pt-BR"
EN: Final = "en"

LANGUAGE_NAMES: Final[dict[str, str]] = {PT_BR: "Português (BR)", EN: "English"}

_CATALOG: Final[dict[str, dict[str, str]]] = {
    PT_BR: {
        # --- shell -------------------------------------------------------
        "app.name": "Transcriber",
        "app.eyebrow": "áudio para texto",
        "app.title": "transcriber",
        "app.tagline": "seu áudio vira texto aqui dentro. nada sai do computador.",
        "footer.privacy": "Transcrição realizada localmente no seu computador.",
        "footer.first_run": (
            "Na primeira vez que um modelo é usado ele precisa ser baixado (requer "
            "internet). Depois disso ele fica salvo no seu computador e as "
            "transcrições rodam offline."
        ),
        # --- queue -------------------------------------------------------
        "queue.label": "fila de áudios",
        "queue.add": "Adicionar áudios",
        "queue.remove_selected": "Remover selecionado",
        "queue.remove_done": "Remover concluídos",
        "queue.clear": "Limpar fila",
        "queue.column.file": "arquivo",
        "queue.column.state": "estado",
        "queue.column.time": "tempo",
        "queue.added": "{added} áudio(s) na fila",
        "queue.ignored": "{ignored} ignorado(s) por formato ou repetição",
        "queue.empty": "nenhum arquivo na fila",
        "queue.busy": "Aguarde o fim do lote para mexer na fila.",
        # --- job states --------------------------------------------------
        "state.pending": "na fila",
        "state.running": "transcrevendo",
        "state.done": "concluído",
        "state.error": "erro",
        "state.cancelled": "cancelado",
        "count.done": "{count} concluído(s)",
        "count.error": "{count} com erro",
        "count.cancelled": "{count} cancelado(s)",
        "count.running": "{count} transcrevendo",
        "count.pending": "{count} na fila",
        # --- options -----------------------------------------------------
        "options.language": "idioma",
        "options.model": "modelo",
        "options.parallel": "simultâneas",
        "options.interface": "interface",
        "options.gpu": "gpu",
        "gpu.use": "usar CUDA",
        "workers.queue": "1 · fila",
        "workers.parallel": "{count} · paralelo",
        "language.auto": "Automático",
        "language.pt": "Português",
        "language.en": "Inglês",
        "language.es": "Espanhol",
        "warn.parallel_heavy": (
            "{workers} transcrições simultâneas com o modelo {model} pedem muita "
            "memória e não aceleram em CPU — prefira 1 · fila."
        ),
        "warn.parallel_cpu": (
            "Em CPU o ganho do paralelo é pequeno: o motor já usa todos os núcleos "
            "em um arquivo só."
        ),
        "hint.download": "O modelo {model} ainda não está no computador: o primeiro uso baixa {size}.",
        # --- actions -----------------------------------------------------
        "action.transcribe": "Transcrever",
        "action.cancel": "Cancelar",
        "result.label": "transcrição",
        "result.empty_title": "nenhuma transcrição ainda",
        "result.empty_body": "adicione um ou mais áudios e a linha começa a andar.",
        "action.copy": "Copiar texto",
        "action.save_txt": "Salvar TXT",
        "action.save_srt": "Salvar SRT",
        "action.save_all": "Salvar todos",
        "action.open_folder": "Abrir pasta",
        "action.clear": "Limpar",
        # --- status ------------------------------------------------------
        "status.ready": "pronto.",
        "status.preparing": "preparando...",
        "status.loading_model": "Carregando modelo {model} ({device})...",
        "status.analyzing": "Analisando o áudio...",
        "status.transcribing_pct": "Transcrevendo... {percent}",
        "status.transcribing_count": "Transcrevendo... {count} trechos",
        "status.transcribing_file": "transcrevendo {name}",
        "status.gpu_fallback": "Problema com a GPU — refazendo na CPU...",
        "status.finished": "Concluído.",
        "status.cancelling": "cancelando...",
        "status.cancelled": "Transcrição cancelada.",
        "status.copied": "texto copiado.",
        "status.saved": "salvo em {path}",
        "status.saved_many": "{count} arquivo(s) salvos em {path}",
        # --- dialogs -----------------------------------------------------
        "dialog.pick_audio": "Adicionar áudios",
        "dialog.audio_files": "Arquivos de áudio",
        "dialog.all_files": "Todos os arquivos",
        "dialog.save": "Salvar {kind}",
        "dialog.save_all": "Salvar todos em",
        "dialog.kind_text": "Texto",
        "dialog.kind_subtitle": "Legenda",
        "dialog.need_queue": "Adicione pelo menos um áudio à fila antes de transcrever.",
        "dialog.need_selection": "Selecione um áudio da fila primeiro.",
        "dialog.cannot_remove_running": "Este áudio está sendo transcrito agora.",
        "dialog.nothing_to_save": "Não há nada para salvar ainda.",
        "dialog.nothing_done": "Nenhuma transcrição concluída para exportar.",
        "dialog.busy_clear": "Aguarde o fim da transcrição para limpar.",
        "dialog.confirm_close": "Uma transcrição está em andamento. Deseja fechar mesmo assim?",
        # --- summary -----------------------------------------------------
        "summary.file": "Arquivo: {name}",
        "summary.language": "Idioma detectado: {language}",
        "summary.confidence": " — confiança {value}",
        "summary.model": "Modelo: {model}",
        "summary.device": "Dispositivo: {device}",
        "summary.duration": "Duração do áudio: {duration}",
        "summary.elapsed": "Tempo de processamento: {seconds} segundos",
        "summary.short": "{duration} de áudio · {seconds}s · {model} · {device}",
        "summary.unknown_language": "não identificado",
        # --- errors ------------------------------------------------------
        "error.no_file": "Nenhum arquivo de áudio foi selecionado.",
        "error.not_found": "O arquivo não foi encontrado:\n{path}",
        "error.not_found.hint": "Ele pode ter sido movido, renomeado ou excluído.",
        "error.not_a_file": "O caminho não é um arquivo:\n{path}",
        "error.unsupported": "Formato não suportado: {suffix}",
        "error.unsupported.hint": "Formatos aceitos: {formats}",
        "error.unreadable": "Não foi possível ler o arquivo:\n{path}",
        "error.empty_file": "O arquivo de áudio está vazio (0 bytes).",
        "error.no_extension": "(sem extensão)",
        "error.missing_library": "A biblioteca faster-whisper não está instalada.",
        "error.missing_library.hint": (
            "Ative o ambiente virtual e rode: pip install -r requirements.txt"
        ),
        "error.out_of_memory": "Memória insuficiente para o modelo '{model}'.",
        "error.out_of_memory.hint": (
            "Escolha um modelo menor (small ou base) e feche outros programas."
        ),
        "error.download": "Não foi possível baixar o modelo '{model}'.",
        "error.download.hint": (
            "O primeiro uso de cada modelo exige conexão com a internet. "
            "Verifique a rede e tente novamente."
        ),
        "error.model_not_found": "O modelo '{model}' não foi encontrado.",
        "error.model_not_found.hint": (
            "Escolha um dos modelos da lista (tiny, base, small, medium, large-v3)."
        ),
        "error.cuda": "A GPU (CUDA) não pôde ser usada.",
        "error.cuda.hint": (
            "A transcrição pode ser feita na CPU — desmarque a opção de GPU."
        ),
        "error.audio_decode": "Não foi possível ler o áudio deste arquivo.",
        "error.audio_decode.hint": (
            "Confirme se o arquivo não está corrompido ou aberto em outro programa."
        ),
        "error.load_failed": "Falha ao carregar o modelo: {kind}.",
        "error.transcribe_failed": "Falha ao transcrever o áudio: {kind}.",
        "error.log_hint": "Detalhes técnicos foram gravados em transcriber.log.",
        "error.no_speech": "Nenhuma fala foi encontrada neste áudio.",
        "error.no_speech.hint": (
            "O arquivo pode conter só silêncio, música ou ruído. "
            "Tente outro arquivo ou um modelo maior."
        ),
        "error.cancelled": "Transcrição cancelada pelo usuário.",
        "error.unexpected": "Erro inesperado durante a transcrição.",
        "error.unexpected.detail": "Erro inesperado: {kind}.",
        "error.start_failed": "Não foi possível iniciar a transcrição.",
        "error.save_failed": "Não foi possível salvar o arquivo.",
        "error.save_failed.detail": "Não foi possível salvar em:\n{path}\n\n{reason}",
        "error.save_some_failed": "Alguns arquivos não puderam ser salvos.",
        "error.save_some_failed.detail": "{count} arquivo(s) gravado(s).\n\nFalhas:\n{failures}",
        "error.open_folder": "Não foi possível abrir a pasta.",
        "error.open_folder.detail": "Não foi possível abrir:\n{path}\n\n{reason}",
        "error.no_gui": (
            "Não foi possível iniciar a interface gráfica.\n"
            "Detalhe: {detail}\n"
            "No Linux instale o Tkinter (ex.: sudo apt install python3-tk)."
        ),
        "error.fatal": (
            "A aplicação encontrou um erro inesperado. "
            "Consulte transcriber.log para os detalhes."
        ),
    },
    EN: {
        # --- shell -------------------------------------------------------
        "app.name": "Transcriber",
        "app.eyebrow": "audio to text",
        "app.title": "transcriber",
        "app.tagline": "your audio becomes text in here. nothing leaves the computer.",
        "footer.privacy": "Transcription runs locally on your computer.",
        "footer.first_run": (
            "The first time a model is used it has to be downloaded (needs internet). "
            "After that it stays on your computer and transcriptions run offline."
        ),
        # --- queue -------------------------------------------------------
        "queue.label": "audio queue",
        "queue.add": "Add audio",
        "queue.remove_selected": "Remove selected",
        "queue.remove_done": "Remove finished",
        "queue.clear": "Clear queue",
        "queue.column.file": "file",
        "queue.column.state": "state",
        "queue.column.time": "time",
        "queue.added": "{added} audio file(s) queued",
        "queue.ignored": "{ignored} skipped (unsupported format or duplicate)",
        "queue.empty": "no files in the queue",
        "queue.busy": "Wait for the batch to finish before changing the queue.",
        # --- job states --------------------------------------------------
        "state.pending": "queued",
        "state.running": "transcribing",
        "state.done": "done",
        "state.error": "error",
        "state.cancelled": "cancelled",
        "count.done": "{count} done",
        "count.error": "{count} failed",
        "count.cancelled": "{count} cancelled",
        "count.running": "{count} transcribing",
        "count.pending": "{count} queued",
        # --- options -----------------------------------------------------
        "options.language": "language",
        "options.model": "model",
        "options.parallel": "concurrent",
        "options.interface": "interface",
        "options.gpu": "gpu",
        "gpu.use": "use CUDA",
        "workers.queue": "1 · queue",
        "workers.parallel": "{count} · parallel",
        "language.auto": "Automatic",
        "language.pt": "Portuguese",
        "language.en": "English",
        "language.es": "Spanish",
        "warn.parallel_heavy": (
            "{workers} concurrent transcriptions with the {model} model need a lot of "
            "memory and are no faster on CPU — prefer 1 · queue."
        ),
        "warn.parallel_cpu": (
            "On CPU the gain from running in parallel is small: the engine already "
            "uses every core on a single file."
        ),
        "hint.download": "The {model} model is not on this computer yet: the first run downloads {size}.",
        # --- actions -----------------------------------------------------
        "action.transcribe": "Transcribe",
        "action.cancel": "Cancel",
        "result.label": "transcription",
        "result.empty_title": "no transcription yet",
        "result.empty_body": "add one or more audio files and the line starts moving.",
        "action.copy": "Copy text",
        "action.save_txt": "Save TXT",
        "action.save_srt": "Save SRT",
        "action.save_all": "Save all",
        "action.open_folder": "Open folder",
        "action.clear": "Clear",
        # --- status ------------------------------------------------------
        "status.ready": "ready.",
        "status.preparing": "preparing...",
        "status.loading_model": "Loading {model} model ({device})...",
        "status.analyzing": "Analysing the audio...",
        "status.transcribing_pct": "Transcribing... {percent}",
        "status.transcribing_count": "Transcribing... {count} segments",
        "status.transcribing_file": "transcribing {name}",
        "status.gpu_fallback": "GPU problem — falling back to CPU...",
        "status.finished": "Finished.",
        "status.cancelling": "cancelling...",
        "status.cancelled": "Transcription cancelled.",
        "status.copied": "text copied.",
        "status.saved": "saved to {path}",
        "status.saved_many": "{count} file(s) saved to {path}",
        # --- dialogs -----------------------------------------------------
        "dialog.pick_audio": "Add audio",
        "dialog.audio_files": "Audio files",
        "dialog.all_files": "All files",
        "dialog.save": "Save {kind}",
        "dialog.save_all": "Save all to",
        "dialog.kind_text": "Text",
        "dialog.kind_subtitle": "Subtitle",
        "dialog.need_queue": "Add at least one audio file to the queue first.",
        "dialog.need_selection": "Select an audio file from the queue first.",
        "dialog.cannot_remove_running": "This audio file is being transcribed right now.",
        "dialog.nothing_to_save": "There is nothing to save yet.",
        "dialog.nothing_done": "No finished transcription to export.",
        "dialog.busy_clear": "Wait for the transcription to finish before clearing.",
        "dialog.confirm_close": "A transcription is running. Close anyway?",
        # --- summary -----------------------------------------------------
        "summary.file": "File: {name}",
        "summary.language": "Detected language: {language}",
        "summary.confidence": " — confidence {value}",
        "summary.model": "Model: {model}",
        "summary.device": "Device: {device}",
        "summary.duration": "Audio duration: {duration}",
        "summary.elapsed": "Processing time: {seconds} seconds",
        "summary.short": "{duration} of audio · {seconds}s · {model} · {device}",
        "summary.unknown_language": "not identified",
        # --- errors ------------------------------------------------------
        "error.no_file": "No audio file was selected.",
        "error.not_found": "File not found:\n{path}",
        "error.not_found.hint": "It may have been moved, renamed or deleted.",
        "error.not_a_file": "This path is not a file:\n{path}",
        "error.unsupported": "Unsupported format: {suffix}",
        "error.unsupported.hint": "Accepted formats: {formats}",
        "error.unreadable": "Could not read the file:\n{path}",
        "error.empty_file": "The audio file is empty (0 bytes).",
        "error.no_extension": "(no extension)",
        "error.missing_library": "The faster-whisper library is not installed.",
        "error.missing_library.hint": (
            "Activate the virtual environment and run: pip install -r requirements.txt"
        ),
        "error.out_of_memory": "Not enough memory for the '{model}' model.",
        "error.out_of_memory.hint": (
            "Pick a smaller model (small or base) and close other programs."
        ),
        "error.download": "Could not download the '{model}' model.",
        "error.download.hint": (
            "The first use of each model needs an internet connection. "
            "Check your network and try again."
        ),
        "error.model_not_found": "The '{model}' model was not found.",
        "error.model_not_found.hint": (
            "Pick one of the listed models (tiny, base, small, medium, large-v3)."
        ),
        "error.cuda": "The GPU (CUDA) could not be used.",
        "error.cuda.hint": "Transcription can run on the CPU — untick the GPU option.",
        "error.audio_decode": "Could not read the audio in this file.",
        "error.audio_decode.hint": (
            "Check that the file is not corrupted or open in another program."
        ),
        "error.load_failed": "Failed to load the model: {kind}.",
        "error.transcribe_failed": "Failed to transcribe the audio: {kind}.",
        "error.log_hint": "Technical details were written to transcriber.log.",
        "error.no_speech": "No speech was found in this audio.",
        "error.no_speech.hint": (
            "The file may contain only silence, music or noise. "
            "Try another file or a bigger model."
        ),
        "error.cancelled": "Transcription cancelled by the user.",
        "error.unexpected": "Unexpected error during transcription.",
        "error.unexpected.detail": "Unexpected error: {kind}.",
        "error.start_failed": "Could not start the transcription.",
        "error.save_failed": "Could not save the file.",
        "error.save_failed.detail": "Could not save to:\n{path}\n\n{reason}",
        "error.save_some_failed": "Some files could not be saved.",
        "error.save_some_failed.detail": "{count} file(s) written.\n\nFailures:\n{failures}",
        "error.open_folder": "Could not open the folder.",
        "error.open_folder.detail": "Could not open:\n{path}\n\n{reason}",
        "error.no_gui": (
            "Could not start the graphical interface.\n"
            "Detail: {detail}\n"
            "On Linux install Tkinter (e.g. sudo apt install python3-tk)."
        ),
        "error.fatal": (
            "The application hit an unexpected error. "
            "See transcriber.log for details."
        ),
    },
}

DEFAULT_LANGUAGE: Final = PT_BR
_current = DEFAULT_LANGUAGE


def available_languages() -> tuple[str, ...]:
    return tuple(_CATALOG)


def get_language() -> str:
    return _current


def set_language(code: str) -> None:
    """Switch the interface language. Unknown codes keep the current one."""
    global _current
    if code in _CATALOG:
        _current = code


def t(key: str, **params: object) -> str:
    """Translate ``key`` in the current language, formatting ``params``."""
    template = _CATALOG.get(_current, {}).get(key)
    if template is None:
        template = _CATALOG[DEFAULT_LANGUAGE].get(key, key)
    try:
        return template.format(**params) if params else template
    except (KeyError, IndexError):
        return template
