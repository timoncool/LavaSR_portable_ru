"""
LavaSR Portable — Улучшение и суперразрешение аудио
Портативная русская версия

Авторы:
@Nerual Dreaming - портативная версия, русификация
Нейро-Софт (t.me/neuroport) - репаки и портативки полезных нейросетей
Оригинальная модель: LavaSR (Yatharth Sharma)
"""

import os
import sys
import time
import glob as glob_module
import datetime
from pathlib import Path

# ============================================================
# Windows: патч файлового ввода-вывода с повторными попытками
# Решает проблему блокировки файлов антивирусами на Windows
# ============================================================
if sys.platform == "win32":
    import functools

    def _retry_open(original_open):
        @functools.wraps(original_open)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(20):
                try:
                    return await original_open(*args, **kwargs)
                except PermissionError as e:
                    last_error = e
                    delay = 0.2 * (1.2 ** attempt)
                    import asyncio
                    await asyncio.sleep(delay)
            raise last_error
        return wrapper

    try:
        import anyio
        anyio.open_file = _retry_open(anyio.open_file)
    except ImportError:
        pass

    try:
        import aiofiles.threadpool
        aiofiles.threadpool._open = _retry_open(aiofiles.threadpool._open)
    except (ImportError, AttributeError):
        pass

    try:
        import starlette.responses
        starlette.responses.anyio.open_file = _retry_open(starlette.responses.anyio.open_file)
    except (ImportError, AttributeError):
        pass

# ============================================================
# Основные импорты
# ============================================================
import gradio as gr
import torch
import numpy as np
import soundfile as sf

# ============================================================
# Пути
# ============================================================
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
TEMP_DIR = SCRIPT_DIR / "temp"
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Поддерживаемые аудиоформаты
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".wma", ".aac", ".opus", ".webm"}

# ============================================================
# Глобальное состояние
# ============================================================
lava_model = None
model_loading = False
model_load_error = None
batch_stop_flag = False


def get_device():
    """Определение устройства: CUDA или CPU."""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)
        return "cuda", f"{gpu_name} ({vram_mb:.0f} МБ VRAM)"
    return "cpu", "CPU (без GPU)"


def load_model():
    """Загрузка модели LavaSR."""
    global lava_model, model_loading, model_load_error

    if lava_model is not None:
        return "Модель уже загружена."

    if model_loading:
        return "Модель уже загружается, подождите..."

    model_loading = True
    model_load_error = None

    try:
        from LavaSR.model import LavaEnhance2

        device, device_info = get_device()

        lava_model = LavaEnhance2("YatharthS/LavaSR", device)

        model_loading = False
        return f"Модель загружена на {device_info}"

    except Exception as e:
        model_loading = False
        model_load_error = str(e)
        return f"ОШИБКА загрузки модели: {e}"


def _ensure_model():
    """Убеждаемся что модель загружена. Возвращает None или строку ошибки."""
    global lava_model
    if lava_model is None:
        load_model()
        if lava_model is None:
            return f"Не удалось загрузить модель: {model_load_error}"
    return None


def _detect_sample_rate(file_path):
    """Определение частоты дискретизации аудиофайла."""
    import librosa
    return librosa.get_samplerate(file_path)


def _enhance_file(file_path, denoise):
    """Внутренняя функция улучшения одного файла. Возвращает (sr, numpy_int16, detected_sr) или кидает исключение."""
    detected_sr = _detect_sample_rate(file_path)
    input_audio_tensor, actual_sr = lava_model.load_audio(
        file_path, input_sr=detected_sr
    )

    # Автоматическое включение батчинга для длинных файлов (>10 сек на 16кГц)
    num_samples = input_audio_tensor.shape[-1]
    auto_batch = num_samples > 16000 * 10

    output_audio_tensor = lava_model.enhance(
        input_audio_tensor,
        denoise=denoise,
        batch=auto_batch,
    )

    output_np = output_audio_tensor.cpu().numpy().squeeze()
    output_np = (np.clip(output_np, -1.0, 1.0) * 32767).astype(np.int16)

    return 48000, output_np, detected_sr


def _save_wav(filename_stem, sr, audio_int16):
    """Сохранение WAV файла в output/. Возвращает путь."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_stem}_{timestamp}.wav"
    filepath = OUTPUT_DIR / filename

    audio_float = audio_int16.astype(np.float32) / 32767.0
    sf.write(str(filepath), audio_float, sr)

    return filepath


# ============================================================
# Обработка одного файла
# ============================================================
def process_audio(input_file, denoise):
    """Обработка аудио: улучшение и суперразрешение."""
    if input_file is None:
        gr.Warning("Загрузите аудиофайл!")
        return None, None, ""

    err = _ensure_model()
    if err:
        gr.Warning(err)
        return None, None, f"Ошибка: {err}"

    try:
        start_time = time.time()

        detected_sr = _detect_sample_rate(input_file)

        # Загрузка для отображения входа
        input_audio_tensor, _ = lava_model.load_audio(input_file, input_sr=detected_sr)
        input_np = input_audio_tensor.cpu().numpy().squeeze()
        input_np = (np.clip(input_np, -1.0, 1.0) * 32767).astype(np.int16)

        # Улучшение
        out_sr, output_np, _ = _enhance_file(input_file, denoise)

        elapsed = time.time() - start_time
        duration_sec = len(output_np) / out_sr
        device_name = "GPU" if torch.cuda.is_available() else "CPU"

        status = (
            f"Готово за {elapsed:.1f} сек | "
            f"Длительность: {duration_sec:.1f} сек | "
            f"Устройство: {device_name} | "
            f"Вход: {detected_sr} Гц -> Выход: 48000 Гц"
        )

        return (16000, input_np), (out_sr, output_np), status

    except Exception as e:
        gr.Warning(f"Ошибка обработки: {e}")
        return None, None, f"Ошибка: {e}"


def save_audio(enhanced_audio):
    """Сохранение улучшенного аудио в папку output/."""
    if enhanced_audio is None:
        gr.Warning("Нет аудио для сохранения!")
        return "Нет аудио для сохранения."

    try:
        sr, audio_data = enhanced_audio
        filepath = _save_wav("lavasr", sr, audio_data)
        return f"Сохранено: {filepath}"
    except Exception as e:
        return f"Ошибка сохранения: {e}"


# ============================================================
# Микрофон
# ============================================================
def process_microphone(mic_audio, denoise):
    """Обработка аудио с микрофона."""
    if mic_audio is None:
        gr.Warning("Запишите аудио с микрофона!")
        return None, None, ""

    mic_sr, mic_data = mic_audio

    temp_path = TEMP_DIR / "mic_input.wav"
    if mic_data.dtype in (np.int16, np.int32):
        mic_float = mic_data.astype(np.float32) / np.iinfo(mic_data.dtype).max
    else:
        mic_float = mic_data.astype(np.float32)

    if mic_float.ndim > 1:
        mic_float = mic_float.mean(axis=1)

    sf.write(str(temp_path), mic_float, mic_sr)

    return process_audio(str(temp_path), denoise)


# ============================================================
# Пакетная обработка
# ============================================================
def process_batch(files, prefix, denoise):
    """Пакетная обработка списка аудиофайлов. Генератор — yield обновляет лог и плееры в реальном времени."""
    global batch_stop_flag
    batch_stop_flag = False

    if not files:
        gr.Warning("Загрузите аудиофайлы!")
        yield "Файлы не выбраны.", []
        return

    err = _ensure_model()
    if err:
        yield f"Ошибка: {err}", []
        return

    # Создаём подпапку для результатов
    prefix = (prefix or "").strip()
    if not prefix:
        prefix = datetime.datetime.now().strftime("batch_%Y%m%d_%H%M%S")
    prefix = "".join(c for c in prefix if c not in r'\/:*?"<>|')
    batch_output_dir = OUTPUT_DIR / prefix
    batch_output_dir.mkdir(parents=True, exist_ok=True)

    total = len(files)
    log_lines = []
    result_files = []
    success_count = 0
    error_count = 0
    start_total = time.time()
    device_name = "GPU" if torch.cuda.is_available() else "CPU"

    log_lines.append(f"Пакетная обработка: {total} файлов")
    log_lines.append(f"Устройство: {device_name} | Папка: {batch_output_dir}")
    log_lines.append("=" * 50)
    yield "\n".join(log_lines), result_files

    for i, file_path in enumerate(files):
        if batch_stop_flag:
            log_lines.append(f"\nОстановлено пользователем после {i} из {total} файлов.")
            yield "\n".join(log_lines), result_files
            break

        fname = Path(file_path).stem
        log_lines.append(f"\n[{i+1}/{total}] Обработка: {fname}...")
        yield "\n".join(log_lines), result_files

        try:
            start_time = time.time()

            out_sr, output_np, detected_sr = _enhance_file(file_path, denoise)

            out_filename = f"{fname}.wav"
            out_filepath = batch_output_dir / out_filename
            audio_float = output_np.astype(np.float32) / 32767.0
            sf.write(str(out_filepath), audio_float, out_sr)

            elapsed = time.time() - start_time
            duration_sec = len(output_np) / out_sr
            success_count += 1

            # Добавляем файл в список результатов для плееров
            result_files.append(str(out_filepath))

            log_lines[-1] = (
                f"[{i+1}/{total}] {fname} -> {out_filename} "
                f"({detected_sr} Гц -> 48000 Гц, {duration_sec:.1f} сек, за {elapsed:.1f} сек)"
            )
            yield "\n".join(log_lines), result_files

        except Exception as e:
            error_count += 1
            log_lines[-1] = f"[{i+1}/{total}] {fname}: ОШИБКА - {e}"
            yield "\n".join(log_lines), result_files

    elapsed_total = time.time() - start_total
    log_lines.append("\n" + "=" * 50)
    log_lines.append(
        f"Готово: {success_count} успешно, {error_count} ошибок "
        f"из {total} файлов за {elapsed_total:.1f} сек"
    )
    log_lines.append(f"Результаты: {batch_output_dir}")
    yield "\n".join(log_lines), result_files


def stop_batch():
    """Остановка пакетной обработки."""
    global batch_stop_flag
    batch_stop_flag = True
    return "Останавливаем после текущего файла..."


# ============================================================
# Gradio UI — Тёмная тема
# ============================================================
theme = gr.themes.Base(
    primary_hue=gr.themes.colors.blue,
    secondary_hue=gr.themes.colors.slate,
    neutral_hue=gr.themes.colors.slate,
    font=gr.themes.GoogleFont("Inter"),
).set(
    body_background_fill="#0f1117",
    body_background_fill_dark="#0f1117",
    block_background_fill="#1a1b26",
    block_background_fill_dark="#1a1b26",
    block_border_color="#2a2b3d",
    block_border_color_dark="#2a2b3d",
    block_label_background_fill="#1a1b26",
    block_label_background_fill_dark="#1a1b26",
    block_title_text_color="#c0caf5",
    block_title_text_color_dark="#c0caf5",
    body_text_color="#a9b1d6",
    body_text_color_dark="#a9b1d6",
    input_background_fill="#24283b",
    input_background_fill_dark="#24283b",
    input_border_color="#414868",
    input_border_color_dark="#414868",
    button_primary_background_fill="#7aa2f7",
    button_primary_background_fill_dark="#7aa2f7",
    button_primary_text_color="#1a1b26",
    button_primary_text_color_dark="#1a1b26",
    button_secondary_background_fill="#414868",
    button_secondary_background_fill_dark="#414868",
    button_secondary_text_color="#c0caf5",
    button_secondary_text_color_dark="#c0caf5",
)

_, device_info_str = get_device()

APP_CSS = """
    .status-bar {
        padding: 8px 12px;
        border-radius: 6px;
        background: #24283b;
        color: #7aa2f7;
        font-family: monospace;
    }
    footer { display: none !important; }
"""

with gr.Blocks(title="LavaSR — Улучшение аудио") as demo:

    gr.Markdown(
        f"# LavaSR — Улучшение и суперразрешение аудио\n"
        f"Ультрабыстрая модель улучшения речи: шумоподавление + повышение частоты дискретизации до 48 кГц. "
        f"Устройство: **{device_info_str}**"
    )
    gr.Markdown(
        "Собрал [Nerual Dreaming](https://t.me/nerual_dreming) — основатель "
        "[ArtGeneration.me](https://artgeneration.me/), техноблогер и нейро-евангелист."
    )
    gr.Markdown(
        "Канал [Нейро-Софт](https://t.me/neuroport) — репаки и портативки полезных нейросетей"
    )

    with gr.Tabs():
        # ============================
        # Вкладка: Загрузка файла
        # ============================
        with gr.TabItem("Загрузка файла"):
            with gr.Row():
                with gr.Column(scale=1):
                    input_audio = gr.Audio(
                        type="filepath",
                        label="Входное аудио",
                        sources=["upload"],
                    )

                    with gr.Accordion("Настройки", open=True):
                        denoise_toggle = gr.Checkbox(
                            label="Очистить запись от шума",
                            value=False,
                            info="Удаление фонового шума из аудио.",
                        )

                    enhance_btn = gr.Button(
                        "Улучшить аудио",
                        variant="primary",
                        size="lg",
                    )

                with gr.Column(scale=1):
                    resampled_output = gr.Audio(
                        label="Исходное аудио (16 кГц)",
                        interactive=False,
                    )
                    enhanced_output = gr.Audio(
                        label="Улучшенное аудио (48 кГц)",
                        interactive=False,
                    )

                    with gr.Row():
                        save_btn = gr.Button(
                            "Сохранить результат",
                            variant="secondary",
                        )

                    status_text = gr.Textbox(
                        label="Статус",
                        interactive=False,
                        elem_classes=["status-bar"],
                    )
                    save_status = gr.Textbox(
                        label="Сохранение",
                        interactive=False,
                    )

            enhance_btn.click(
                fn=process_audio,
                inputs=[input_audio, denoise_toggle],
                outputs=[resampled_output, enhanced_output, status_text],
            )

            save_btn.click(
                fn=save_audio,
                inputs=[enhanced_output],
                outputs=[save_status],
            )

        # ============================
        # Вкладка: Микрофон
        # ============================
        with gr.TabItem("Микрофон"):
            with gr.Row():
                with gr.Column(scale=1):
                    mic_input = gr.Audio(
                        sources=["microphone"],
                        label="Запись с микрофона",
                    )

                    with gr.Accordion("Настройки", open=True):
                        mic_denoise = gr.Checkbox(
                            label="Очистить запись от шума",
                            value=True,
                            info="Рекомендуется для записи с микрофона.",
                        )

                    mic_enhance_btn = gr.Button(
                        "Улучшить запись",
                        variant="primary",
                        size="lg",
                    )

                with gr.Column(scale=1):
                    mic_resampled = gr.Audio(
                        label="Исходная запись (16 кГц)",
                        interactive=False,
                    )
                    mic_enhanced = gr.Audio(
                        label="Улучшенная запись (48 кГц)",
                        interactive=False,
                    )

                    with gr.Row():
                        mic_save_btn = gr.Button(
                            "Сохранить результат",
                            variant="secondary",
                        )

                    mic_status = gr.Textbox(
                        label="Статус",
                        interactive=False,
                        elem_classes=["status-bar"],
                    )
                    mic_save_status = gr.Textbox(
                        label="Сохранение",
                        interactive=False,
                    )

            mic_enhance_btn.click(
                fn=process_microphone,
                inputs=[mic_input, mic_denoise],
                outputs=[mic_resampled, mic_enhanced, mic_status],
            )

            mic_save_btn.click(
                fn=save_audio,
                inputs=[mic_enhanced],
                outputs=[mic_save_status],
            )

        # ============================
        # Вкладка: Пакетная обработка
        # ============================
        with gr.TabItem("Пакетная обработка"):
            gr.Markdown(
                "Выберите несколько аудиофайлов — они будут обработаны по очереди "
                "и сохранены в подпапку `output/<префикс>/`."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    batch_files = gr.File(
                        label="Аудиофайлы",
                        file_count="multiple",
                        file_types=[".wav", ".mp3", ".flac", ".ogg", ".m4a", ".wma", ".aac", ".opus", ".webm"],
                        type="filepath",
                    )

                    with gr.Accordion("Настройки", open=True):
                        batch_prefix = gr.Textbox(
                            label="Имя папки для результатов",
                            value="",
                            placeholder="podcast_cleaned",
                            info="Результаты сохранятся в output/<имя>/. Если пусто — создастся по дате.",
                        )
                        batch_denoise = gr.Checkbox(
                            label="Очистить запись от шума",
                            value=False,
                        )

                    with gr.Row():
                        batch_start_btn = gr.Button(
                            "Обработать все",
                            variant="primary",
                            size="lg",
                        )
                        batch_stop_btn = gr.Button(
                            "Остановить",
                            variant="stop",
                            size="lg",
                        )

                with gr.Column(scale=1):
                    batch_log = gr.Textbox(
                        label="Лог обработки",
                        interactive=False,
                        lines=15,
                        max_lines=40,
                        elem_classes=["status-bar"],
                    )

                    gr.Markdown("**Результаты — прослушивание:**")
                    batch_results_state = gr.State([])

                    @gr.render(inputs=[batch_results_state])
                    def render_batch_players(file_list):
                        if not file_list:
                            return
                        for fp in file_list:
                            gr.Audio(
                                value=fp,
                                label=Path(fp).stem,
                                interactive=False,
                            )

            batch_start_btn.click(
                fn=process_batch,
                inputs=[batch_files, batch_prefix, batch_denoise],
                outputs=[batch_log, batch_results_state],
            )

            batch_stop_btn.click(
                fn=stop_batch,
                outputs=[batch_log],
            )

    # ============================
    # Информация
    # ============================
    gr.Markdown(
        """
        ---
        **Возможности:**
        - Повышение частоты дискретизации (8-48 кГц -> 48 кГц)
        - Шумоподавление (удаление фонового шума из речи)
        - Пакетная обработка множества файлов
        - ~5000x реального времени на GPU, ~60x на CPU
        - Размер модели: ~50 МБ, ~500 МБ VRAM

        **Поддерживаемые форматы:** WAV, MP3, FLAC, OGG, M4A, WMA, AAC, OPUS, WEBM
        """
    )


# ============================================================
# Запуск
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  LavaSR Portable — Улучшение и суперразрешение аудио")
    print("=" * 60)
    print()
    print(f"Устройство: {device_info_str}")
    print("Загрузка модели...")

    load_status = load_model()
    print(load_status)
    print()

    demo.queue(default_concurrency_limit=2).launch(
        server_name="127.0.0.1",
        server_port=None,
        share=False,
        show_error=True,
        inbrowser=True,
        theme=theme,
        css=APP_CSS,
    )
